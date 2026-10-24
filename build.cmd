@echo off
setlocal
set PY=python
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe

echo [*] installing PyInstaller if needed
"%PY%" -m pip install --quiet --upgrade pyinstaller

echo [*] building single-file exe
"%PY%" -m PyInstaller --noconfirm --clean IDMFix.spec

echo [*] done: dist\IDMFix.exe
endlocal