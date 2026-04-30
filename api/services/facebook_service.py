import threading
import random
from typing import List
from api.services.dispositivo_service import dispositivo_service
from api.services.tareas_service import tareas_service
from api.models import DispositivoEstado
from api.utils.facebook_automator import FacebookAutomator
import logging


class FacebookService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False): return
        self.fb_detener_flags = {}
        self.contadores_rotacion = {}
        self._initialized = True

    def ejecutar_cambio_cuentas(self, dispositivos_ids: List[str], tarea_id: str):
        for d_id in dispositivos_ids:
            if d_id not in self.contadores_rotacion:
                self.contadores_rotacion[d_id] = 0
            else:
                self.contadores_rotacion[d_id] += 1

            indice = self.contadores_rotacion[d_id]
            flag = threading.Event()
            self.fb_detener_flags[d_id] = flag
            threading.Thread(target=self._worker_cambio_cuenta, args=(d_id, indice, flag, tarea_id),
                             daemon=True).start()

    def _worker_cambio_cuenta(self, d_id, indice, flag, t_id):
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            automator = FacebookAutomator(d_id)
            exito = automator.rotar_perfil_secuencial(indice, flag)
            self._finalizar_tarea(d_id, t_id, exito)
        except Exception:
            self._finalizar_tarea(d_id, t_id, False)

    def ejecutar_likes(self, d_ids, link, t_id):
        for d_id in d_ids:
            flag = threading.Event()
            threading.Thread(target=self._worker_like, args=(d_id, link, flag, t_id), daemon=True).start()

    def _worker_like(self, d_id, link, flag, t_id):
        automator = FacebookAutomator(d_id)
        exito = automator.proceso_like_facebook(link, flag)
        self._finalizar_tarea(d_id, t_id, exito)

    def ejecutar_comentarios(self, d_ids, link, textos, t_id):
        """
        Cada dispositivo recibe el comentario que le corresponde por índice.
        Si d_ids[0] existe, usará textos[0].
        """
        # Usamos zip de nuevo por seguridad extrema para mantener el mapeo 1 a 1
        for d_id, texto_unico in zip(d_ids, textos):
            flag = threading.Event()

            # IMPORTANTE: Se pasa 'texto_unico' directamente al worker.
            # Ya no hay random.choice(textos)
            threading.Thread(
                target=self._worker_comentario,
                args=(d_id, link, texto_unico, flag, t_id),
                daemon=True
            ).start()

    def _worker_comentario(self, d_id, link, texto, flag, t_id):
        automator = FacebookAutomator(d_id)
        exito = automator.proceso_comentario_reels(link, texto, flag)
        self._finalizar_tarea(d_id, t_id, exito)

    def _finalizar_tarea(self, d_id, t_id, exito):
        if exito:
            tareas_service.incrementar_completados(t_id)
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.INACTIVO)
        else:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.ERROR)
        if d_id in self.fb_detener_flags: del self.fb_detener_flags[d_id]
        tareas_service.marcar_dispositivo_finalizado(t_id, exito=exito)

    def ejecutar_compartir(self, d_ids: List[str], link: str, t_id: str):
        for d_id in d_ids:
            flag = threading.Event()
            self.fb_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_compartir,
                args=(d_id, link, flag, t_id),
                daemon=True
            ).start()

    def _worker_compartir(self, d_id, link, flag, t_id):
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            automator = FacebookAutomator(d_id)
            exito = automator.proceso_compartir_post(link, flag)
            self._finalizar_tarea(d_id, t_id, exito)
        except Exception as e:
            print(f"Error en worker compartir: {e}")
            self._finalizar_tarea(d_id, t_id, False)

    # --- MÉTODOS PARA FLUJO COMPLETO (LIKE + COMENTARIO + COMPARTIR) ---

    def ejecutar_flujo_completo(self, dispositivos_ids: List[str], link: str, comentario, tarea_id: str):
        for d_id in dispositivos_ids:
            # VALIDACIÓN: Si es array (list), elige uno al azar. Si es string, lo usa tal cual.
            # Si por error llega algo vacío, pone un comentario por defecto.
            if isinstance(comentario, list) and len(comentario) > 0:
                texto_final = random.choice(comentario)
            elif isinstance(comentario, str):
                texto_final = comentario
            else:
                texto_final = "Excelente contenido! 🔥"  # Fallback de seguridad

            flag = threading.Event()
            self.fb_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_flujo_completo,
                args=(d_id, link, texto_final, flag, tarea_id),
                daemon=True
            ).start()
    def _worker_flujo_completo(self, d_id, link, comentario, flag, t_id):
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            automator = FacebookAutomator(d_id)

            # Ejecuta la secuencia Like -> Comentario -> Compartir
            exito = automator.ejecutar_flujo_completo_fb(link, comentario, flag)

            self._finalizar_tarea(d_id, t_id, exito)
        except Exception as e:
            print(f"Error en worker flujo completo: {e}")
            self._finalizar_tarea(d_id, t_id, False)


facebook_service = FacebookService()