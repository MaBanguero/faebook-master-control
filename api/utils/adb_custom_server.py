"""
Sistema de ADB Server Personalizado para YouTube/TikTok Master Control
Optimizado para Ubuntu/Linux
"""

import subprocess
import time
import os
from typing import Optional, Dict, List
from dataclasses import dataclass
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración del servidor ADB desde .env
CUSTOM_ADB_PORT = int(os.getenv('CUSTOM_ADB_PORT', '5037'))
# En Ubuntu usamos el comando global
ADB_PATH = "adb"

@dataclass
class ADBDevice:
    """Representa un dispositivo ADB detectado"""
    adb_id: str
    status: str
    model: Optional[str] = None
    android_version: Optional[str] = None
    connection_type: str = "unknown"

    def __post_init__(self):
        """Detecta el tipo de conexión en Linux"""
        if ':' in self.adb_id:
            self.connection_type = "network"
        else:
            self.connection_type = "usb"


class CustomADBManager:
    """Gestor de ADB Server Personalizado"""

    def __init__(self):
        self.port = CUSTOM_ADB_PORT
        self.adb_path = ADB_PATH
        # En Linux es vital que el PATH esté presente para encontrar adb
        self.env = os.environ.copy()
        self.env['ANDROID_ADB_SERVER_PORT'] = str(self.port)

    def _run_adb_command(self, *args, timeout=10) -> subprocess.CompletedProcess:
        """
        Ejecuta un comando ADB con el puerto personalizado.
        Formato Linux: adb -P <port> <args>
        """
        # IMPORTANTE: No incluimos 'start-server' aquí para evitar bloqueos
        cmd = [self.adb_path, "-P", str(self.port)] + list(args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=self.env
        )

    def is_server_running(self) -> bool:
        """Verifica si el servidor responde en el puerto configurado"""
        try:
            # 'host-features' es un comando ligero para verificar salud del server
            result = self._run_adb_command('host-features', timeout=3)
            return result.returncode == 0
        except:
            return False

    def start_server(self) -> bool:
        """Inicia el servidor ADB personalizado"""
        try:
            if self.is_server_running():
                print(f"✅ Servidor ADB ya está activo en puerto {self.port}")
                return True

            print(f"🚀 Iniciando servidor ADB en puerto {self.port}...")
            # Aquí sí usamos start-server explícitamente
            result = subprocess.run(
                [self.adb_path, "-P", str(self.port), "start-server"],
                env=self.env,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                time.sleep(1)
                return True
            return False
        except Exception as e:
            print(f"❌ Error al iniciar servidor ADB: {e}")
            return False

    def get_connected_devices(self, verbose: bool = False) -> List[ADBDevice]:
        """Obtiene la lista de dispositivos conectados"""
        devices = []
        try:
            # Asegurar que el servidor esté vivo
            if not self.is_server_running():
                self.start_server()

            # Ejecutamos 'devices -l' para obtener modelo de una vez si es posible
            result = self._run_adb_command('devices', timeout=10)

            if result.returncode != 0:
                return devices

            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return devices

            for line in lines[1:]:
                if not line.strip() or 'list of devices' in line.lower():
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    adb_id = parts[0]
                    status = parts[1]

                    if status == 'device':
                        device = ADBDevice(adb_id=adb_id, status=status)
                        # Solo pedimos info extra si es necesario para no ralentizar
                        device.model = self._get_device_model(adb_id)
                        devices.append(device)

                        if verbose:
                            icon = "🔌" if device.connection_type == "usb" else "📡"
                            print(f"✅ Detectado {icon} {adb_id} [{device.model or 'N/A'}]")

            return devices
        except Exception as e:
            if verbose: print(f"❌ Error: {e}")
            return devices

    def _get_device_model(self, device_id: str) -> Optional[str]:
        try:
            result = self._run_adb_command('-s', device_id, 'shell', 'getprop', 'ro.product.model', timeout=4)
            return result.stdout.strip() if result.returncode == 0 else None
        except: return None

    def execute_command(self, device_id: str, command: str) -> Dict:
        """Ejecuta comando shell en dispositivo"""
        try:
            # En Linux usamos la lista de argumentos para evitar problemas de escape
            args = ['-s', device_id, 'shell'] + command.split()
            result = self._run_adb_command(*args, timeout=30)
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {'success': False, 'stderr': str(e)}

custom_adb_manager = CustomADBManager()