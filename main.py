import os
import time
import subprocess
from dotenv import load_dotenv

# Cargar variables de entorno primero
load_dotenv()

# CONFIGURAR PUERTO ADB DESDE .ENV
CUSTOM_ADB_PORT = int(os.getenv('CUSTOM_ADB_PORT', '5037'))
# Esta variable de entorno es crucial para que uiautomator2 y adb sepan qué puerto usar
os.environ['ANDROID_ADB_SERVER_PORT'] = str(CUSTOM_ADB_PORT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.controllers import dispositivo_controller, tareas_controller, facebook_controller, tiktok_controller, instagram_controller
from api.controllers.ai_controller import router as ai_router
from api.utils.adb_custom_server import custom_adb_manager

# En Ubuntu, simplemente usamos "adb". Asegúrate de tenerlo instalado: sudo apt install adb
ADB_EXECUTABLE = "adb"

app = FastAPI(title="YouTube/TikTok Master Control API")

# CORS - Configuración para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar el servidor - Versión Optimizada para Ubuntu"""
    print("")
    print("=" * 60)
    print("🚀 INICIALIZANDO MASTER CONTROL (LINUX/UBUNTU MODE)")
    print("=" * 60)

    # Paso 0: Reiniciar servidor ADB con sintaxis correcta de Linux
    print(f"🔄 Paso 0: Reiniciando servidor ADB en puerto {CUSTOM_ADB_PORT}...")
    try:
        # 1. Matar procesos previos en ese puerto
        subprocess.run([ADB_EXECUTABLE, "-P", str(CUSTOM_ADB_PORT), "kill-server"],
                       capture_output=True, check=False)
        time.sleep(1)

        # 2. Iniciar el servidor
        subprocess.run([ADB_EXECUTABLE, "-P", str(CUSTOM_ADB_PORT), "start-server"],
                       check=True, timeout=10)
        print("✅ Servidor ADB reiniciado correctamente")
    except Exception as e:
        print(f"⚠️ Nota: No se pudo reiniciar ADB (podría no ser necesario): {e}")

    # Paso 1: Resetear servicios UIAutomator2
    print("🔄 Paso 1: Verificando dispositivos y reseteando UIAutomator2...")
    try:
        from reset_all_devices import reset_device, get_connected_devices

        # IMPORTANTE: get_connected_devices debe usar el puerto del .env internamente
        devices = get_connected_devices()
        if devices:
            print(f"   📱 {len(devices)} dispositivo(s) detectado(s)")
            for device_id in devices:
                reset_device(device_id)
            print(f"   ✅ Limpieza de servicios completada")
        else:
            print("   ℹ️ No se detectaron dispositivos por USB/Red")
    except Exception as e:
        print(f"   ⚠️ Error en reset_all_devices: {e}")

    # Paso 2: Iniciar manager de ADB personalizado
    print(f"🔄 Paso 2: Conectando Manager al puerto {CUSTOM_ADB_PORT}...")
    if custom_adb_manager.start_server():
        print("✅ Manager conectado exitosamente")

        # Paso 3: Mostrar dispositivos detectados por el Manager
        print("🔄 Paso 3: Lista final de dispositivos...")
        time.sleep(1)  # Esperar a que el manager refresque la lista
        devices = custom_adb_manager.get_connected_devices(verbose=True)
        if not devices:
            print("⚠️ ADVERTENCIA: La API no ve dispositivos. Revisa permisos USB (udev).")
    else:
        print("❌ ERROR: El custom_adb_manager no pudo iniciar")

    print("=" * 60)
    print("✅ Sistema listo para recibir peticiones")
    print("=" * 60)


# Incluir rutas de la API
app.include_router(dispositivo_controller.router, prefix="/api", tags=["dispositivos"])
app.include_router(tareas_controller.router, prefix="/api", tags=["tareas"])
app.include_router(facebook_controller.router, prefix="/api", tags=["facebook"])
app.include_router(tiktok_controller.router, prefix="/api", tags=["tiktok"])
app.include_router(instagram_controller.router, prefix="/api", tags=["instagram"])
app.include_router(ai_router, prefix="/api", tags=["ia"])


@app.get("/health")
def health_check():
    return {"status": "healthy", "os": "ubuntu/linux"}

# Servir el frontend estático (debe ir al final)
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")