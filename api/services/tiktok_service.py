"""
Servicio TikTok — multi-dispositivo con multi-cuenta.
Cada proceso (likes, comentarios, compartidas) maneja su propia rotación de cuentas.
"""
import random
import threading
import sys
from typing import List, Union

from api.models.dispositivo import DispositivoEstado
from api.services.dispositivo_service import dispositivo_service
from api.services.tareas_service import tareas_service
from api.utils.tiktok_automator import TiktokAutomator


class TiktokService:
    def __init__(self):
        self.tt_detener_flags: dict[str, threading.Event] = {}

    def detener_todos(self):
        for flag in self.tt_detener_flags.values():
            flag.set()

    def _finalizar_tarea(self, d_id: str, t_id: str, exito: bool):
        if exito:
            tareas_service.incrementar_completados(t_id)
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.INACTIVO)
        else:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.ERROR)
        self.tt_detener_flags.pop(d_id, None)
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
        Ejecuta like + comentario + compartir en cada dispositivo.

        Regla: 1 comentario = 1 cuenta. Sin repeticiones.

        - comentario string → 1 cuenta, se usa una sola vez
        - comentario list[str] → N cuentas, un comentario distinto por cuenta
        - comentario vacío → like + compartir sin comentar
        - Multi-dispositivo: la lista se reparte equitativamente
        """
        # Normalizar comentarios
        if isinstance(comentario, list) and len(comentario) > 0:
            comentarios = [c for c in comentario if isinstance(c, str) and c.strip()]
        elif isinstance(comentario, str):
            c = comentario.strip()
            comentarios = [c] if c else []
        else:
            comentarios = ["Excelente contenido! 🔥"]

        if not any(c.strip() for c in comentarios):
            comentarios = []

        num_dispositivos = len(dispositivos_ids)

        for i, d_id in enumerate(dispositivos_ids):
            # Repartir comentarios entre dispositivos
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
            self.tt_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_flujo_multi_cuenta,
                args=(d_id, link, comentarios_dispositivo, flag, tarea_id),
                daemon=True,
            ).start()

    def _worker_flujo_multi_cuenta(self, d_id, link, comentarios, flag, t_id):
        """Worker: like + comentario + compartir. TikTok maneja su propia rotación de cuentas."""
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            automator = TiktokAutomator(d_id, skip_reset=True)

            print(f"📋 [{d_id}] {automator.cuentas_por_dispositivo} cuentas configuradas", flush=True)
            print(f"💬 [{d_id}] {len(comentarios)} comentario(s) asignados", flush=True)

            # 1. LIKE
            print(f"--- [{d_id}] LIKE ---", flush=True)
            likes = automator.proceso_likes(link, flag)
            print(f"   👍 {likes} like(s)", flush=True)
            if flag and flag.is_set():
                self._finalizar_tarea(d_id, t_id, False)
                return

            # 2. COMENTARIO (solo si hay texto)
            c_ok = 0
            if comentarios:
                print(f"--- [{d_id}] COMENTARIOS ({len(comentarios)}) ---", flush=True)
                c_ok = automator.proceso_comentarios(link, comentarios, flag)
                print(f"   💬 {c_ok} comentario(s) publicados", flush=True)
                if flag and flag.is_set():
                    self._finalizar_tarea(d_id, t_id, False)
                    return
            else:
                print(f"--- [{d_id}] COMENTARIO (omitido - sin texto) ---", flush=True)

            # 3. COMPARTIR
            print(f"--- [{d_id}] COMPARTIR ---", flush=True)
            compartidas = automator.proceso_compartidas(link, flag)
            print(f"   📤 {compartidas} compartida(s)", flush=True)

            print(f"📊 [{d_id}] Flujo completado: {likes}L / {c_ok}C / {compartidas}S", flush=True)
            self._finalizar_tarea(d_id, t_id, True)

        except Exception as e:
            print(f"❌ [{d_id}] Error en worker TikTok: {e}", flush=True)
            self._finalizar_tarea(d_id, t_id, False)

    # ── CALENTAMIENTO ──

    def ejecutar_calentamiento(self, dispositivos_ids: List[str], tarea_id: str):
        """Lanza calentamiento ultra-random en cada dispositivo."""
        for d_id in dispositivos_ids:
            flag = threading.Event()
            self.tt_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_calentamiento,
                args=(d_id, flag, tarea_id),
                daemon=True,
            ).start()

    def _worker_calentamiento(self, d_id: str, flag: threading.Event, t_id: str):
        """Worker de calentamiento TikTok en un dispositivo."""
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            automator = TiktokAutomator(d_id, skip_reset=True)
            automator.proceso_calentamiento(detener_flag=flag)
            self._finalizar_tarea(d_id, t_id, True)
        except Exception as e:
            print(f"❌ [{d_id}] Error calentamiento TT: {e}", flush=True)
            self._finalizar_tarea(d_id, t_id, False)


tiktok_service = TiktokService()
