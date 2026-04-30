@echo off
echo ========================================
echo Configurando entorno virtual Python
echo ========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    echo Por favor instala Python 3.8+ desde python.org
    pause
    exit /b 1
)

echo [1/4] Creando entorno virtual...
python -m venv venv
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)
echo ✓ Entorno virtual creado

echo.
echo [2/4] Activando entorno virtual...
call venv\Scripts\activate.bat
echo ✓ Entorno virtual activado

echo.
echo [3/4] Actualizando pip...
python -m pip install --upgrade pip
echo ✓ Pip actualizado

echo.
echo [4/4] Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Hubo un problema instalando las dependencias
    pause
    exit /b 1
)
echo ✓ Dependencias instaladas

echo.
echo ========================================
echo ✓ Configuracion completada exitosamente
echo ========================================
echo.
echo Para iniciar el servidor, ejecuta: start.bat
echo.
pause
