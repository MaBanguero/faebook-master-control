import subprocess
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

# Ruta fija de ADB
ADB_PATH = 'adb'

@dataclass
class ADBDevice:
    """Representa un dispositivo ADB detectado"""
    adb_id: str
    status: str
    model: Optional[str] = None
    android_version: Optional[str] = None
    connection_type: str = "unknown"  # "usb", "network", o "unknown"
    
    def __post_init__(self):
        """Detecta el tipo de conexión basado en el adb_id"""
        if ':' in self.adb_id and '.' in self.adb_id:
            # Formato IP:puerto (ej: 192.168.1.11:5555)
            self.connection_type = "network"
        elif len(self.adb_id) > 10 and self.adb_id[0].isalpha():
            # Formato serial USB (ej: A00000V590232610542)
            self.connection_type = "usb"
        else:
            self.connection_type = "unknown"

class ADBManager:
    """Gestor para operaciones ADB - YouTube/TikTok Master Control"""
    
    @staticmethod
    def is_adb_available() -> bool:
        """Verifica si ADB está disponible en el sistema"""
        try:
            result = subprocess.run([ADB_PATH, 'version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def get_connected_devices() -> List[ADBDevice]:
        """
        Obtiene la lista de dispositivos conectados via ADB
        Detecta AMBOS tipos de conexión: USB y Network (OTG)
        
        Returns:
            List[ADBDevice]: Lista de dispositivos conectados (USB + Network)
        """
        devices = []
        
        if not ADBManager.is_adb_available():
            print("❌ ADB no está disponible en el sistema")
            return devices
        
        try:
            result = subprocess.run([ADB_PATH, 'devices'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode != 0:
                print(f"❌ Error ejecutando 'adb devices': {result.stderr}")
                return devices
            
            lines = result.stdout.strip().split('\n')
            
            if len(lines) < 2:
                print("ℹ️ No hay dispositivos conectados")
                return devices
            
            usb_count = 0
            network_count = 0
            
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 2:
                    adb_id = parts[0].strip()
                    status = parts[1].strip()
                    
                    if status in ['device', 'online']:
                        device = ADBDevice(adb_id=adb_id, status=status)
                        device.model = ADBManager._get_device_model(adb_id)
                        device.android_version = ADBManager._get_android_version(adb_id)
                        devices.append(device)
                        
                        connection_emoji = "🔌" if device.connection_type == "usb" else "📡"
                        connection_label = "USB" if device.connection_type == "usb" else "Network"
                        print(f"✅ Dispositivo detectado ({connection_emoji} {connection_label}): {adb_id} ({device.model or 'Unknown'})")
                        
                        if device.connection_type == "usb":
                            usb_count += 1
                        elif device.connection_type == "network":
                            network_count += 1
            
            print(f"\n📱 === RESUMEN DE DISPOSITIVOS ===")
            print(f"   🔌 USB: {usb_count} dispositivo(s)")
            print(f"   📡 Network: {network_count} dispositivo(s)")
            print(f"   ✅ Total activos: {len(devices)}\n")
            
            return devices
            
        except subprocess.TimeoutExpired:
            print("❌ Timeout ejecutando 'adb devices'")
            return devices
        except Exception as e:
            print(f"❌ Error inesperado obteniendo dispositivos ADB: {e}")
            return devices
    
    @staticmethod
    def _get_device_model(device_id: str) -> Optional[str]:
        """Obtiene el modelo del dispositivo"""
        try:
            result = subprocess.run([ADB_PATH, '-s', device_id, 'shell', 'getprop', 'ro.product.model'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    @staticmethod
    def _get_android_version(device_id: str) -> Optional[str]:
        """Obtiene la versión de Android del dispositivo"""
        try:
            result = subprocess.run([ADB_PATH, '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    @staticmethod
    def execute_command(device_id: str, command: str) -> Dict[str, any]:
        """
        Ejecuta un comando ADB en un dispositivo específico
        
        Args:
            device_id: ID del dispositivo ADB
            command: Comando a ejecutar
            
        Returns:
            Dict con el resultado del comando
        """
        try:
            result = subprocess.run([ADB_PATH, '-s', device_id, 'shell', command], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30)
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timeout',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
