from typing import Dict, List, Optional
from datetime import datetime, timedelta
from api.models.tarea_activa import TareaActiva
from api.services.dispositivo_service import dispositivo_service
from api.models.dispositivo import DispositivoEstado
import asyncio
import threading

class TareasService:
    """Servicio para gestionar tareas activas en memoria"""
    
    def __init__(self):
        # Cache en memoria de tareas activas
        self._tareas: Dict[str, TareaActiva] = {}
        self._lock = asyncio.Lock()
        # Servicio de dispositivos para actualizar estados cuando se crean/terminan tareas
        self._dispositivo_service = dispositivo_service
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Seguimiento adicional para detener tareas desde threads
        self._detener_flags: Dict[str, Dict[str, threading.Event]] = {}
        self._tarea_dispositivos_pendientes: Dict[str, int] = {}
        self._tarea_exitosa: Dict[str, bool] = {}
        self._thread_lock = threading.Lock()

    def _capture_loop(self):
        """Guarda referencia al event loop principal para uso desde threads."""
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # No hay loop corriendo en este hilo (por ejemplo, durante tests)
                pass
    
    async def crear_tarea(
        self,
        tipo: str,
        dispositivos_ids: List[str],
        config: dict,
        total_esperado: int = 0
    ) -> TareaActiva:
        """
        Crea una nueva tarea activa

        Args:
            tipo: Tipo de tarea ("comentarios", "compartidas", "likes", "suscripciones")
            dispositivos_ids: Lista de IDs de dispositivos
            config: Configuración original de la tarea
            total_esperado: Total de operaciones esperadas

        Returns:
            Nueva tarea creada
        """
        self._capture_loop()
        async with self._lock:
            tarea = TareaActiva.crear(tipo, dispositivos_ids, config, total_esperado)
            self._tareas[tarea.id] = tarea
            with self._thread_lock:
                self._tarea_dispositivos_pendientes[tarea.id] = len(dispositivos_ids)
                self._tarea_exitosa[tarea.id] = False

            print(f"✅ Tarea creada: {tarea.id} (tipo: {tipo}, dispositivos: {len(dispositivos_ids)})")

            # Pre-cargar el cache de dispositivos UNA SOLA VEZ antes de iterar
            print(f"🔄 Pre-cargando cache de dispositivos...")
            self._dispositivo_service.obtener_dispositivos()

            # Marcar todos los dispositivos asignados a esta tarea como 'en_tarea'
            try:
                for device_id in dispositivos_ids:
                    self._dispositivo_service.actualizar_estado(device_id, DispositivoEstado.EN_TAREA)
            except Exception as e:
                print(f"⚠️ Error marcando dispositivos como en_tarea: {e}")

            return tarea
    
    async def obtener_tarea(self, tarea_id: str) -> Optional[TareaActiva]:
        """
        Obtiene una tarea por su ID
        
        Args:
            tarea_id: ID de la tarea
            
        Returns:
            Tarea encontrada o None
        """
        self._capture_loop()
        return self._tareas.get(tarea_id)
    
    async def obtener_tareas_activas(self) -> List[TareaActiva]:
        """
        Obtiene todas las tareas activas (no completadas ni fallidas)
        
        Returns:
            Lista de tareas activas
        """
        self._capture_loop()
        async with self._lock:
            tareas_activas = [
                tarea for tarea in self._tareas.values()
                if tarea.estado in ["iniciando", "ejecutando", "deteniendo"]
            ]
            # Ordenar por fecha de inicio (más recientes primero)
            tareas_activas.sort(key=lambda t: t.fecha_inicio, reverse=True)
            return tareas_activas
    
    async def obtener_todas_tareas(self) -> List[TareaActiva]:
        """
        Obtiene todas las tareas (incluidas completadas y fallidas)
        
        Returns:
            Lista de todas las tareas
        """
        self._capture_loop()
        async with self._lock:
            todas = list(self._tareas.values())
            todas.sort(key=lambda t: t.fecha_inicio, reverse=True)
            return todas
    
    async def actualizar_estado(self, tarea_id: str, nuevo_estado: str):
        """
        Actualiza el estado de una tarea
        
        Args:
            tarea_id: ID de la tarea
            nuevo_estado: Nuevo estado ("iniciando", "ejecutando", "completada", "fallida")
        """
        self._capture_loop()
        async with self._lock:
            tarea = self._tareas.get(tarea_id)
            if tarea:
                tarea.estado = nuevo_estado
                print(f"🔄 Tarea {tarea_id[:8]}... estado: {nuevo_estado}")
    
    async def actualizar_metrica(self, tarea_id: str, metrica: str, incremento: int = 1):
        """
        Actualiza una métrica de una tarea
        
        Args:
            tarea_id: ID de la tarea
            metrica: Nombre de la métrica ("exitosos", "fallidos", "en_proceso")
            incremento: Valor a incrementar
        """
        self._capture_loop()
        async with self._lock:
            tarea = self._tareas.get(tarea_id)
            if tarea:
                tarea.actualizar_metrica(metrica, incremento)
    
    async def finalizar_tarea(self, tarea_id: str, exito: bool = True):
        """
        Finaliza una tarea
        
        Args:
            tarea_id: ID de la tarea
            exito: Si la tarea se completó exitosamente
        """
        self._capture_loop()
        async with self._lock:
            tarea = self._tareas.get(tarea_id)
            if tarea:
                tarea.finalizar(exito)
                print(f"✅ Tarea finalizada: {tarea_id[:8]}... (éxito: {exito})")
                self._limpiar_tracking_tarea(tarea_id)

                # Restaurar estado de los dispositivos asignados (si aún existen)
                try:
                    for device_id in tarea.dispositivos_ids:
                        # Solo restablecer a INACTIVO si actualmente están en 'en_tarea'
                        dispositivo = self._dispositivo_service.obtener_dispositivo(device_id)
                        if dispositivo and dispositivo.estado == DispositivoEstado.EN_TAREA:
                            self._dispositivo_service.actualizar_estado(device_id, DispositivoEstado.INACTIVO)
                except Exception as e:
                    print(f"⚠️ Error restaurando estado de dispositivos al finalizar tarea: {e}")
    
    async def limpiar_tareas_antiguas(self, horas: int = 24):
        """
        Elimina tareas completadas o fallidas con más de X horas
        
        Args:
            horas: Número de horas para considerar una tarea como antigua
        """
        self._capture_loop()
        async with self._lock:
            ahora = datetime.now()
            limite = ahora - timedelta(hours=horas)
            
            tareas_a_eliminar = []
            
            for tarea_id, tarea in self._tareas.items():
                if tarea.estado in ["completada", "fallida"] and tarea.fecha_fin:
                    if tarea.fecha_fin < limite:
                        tareas_a_eliminar.append(tarea_id)
            
            for tarea_id in tareas_a_eliminar:
                del self._tareas[tarea_id]
            
            if tareas_a_eliminar:
                print(f"🧹 Limpiadas {len(tareas_a_eliminar)} tareas antiguas")

    def incrementar_completados(self, tarea_id: str, incremento: int = 1):
        """
        Incrementa la métrica de completados. Versión sync-safe (thread-safe).
        """
        tarea = self._tareas.get(tarea_id)
        if tarea:
            tarea.actualizar_metrica("exitosos", incremento)

    def registrar_flag(self, tarea_id: str, dispositivo_id: str, flag: threading.Event):
        """Asocia el flag de detener de un dispositivo a su tarea."""
        with self._thread_lock:
            tarea_flags = self._detener_flags.setdefault(tarea_id, {})
            tarea_flags[dispositivo_id] = flag

    def liberar_flag(self, tarea_id: str, dispositivo_id: str):
        """Elimina el flag de un dispositivo cuando deja de usarse."""
        with self._thread_lock:
            tarea_flags = self._detener_flags.get(tarea_id)
            if not tarea_flags:
                return
            tarea_flags.pop(dispositivo_id, None)
            if not tarea_flags:
                self._detener_flags.pop(tarea_id, None)

    def detener_tarea(self, tarea_id: str) -> int:
        """
        Dispara los flags de detener de todos los dispositivos de una tarea.
        Returns el número de dispositivos notificados.
        """
        with self._thread_lock:
            tarea_flags = self._detener_flags.get(tarea_id, {})
            count = 0
            for flag in list(tarea_flags.values()):
                flag.set()
                count += 1
            return count

    def detener_todas(self) -> int:
        """Detiene todas las tareas activas. Returns número de tareas detenidas."""
        with self._thread_lock:
            count = 0
            for tarea_id, flags in list(self._detener_flags.items()):
                for flag in list(flags.values()):
                    flag.set()
                count += 1
            self._detener_flags.clear()
            # También detener flags de plataformas
            try:
                from api.services.facebook_service import facebook_service
                facebook_service.detener_todos()
            except Exception: pass
            try:
                from api.services.tiktok_service import tiktok_service
                tiktok_service.detener_todos()
            except Exception: pass
            try:
                from api.services.instagram_service import instagram_service
                instagram_service.detener_todos()
            except Exception: pass
            return count

    def marcar_dispositivo_finalizado(self, tarea_id: str, exito: bool = True):
        """
        Indica que un dispositivo terminó. Cuando todos terminan se finaliza la tarea automáticamente.
        Versión sync-safe: actualiza tarea y dispositivos directamente sin depender del event loop.
        """
        finalizar = False
        with self._thread_lock:
            if exito:
                previo = self._tarea_exitosa.get(tarea_id, False)
                self._tarea_exitosa[tarea_id] = previo or True
            pendientes = self._tarea_dispositivos_pendientes.get(tarea_id)
            if pendientes is not None:
                pendientes = max(0, pendientes - 1)
                if pendientes == 0:
                    finalizar = True
                    self._tarea_dispositivos_pendientes.pop(tarea_id, None)
                else:
                    self._tarea_dispositivos_pendientes[tarea_id] = pendientes

        if finalizar:
            exito_final = self._tarea_exitosa.pop(tarea_id, False)
            # === FINALIZACIÓN SÍNCRONA (no depende del event loop) ===
            self._finalizar_tarea_sync(tarea_id, exito_final)

    def _finalizar_tarea_sync(self, tarea_id: str, exito: bool):
        """Finaliza una tarea de forma síncrona (thread-safe)."""
        tarea = self._tareas.get(tarea_id)
        if tarea:
            tarea.finalizar(exito)
            print(f"✅ Tarea finalizada: {tarea_id[:8]}... (éxito: {exito})")
            self._limpiar_tracking_tarea(tarea_id)
            # Restaurar estado de dispositivos EN_TAREA
            try:
                for device_id in tarea.dispositivos_ids:
                    dispositivo = self._dispositivo_service.obtener_dispositivo(device_id)
                    if dispositivo and dispositivo.estado == DispositivoEstado.EN_TAREA:
                        self._dispositivo_service.actualizar_estado(device_id, DispositivoEstado.INACTIVO)
            except Exception as e:
                print(f"⚠️ Error restaurando estado de dispositivos: {e}")

    def _limpiar_tracking_tarea(self, tarea_id: str):
        """Remueve referencias internas para evitar fugas de memoria."""
        with self._thread_lock:
            self._detener_flags.pop(tarea_id, None)
            self._tarea_dispositivos_pendientes.pop(tarea_id, None)
            self._tarea_exitosa.pop(tarea_id, None)

# Instancia global del servicio
tareas_service = TareasService()
