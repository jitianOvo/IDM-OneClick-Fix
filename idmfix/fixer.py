# -*- coding: utf-8 -*-
import hashlib
import os
import shutil
import subprocess
import sys
import time
import winreg

from . import config
from .notifications import apply_corrupt_notification_fix

NO_WINDOW = 0x08000000

TARGET_KEYS = (
    "registration_flag", "expiry_display_9999", "trial_nag_kill", "counterfeit_guard",
    "tripwire_exit_4D514", "tripwire_exit_66CB9", "tripwire_exit_120B7A", "tripwire_branch_6C7AC",
    "license_popup_525EF", "license_popup_5260D", "license_popup_52670", "license_popup_5271F",
    "license_popup_52795", "license_popup_527B1", "license_popup_527F9", "counterfeit_broadcast_68220",
    "mdata_write_66C99", "mdata_write_120A54", "longtext_popup_75604", "latent_popup_79FF9",
    "registration_dialog_52812", "wrapper_shortcut_A_742E0", "wrapper_shortcut_B_1BE95",
    "download_reg_dialog_94514",
)

HELPERS = ("IDMMsgHost.exe", "IDMIntegrator64.exe", "idmBroker.exe",
           "IEMonitor.exe", "IDMGrHlp.exe", "MediumILStart.exe")

PROCS = ("IDMan.exe", "idmBroker.exe", "IDMIntegrator64.exe", "IEMonitor.exe",
         "IDMGrHlp.exe", "IDMMsgHost.exe", "MediumILStart.exe", "idmupdt.exe", "idmupdt2.exe")


def log(msg=""):
    print(msg, flush=True)


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate():
    import ctypes
    exe = sys.executable
    args = " ".join(['"' + a + '"' for a in sys.argv])
    return ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1) > 32


def run(cmd, timeout=180):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except Exception:
        return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def kill_all():
    for _ in range(3):
        alive = 0
        for name in PROCS:
            r = run(["taskkill", "/F", "/IM", name, "/T"], timeout=30)
            if r is not None and r.returncode == 0:
                alive += 1
        if alive == 0:
            break
        time.sleep(2)
    run(["sc", "stop", "IDMWFP"], timeout=60)
    time.sleep(2)


def unlock_acl(path):
    for p in (path, path + ".bak-original"):
        if os.path.exists(p):
            run(["icacls", p, "/remove:d", "Everyone"])
            run(["icacls", p, "/grant", "*S-1-5-32-544:F"])


def disable_autostart():
    for root, label in ((winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")):
        try:
            with winreg.OpenKey(root, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                winreg.KEY_SET_VALUE | winreg.KEY_READ) as k:
                try:
                    winreg.QueryValueEx(k, "IDMan")
                    winreg.DeleteValue(k, "IDMan")
                    log("   removed Run entry (" + label + ")")
                except FileNotFoundError:
                    pass
        except Exception:
            pass


def neuter_helpers():
    done = []
    for name in HELPERS:
        pth = os.path.join(config.install_dir(), name)
        if os.path.isfile(pth):
            try:
                os.replace(pth, pth + ".off")
                done.append(name)
            except Exception:
                pass
    return done


def restore_helpers(names):
    for name in names:
        pth = os.path.join(config.install_dir(), name)
        if os.path.isfile(pth + ".off"):
            try:
                os.replace(pth + ".off", pth)
            except Exception:
                pass


CORRUPT_FLAG_VA = 0x7893A0


def find_corrupt_gate(pe):
    """Return (offset, old, new) that neutralises the corrupt-dialog gate.

    The gate is `cmp dword ptr [flag], 0` followed by a jump that skips the dialog
    call when the flag is clean. Replacing the two-byte jump with NOPs makes the
    dialog call unconditional, which is the opposite of what is needed. Instead the
    whole compare+jump is turned into NOPs so control always falls through to the
    normal code path.
    """
    flag = CORRUPT_FLAG_VA
    pattern = b"\x83\x3d" + flag.to_bytes(4, "little") + b"\x00\x74"
    hits = []
    start = 0
    while True:
        i = pe.data.find(pattern, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    if len(hits) != 1:
        return None
    off = hits[0]
    old = bytes(pe.data[off:off + len(pattern) + 1])
    new = b"\x90" * len(old)
    return off, old, new


def build_patched(original):
    sys.path.insert(0, config.vendor_dir())
    import idm_engine as engine
    tmpdir = os.path.join(config.root(), "staging")
    os.makedirs(tmpdir, exist_ok=True)
    tmp = os.path.join(tmpdir, "IDMan.exe")
    with open(tmp, "wb") as f:
        f.write(original)
    pe = engine.PE(tmp)
    sites, _ = engine.build_all_sites(pe)
    data = bytearray(pe.data)
    applied = 0
    for site in sites:
        if site.key in TARGET_KEYS:
            data[site.offset:site.offset + len(site.new)] = site.new
            applied += 1

    gate = find_corrupt_gate(pe)
    if gate is not None:
        off, old, new = gate
        data[off:off + len(new)] = new
        applied += 1
        log("   corrupt gate: neutralised at file 0x%X" % off)
    else:
        log("   [warn] corrupt gate not located")

    if applied == 0:
        return None
    try:
        fixed = apply_corrupt_notification_fix(bytes(data))
    except ValueError as error:
        log("   [!] unsupported notification layout: %s" % error)
        return None
    log("   patch sites: %d / %d" % (applied, len(TARGET_KEYS)))
    log("   corrupt notice: disabled; repair page and hourly retry: disabled")
    log("   PE checksum: recalculated")
    return fixed


def swap_in(new_bytes):
    target = config.idman_exe()
    tmp = target + ".new"
    old = target + ".old"
    try:
        with open(tmp, "wb") as f:
            f.write(new_bytes)
    except Exception as e:
        log("  !! write temp failed: %s" % e)
        return False
    try:
        if os.path.exists(old):
            os.remove(old)
    except Exception:
        pass
    try:
        os.replace(target, old)
    except Exception as e:
        log("  !! rename failed: %s" % e)
        return False
    try:
        shutil.copy2(tmp, target)
        os.remove(tmp)
        return True
    except Exception as e:
        log("  !! copy failed: %s" % e)
        try:
            os.replace(old, target)
        except Exception:
            pass
        return False


def lockdown_registry():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\DownloadManager", 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "CheckUpdtVM", 0, winreg.REG_DWORD, 3650)
            winreg.SetValueEx(k, "LstCheck", 0, winreg.REG_SZ, "01/01/38")
            winreg.SetValueEx(k, "LastCheckQU", 0, winreg.REG_DWORD, int(time.time()))
        log("   update timer locked")
    except Exception as e:
        log("   [warn] %s" % e)

    for pth in (os.path.join(os.environ.get("APPDATA", ""), "IDM", "idmupdt.exe"),
                os.path.join(config.install_dir(), "idmupdt.exe"),
                os.path.join(config.install_dir(), "idmupdt2.exe")):
        if os.path.isfile(pth):
            try:
                os.replace(pth, pth + ".bak-fuckidm")
                log("   isolated " + os.path.basename(pth))
            except Exception:
                pass

    run(["netsh", "advfirewall", "firewall", "delete", "rule", "name=FuckIDM-Block-AuthServers"])
    run(["netsh", "advfirewall", "firewall", "add", "rule",
         "name=FuckIDM-Block-AuthServers", "dir=out", "action=block",
         "program=" + config.idman_exe(), "remoteip=67.18.0.0/16",
         "enable=yes", "profile=any"])


def find_original():
    target = config.idman_exe()
    for cand in (target + ".old", target + ".bak-original", target + ".replaced"):
        if os.path.isfile(cand):
            return cand
    return None


def status():
    target = config.idman_exe()
    if not os.path.isfile(target):
        log("IDM      : not installed")
        return 1
    log("IDM      : " + target)
    log("Version  : " + config.idm_version())
    backup = find_original()
    log("Backup   : " + (os.path.basename(backup) if backup else "none"))
    return 0


def install():
    target = config.idman_exe()
    if not os.path.isfile(target):
        log("[!] IDM not found: " + target)
        return 2
    os.makedirs(config.root(), exist_ok=True)

    log("[1/5] checking state")
    original = find_original()
    log("   backup: " + (os.path.basename(original) if original else "none"))
    if original is None:
        log("   no original backup; creating one")
        try:
            shutil.copy2(target, target + ".bak-original")
            original = target + ".bak-original"
        except Exception as e:
            log("[!] cannot create backup: %s" % e)
            return 3

    log("[2/5] building patch")
    with open(original, "rb") as f:
        new_bytes = build_patched(f.read())
    if new_bytes is None:
        log("[!] signature mismatch; unsupported IDM build")
        return 4

    log("[3/5] writing")
    disable_autostart()
    offed = neuter_helpers()
    kill_all()
    unlock_acl(target)
    ok = False
    for attempt in range(1, 4):
        log("   attempt %d/3" % attempt)
        if swap_in(new_bytes):
            ok = True
            break
        kill_all()
        time.sleep(3)
    restore_helpers(offed)
    if not ok:
        log("[!] write failed; reboot and retry")
        return 5

    log("[4/5] locking down")
    unlock_acl(target)
    run(["icacls", target, "/deny", "*S-1-1-0:(WD,DE)"])
    lockdown_registry()

    log("[5/5] done")
    log("   hash: " + sha256(target))
    log("")
    log("[+] IDM is now full version; update prompts disabled")
    try:
        subprocess.Popen([target], cwd=config.install_dir())
    except Exception:
        pass
    return 0
