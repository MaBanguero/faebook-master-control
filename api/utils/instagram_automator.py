"""
Instagram Automator — automatización de Instagram con uiautomator2.
Selectores verificados con dump de UI real.
"""
import os
import time
import random
import threading
from collections import deque
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()
CUSTOM_ADB_PORT = int(os.getenv('CUSTOM_ADB_PORT', '5037'))
os.environ['ANDROID_ADB_SERVER_PORT'] = str(CUSTOM_ADB_PORT)

import uiautomator2 as u2

PACKAGE = "com.instagram.android"


class InstagramAutomator:
    def __init__(self, device_id: str, skip_reset: bool = False):
        self.device_id = device_id
        self.device: Optional[u2.Device] = None
        self.cuentas_usadas: List[str] = []
        self.sin_cuentas_disponibles = False
        self.cuentas_por_dispositivo = int(os.getenv('CUENTAS_POR_DISPOSITIVO', '5'))

        print(f"⚙️ [IG][{self.device_id}] {self.cuentas_por_dispositivo} cuentas configuradas")

        if not self._verificar_conexion():
            raise Exception(f"Dispositivo {self.device_id} no disponible")

        if not skip_reset:
            self._reset_services()
        else:
            print(f"⏩ [IG][{self.device_id}] Reset omitido")

        self._connect()

    # ── conexión ──────────────────────────────────────────────

    def _verificar_conexion(self) -> bool:
        import subprocess
        try:
            r = subprocess.run(
                ['adb', '-P', str(CUSTOM_ADB_PORT), 'devices'],
                capture_output=True, text=True, timeout=10
            )
            return f"{self.device_id}\tdevice" in r.stdout
        except Exception:
            return False

    def _reset_services(self):
        try:
            import subprocess
            for cmd in [
                ['adb', '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'am', 'force-stop', 'com.github.uiautomator'],
                ['adb', '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'pkill', '-9', 'uiautomator'],
                ['adb', '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'pkill', '-9', 'atd'],
                ['adb', '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'settings', 'put', 'secure', 'enabled_accessibility_services', 'null'],
            ]:
                subprocess.run(cmd, capture_output=True, timeout=5)
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ [IG][{self.device_id}] Reset warning: {e}")

    def _connect(self):
        self.device = u2.connect(self.device_id)
        print(f"✅ [IG][{self.device_id}] Conectado via uiautomator2")

    # ── utilidades ────────────────────────────────────────────

    def random_sleep(self, lo: int, hi: int):
        t = random.randint(lo, hi)
        print(f"💤 [IG][{self.device_id}] Sleep {t}s")
        time.sleep(t)

    def short_sleep(self, s: float = 2.0):
        time.sleep(s)

    def press_back(self):
        self.device.press("back")
        self.short_sleep(1)

    def double_tap(self):
        w, h = self.device.window_size()
        print(f"👆👆 [IG][{self.device_id}] Doble tap ({w//2}, {h//2})")
        self.device.double_click(w // 2, h // 2)

    def _should_stop(self, flag, ctx: str) -> bool:
        if flag and flag.is_set():
            print(f"[IG][{self.device_id}] Stop en {ctx}")
            return True
        return False

    def _hay_cuentas(self, proceso: str) -> bool:
        if self.sin_cuentas_disponibles:
            print(f"[IG][{self.device_id}] Sin cuentas para {proceso}")
            return False
        return True

    # ── apertura de links ────────────────────────────────────

    def open_instagram_link(self, link: str):
        """Abre un link de Instagram usando el package explícito."""
        print(f"📱 [IG][{self.device_id}] Abriendo link...")
        self.short_sleep(2)
        self.device.shell(
            f'am start -a android.intent.action.VIEW -d "{link}" '
            f'{PACKAGE}'
        )
        self.random_sleep(2, 4)
        self.device.set_orientation("natural")
        self.random_sleep(5, 10)
        print(f"✅ [IG][{self.device_id}] Link abierto")

    def _restart_app(self):
        print(f"[IG][{self.device_id}] Reiniciando Instagram...")
        self.device.app_stop(PACKAGE)
        self.random_sleep(3, 6)
        self.device.app_start(PACKAGE)
        self.random_sleep(5, 10)
        print(f"[IG][{self.device_id}] Instagram reiniciado")

    # ── cambio de cuenta ─────────────────────────────────────

    def cambiar_cuenta(self, seg_min: int = 5, seg_max: int = 15) -> bool:
        """
        Cambia de cuenta en Instagram. Abre el perfil, toca el username
        en la barra superior, y selecciona una cuenta no usada.
        """
        try:
            print(f"[IG][{self.device_id}] Rotando cuenta...")
            self.device.app_stop(PACKAGE)
            self.random_sleep(2, 4)
            self.random_sleep(seg_min, seg_max)
            self.device.app_start(PACKAGE)
            self.random_sleep(5, 8)

            # 1. Ir a Perfil
            perfil_tab = 'com.instagram.android:id/profile_tab'
            if not self.device(resourceId=perfil_tab).exists:
                print(f"[IG][{self.device_id}] Tab Perfil no encontrado")
                return False
            self.device(resourceId=perfil_tab).click()
            self.random_sleep(3, 5)

            # 2. Tocar el username para abrir account switcher
            title_rid = 'com.instagram.android:id/action_bar_title'
            if not self.device(resourceId=title_rid).exists:
                print(f"[IG][{self.device_id}] Username no encontrado")
                return False
            self.device(resourceId=title_rid).click()
            self.random_sleep(3, 5)

            # 3. Seleccionar cuenta no usada
            # Solo considerar texto que parezca username: letras, números, _, .
            import re
            cuenta_seleccionada = False
            for elem in self.device.xpath('//*').all():
                try:
                    txt = (elem.info.get('text') or '').strip()
                except Exception:
                    continue
                if not txt:
                    continue

                # Validar que sea un username real de Instagram
                # Username: solo [a-z0-9_.], sin espacios, entre 3 y 30 chars
                if not re.match(r'^[a-zA-Z0-9_.]{3,30}$', txt):
                    continue
                # Excluir cosas que no son cuentas
                if txt.lower() in ['agregar cuenta de instagram', 'add account']:
                    continue
                if txt in self.cuentas_usadas:
                    continue

                print(f"[IG][{self.device_id}] Cambiando a: {txt}")
                elem.click()
                self.cuentas_usadas.append(txt)
                self.random_sleep(3, 5)
                cuenta_seleccionada = True
                break

            if not cuenta_seleccionada:
                print(f"[IG][{self.device_id}] Todas las cuentas usadas")
                return False

            print(f"[IG][{self.device_id}] Cambio de cuenta OK")
            return True

        except Exception as e:
            print(f"[IG][{self.device_id}] Error rotando cuenta: {e}")
            return False

    # ── procesos ─────────────────────────────────────────────

    def proceso_likes(self, link: str, detener_flag=None) -> int:
        """Like en un reel/post de Instagram."""
        if not self._hay_cuentas("likes"):
            return 0

        like_rid = 'com.instagram.android:id/like_button'
        self._restart_app()
        print(f"[IG][{self.device_id}] Abriendo para like: {link}")
        self.open_instagram_link(link)

        # Ver video un rato antes
        watch = random.randint(8, 20)
        print(f"[IG][{self.device_id}] Viendo {watch}s...")
        time.sleep(watch)

        if self._should_stop(detener_flag, "likes"):
            return 0

        if self.device(resourceId=like_rid).exists:
            self.device(resourceId=like_rid).click()
            print(f"[IG][{self.device_id}] Like ✅")
            self.random_sleep(1, 3)
            self.press_back()
            return 1

        print(f"[IG][{self.device_id}] Botón like no encontrado")
        return 0

    def proceso_comentarios(self, link: str, comentarios: List[str], detener_flag=None) -> int:
        """Comentario en un reel/post de Instagram."""
        if not self._hay_cuentas("comentarios"):
            return 0

        comentarios = [c.strip() for c in (comentarios or []) if c and c.strip()]
        if not comentarios:
            return 0

        comment_btn_rid = 'com.instagram.android:id/comment_button'
        comment_input_rid = 'com.instagram.android:id/comment_composer_text_view'
        post_btn_rid = 'com.instagram.android:id/layout_comment_thread_post_button_icon'

        publicados = 0
        for comentario in comentarios:
            if self._should_stop(detener_flag, "comentarios"):
                break

            try:
                self._restart_app()
                print(f"[IG][{self.device_id}] Comentario: {comentario}")
                self.open_instagram_link(link)
                self.random_sleep(5, 10)

                # 1. Click en botón comentario
                btn = self.device(resourceId=comment_btn_rid)
                if not btn.exists:
                    print(f"[IG][{self.device_id}] Botón comentario no encontrado")
                    break
                btn.click()
                self.random_sleep(2, 3)

                # 2. Click en campo de texto
                inp = self.device(resourceId=comment_input_rid)
                if not inp.exists:
                    print(f"[IG][{self.device_id}] Campo comentario no encontrado")
                    break
                inp.click()
                self.short_sleep(1)

                # 3. Escribir
                self.device.send_keys(comentario, clear=True)
                self.short_sleep(2)

                # 4. Click en Publicar
                post_btn = self.device(resourceId=post_btn_rid)
                if post_btn.exists:
                    post_btn.click()
                    self.short_sleep(2)
                    publicados += 1
                    print(f"[IG][{self.device_id}] Comentario #{publicados} ✅")
                else:
                    print(f"[IG][{self.device_id}] Botón Publicar no encontrado")

            except Exception as e:
                print(f"[IG][{self.device_id}] Error comentario: {e}")
            finally:
                self.device.press("home")
                self.short_sleep(2)

        return publicados

    def proceso_compartir(self, link: str, detener_flag=None) -> int:
        """Compartir un reel/post de Instagram (repost o enviar)."""
        if not self._hay_cuentas("compartir"):
            return 0

        share_rid = 'com.instagram.android:id/direct_share_button'
        self._restart_app()
        print(f"[IG][{self.device_id}] Abriendo para compartir: {link}")
        self.open_instagram_link(link)
        self.random_sleep(5, 10)

        if self._should_stop(detener_flag, "compartir"):
            return 0

        if self.device(resourceId=share_rid).exists:
            self.device(resourceId=share_rid).click()
            self.random_sleep(2, 3)
            # Cerrar el popup de compartir si aparece
            self.press_back()
            print(f"[IG][{self.device_id}] Compartir ✅")
            return 1

        print(f"[IG][{self.device_id}] Botón compartir no encontrado")
        return 0

    # ═══════════════════════════════════════════════════════════════
    # CALENTAMIENTO DE CUENTA (ultra-random)
    # ═══════════════════════════════════════════════════════════════

    def proceso_calentamiento(self, detener_flag=None):
        """
        Calentamiento de cuenta Instagram ultra-random.
        Simula comportamiento humano real: scroll Reels, Explore, Stories,
        likes, saves, follows esporádicos. Sesiones de duración variable
        con pausas aleatorias. Rota cuentas entre sesiones.
        """
        if not self._hay_cuentas("calentamiento"):
            return

        # ── Selectores ──
        REELS_TAB = 'com.instagram.android:id/reel_tab'
        EXPLORE_TAB = 'com.instagram.android:id/explore_tab'
        HOME_TAB = 'com.instagram.android:id/tab_home_button'
        LIKE_BTN = 'com.instagram.android:id/like_button'
        SAVE_BTN = 'com.instagram.android:id/save_button'
        COMMENT_BTN = 'com.instagram.android:id/comment_button'
        FOLLOW_BTN = 'com.instagram.android:id/follow_button'
        STORIES_TRAY = 'com.instagram.android:id/reel_viewer_container'

        def chance(pct: float) -> bool:
            return random.random() * 100 < pct

        def _scroll_feed(direction="up", scale=None):
            """Scroll con escala random para simular scrolls largos o cortos."""
            s = scale or random.uniform(0.3, 0.9)
            try:
                if direction == "up":
                    self.device.swipe_ext("up", scale=s)
                elif direction == "down":
                    self.device.swipe_ext("down", scale=s)
            except Exception:
                pass
            self.short_sleep(random.uniform(0.5, 2.0))

        def _scroll_comments(num=3):
            """Entra a comentarios, hace scroll, sale sin comentar."""
            btn = self.device(resourceId=COMMENT_BTN)
            if not btn.exists:
                return False
            btn.click()
            self.random_sleep(1, 3)
            for _ in range(num):
                _scroll_feed("up", scale=0.7)
                self.short_sleep(random.uniform(0.5, 1.5))
            self.press_back()
            return True

        def _watch_reel():
            """Mira un reel con duración random y decide si interactuar."""
            watch = random.randint(2, 45)
            print(f"[IG][{self.device_id}] Viendo reel {watch}s...")
            time.sleep(watch)

            if self._should_stop(detener_flag, "watch"):
                return

            # Like (~35% probabilidad)
            if chance(35):
                like = self.device(resourceId=LIKE_BTN)
                if like.exists:
                    like.click()
                    print(f"   ❤️ Like")
                    self.short_sleep(0.3)

            # Save (~8%)
            if chance(8):
                save = self.device(resourceId=SAVE_BTN)
                if save.exists:
                    save.click()
                    print(f"   🔖 Guardado")
                    self.short_sleep(0.3)

            # Mirar comentarios (~25%)
            if chance(25):
                _scroll_comments(random.randint(1, 4))

            # Share (~3%)
            if chance(3):
                share_rid = 'com.instagram.android:id/direct_share_button'
                shr = self.device(resourceId=share_rid)
                if shr.exists:
                    shr.click()
                    self.short_sleep(2)
                    self.press_back()

            # Seguir (~2% - muy raro durante calentamiento)
            if chance(2):
                fw = self.device(resourceId=FOLLOW_BTN)
                if fw.exists:
                    fw.click()
                    print(f"   👤 Follow")
                    self.short_sleep(0.5)

        def _browse_reels(minutos=8):
            """Navega por Reels durante X minutos."""
            print(f"[IG][{self.device_id}] 📱 Navegando Reels ~{minutos}min...")
            self._restart_app()
            # Ir a Reels tab
            reel_tab = self.device(resourceId=REELS_TAB)
            if reel_tab.exists:
                reel_tab.click()
                self.random_sleep(2, 4)
            else:
                # Si no hay Reels tab dedicada, usar feed
                print(f"[IG][{self.device_id}] Reels tab no encontrada, usando feed")
                home = self.device(resourceId=HOME_TAB)
                if home.exists:
                    home.click()
                    self.random_sleep(2, 4)

            deadline = time.time() + (minutos * 60)
            reels_vistos = 0

            while time.time() < deadline:
                if self._should_stop(detener_flag, "reels"):
                    break

                # ~80% scroll up (siguiente reel), ~15% pausa y mira, ~5% scroll back
                roll = random.randint(1, 100)
                if roll <= 80:
                    _watch_reel()
                    reels_vistos += 1
                    _scroll_feed("up")
                elif roll <= 95:
                    # Pausa sin scroll — como si el usuario se distrajera
                    pause = random.randint(3, 20)
                    print(f"[IG][{self.device_id}] Pausa humana {pause}s...")
                    time.sleep(pause)
                else:
                    # Scroll back — como si quisiera volver a ver
                    _scroll_feed("down", scale=0.5)
                    self.short_sleep(1)
                    _watch_reel()

                # Cada ~8 reels, mini-pausa
                if reels_vistos > 0 and reels_vistos % random.randint(6, 12) == 0:
                    p = random.randint(10, 45)
                    print(f"[IG][{self.device_id}] Mini-descanso {p}s...")
                    time.sleep(p)

            return reels_vistos

        def _browse_explore(minutos=5):
            """Navega por Explore con scrolls lentos (como buscando contenido)."""
            print(f"[IG][{self.device_id}] 🔍 Navegando Explore ~{minutos}min...")
            explore = self.device(resourceId=EXPLORE_TAB)
            if not explore.exists:
                print(f"[IG][{self.device_id}] Explore tab no encontrada")
                return

            explore.click()
            self.random_sleep(2, 4)

            deadline = time.time() + (minutos * 60)
            while time.time() < deadline:
                if self._should_stop(detener_flag, "explore"):
                    break

                # Scroll lento simulando búsqueda visual
                for _ in range(random.randint(1, 3)):
                    _scroll_feed("up", scale=random.uniform(0.2, 0.5))
                    time.sleep(random.uniform(1, 4))

                # ~20% abrir un post del explore
                if chance(20):
                    # Tap en centro-pantalla (aproximadamente donde está el contenido)
                    w, h = self.device.window_size()
                    self.device.click(w // 2, int(h * 0.35))
                    self.random_sleep(3, 8)
                    # Scroll comentarios
                    if chance(40):
                        _scroll_comments(random.randint(1, 3))
                    self.press_back()
                    self.short_sleep(1)

                # Pausa random
                time.sleep(random.randint(2, 8))

        def _watch_stories():
            """Mira stories si hay disponibles (sin interactuar)."""
            print(f"[IG][{self.device_id}] 👁️ Revisando Stories...")
            # Las stories suelen estar en la parte superior — tap centro-arriba
            w, h = self.device.window_size()
            # La primera story bubble suele estar aprox en x=10% ancho, y=8% alto
            story_x = int(w * 0.1)
            story_y = int(h * 0.06)
            self.device.click(story_x, story_y)
            self.random_sleep(2, 4)

            # Ver algunas stories (3-10)
            num_stories = random.randint(3, 10)
            for _ in range(num_stories):
                if self._should_stop(detener_flag, "stories"):
                    break
                watch = random.randint(2, 8)
                time.sleep(watch)
                # Tap derecho para siguiente story
                self.device.click(int(w * 0.85), h // 2)
                self.short_sleep(0.3)

            # Salir de stories
            self.press_back()
            self.short_sleep(1)

        # ── FLUJO PRINCIPAL ──
        session_seconds = random.randint(5 * 60, 45 * 60)
        break_seconds = random.randint(5 * 60, 60 * 60)

        print(f"[IG][{self.device_id}] 🔥 CALENTAMIENTO IG: {session_seconds // 60}min sesión, {break_seconds // 60}min descanso")

        try:
            self._restart_app()

            # Armar plan de actividades random
            actividades = []
            # Siempre Reels como base
            actividades.append(("reels", random.randint(3, 15)))
            # ~70% agregar Explore
            if chance(70):
                actividades.append(("explore", random.randint(2, 8)))
            # ~40% mirar Stories
            if chance(40):
                actividades.append(("stories", 0))  # duración implícita
            # ~15% segunda ronda de Reels
            if chance(15):
                actividades.append(("reels", random.randint(2, 8)))

            # Barajar orden
            random.shuffle(actividades)

            # Si hay stories, ponerlas al inicio (más natural: abrir IG → ver stories primero)
            stories_act = [a for a in actividades if a[0] == "stories"]
            otras_act = [a for a in actividades if a[0] != "stories"]
            random.shuffle(otras_act)
            actividades = stories_act + otras_act

            print(f"[IG][{self.device_id}] Plan: {[f'{a}({m}m)' for a, m in actividades]}")

            session_end = time.time() + session_seconds
            for actividad, minutos in actividades:
                if time.time() >= session_end:
                    break
                if self._should_stop(detener_flag, f"act-{actividad}"):
                    break

                if actividad == "reels":
                    # Ajustar duración para no pasarse del tiempo total
                    remaining = max(1, int((session_end - time.time()) / 60))
                    duracion = min(minutos, remaining)
                    if duracion > 0:
                        _browse_reels(duracion)
                elif actividad == "explore":
                    remaining = max(1, int((session_end - time.time()) / 60))
                    duracion = min(minutos, remaining)
                    if duracion > 0:
                        _browse_explore(duracion)
                elif actividad == "stories":
                    _watch_stories()

            print(f"[IG][{self.device_id}] ✅ Calentamiento IG completado")

        except Exception as e:
            print(f"[IG][{self.device_id}] ❌ Error calentamiento IG: {e}")
            raise
        finally:
            try:
                self.device.app_stop(PACKAGE)
            except Exception:
                pass

            # Descanso entre sesiones
            if not (detener_flag and detener_flag.is_set()):
                print(f"[IG][{self.device_id}] 😴 Descanso {break_seconds // 60}min...")
                break_end = time.time() + break_seconds
                while time.time() < break_end:
                    if detener_flag and detener_flag.is_set():
                        break
                    time.sleep(min(30, break_end - time.time()))

        # Rotar cuenta para siguiente sesión
        self._post_rotacion("calentamiento", 5 * 60, 30 * 60, detener_flag)
        self.device.app_stop(PACKAGE)
        self.random_sleep(2, 5)

    def _post_rotacion(self, proceso: str, seg_min: int, seg_max: int, flag):
        if self._should_stop(flag, f"post-{proceso}"):
            return False
        if self.sin_cuentas_disponibles:
            return False
        if len(self.cuentas_usadas) >= self.cuentas_por_dispositivo:
            self.sin_cuentas_disponibles = True
            return False
        if not self.cambiar_cuenta(seg_min, seg_max):
            self.sin_cuentas_disponibles = True
            return False
        return True
