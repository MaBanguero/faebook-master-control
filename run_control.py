import os
import subprocess
import time
import sys
import threading
import yaml
import requests  # Para consultar el Gist
from pathlib import Path

# --- CONFIGURACIÓN ---
# Pega aquí el enlace RAW de tu Gist (ej: https://gist.githubusercontent.com/.../raw/...)
URL_GIST_RAW = "https://gist.github.com/MaBanguero/5777369f688946566d0faac25c6ebb03/raw/17702f1c60c8d56d183ae5b5965e7769f7fce877/gistfile1.txt"


# --- FUNCIONES DE UTILERÍA ---
def get_paths():
    """Obtiene rutas relativas al ejecutable/script"""
    base_dir = Path(__file__).parent
    config_path = base_dir / "cloudflared" / "config.yml"
    return base_dir, config_path


def load_tunnel_config(config_path):
    """Lee el config.yml para saber qué túnel lanzar"""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            tunnel_id = config.get('tunnel')
            if not tunnel_id: return None
            return tunnel_id
    except Exception as e:
        print(f"⚠️ Aviso: No se pudo leer config.yml ({e})")
        return None


# --- SEGURIDAD (GIST) ---
def validar_licencia_nube():
    """
    Descarga la clave desde el Gist y la valida.
    Retorna True si la clave es correcta.
    Retorna False si hay error de conexión o clave incorrecta.
    """
    print("🌍 Verificando licencia en la nube...")

    try:
        # 1. Descargar clave maestra (Timeout de 5 segs para no congelar)
        respuesta = requests.get(URL_GIST_RAW, timeout=10)

        if respuesta.status_code != 200:
            print("❌ Error: No se pudo conectar al servidor de licencias.")
            print(f"   Código de estado: {respuesta.status_code}")
            return False

        clave_maestra = respuesta.text.strip()
        print(clave_maestra)

        # Opcional: Kill Switch remoto
        if clave_maestra != "Acceso2025":
            print("⛔ ACCESO DENEGADO POR EL ADMINISTRADOR.")
            return False
        else:
            return True


    except requests.exceptions.ConnectionError:
        print("❌ Error: Se requiere conexión a internet para validar la licencia.")
        return False
    except Exception as e:
        print(f"❌ Error inesperado en validación: {e}")
        return False


# --- GESTIÓN DEL TÚNEL (NO BLOQUEANTE) ---
def monitor_tunel(process):
    """Solo imprime logs, NO cierra el programa si falla"""
    try:
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if "Registered tunnel connection" in line:
                print(f"☁️  [Cloudflare] Túnel conectado exitosamente.")
            elif "ERR" in line:
                print(f"⚠️ [Cloudflare Error] {line}")
    except:
        pass


def iniciar_tunel_seguro():
    """Intenta iniciar el túnel en un hilo aparte"""
    base_dir, config_path = get_paths()
    tunnel_id = load_tunnel_config(config_path)

    if not tunnel_id:
        print("⚠️ No se iniciará el túnel (Falta ID en config). La App funcionará localmente.")
        return None

    print("🚀 Iniciando servicio de Cloudflare (Segundo plano)...")
    try:
        # Lanzamos el proceso sin esperar (Popen)
        tunnel_proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--config", str(config_path), "run", tunnel_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        # Hilo para leer los logs sin bloquear el programa principal
        t = threading.Thread(target=monitor_tunel, args=(tunnel_proc,), daemon=True)
        t.start()
        return tunnel_proc
    except Exception as e:
        print(f"⚠️ Error al intentar lanzar Cloudflare: {e}")
        print("   -> La aplicación continuará solo en modo LOCAL.")
        return None


# --- MAIN ---
def main():
    # 1. VALIDACIÓN DE SEGURIDAD (Esto SÍ detiene el programa si falla)
    if not validar_licencia_nube():
        input("Presione Enter para salir...")
        sys.exit(1)

    # 2. LIMPIEZA DE PUERTO (Opcional, para Linux)
    subprocess.run(["sudo", "fuser", "-k", "8000/tcp"], capture_output=True)

    # 3. INICIAR TÚNEL (Esto NO detiene el programa si falla)
    tunnel_process = iniciar_tunel_seguro()

    # 4. INICIAR BACKEND
    # El backend arranca independientemente de si el túnel funcionó o no
    print("\n✅ Iniciando Servidor Backend (Local)...")
    print("   Disponible en: http://localhost:8000")

    try:
        import uvicorn
        # IMPORTANTE: Cambia 'main:app' por la ubicación real de tu objeto FastAPI
        # Si este archivo YA ES tu main.py y tienes 'app = FastAPI()', usa 'app' directo:
        from main import app

        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

    except KeyboardInterrupt:
        print("\n👋 Cerrando sistema...")
    except Exception as e:
        print(f"❌ Error crítico del servidor: {e}")
    finally:
        # Al cerrar la app, matamos el túnel si estaba vivo
        if tunnel_process:
            print("🧹 Cerrando túnel...")
            tunnel_process.terminate()
