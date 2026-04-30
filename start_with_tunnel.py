"""
Inicio completo de YouTube & TikTok Master Control:
- Limpia servicios uiautomator2 en todos los dispositivos conectados
- Arranca el túnel de Cloudflare
- Levanta el backend de FastAPI en el puerto 8000
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path


PUBLIC_HOSTNAME = "https://api-youtubetiktok.apkks.xyz"
TUNNEL_NAME = "facebook-master"


def print_log(message: str, level: str = "INFO") -> None:
    colors = {
        "INFO": "\033[96m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m",
    }
    color = colors.get(level, colors["INFO"])
    reset = colors["RESET"]
    print(f"{color}[{level}]{reset} {message}")


def get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def get_cloudflared_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "cloudflared"
    return get_base_path() / "cloudflared"


def reset_connected_devices() -> None:
    print_log("[1/3] Limpiando servicios uiautomator2 en dispositivos...", "INFO")
    try:
        from reset_all_devices import get_connected_devices, reset_device

        devices = get_connected_devices()
        if not devices:
            print_log("No se detectaron dispositivos. Continuando...", "WARNING")
            return
        success = 0
        for device_id in devices:
            if reset_device(device_id):
                success += 1
        print_log(f"Servicios reiniciados en {success}/{len(devices)} dispositivos.", "SUCCESS")
    except Exception as exc:
        print_log(f"Error durante el reset de dispositivos: {exc}", "WARNING")


def start_cloudflared_tunnel() -> subprocess.Popen | None:
    print_log("[2/3] Iniciando Cloudflare Tunnel...", "INFO")
    cloudflared_dir = get_cloudflared_dir()
    exe_path = cloudflared_dir / "cloudflared.exe"
    config_path = cloudflared_dir / "config.yml"
    credentials_path = cloudflared_dir / "credentials.json"

    for file_path in (exe_path, config_path, credentials_path):
        if not file_path.exists():
            print_log(f"Archivo requerido no encontrado: {file_path}", "ERROR")
            return None

    try:
        process = subprocess.Popen(
            [str(exe_path), "tunnel", "--config", str(config_path), "run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cloudflared_dir),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception as exc:  # pragma: no cover
        print_log(f"No se pudo iniciar el túnel: {exc}", "ERROR")
        return None

    print_log("Esperando a que el túnel se establezca...", "INFO")
    time.sleep(5)

    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print_log("El túnel terminó prematuramente.", "ERROR")
        if stdout:
            print_log(stdout.decode("utf-8", errors="ignore"), "ERROR")
        if stderr:
            print_log(stderr.decode("utf-8", errors="ignore"), "ERROR")
        return None

    print_log(f"Túnel activo. Dominio público: {PUBLIC_HOSTNAME}", "SUCCESS")
    return process


def monitor_tunnel(process: subprocess.Popen) -> None:
    try:
        while True:
            if process.poll() is not None:
                print_log("El túnel Cloudflare se detuvo.", "WARNING")
                stdout, stderr = process.communicate()
                if stdout:
                    print_log(stdout.decode("utf-8", errors="ignore"), "WARNING")
                if stderr:
                    print_log(stderr.decode("utf-8", errors="ignore"), "WARNING")
                break
            time.sleep(10)
    except Exception:
        pass


def start_backend() -> None:
    print_log("[3/3] Lanzando backend FastAPI...", "INFO")
    import uvicorn  # local import para PyInstaller
    from main import app

    print_log("Servidor local: http://0.0.0.0:8000", "INFO")
    print_log(f"Servidor público: {PUBLIC_HOSTNAME}", "INFO")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_keep_alive=30,
        limit_concurrency=100,
        log_level="warning",
    )


def main() -> None:
    tunnel_process: subprocess.Popen | None = None
    try:
        reset_connected_devices()
        tunnel_process = start_cloudflared_tunnel()

        if tunnel_process is None:
            print_log(
                "El túnel no se pudo iniciar. El backend solo estará disponible en localhost.",
                "WARNING",
            )
        else:
            threading.Thread(target=monitor_tunnel, args=(tunnel_process,), daemon=True).start()

        start_backend()
    except KeyboardInterrupt:
        print_log("Deteniendo servicios...", "WARNING")
    finally:
        if tunnel_process and tunnel_process.poll() is None:
            print_log("Cerrando túnel Cloudflare...", "INFO")
            tunnel_process.terminate()
            try:
                tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel_process.kill()
        print_log("YouTube & TikTok Master Control finalizado.", "SUCCESS")


if __name__ == "__main__":
    main()
