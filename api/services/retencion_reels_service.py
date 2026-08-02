"""
RetencionReelsService — Workers multi-dispositivo para retención de Facebook Reels.
"""

import threading
import time
import random
from typing import List, Dict

from api.utils.facebook_automator import FacebookAutomator
from api.services.tareas_service import tareas_service
from api.services.dispositivo_service import dispositivo_service
from api.models.dispositivo import DispositivoEstado


class RetencionReelsService:
    """Servicio singleton para ejecutar retención de reels en múltiples dispositivos."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.retencion_flags: Dict[str, threading.Event] = {}
        self._rw_lock = threading.Lock()

    def ejecutar(self, dispositivos_ids: List[str], tarea_id: str,
                 duracion_sesion_min: int = 8,
                 descanso_entre_cuentas_min: int = 20):
        """
        Lanza workers en paralelo, uno por dispositivo.

        Args:
            dispositivos_ids: Lista de IDs de dispositivos
            tarea_id: ID de la tarea asociada
            duracion_sesion_min: Minutos viendo reels por cuenta
            descanso_entre_cuentas_min: Minutos de descanso entre cuentas
        """
        for d_id in dispositivos_ids:
            flag = threading.Event()
            with self._rw_lock:
                self.retencion_flags[d_id] = flag

            threading.Thread(
                target=self._worker_retencion,
                args=(d_id, tarea_id, duracion_sesion_min, descanso_entre_cuentas_min, flag),
                daemon=True
            ).start()

    def _worker_retencion(self, d_id: str, t_id: str,
                           duracion_min: int, descanso_min: int,
                           flag: threading.Event):
        """Worker: ejecuta retención multi-cuenta en 1 dispositivo."""
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            dev = dispositivo_service.obtener_dispositivo(d_id)
            adb_id = dev.adb_id if dev else d_id
            automator = FacebookAutomator(adb_id)

            print(f"[{d_id}] 📱 Iniciando retención Reels...")

            resultado = automator.proceso_retencion_multi_cuenta(
                duracion_sesion_cuenta_min=duracion_min,
                descanso_entre_cuentas_min=descanso_min,
                detener_flag=flag,
            )

            exito = resultado.get("reels_vistos", 0) > 0
            self._finalizar_tarea(d_id, t_id, exito)
            print(f"[{d_id}] ✅ Retención finalizada: {resultado}")

        except Exception as e:
            print(f"[{d_id}] ❌ Error en retención: {e}")
            self._finalizar_tarea(d_id, t_id, False)

    def _finalizar_tarea(self, d_id: str, t_id: str, exito: bool):
        """Finaliza la tarea de retención para un dispositivo."""
        if exito:
            tareas_service.incrementar_completados(t_id)
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.INACTIVO)
        else:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.ERROR)
        with self._rw_lock:
            self.retencion_flags.pop(d_id, None)
        tareas_service.marcar_dispositivo_finalizado(t_id, exito=exito)

    def detener(self, dispositivos_ids: List[str] = None) -> int:
        """
        Detiene workers de retención. Si no se especifican dispositivos, detiene todos.

        Returns:
            Número de dispositivos detenidos
        """
        detenidos = 0
        with self._rw_lock:
            ids_a_detener = dispositivos_ids if dispositivos_ids else list(self.retencion_flags.keys())
            for d_id in ids_a_detener:
                flag = self.retencion_flags.get(d_id)
                if flag:
                    flag.set()
                    detenidos += 1
        return detenidos


retencion_service = RetencionReelsService()
