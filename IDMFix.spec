# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[("vendor/idm_engine.py", "vendor")],
    hiddenimports=["idm_engine"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "email", "html", "http", "xml", "pydoc"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="IDMFix",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    icon=None,
)