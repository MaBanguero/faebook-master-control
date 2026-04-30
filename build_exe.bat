@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo  YouTube ^& TikTok Master Control - Build EXE
echo ============================================
echo.

REM Limpiar artefactos previos
if exist build (
    echo - Eliminando carpeta build...
    rmdir /s /q build
)
if exist dist (
    echo - Eliminando carpeta dist...
    rmdir /s /q dist
)
echo.

REM Ejecutar PyInstaller
echo - Ejecutando PyInstaller...
python -m PyInstaller YoutubeTiktokMasterControl.spec --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller falló.
    exit /b 1
)

set "DIST_DIR=dist\YoutubeTiktokMasterControl"
if not exist "%DIST_DIR%" (
    echo ERROR: No se encontró %DIST_DIR%.
    exit /b 1
)

REM Asegurar que cloudflared.exe existe
if not exist "cloudflared\cloudflared.exe" (
    echo - Descargando cloudflared.exe...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared\cloudflared.exe'"
    if errorlevel 1 (
        echo ERROR: No se pudo descargar cloudflared.exe
        exit /b 1
    )
)

REM Copiar archivos requeridos
echo - Copiando archivos de cloudflared al dist...
mkdir "%DIST_DIR%\cloudflared" 2>nul
copy /Y "cloudflared\cloudflared.exe" "%DIST_DIR%\cloudflared\" >nul
copy /Y "cloudflared\config.yml" "%DIST_DIR%\cloudflared\" >nul
copy /Y "cloudflared\credentials.json" "%DIST_DIR%\cloudflared\" >nul

echo - Copiando .env...
copy /Y ".env" "%DIST_DIR%\." >nul

echo.
echo ============================================
echo  Build completado correctamente.
echo  Ejecutable: %DIST_DIR%\YoutubeTiktokMasterControl.exe
echo ============================================
exit /b 0
