# -*- coding: utf-8 -*-
import os
import sys


def root():
    return os.environ.get("IDMFIX_ROOT", r"C:\IDM-Fix")


def install_dir():
    explicit = os.environ.get("IDMFIX_DIR")
    if explicit:
        return explicit
    return r"C:\Program Files (x86)\Internet Download Manager"


def idman_exe():
    return os.path.join(install_dir(), "IDMan.exe")


def vendor_dir():
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "vendor")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")


def idm_version():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\DownloadManager", 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, "idmvers")
            return str(val)
    except Exception:
        return "unknown"
