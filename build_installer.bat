@echo off
setlocal

REM One-shot build: freeze with PyInstaller, then wrap with Inno Setup.
REM Prereqs: Python 3.11+, Inno Setup 6 installed at the default location.

echo [1/3] Installing/upgrading Python build dependencies...
py -m pip install --upgrade pyinstaller ttkbootstrap matplotlib openpyxl
if errorlevel 1 goto :err

echo [2/3] Building Magazin.exe with PyInstaller...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
py -m PyInstaller --noconfirm --clean magazin.spec
if errorlevel 1 goto :err

echo [3/3] Building MagazinSetup.exe with Inno Setup...
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo ERROR: Inno Setup not found at "%ISCC%".
    echo Install it from https://jrsoftware.org/isdl.php and re-run this script.
    goto :err
)
"%ISCC%" installer.iss
if errorlevel 1 goto :err

echo.
echo Done. Installer: output\MagazinSetup.exe
exit /b 0

:err
echo.
echo Build FAILED.
exit /b 1
