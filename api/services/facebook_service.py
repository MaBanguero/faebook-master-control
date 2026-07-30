import threading
import random
from typing import List
from api.services.dispositivo_service import dispositivo_service
from api.services.tareas_service import tareas_service
from api.models import DispositivoEstado
from api.utils.facebook_automator import FacebookAutomator
from api.utils.interaction_tracker import tracker
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

    def detener_todos(self):
        for flag in self.fb_detener_flags.values():
            flag.set()
        self.fb_detener_flags.clear()

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
            dev = dispositivo_service.obtener_dispositivo(d_id)
            adb_id = dev.adb_id if dev else d_id
            automator = FacebookAutomator(adb_id)
            exito = automator.rotar_perfil_secuencial(indice, flag)
            self._finalizar_tarea(d_id, t_id, exito)
        except Exception:
            self._finalizar_tarea(d_id, t_id, False)

    def ejecutar_likes(self, d_ids, link, t_id):
        for d_id in d_ids:
            flag = threading.Event()
            threading.Thread(target=self._worker_like, args=(d_id, link, flag, t_id), daemon=True).start()

    def _worker_like(self, d_id, link, flag, t_id):
        dev = dispositivo_service.obtener_dispositivo(d_id)
        adb_id = dev.adb_id if dev else d_id
        automator = FacebookAutomator(adb_id)

        # Obtener cuentas y filtrar por las que AÚN NO han likeado este link
        cuentas = automator.obtener_cuentas()
        disponibles = [c for c in cuentas if not tracker.is_interacted(adb_id, c, link, "like")]

        if not cuentas:
            print(f"❌ [{d_id}] Sin cuentas configuradas en Facebook")
            self._finalizar_tarea(d_id, t_id, False)
            return

        if not disponibles:
            print(f"✅ [{d_id}] Todas las {len(cuentas)} cuentas ya likearon este link. Saltando.")
            self._finalizar_tarea(d_id, t_id, True)
            return

        print(f"📋 [{d_id}] {len(disponibles)}/{len(cuentas)} cuentas disponibles para like")

        exitos = 0
        for cuenta in disponibles:
            if flag and flag.is_set():
                break
            print(f"   🔄 [{d_id}] Rotando a '{cuenta}'...")
            if automator.rotar_a_cuenta(cuenta, flag):
                exito = automator.proceso_like_facebook(link, flag)
                if exito:
                    tracker.record(adb_id, cuenta, link, "like")
                    exitos += 1
                    print(f"   ✅ [{d_id}] Like: '{cuenta}' → OK")
                else:
                    print(f"   ❌ [{d_id}] Like: '{cuenta}' → FALLÓ")
            else:
                print(f"   ⚠️ [{d_id}] No se pudo rotar a '{cuenta}'")

        self._finalizar_tarea(d_id, t_id, exitos > 0)

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
        dev = dispositivo_service.obtener_dispositivo(d_id)
        adb_id = dev.adb_id if dev else d_id
        automator = FacebookAutomator(adb_id)
        exito = automator.proceso_comentario_reels(link, texto, flag)
        self._finalizar_tarea(d_id, t_id, exito)

    def _finalizar_tarea(self, d_id, t_id, exito):
        if exito:
            tareas_service.incrementar_completados(t_id)
        dispositivo_service.actualizar_estado(d_id, DispositivoEstado.INACTIVO)
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
            dev = dispositivo_service.obtener_dispositivo(d_id)
            adb_id = dev.adb_id if dev else d_id
            automator = FacebookAutomator(adb_id)
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

    def ejecutar_flujo_multi_cuenta(self, dispositivos_ids: List[str], link: str,
                                     comentario, tarea_id: str, cuentas_a_usar: int = 0):
        """
        Ejecuta el flujo completo en múltiples cuentas por dispositivo.

        Regla: 1 comentario = 1 cuenta. Sin repeticiones.

        - comentario string → 1 cuenta al azar, el comentario se usa una sola vez
        - comentario list[str] → N cuentas al azar, un comentario distinto por cuenta
        - Multi-dispositivo: la lista se reparte equitativamente entre dispositivos
        """
        # Normalizar comentarios
        if isinstance(comentario, list) and len(comentario) > 0:
            comentarios = [c for c in comentario if isinstance(c, str) and c.strip()]
        elif isinstance(comentario, str):
            comentarios = [comentario]
        else:
            comentarios = ["Excelente contenido! 🔥"]

        num_dispositivos = len(dispositivos_ids)

        for i, d_id in enumerate(dispositivos_ids):
            # Repartir comentarios entre dispositivos — siempre si hay más de 1 dispositivo
            if num_dispositivos > 1:
                chunk_size = max(1, len(comentarios) // num_dispositivos)
                inicio = i * chunk_size
                if i == num_dispositivos - 1:
                    comentarios_dispositivo = comentarios[inicio:]
                else:
                    comentarios_dispositivo = comentarios[inicio:inicio + chunk_size]
            else:
                comentarios_dispositivo = comentarios

            # Siempre lanzar worker — si no hay comentarios, hace like + compartir sin comentar
            flag = threading.Event()
            self.fb_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_flujo_multi_cuenta,
                args=(d_id, link, comentarios_dispositivo, flag, tarea_id),
                daemon=True
            ).start()

    def _worker_flujo_multi_cuenta(self, d_id, link, comentarios, flag, t_id):
        """Worker: 1 cuenta = 1 flujo (like+comentario+compartir). Tracking por nombre."""
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            dev = dispositivo_service.obtener_dispositivo(d_id)
            adb_id = dev.adb_id if dev else d_id
            automator = FacebookAutomator(adb_id)

            # Obtener cuentas reales y filtrar
            cuentas = automator.obtener_cuentas()
            disponibles = [c for c in cuentas if not tracker.is_interacted(adb_id, c, link, "like")]

            if not cuentas:
                print(f"❌ [{d_id}] Sin cuentas configuradas en Facebook")
                self._finalizar_tarea(d_id, t_id, False)
                return

            if not disponibles:
                print(f"✅ [{d_id}] Todas las {len(cuentas)} cuentas ya likearon este link. Saltando.")
                self._finalizar_tarea(d_id, t_id, True)
                return

            print(f"📋 [{d_id}] {len(disponibles)}/{len(cuentas)} cuentas disponibles")
            print(f"💬 [{d_id}] {len(comentarios)} comentario(s) asignados")

            # Emparejar cuentas con comentarios (1 a 1)
            n = min(len(disponibles), len(comentarios) if comentarios else len(disponibles))
            exitos = 0
            fallos = 0

            for i in range(n):
                if flag and flag.is_set():
                    break
                cuenta = disponibles[i]
                texto = comentarios[i] if i < len(comentarios) else ""

                print(f"\n🔁 [{d_id}] {i+1}/{n}: '{cuenta}'")
                if automator.rotar_a_cuenta(cuenta, flag):
                    exito, _ = automator.ejecutar_flujo_completo_fb(link, texto, flag)
                    if exito:
                        tracker.record(adb_id, cuenta, link, "like")
                        exitos += 1
                    else:
                        fallos += 1
                else:
                    fallos += 1

            exito_total = exitos > 0 and fallos == 0
            print(f"\n📊 [{d_id}] Multi-flujo: {exitos} éxitos, {fallos} fallos de {n} cuentas")
            self._finalizar_tarea(d_id, t_id, exito_total)

        except Exception as e:
            print(f"❌ Error en worker multi-cuenta: {e}")
            self._finalizar_tarea(d_id, t_id, False)
    def _worker_flujo_completo(self, d_id, link, comentario, flag, t_id):
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            dev = dispositivo_service.obtener_dispositivo(d_id)
            adb_id = dev.adb_id if dev else d_id
            automator = FacebookAutomator(adb_id)

            # Obtener cuentas y filtrar disponibles
            cuentas = automator.obtener_cuentas()
            disponibles = [c for c in cuentas if not tracker.is_interacted(adb_id, c, link, "like")]

            if not disponibles:
                print(f"✅ [{d_id}] Todas las cuentas ya likearon este link. Saltando.")
                self._finalizar_tarea(d_id, t_id, True)
                return

            # Usar la primera cuenta disponible
            cuenta = disponibles[0]
            print(f"🔁 [{d_id}] Usando cuenta: '{cuenta}' ({len(disponibles)} disponibles)")

            if automator.rotar_a_cuenta(cuenta, flag):
                exito, _ = automator.ejecutar_flujo_completo_fb(link, comentario, flag)
                if exito:
                    tracker.record(adb_id, cuenta, link, "like")
            else:
                exito = False

            self._finalizar_tarea(d_id, t_id, exito)
        except Exception as e:
            print(f"Error en worker flujo completo: {e}")
            self._finalizar_tarea(d_id, t_id, False)

    # ── CALENTAMIENTO ──

    def ejecutar_calentamiento(self, dispositivos_ids: List[str], tarea_id: str):
        """Lanza calentamiento ultra-random en cada dispositivo."""
        for d_id in dispositivos_ids:
            if d_id not in self.contadores_rotacion:
                self.contadores_rotacion[d_id] = 0
            indice = self.contadores_rotacion[d_id]

            flag = threading.Event()
            self.fb_detener_flags[d_id] = flag
            threading.Thread(
                target=self._worker_calentamiento,
                args=(d_id, indice, flag, tarea_id),
                daemon=True,
            ).start()

    def _worker_calentamiento(self, d_id: str, indice: int, flag: threading.Event, t_id: str):
        """Worker de calentamiento Facebook en un dispositivo."""
        try:
            dispositivo_service.actualizar_estado(d_id, DispositivoEstado.TRABAJANDO)
            dev = dispositivo_service.obtener_dispositivo(d_id)
            adb_id = dev.adb_id if dev else d_id
            automator = FacebookAutomator(adb_id)
            siguiente = automator.proceso_calentamiento(
                detener_flag=flag,
                indice_inicial=indice,
            )
            self.contadores_rotacion[d_id] = siguiente
            self._finalizar_tarea(d_id, t_id, True)
        except Exception as e:
            print(f"❌ [{d_id}] Error calentamiento FB: {e}", flush=True)
            self._finalizar_tarea(d_id, t_id, False)


facebook_service = FacebookService()