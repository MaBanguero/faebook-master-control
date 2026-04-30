@echo off
REM Script de inicio para YouTube & TikTok Master Control
REM 1. Limpia servidor ADB anterior
REM 2. Inicia el servidor ADB (puerto 5037 por defecto)
REM 3. Conecta dispositivos de la red
REM 4. Resetea servicios uiautomator2
REM 5. Activa el entorno virtual
REM 6. Ejecuta FastAPI

echo.
echo ============================================================
echo   YOUTUBE / TIKTOK MASTER CONTROL - INICIO COMPLETO
echo ============================================================
echo.

set ANDROID_ADB_SERVER_PORT=5037
set ADB_PATH=adb

REM ===== PASO 0: LIMPIAR SERVIDOR ADB =====
echo [0/4] Limpiando servidor ADB anterior...
%ADB_PATH% kill-server >nul 2>&1
taskkill /f /im adb.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo    ✓ Servidor ADB limpiado
echo.

REM ===== PASO 1: INICIAR SERVIDOR ADB =====
echo [1/4] Iniciando servidor ADB (Puerto %ANDROID_ADB_SERVER_PORT%)...
%ADB_PATH% start-server
if %errorlevel% neq 0 (
    echo ERROR: No se pudo iniciar el servidor ADB
    pause
    exit /b 1
)
echo    ✓ Servidor ADB iniciado
echo.

REM ===== PASO 2: CONECTAR DISPOSITIVOS =====
echo [2/4] Conectando dispositivos 192.168.1.11-30...
for /L %%i in (11,1,30) do (
    echo   - Conectando 192.168.1.%%i:5555
    %ADB_PATH% connect 192.168.1.%%i:5555 >nul 2>&1
)
echo    ✓ Intentos de conexión completados
echo.
timeout /t 2 /nobreak >nul

REM ===== PASO 3: RESETEAR SERVICIOS UIA2 =====
echo [3/4] Reseteando servicios uiautomator2...
python reset_all_devices.py
echo.

REM ===== PASO 4: ACTIVAR VENV E INICIAR SERVER =====
echo [4/4] Activando entorno virtual...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ADVERTENCIA: No se encontró el entorno virtual (venv)
)
echo    ✓ Entorno virtual listo
echo.

echo Iniciando servidor FastAPI...
echo ============================================================
echo   API disponible en http://localhost:8000
echo   Servidor ADB: puerto %ANDROID_ADB_SERVER_PORT%
echo   Presiona Ctrl+C para detener
echo ============================================================
echo.

python main.py

echo.
echo Servidor detenido.
pause

