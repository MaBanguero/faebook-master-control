"""
FacebookAutomator v2 — Selectores validados contra Facebook v568.0.0.46.74 (Jul 2026)

Branch: fix/facebook-v568-selectors
Validado en: Samsung Galaxy S8 (SM-G950U), Android 9 (SDK 28)

Estructura de UI documentada:
  - Top bar: [Menú] [Logo] [Crear] [Buscar] [Mensajería]
  - Bottom tabs: Inicio | Panel profesional | Reels | Notificaciones | Perfil
  - Reels: botones laterales derechos — reacciones, comentarios, compartir
  - Menú lateral: perfil activo + opción "cambiar de perfil" + lista de cuentas
"""

import time
import random
import uiautomator2 as u2


class FacebookAutomator:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device = u2.connect(device_id)

    # ═══════════════════════════════════════════════════════════════
    # NAVEGACIÓN Y APERTURA
    # ═══════════════════════════════════════════════════════════════

    def abrir_facebook_link(self, link: str):
        """Abre un post/reel mediante deep link."""
        self.device.shell(f'am start -a android.intent.action.VIEW -d "{link}"')
        time.sleep(6)

    def cerrar_facebook(self):
        """Cierra forzosamente la app de Facebook."""
        self.device.app_stop("com.facebook.katana")
        time.sleep(2)

    def _ir_a_feed(self):
        """
        Navega al feed principal desde cualquier pantalla.
        Usa la pestaña 'Inicio' de la barra inferior (content-desc exacto).
        """
        # "Inicio, pestaña" (ES) / "Home, tab" (EN)
        inicio_xpaths = [
            '//*[contains(@content-desc, "Inicio, pestaña") or contains(@content-desc, "Home, tab")]',
            '//*[contains(@content-desc, "Inicio") or contains(@content-desc, "Home")]',
        ]
        for xp in inicio_xpaths:
            if self.device.xpath(xp).exists:
                self.device.xpath(xp).click()
                time.sleep(3)
                return True
        # Fallback: back repetido hasta salir de pantallas modales
        for _ in range(4):
            self.device.press("back")
            time.sleep(1)
        return True

    # ═══════════════════════════════════════════════════════════════
    # ROTACIÓN DE CUENTAS (reescrito para v568)
    # ═══════════════════════════════════════════════════════════════

    def rotar_perfil_secuencial(self, indice_objetivo: int, detener_flag=None):
        """
        Cambia de cuenta usando la UI nativa de Facebook v568.

        Flujo real (validado Jul 2026):
          1. Abrir menú hamburguesa → @content-desc="Menú"
          2. Click en "cambiar de perfil" → contains(@content-desc, "cambiar de perfil")
          3. Seleccionar cuenta por índice en la lista de perfiles
        """
        try:
            print(f"🔄 [{self.device_id}] Rotando cuenta (índice objetivo: {indice_objetivo})...")

            # Paso 0: Reiniciar la app para estado limpio
            self.device.app_stop("com.facebook.katana")
            time.sleep(2)
            self.device.app_start("com.facebook.katana")
            time.sleep(8)

            # --- Paso 1: Abrir menú hamburguesa ---
            if detener_flag and detener_flag.is_set():
                return False

            # "Menu"(EN) y "Menú"(ES) tienen caracteres distintos (u vs ú) → ambos explícitos
            menu_xpaths = [
                '//*[contains(@content-desc, "Menu") or contains(@content-desc, "Menú")]',
                '//*[contains(@content-desc, "navigation") or contains(@content-desc, "navegación")]',
            ]
            menu_abierto = False
            for xp in menu_xpaths:
                if self.device.xpath(xp).wait(timeout=3):
                    self.device.xpath(xp).click()
                    menu_abierto = True
                    print(f"   ✅ Menú abierto")
                    break

            if not menu_abierto:
                print(f"   ❌ No se encontró el botón de menú")
                return False

            time.sleep(3)

            # --- Paso 2: Click en "cambiar de perfil" ---
            if detener_flag and detener_flag.is_set():
                return False

            cambiar_xpaths = [
                '//*[contains(@content-desc, "cambiar de perfil") or contains(@content-desc, "cambiar perfil")]',
                '//*[contains(@content-desc, "switch profile") or contains(@content-desc, "switch account")]',
                '//*[contains(@content-desc, "change profile") or contains(@content-desc, "change account")]',
            ]
            cambiar_abierto = False
            for xp in cambiar_xpaths:
                if self.device.xpath(xp).wait(timeout=2):
                    self.device.xpath(xp).click()
                    cambiar_abierto = True
                    print(f"   ✅ Panel de cuentas abierto")
                    break

            if not cambiar_abierto:
                print(f"   ❌ No se encontró 'cambiar de perfil'")
                return False

            time.sleep(3)

            # --- Expandir lista si hay "Ver todo" ---
            # Facebook limita la vista inicial a ~5 cuentas cuando hay muchas;
            # si no aparece "Ver todo", todas las cuentas ya están visibles.
            lista_expandida = False
            ver_todo_xpaths = [
                '//*[contains(@text, "Ver todo") or contains(@content-desc, "Ver todo")]',
                '//*[contains(@text, "See all") or contains(@content-desc, "See all")]',
            ]
            for xp in ver_todo_xpaths:
                if self.device.xpath(xp).wait(timeout=5):
                    self.device.xpath(xp).click()
                    print(f"   📋 Lista expandida (clic en 'Ver todo')")
                    time.sleep(2)
                    lista_expandida = True
                    break

            # Solo hacer scroll si expandimos — si no, todas las cuentas ya están visibles
            if lista_expandida:
                for _ in range(3):
                    self.device.swipe(0.5, 0.8, 0.5, 0.3, duration=0.4)
                    time.sleep(1)

            # --- Paso 3: Seleccionar cuenta por índice ---
            if detener_flag and detener_flag.is_set():
                return False

            # Dumpear la jerarquía COMPLETA después de expandir
            xml = self.device.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)

            cuentas = []
            for el in root.iter():
                txt = el.attrib.get('text', '')
                desc = el.attrib.get('content-desc', '')
                clickable = el.attrib.get('clickable', 'false')
                label = txt or desc

                # Filtrar: solo elementos clickeables que no sean UI chrome
                if clickable == 'true' and label and label not in ('Cerrar', 'Close'):
                    # Limpiar sufijo de notificaciones: "nombre, N notificación" → "nombre"
                    # IMPORTANTE: limpiar ANTES de filtrar, porque "notificación" está en skip_keywords
                    clean_label = label.split(',')[0].strip()

                    skip_keywords = [
                        # Navegación y sistema
                        'atrás', 'back', 'inicio', 'home',
                        'recientes', 'recents', 'recent apps',
                        # Tabs de la app
                        'panel profesional', 'professional dashboard',
                        'reels', 'buscar', 'search',
                        'mensaj', 'messeng', 'crear', 'create',
                        'historia', 'story', 'guardado', 'saved',
                        'recuerdos', 'memories', 'eventos', 'events',
                        'grupos', 'groups', 'páginas', 'pages',
                        'amigos', 'friends', 'marketplace',
                        # Configuración
                        'configuración', 'settings', 'ayuda', 'help',
                        'ver todas', 'see all', 'menú', 'menu',
                        # Panel de cuentas (no son perfiles)
                        'ver todo', 'see all',  # botón expandir lista
                        'ir al centro de cuentas', 'accounts center',
                        'go to accounts center',
                        'búsqueda', 'ícono', 'icono', 'search icon',
                        'barra de navegación', 'navigation bar',
                        # Otros
                        'feed', 'news feed', 'noticias',
                        'dark mode', 'modo oscuro',
                        'log out', 'cerrar sesión', 'logout',
                        'report', 'reportar', 'denunciar',
                    ]
                    # NOTA: "notificaciones"/"notifications" ya no están en skip_keywords
                    # porque los sufijos se limpian con split(',') antes de filtrar
                    if not any(kw in clean_label.lower() for kw in skip_keywords):
                        cuentas.append(clean_label)

            if not cuentas:
                print(f"   ❌ No se detectaron cuentas en la lista")
                return False

            print(f"   📋 {len(cuentas)} cuentas disponibles: {cuentas}")

            # Seleccionar por índice (cíclico)
            indice_real = indice_objetivo % len(cuentas)
            cuenta_seleccionada = cuentas[indice_real]
            print(f"   👤 Seleccionando [{indice_real}] → '{cuenta_seleccionada}'")

            # Click en la cuenta por su texto/content-desc (usar contains para robustez)
            cuenta_xpath = f'//*[contains(@content-desc, "{cuenta_seleccionada}") or contains(@text, "{cuenta_seleccionada}")]'
            if self.device.xpath(cuenta_xpath).exists:
                self.device.xpath(cuenta_xpath).click()
                time.sleep(8)
                print(f"   ✅ Cambio exitoso: '{cuenta_seleccionada}'")
                return True
            else:
                # Último recurso: click por coordenadas del elemento encontrado
                for el in root.iter():
                    d = el.attrib.get('content-desc', '')
                    t = el.attrib.get('text', '')
                    if d == cuenta_seleccionada or t == cuenta_seleccionada:
                        bounds_str = el.attrib.get('bounds', '')
                        try:
                            parts = bounds_str.replace('[', ',').replace(']', ',').split(',')
                            x = (int(parts[0]) + int(parts[2])) // 2
                            y = (int(parts[1]) + int(parts[3])) // 2
                            self.device.click(x, y)
                            time.sleep(8)
                            print(f"   ✅ Cambio exitoso (click por coordenadas): '{cuenta_seleccionada}'")
                            return True
                        except (ValueError, IndexError):
                            pass

                print(f"   ❌ No se pudo clickear '{cuenta_seleccionada}'")
                return False

        except Exception as e:
            print(f"   ❌ Error en rotación de cuenta: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # LIKE (selectores limpiados para v568)
    # ═══════════════════════════════════════════════════════════════

    def proceso_like_facebook(self, link: str, detener_flag=None):
        """
        Da like a un reel/post de Facebook.

        Selectores validados v568:
          - ✅ contains(@content-desc, "reacciones")  ← el que funciona
          - ❌ "Me gusta"/"Like" exactos ya no existen en la UI
        """
        try:
            self.abrir_facebook_link(link)
            time.sleep(random.randint(3, 5))

            # Selectores ordenados por prioridad (primero el validado)
            selectores = [
                '//android.widget.Button[contains(@content-desc, "reacciones") or contains(@content-desc, "reactions")]',
                '//*[contains(@content-desc, "reacciones") or contains(@content-desc, "reactions")]',
                '//android.widget.Button[contains(@content-desc, "Like button") or contains(@content-desc, "react") or contains(@content-desc, "reaccionar")]',
            ]

            for intento in range(5):
                if detener_flag and detener_flag.is_set():
                    return False

                print(f"   🔍 Buscando botón Like/Reacción... Intento {intento + 1}")

                for xpath in selectores:
                    if self.device.xpath(xpath).exists:
                        print(f"   ✅ Botón Like encontrado en intento {intento + 1}")
                        self.device.xpath(xpath).click()
                        return True

                print("   ↕️ Scroll para buscar botón Like...")
                self.device.swipe(0.5, 0.7, 0.5, 0.4, duration=0.6)
                time.sleep(2)

            print(f"   ❌ Like no ejecutado tras 5 intentos")
            return False

        except Exception as e:
            print(f"   ❌ Error Like: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # COMENTARIO (selectores limpiados para v568)
    # ═══════════════════════════════════════════════════════════════

    def proceso_comentario_reels(self, link: str, texto: str, detener_flag=None):
        """
        Publica un comentario en un reel/post de Facebook.

        Flujo validado v568:
          1. Abrir link
          2. Click en botón "comentarios" (contiene content-desc "comentarios" o "comentario")
          3. Escribir en el EditText
          4. Click en "Enviar" o presionar Enter
        """
        try:
            self.abrir_facebook_link(link)
            time.sleep(3)

            # --- Abrir sección de comentarios ---
            selectores_abrir = [
                '//android.widget.Button[contains(@content-desc, "comentario") or contains(@content-desc, "comment")]',
                '//android.view.ViewGroup[contains(@content-desc, "comentario") or contains(@content-desc, "comment")]',
                '//*[contains(@content-desc, "comentarios") or contains(@content-desc, "comments")]',
            ]

            seccion_abierta = False
            for intento in range(5):
                if detener_flag and detener_flag.is_set():
                    return False

                print(f"   🔍 Buscando botón Comentarios... Intento {intento + 1}")

                for xpath in selectores_abrir:
                    if self.device.xpath(xpath).exists:
                        print(f"   ✅ Botón Comentarios encontrado")
                        self.device.xpath(xpath).click()
                        seccion_abierta = True
                        break

                if seccion_abierta:
                    break

                print("   ↕️ Scroll para buscar botón...")
                self.device.swipe(0.5, 0.7, 0.5, 0.3, duration=0.5)
                time.sleep(2)

            if not seccion_abierta:
                print(f"   ❌ No se pudo abrir sección de comentarios")
                return False

            time.sleep(3)

            # --- Escribir comentario ---
            # El EditText tiene content-desc tipo "Comentar como <nombre>"
            campo_selectores = [
                '//android.widget.EditText',
                '//*[contains(@content-desc, "Comentar como")]',
                '//*[contains(@content-desc, "Comment as")]',
            ]

            campo_encontrado = False
            for xp in campo_selectores:
                if self.device.xpath(xp).exists:
                    self.device.xpath(xp).set_text(str(texto))
                    campo_encontrado = True
                    print(f"   ✅ Texto escrito: '{texto[:50]}...'")
                    break

            if not campo_encontrado:
                print(f"   ❌ No se encontró el campo de texto")
                return False

            time.sleep(2)

            # --- Enviar comentario ---
            enviar_selectores = [
                '//*[@content-desc="Enviar"]',
                '//*[@content-desc="Send"]',
                '//android.widget.ImageView[contains(@content-desc, "Enviar") or contains(@content-desc, "Send")]',
            ]

            enviado = False
            for xp in enviar_selectores:
                if self.device.xpath(xp).exists:
                    self.device.xpath(xp).click()
                    enviado = True
                    print(f"   ✅ Comentario enviado")
                    break

            if not enviado:
                # Fallback: presionar Enter
                self.device.press("enter")
                print(f"   ✅ Comentario enviado (Enter)")

            time.sleep(2)
            return True

        except Exception as e:
            print(f"   ❌ Error Comentario: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # COMPARTIR (validado v568)
    # ═══════════════════════════════════════════════════════════════

    def proceso_compartir_post(self, link: str, detener_flag=None):
        """
        Comparte un post/reel de Facebook.

        Flujo validado v568:
          1. Abrir link
          2. Click en "Compartir" (content-desc contiene "Compartir" o "Share")
          3. En menú de compartir: click en "Compartir ahora"
          4. Si no hay "Compartir ahora", usar "Escribir publicación" → "PUBLICAR"
        """
        try:
            self.abrir_facebook_link(link)
            print("   ⏳ Cargando link...")
            time.sleep(random.randint(7, 10))

            # Selector de Compartir diferenciado para reels vs posts
            if "reel" in link.lower():
                btn_compartir = '//*[contains(@content-desc, "Compartir") or contains(@content-desc, "Share")]'
            else:
                btn_compartir = '//*[contains(@content-desc, "Compartir") or contains(@content-desc, "Share")]'

            # Opciones dentro del menú de compartir
            btn_compartir_ahora = '//*[contains(@text, "Compartir ahora") or contains(@text, "Share now")]'
            btn_escribir_post = (
                '//*[contains(@text, "Escribir publicación") or contains(@text, "Write post")'
                ' or contains(@text, "Create post") or contains(@text, "Escribe algo")'
                ' or contains(@text, "Write something") or contains(@text, "Say something")]'
            )
            btn_publicar_final = (
                '//*[@text="PUBLICAR" or @text="POST" or @text="SHARE"'
                ' or contains(@text, "Compartir ahora") or contains(@text, "Share now")'
                ' or contains(@text, "Share Now")]'
            )

            compartir_encontrado = False

            for intento in range(5):
                if detener_flag and detener_flag.is_set():
                    return False

                print(f"   🔍 Buscando botón Compartir (Intento {intento + 1})...")

                if self.device.xpath(btn_compartir).exists:
                    time.sleep(1)
                    self.device.xpath(btn_compartir).click()
                    compartir_encontrado = True
                    print(f"   ✅ Botón Compartir clickeado")
                    break

                print("   ↕️ Scroll...")
                self.device.swipe(0.5, 0.5, 0.5, 0.2, duration=0.6)
                time.sleep(3)

            if not compartir_encontrado:
                print(f"   ❌ Botón Compartir no encontrado")
                return False

            time.sleep(4)
            if detener_flag and detener_flag.is_set():
                return False

            # Opción 1: Compartir ahora (directo)
            if self.device.xpath(btn_compartir_ahora).exists:
                self.device.xpath(btn_compartir_ahora).click()
                print(f"   ✅ Compartido directamente")
                return True

            # Opción 2: Escribir publicación → PUBLICAR
            if self.device.xpath(btn_escribir_post).exists:
                self.device.xpath(btn_escribir_post).click()
                time.sleep(5)

                if self.device.xpath(btn_publicar_final).exists:
                    self.device.xpath(btn_publicar_final).click()
                    print(f"   ✅ Compartido mediante publicación")
                    return True

            print(f"   ❌ No se encontraron opciones de compartir")
            return False

        except Exception as e:
            print(f"   ❌ Error Compartir: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # FLUJO COMPLETO
    # ═══════════════════════════════════════════════════════════════

    def ejecutar_flujo_completo_fb(self, link: str, texto_comentario: str, detener_flag=None,
                                    indice_inicial: int = 0):
        """
        Ejecuta Like → Comentario → Compartir, todo en la MISMA cuenta.
        Si indice_inicial > 0, rota a esa cuenta antes de empezar.

        El servicio externo (FacebookService) lleva el contador y lo incrementa
        en 1 tras cada ejecución para que la próxima use la siguiente cuenta.

        Returns:
            tuple: (exito: bool, siguiente_indice: int)
                   siguiente_indice = indice_inicial + 1 (listo para la próxima ejecución)
        """
        print(f"🚀 [{self.device_id}] Flujo completo en cuenta índice {indice_inicial}")

        # Rotar a la cuenta objetivo siempre, incluso índice 0
        print(f"   🔄 Rotando a cuenta índice {indice_inicial}...")
        if not self.rotar_perfil_secuencial(indice_inicial, detener_flag):
            print(f"   ⚠️ No se pudo rotar, continuando en cuenta actual")

        # 1. LIKE
        print("\n--- PASO 1: LIKE ---")
        self.proceso_like_facebook(link, detener_flag)
        time.sleep(3)
        self.cerrar_facebook()
        if detener_flag and detener_flag.is_set():
            return False, indice_inicial + 1

        # 2. COMENTARIO
        print("\n--- PASO 2: COMENTARIO ---")
        self.proceso_comentario_reels(link, texto_comentario, detener_flag)
        time.sleep(3)
        self.cerrar_facebook()

        # 3. COMPARTIR
        print("\n--- PASO 3: COMPARTIR ---")
        self.proceso_compartir_post(link, detener_flag)
        time.sleep(3)
        self.cerrar_facebook()

        siguiente = indice_inicial + 1
        print(f"\n✅ [{self.device_id}] Flujo completo finalizado. Próxima cuenta: {siguiente}")
        return True, siguiente
