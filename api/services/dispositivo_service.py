from typing import List, Optional, Dict
from api.models import Dispositivo, DispositivoEstado
from api.utils.adb_custom_server import custom_adb_manager, ADBDevice
from datetime import datetime
import hashlib
import threading

class DispositivoService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementación Singleton thread-safe"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Solo inicializar una vez
        if not hasattr(self, '_initialized'):
            # Cache de dispositivos para mantener estado
            self._dispositivos_cache: Dict[str, Dispositivo] = {}
            self._last_refresh = None
            self._refresh_interval = 10  # Segundos entre refresh de ADB
            self._initialized = True
    
    def _generar_dispositivo_id(self, adb_id: str) -> str:
        """Genera un ID único para el dispositivo basado en su ADB ID"""
        return hashlib.md5(adb_id.encode()).hexdigest()[:8]
    
    def _crear_dispositivo_desde_adb(self, adb_device: ADBDevice) -> Dispositivo:
        """Convierte un ADBDevice a un Dispositivo del modelo"""
        device_id = self._generar_dispositivo_id(adb_device.adb_id)
        
        # Emoji según tipo de conexión
        connection_emoji = ""
        if adb_device.connection_type == "usb":
            connection_emoji = "🔌 "
        elif adb_device.connection_type == "network":
            connection_emoji = "📡 "
        
        # Generar nombre descriptivo
        if adb_device.model:
            nombre = f"{connection_emoji}{adb_device.model} ({adb_device.adb_id})"
        else:
            connection_label = adb_device.connection_type.upper() if adb_device.connection_type != "unknown" else ""
            nombre = f"{connection_emoji}Dispositivo {connection_label} ({adb_device.adb_id})"
        
        return Dispositivo(
            id=device_id,
            nombre=nombre,
            estado=DispositivoEstado.INACTIVO,
            adb_id=adb_device.adb_id,
            ultima_actualizacion=datetime.now().isoformat()
        )
    
    def _refresh_dispositivos(self, force: bool = False) -> List[Dispositivo]:
        """
        Refresca la lista de dispositivos desde ADB y mantiene estados existentes
        Args:
            force: Si es True, forzar refresh incluso si no ha pasado el intervalo
        """
        # Verificar si necesitamos hacer refresh
        now = datetime.now()
        if not force and self._last_refresh is not None:
            seconds_since_refresh = (now - self._last_refresh).total_seconds()
            if seconds_since_refresh < self._refresh_interval:
                # Devolver cache sin hacer refresh de ADB
                return list(self._dispositivos_cache.values())
        
        try:
            # Solo verbose en el primer refresh (cuando _last_refresh es None)
            is_first_refresh = self._last_refresh is None
            
            if is_first_refresh:
                print(f"🔄 Refrescando dispositivos desde ADB personalizado (Puerto {custom_adb_manager.port})...")
            
            # Obtener dispositivos ADB actuales (silencioso excepto en primer refresh)
            adb_devices = custom_adb_manager.get_connected_devices(verbose=is_first_refresh)
            dispositivos_actuales = []
            
            if not adb_devices:
                if is_first_refresh:
                    print("ℹ️ No se encontraron dispositivos ADB conectados")
                return []
            
            for adb_device in adb_devices:
                device_id = self._generar_dispositivo_id(adb_device.adb_id)
                
                # Si el dispositivo ya está en cache, mantener su estado
                if device_id in self._dispositivos_cache:
                    dispositivo = self._dispositivos_cache[device_id]
                    # Actualizar timestamp pero MANTENER estado
                    dispositivo.ultima_actualizacion = now.isoformat()
                    if is_first_refresh:
                        print(f"✅ Manteniendo estado '{dispositivo.estado}' para {dispositivo.nombre}")
                else:
                    # Crear nuevo dispositivo
                    dispositivo = self._crear_dispositivo_desde_adb(adb_device)
                    print(f"🆕 Nuevo dispositivo detectado: {dispositivo.nombre}")
                
                dispositivos_actuales.append(dispositivo)
            
            # Actualizar cache - solo mantener dispositivos que siguen conectados
            nuevo_cache = {}
            for dispositivo in dispositivos_actuales:
                nuevo_cache[dispositivo.id] = dispositivo
            
            self._dispositivos_cache = nuevo_cache
            self._last_refresh = now
            
            if is_first_refresh:
                print(f"✅ Cache actualizado: {len(dispositivos_actuales)} dispositivos")
            
            return dispositivos_actuales
            
        except Exception as e:
            print(f"❌ Error refrescando dispositivos: {e}")
            # En caso de error, devolver cache existente
            if self._dispositivos_cache:
                return list(self._dispositivos_cache.values())
            return []
    
    def obtener_dispositivos(self) -> List[Dispositivo]:
        """
        Obtiene todos los dispositivos conectados
        Usa cache si fue actualizado recientemente
        """
        return self._refresh_dispositivos(force=False)
    
    def obtener_dispositivo(self, dispositivo_id: str) -> Optional[Dispositivo]:
        """
        Obtiene un dispositivo por su ID o ADB ID desde el cache
        Soporta búsqueda por:
        - dispositivo_id (hash MD5)
        - adb_id (192.168.1.20:5555 o ce11171b0814062b05)
        """
        with self._lock:
            # Primero intentar buscar por dispositivo_id (hash)
            if dispositivo_id in self._dispositivos_cache:
                return self._dispositivos_cache[dispositivo_id]

            # Si no se encuentra, intentar buscar por adb_id
            for device in self._dispositivos_cache.values():
                if device.adb_id == dispositivo_id:
                    return device

            # Si cache está vacío, hacer UN SOLO refresh (protegido por lock)
            if not self._dispositivos_cache or self._last_refresh is None:
                print(f"⚠️ Dispositivo {dispositivo_id} no encontrado - Cache vacío, haciendo refresh...")
                self._refresh_dispositivos(force=True)

                # Reintentar búsqueda
                if dispositivo_id in self._dispositivos_cache:
                    return self._dispositivos_cache[dispositivo_id]

                for device in self._dispositivos_cache.values():
                    if device.adb_id == dispositivo_id:
                        return device

            # Si aún no se encuentra, no hacer más refreshes (evitar loops)
            return None
    
    def actualizar_estado(self, dispositivo_id: str, nuevo_estado: DispositivoEstado):
        """
        Actualiza el estado de un dispositivo en el cache
        """
        with self._lock:
            # Buscar por ID (hash) o por adb_id
            dispositivo = None
            if dispositivo_id in self._dispositivos_cache:
                dispositivo = self._dispositivos_cache[dispositivo_id]
            else:
                # Buscar por adb_id
                for device in self._dispositivos_cache.values():
                    if device.adb_id == dispositivo_id:
                        dispositivo = device
                        break

            if dispositivo:
                old_estado = dispositivo.estado
                dispositivo.estado = nuevo_estado
                dispositivo.ultima_actualizacion = datetime.now().isoformat()
                # Solo imprimir si el estado realmente cambió
                if old_estado != nuevo_estado:
                    print(f"✅ Estado actualizado para {dispositivo.nombre}: {old_estado} -> {nuevo_estado}")
            else:
                # No encontrado - no hacer refresh aquí para evitar loops
                print(f"⚠️ Dispositivo {dispositivo_id} no encontrado en cache (no se actualiza estado)")
    
    def ejecutar_comando_adb(self, dispositivo_id: str, comando: str) -> Dict:
        """
        Ejecuta un comando ADB en un dispositivo específico
        """
        dispositivo = self.obtener_dispositivo(dispositivo_id)
        if not dispositivo:
            return {
                'success': False,
                'error': f'Dispositivo {dispositivo_id} no encontrado'
            }
        
        print(f"🔧 Ejecutando comando en {dispositivo.nombre}: {comando}")
        resultado = custom_adb_manager.execute_command(dispositivo.adb_id, comando)
        
        return {
            'success': resultado['success'],
            'stdout': resultado['stdout'],
            'stderr': resultado['stderr'],
            'dispositivo': dispositivo.nombre
        }

# Instancia singleton
dispositivo_service = DispositivoService()
