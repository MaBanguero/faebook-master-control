@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  YouTube & TikTok Master Control - Installer
echo ============================================
echo.

set "DIST_DIR=dist\YoutubeTiktokMasterControl"
set "MAIN_EXE=%DIST_DIR%\YoutubeTiktokMasterControl.exe"

if not exist "%MAIN_EXE%" (
    echo ERROR: No se encontró %MAIN_EXE%.
    echo Ejecuta build_exe.bat primero.
    exit /b 1
)

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo ERROR: Inno Setup no se encuentra en "%ISCC%".
    echo Descárgalo desde https://jrsoftware.org/isdl.php
    exit /b 1
)

"%ISCC%" installer_script.iss
if errorlevel 1 (
    echo ERROR: Falló la creación del instalador.
    exit /b 1
)

echo.
echo Instalador generado en Output\YoutubeTiktokMasterControl_Setup.exe
echo ============================================
exit /b 0
