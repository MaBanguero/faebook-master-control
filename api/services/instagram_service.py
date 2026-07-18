"""
Servicio Instagram — multi-dispositivo con multi-cuenta.
Mismo patrón que TiktokService y FacebookService.
"""
import threading
import sys
from typing import List

from api.models.dispositivo import DispositivoEstado
from api.services.dispositivo_service import dispositivo_service
from api.services.tareas_service import tareas_service
from api.utils.instagram_automator import InstagramAutomator


class InstagramService:
    def __init__(self):
        self.ig_detener_flags: dict[str, threading.Event] = {}

    def detener_todos(self):
        for flag in self.ig_detener_flags.values():
            flag.set()

    def _finalizar_tarea(self, d_id: str, t_id: str, exito: bool):
        if exito:
            tareas_service.incrementar_completados(t_id)
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.INACTIVO)
        else:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.ERROR)
        self.ig_detener_flags.pop(d_id, None)
        tareas_service.marcar_dispositivo_finalizado(t_id, exito=exito)

    def ejecutar_flujo_multi_cuenta(
        self,
        dispositivos_ids: List[str],
        link: str,
        comentario,
        tarea_id: str,
        cuentas_a_usar: int = 0,
    ):
        """
        Like + comentario + compartir en cada dispositivo.

        - comentario string → 1 cuenta
        - comentario list[str] → N cuentas
        - comentario vacío → like + compartir sin comentar
        """
        if isinstance(comentario, list) and len(comentario) > 0:
            comentarios = [c for c in comentario if isinstance(c, str) and c.strip()]
        elif isinstance(comentario, str):
            c = comentario.strip()
            comentarios = [c] if c else []
        else:
            comentarios = ["🔥 Excelente!"]

        if not any(c.strip() for c in comentarios):
            comentarios = []

        num_dispositivos = len(dispositivos_ids)

        for i, d_id in enumerate(dispositivos_ids):
            if num_dispositivos > 1 and comentarios:
                chunk_size = max(1, len(comentarios) // num_dispositivos)
                inicio = i * chunk_size
                if i == num_dispositivos - 1:
                    comentarios_dispositivo = comentarios[inicio:]
                else:
                    comentarios_dispositivo = comentarios[inicio : inicio + chunk_size]
            else:
                comentarios_dispositivo = list(comentarios) if comentarios else []

            flag = threading.Event()
            self.ig_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_flujo,
                args=(d_id, link, comentarios_dispositivo, flag, tarea_id),
                daemon=True,
            ).start()

    def _worker_flujo(self, d_id, link, comentarios, flag, t_id):
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            automator = InstagramAutomator(d_id, skip_reset=True)

            print(f"📋 [IG][{d_id}] {automator.cuentas_por_dispositivo} cuentas", flush=True)
            print(f"💬 [IG][{d_id}] {len(comentarios)} comentarios", flush=True)

            # 1. LIKE
            print(f"--- [IG][{d_id}] LIKE ---", flush=True)
            likes = automator.proceso_likes(link, flag)
            print(f"   👍 {likes} like(s)", flush=True)
            if flag and flag.is_set():
                self._finalizar_tarea(d_id, t_id, False)
                return

            # Rotar cuenta después del like
            if likes > 0 and len(comentarios) > 0:
                print(f"   🔄 Rotando cuenta post-like...", flush=True)
                automator.cambiar_cuenta(3, 8)

            # 2. COMENTARIO
            c_ok = 0
            if comentarios:
                print(f"--- [IG][{d_id}] COMENTARIOS ({len(comentarios)}) ---", flush=True)
                c_ok = automator.proceso_comentarios(link, comentarios, flag)
                print(f"   💬 {c_ok} comentario(s)", flush=True)
                if flag and flag.is_set():
                    self._finalizar_tarea(d_id, t_id, False)
                    return
            else:
                print(f"--- [IG][{d_id}] COMENTARIO (omitido) ---", flush=True)

            # 3. COMPARTIR (desactivado por ahora)
            print(f"--- [IG][{d_id}] COMPARTIR (desactivado) ---", flush=True)

            print(f"📊 [IG][{d_id}] {likes}L / {c_ok}C", flush=True)
            self._finalizar_tarea(d_id, t_id, True)

        except Exception as e:
            print(f"❌ [IG][{d_id}] Error: {e}", flush=True)
            self._finalizar_tarea(d_id, t_id, False)

    # ── CALENTAMIENTO ──

    def ejecutar_calentamiento(self, dispositivos_ids: List[str], tarea_id: str):
        """Lanza calentamiento ultra-random en cada dispositivo."""
        for d_id in dispositivos_ids:
            flag = threading.Event()
            self.ig_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_calentamiento,
                args=(d_id, flag, tarea_id),
                daemon=True,
            ).start()

    def _worker_calentamiento(self, d_id: str, flag: threading.Event, t_id: str):
        """Worker de calentamiento Instagram en un dispositivo."""
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            automator = InstagramAutomator(d_id, skip_reset=True)
            automator.proceso_calentamiento(detener_flag=flag)
            self._finalizar_tarea(d_id, t_id, True)
        except Exception as e:
            print(f"❌ [IG][{d_id}] Error calentamiento IG: {e}", flush=True)
            self._finalizar_tarea(d_id, t_id, False)


instagram_service = InstagramService()
