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

    def rotar_a_cuenta(self, nombre_cuenta: str, detener_flag=None) -> bool:
        """
        Rota a una cuenta específica por nombre.
        Obtiene la lista actual de cuentas, busca el nombre exacto,
        y rota a ese índice.
        """
        cuentas = self.obtener_cuentas()
        if not cuentas:
            print(f"   ❌ No se pudieron obtener cuentas")
            return False
        try:
            idx = cuentas.index(nombre_cuenta)
        except ValueError:
            print(f"   ⚠️ Cuenta '{nombre_cuenta}' no encontrada en la lista actual")
            return False
        return self.rotar_perfil_secuencial(idx, detener_flag)

    def rotar_perfil_secuencial(self, indice_objetivo: int, detener_flag=None):
        """
        Cambia de cuenta usando la UI nativa de Facebook v568.

        Flujo real (validado Jul 2026):
          1. Abrir menú hamburguesa → @content-desc="Menú"
          2. Click en "cambiar de perfil" → contains(@content-desc, "cambiar de perfil")
          3. Seleccionar cuenta por índice en la lista de perfiles

        Tolerancia: 3 intentos totales — internet lento puede causar que los perfiles
        no aparezcan en el primer intento.
        """
        for intento_global in range(3):
            if intento_global > 0:
                print(f"   🔄 [{self.device_id}] Reintento {intento_global+1}/3 por perfiles no cargados...")
                time.sleep(3)

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

                # "Menu"(EN)/"Menú"(ES)/"menu"(v539 lowercase) — todos explícitos
                menu_xpaths = [
                    '//*[contains(@content-desc, "Menu") or contains(@content-desc, "Menú") or contains(@content-desc, "menu")]',
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
                    if intento_global < 2:
                        continue
                    return False

                time.sleep(3)

                # --- Detectar tipo de UI ---
                # v541/v549: cuentas visibles directamente en el menú (sin sub-menú)
                # v553/v571: requiere click en "cambiar de perfil" → sub-menú
                xml = self.device.dump_hierarchy()
                tiene_profile_switcher = "profile switcher" in xml.lower()

                if tiene_profile_switcher:
                    # UI tipo v541/v549: cuentas visibles directo en el menú
                    cuentas_directas = self._parse_cuentas_xml(xml)
                    if cuentas_directas:
                        indice_real = indice_objetivo % len(cuentas_directas)
                        cuenta = cuentas_directas[indice_real]
                        print(f"   📋 {len(cuentas_directas)} cuentas visibles: {cuentas_directas}")
                        print(f"   👤 Seleccionando [{indice_real}] → '{cuenta}'")
                        cuenta_xpath = f'//*[contains(@content-desc, "{cuenta}") or contains(@text, "{cuenta}")]'
                        if self.device.xpath(cuenta_xpath).exists:
                            self.device.xpath(cuenta_xpath).click()
                            time.sleep(8)
                            print(f"   ✅ Cambio exitoso: '{cuenta}' (v541/v549 directo)")
                            return True
                    # Si profile_switcher estaba pero parse falló → reintentar
                    if intento_global < 2:
                        continue
                    return False

                # --- Paso 2: Click en "cambiar de perfil" (tipo clásico) ---
                if detener_flag and detener_flag.is_set():
                    return False

                cambiar_xpaths = [
                    '//*[contains(@content-desc, "cambiar de perfil") or contains(@content-desc, "cambiar perfil") or contains(@content-desc, "Switch profile") or contains(@content-desc, "Switch account") or contains(@content-desc, "Change profile") or contains(@content-desc, "Change account")]',
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
                    print(f"   ❌ No se encontró 'cambiar de perfil' (intento {intento_global+1}/3)")
                    if intento_global < 2:
                        continue
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
                cuentas = self._parse_cuentas_xml(xml)

                if not cuentas:
                    print(f"   ❌ No se detectaron cuentas en la lista (intento {intento_global+1}/3)")
                    if intento_global < 2:
                        continue
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
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(xml)
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

                    print(f"   ❌ No se pudo clickear '{cuenta_seleccionada}' (intento {intento_global+1}/3)")
                    if intento_global < 2:
                        continue
                    return False

            except Exception as e:
                print(f"   ❌ Error en rotación de cuenta (intento {intento_global+1}/3): {e}")
                if intento_global < 2:
                    continue
                return False

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
                btn_compartir = '//*[contains(@content-desc, "Compartir") or contains(@content-desc, "Share") or contains(@content-desc, "Send")]'
            else:
                btn_compartir = '//*[contains(@content-desc, "Compartir") or contains(@content-desc, "Share") or contains(@content-desc, "Send")]'

            # Opciones dentro del menú de compartir
            btn_compartir_ahora = '//*[contains(@text, "Compartir ahora") or contains(@text, "Share now") or contains(@text, "Share Now") or contains(@text, "SHARE NOW") or contains(@content-desc, "Compartir ahora") or contains(@content-desc, "Share now")]'
            btn_escribir_post = (
                '//*[contains(@text, "Escribir publicación") or contains(@text, "Write post")'
                ' or contains(@text, "Create post") or contains(@text, "Escribe algo")'
                ' or contains(@text, "Write something") or contains(@text, "Say something") or contains(@content-desc, "Escribir publicacion") or contains(@content-desc, "Write post")]'
            )
            btn_publicar_final = (
                '//*[@text="PUBLICAR" or @text="POST" or @text="SHARE" or @text="Share"'
                ' or contains(@text, "Compartir ahora") or contains(@text, "Share now")'
                ' or contains(@text, "Share Now") or contains(@content-desc, "Share now")]'
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

    def obtener_cuentas(self):
        """
        Navega al panel de cuentas y devuelve la lista de nombres de perfiles
        disponibles, sin cambiar de cuenta.

        Returns:
            list[str]: nombres de cuentas disponibles, o lista vacía si falla.
        """
        for intento in range(3):
            try:
                if intento > 0:
                    print(f"   🔄 Reintento {intento+1}/3...")
                    time.sleep(3)

                # 0. Asegurar pantalla encendida
                self.device.screen_on()
                time.sleep(1)

                # 1. Forzar cierre y reapertura de Facebook
                self.device.app_stop("com.facebook.katana")
                time.sleep(2)
                self.device.app_start("com.facebook.katana")

                # 2. Esperar a que FB esté en foreground (max 15s)
                for _ in range(30):
                    time.sleep(0.5)
                    try:
                        focus = self.device.shell("dumpsys window | grep mCurrentFocus")
                        if "com.facebook.katana" in focus:
                            break
                    except Exception:
                        pass
                time.sleep(3)

                # 3. Detectar si está en pantalla de login (basado en UI, no en dumpsys)
                #    dumpsys window mCurrentFocus puede reportar LoginActivity
                #    brevemente durante el arranque incluso con sesión activa.
                try:
                    xml_check = self.device.dump_hierarchy()
                    login_keywords = ['Log in', 'Iniciar sesión', 'Create account', 'Crear cuenta',
                                      'Sign up', 'Registrarte', 'Forgot password', 'Olvidé']
                    feed_keywords = ['Home, tab', 'Inicio, pesta', 'News Feed', 'noticias',
                                     'Reels, tab', 'Notifications, tab', 'Profile, tab']
                    
                    tiene_feed = any(kw.lower() in xml_check.lower() for kw in feed_keywords)
                    tiene_login = any(kw.lower() in xml_check.lower() for kw in login_keywords)
                    
                    if tiene_login and not tiene_feed:
                        print(f"   ⚠️ Facebook en pantalla de login (UI) — sin sesión iniciada")
                        return []
                except Exception:
                    pass

                # 4. Menú
                # v539: "Facebook menu" (lowercase), v541+: "Menú"/"Menu"
                menu_xpaths = [
                    '//*[contains(@content-desc, "Menu") or contains(@content-desc, "Menú") or contains(@content-desc, "menu")]',
                    '//*[contains(@content-desc, "navigation") or contains(@content-desc, "navegación")]',
                ]
                for xp in menu_xpaths:
                    if self.device.xpath(xp).wait(timeout=5):
                        self.device.xpath(xp).click()
                        break
                else:
                    if intento < 2:
                        continue
                    return []
                time.sleep(3)

                # 5. Panel de cuentas vía profile switcher (v539/v541/v549/v553)
                #    Click en "Open profile switcher" → panel limpio sin basura del feed
                xml_menu = self.device.dump_hierarchy()
                if "profile switcher" in xml_menu.lower():
                    try:
                        print(f"   🔍 Abriendo panel de cuentas vía profile switcher...")
                        # Intentar múltiples selectores para el botón
                        ps_clicked = False
                        for ps_sel in [
                            self.device(descriptionContains="Open profile switcher"),
                            self.device(descriptionContains="profile switcher"),
                            self.device.xpath('//*[contains(@content-desc, "profile switcher")]'),
                        ]:
                            if ps_sel.wait(timeout=3):
                                ps_sel.click()
                                ps_clicked = True
                                break
                        if not ps_clicked:
                            print(f"   ❌ 'Open profile switcher' no encontrado")
                            if intento < 2:
                                continue
                            return []
                        time.sleep(3)

                        # 1. Parsear cuentas desde la posición inicial (tope del panel)
                        xml_inicial = self.device.dump_hierarchy()
                        cuentas_iniciales = self._parse_cuentas_xml(xml_inicial)

                        # 2. Buscar separador "your instagram profiles" para filtrar
                        separator_y = None
                        for kw in ['your instagram profiles', 'tus perfiles de instagram']:
                            if kw in xml_inicial.lower():
                                import re as _re, xml.etree.ElementTree as _ET
                                root = _ET.fromstring(xml_inicial)
                                for el in root.iter():
                                    txt = (el.attrib.get('text', '') + ' ' +
                                           el.attrib.get('content-desc', '')).lower()
                                    if kw in txt:
                                        bounds = el.attrib.get('bounds', '')
                                        m = _re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                                        if m:
                                            separator_y = int(m.group(2))
                                        break
                                break

                        # Si el separador no estaba visible, scrollear hasta encontrarlo
                        if not separator_y:
                            for _ in range(6):
                                self.device.swipe(500, 1100, 500, 600, steps=40)
                                time.sleep(1.5)
                                xml_ps = self.device.dump_hierarchy()
                                for kw in ['your instagram profiles', 'tus perfiles de instagram']:
                                    if kw in xml_ps.lower():
                                        import re as _re, xml.etree.ElementTree as _ET
                                        root = _ET.fromstring(xml_ps)
                                        for el in root.iter():
                                            txt = (el.attrib.get('text', '') + ' ' +
                                                   el.attrib.get('content-desc', '')).lower()
                                            if kw in txt:
                                                bounds = el.attrib.get('bounds', '')
                                                m = _re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                                                if m:
                                                    separator_y = int(m.group(2))
                                                break
                                        break
                                if separator_y:
                                    break

                        # 3. Filtrar cuentas por Y si hay separador (+50px buffer)
                        if separator_y:
                            cuentas = self._parse_cuentas_xml(xml_inicial, max_y=separator_y + 50)
                        else:
                            cuentas = cuentas_iniciales

                        # Si no encontramos cuentas, intentar "View all"
                        if not cuentas:
                            ver_todo_xpaths = [
                                '//*[contains(@text, "View all") or contains(@content-desc, "View all")]',
                                '//*[contains(@text, "Ver todo") or contains(@content-desc, "Ver todo")]',
                            ]
                            for xp in ver_todo_xpaths:
                                if self.device.xpath(xp).wait(timeout=3):
                                    self.device.xpath(xp).click()
                                    print(f"   📋 'View all' clickeado...")
                                    time.sleep(2)
                                    for _ in range(3):
                                        self.device.swipe(500, 1500, 500, 400, steps=20)
                                        time.sleep(1)
                                    xml_ps = self.device.dump_hierarchy()
                                    cuentas = self._parse_cuentas_xml(xml_ps)
                                    break

                        # Filtrar: remover "Open overflow menu", URLs, genéricos
                        basura = {'more', 'photo', 'rate this translation', 'see more',
                                  'see translation', 'notifications', 'upgrades',
                                  'open overflow menu', 'cancel', 'close'}
                        cuentas = [c for c in cuentas if c.lower() not in basura
                                   and not c.startswith('http')
                                   and '://' not in c]

                        if cuentas:
                            print(f"   ✅ {len(cuentas)} cuentas encontradas: {cuentas}")
                            return cuentas
                        print(f"   ⚠️ Panel abierto pero sin cuentas detectadas")

                    except Exception as e:
                        print(f"   ❌ Error en profile switcher: {e}")

                    if intento < 2:
                        continue
                    return []

                # 6. Cambiar perfil (tipo clásico v553/v571)
                cambiar_xpaths = [
                    '//*[contains(@content-desc, "cambiar de perfil") or contains(@content-desc, "cambiar perfil") or contains(@content-desc, "Switch profile") or contains(@content-desc, "Switch account") or contains(@content-desc, "Change profile") or contains(@content-desc, "Change account")]',
                    '//*[contains(@content-desc, "switch profile") or contains(@content-desc, "switch account")]',
                    '//*[contains(@content-desc, "change profile") or contains(@content-desc, "change account")]',
                ]
                for xp in cambiar_xpaths:
                    if self.device.xpath(xp).wait(timeout=2):
                        self.device.xpath(xp).click()
                        break
                else:
                    if intento < 2:
                        continue
                    return []
                time.sleep(3)

                # 7. Expandir "Ver todo" si existe
                lista_expandida = False
                ver_todo_xpaths = [
                    '//*[contains(@text, "Ver todo") or contains(@content-desc, "Ver todo")]',
                    '//*[contains(@text, "See all") or contains(@content-desc, "See all")]',
                ]
                for xp in ver_todo_xpaths:
                    if self.device.xpath(xp).wait(timeout=5):
                        self.device.xpath(xp).click()
                        time.sleep(2)
                        lista_expandida = True
                        break

                if lista_expandida:
                    for _ in range(3):
                        self.device.swipe(0.5, 0.8, 0.5, 0.3, duration=0.4)
                        time.sleep(1)

                # 8. Parsear cuentas
                xml = self.device.dump_hierarchy()
                cuentas = self._parse_cuentas_xml(xml)
                if cuentas:
                    return cuentas
                elif intento < 2:
                    continue

            except Exception as e:
                if intento < 2:
                    continue
                print(f"   ❌ Error obteniendo cuentas: {e}")

        return []
    def _parse_cuentas_xml(self, xml: str, max_y: int | None = None):
        """Parsea el XML del panel de cuentas y devuelve la lista de nombres.
        
        Args:
            xml: XML hierarchy dump
            max_y: Si se proporciona, solo incluye elementos con Y < max_y
                   (para filtrar perfiles de Facebook antes del separador Instagram)
        """
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)

        skip_keywords = [
            'atrás', 'back', 'inicio', 'home', 'recientes', 'recents', 'recent apps',
            'panel profesional', 'professional dashboard', 'reels', 'buscar', 'search',
            'mensaj', 'messeng', 'crear', 'create', 'historia', 'story', 'guardado', 'saved',
            'recuerdos', 'memories', 'eventos', 'events', 'grupos', 'groups', 'páginas', 'pages',
            'amigos', 'friends', 'marketplace', 'configuración', 'settings', 'ayuda', 'help',
            'ver todas', 'see all', 'menú', 'menu',
            'ver todo', 'ir al centro de cuentas', 'accounts center', 'go to accounts center',
            'búsqueda', 'ícono', 'icono', 'search icon', 'barra de navegación', 'navigation bar',
            'feed', 'news feed', 'noticias', 'dark mode', 'modo oscuro',
            'log out', 'cerrar sesión', 'logout', 'report', 'reportar', 'denunciar',
            'profile picture', 'profile switcher', 'dating',
            'see more', 'notifications', 'profile', 'ads center',
            'upgrade', '#', 'create facebook', 'open overflow',
            'accounts centre', 'go to accounts centre', 'view all',
        ]

        cuentas = []
        for el in root.iter():
            txt = el.attrib.get('text', '')
            desc = el.attrib.get('content-desc', '')
            clickable = el.attrib.get('clickable', 'false')
            label = txt or desc

            if clickable == 'true' and label and label not in ('Cerrar', 'Close', 'Cancelar', 'Cancel'):
                clean_label = label.split(',')[0].strip()
                # Filtrar: basura, URLs, posts largos (>60 chars = no es nombre de cuenta)
                if (len(clean_label) >= 3 and len(clean_label) <= 60
                        and not clean_label.startswith('http')
                        and '://' not in clean_label
                        and not any(kw in clean_label.lower() for kw in skip_keywords)):
                    # Filtrar por posición Y (perfiles FB antes del separador Instagram)
                    if max_y is not None:
                        bounds = el.attrib.get('bounds', '')
                        import re as _re2
                        m = _re2.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                        if m and int(m.group(2)) >= max_y:
                            continue  # debajo del separador → ignorar
                    if clean_label not in cuentas:
                        cuentas.append(clean_label)
        return cuentas

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

        # 2. COMENTARIO (solo si hay texto)
        if texto_comentario and texto_comentario.strip():
            print("\n--- PASO 2: COMENTARIO ---")
            self.proceso_comentario_reels(link, texto_comentario, detener_flag)
            time.sleep(3)
            self.cerrar_facebook()
        else:
            print("\n--- PASO 2: COMENTARIO (omitido - sin texto) ---")

        # 3. COMPARTIR
        print("\n--- PASO 3: COMPARTIR ---")
        self.proceso_compartir_post(link, detener_flag)
        time.sleep(3)
        self.cerrar_facebook()

        siguiente = indice_inicial + 1
        print(f"\n✅ [{self.device_id}] Flujo completo finalizado. Próxima cuenta: {siguiente}")
        return True, siguiente


    # ═══════════════════════════════════════════════════════════════
    # CALENTAMIENTO DE CUENTA v2 (comportamiento humano realista)
    # ═══════════════════════════════════════════════════════════════

    def proceso_calentamiento(self, detener_flag=None, indice_inicial: int = 0):
        """
        Calentamiento de cuenta Facebook con comportamiento humano realista.

        Caracteristicas:
          - Sesiones de 5-12min con orden de acciones aleatorio
          - Likes en 15-30% de posts vistos
          - Shares en 2-5% de posts
          - 1-3 solicitudes de amistad por sesion
          - Retencion variable en videos (40% full, 60% skip 2-6s)
          - 20% abrir comentarios, 30% like a 1-2 comentarios
          - Cerrar app tras sesion, descansar 15-45min
          - Bucle infinito por cuenta hasta detener_flag
        """
        import threading

        def chance(pct: float) -> bool:
            return random.random() * 100 < pct

        def _scroll(direction="up", scale=None, speed=None):
            s = scale or random.uniform(0.2, 0.9)
            dur = speed or random.randint(300, 900)
            try:
                if direction == "up":
                    self.device.swipe_ext("up", scale=s)
                elif direction == "down":
                    self.device.swipe_ext("down", scale=s)
            except Exception:
                w, h = self.device.window_size()
                mid_x = w // 2
                if direction == "up":
                    self.device.swipe(mid_x, int(h * 0.75), mid_x, int(h * 0.25), duration=dur / 1000)
                elif direction == "down":
                    self.device.swipe(mid_x, int(h * 0.25), mid_x, int(h * 0.75), duration=dur / 1000)
            time.sleep(random.uniform(0.3, 1.5))

        def _go_to_feed():
            inicio_xpaths = [
                '//*[contains(@content-desc, "Inicio, pesta") or contains(@content-desc, "Home, tab")]',
                '//*[contains(@content-desc, "Inicio") or contains(@content-desc, "Home")]',
                '//*[contains(@content-desc, "News Feed") or contains(@text, "Feed")]',
            ]
            for xp in inicio_xpaths:
                if self.device.xpath(xp).wait(timeout=2):
                    self.device.xpath(xp).click()
                    time.sleep(2)
                    return True
            for _ in range(4):
                self.device.press("back")
                time.sleep(1)
            return True

        def _go_to_reels():
            reels_xpaths = [
                '//*[contains(@content-desc, "Reels") or contains(@content-desc, "reels")]',
                '//*[contains(@content-desc, "Video") or contains(@content-desc, "video")]',
                '//*[contains(@text, "Reels")]',
            ]
            for xp in reels_xpaths:
                if self.device.xpath(xp).wait(timeout=3):
                    self.device.xpath(xp).click()
                    time.sleep(3)
                    return True
            return False

        def _try_react():
            like_xpaths = [
                '//*[contains(@content-desc, "reacciones") or contains(@content-desc, "reactions")]',
                '//*[contains(@content-desc, "Me gusta") or contains(@content-desc, "Like")]',
            ]
            for xp in like_xpaths:
                if self.device.xpath(xp).exists:
                    if chance(70):
                        self.device.xpath(xp).click()
                    else:
                        try:
                            self.device.xpath(xp).long_click()
                            time.sleep(2)
                            w, h = self.device.window_size()
                            reactions = [
                                (int(w * 0.25), int(h * 0.55)),
                                (int(w * 0.40), int(h * 0.50)),
                                (int(w * 0.55), int(h * 0.55)),
                                (int(w * 0.70), int(h * 0.55)),
                            ]
                            rx, ry = random.choice(reactions)
                            self.device.click(rx, ry)
                        except Exception:
                            self.device.xpath(xp).click()
                    time.sleep(random.uniform(0.3, 1.0))
                    return True
            return False

        def _open_comments():
            comment_xpaths = [
                '//*[contains(@content-desc, "comentario") or contains(@content-desc, "comment")]',
                '//*[contains(@content-desc, "Comentar") or contains(@content-desc, "Comment")]',
                '//*[contains(@text, "Comentar") or contains(@text, "Comment")]',
            ]
            for xp in comment_xpaths:
                if self.device.xpath(xp).exists:
                    self.device.xpath(xp).click()
                    time.sleep(2)
                    return True
            return False

        def _like_random_comments():
            # Buscar botones de like en comentarios (iconos pequenos)
            like_icon_xpaths = [
                '//*[contains(@content-desc, "Me gusta") or contains(@content-desc, "Like")]',
                '//*[contains(@content-desc, "reacciones") or contains(@content-desc, "reactions")]',
            ]
            liked = 0
            for xp in like_icon_xpaths:
                elements = self.device.xpath(xp).all()
                for el in elements[:3]:  # max 3 intentos
                    try:
                        el.click()
                        liked += 1
                        time.sleep(random.uniform(0.5, 1.5))
                        if liked >= random.randint(1, 2):
                            break
                    except Exception:
                        pass
                if liked > 0:
                    break
            return liked

        def _try_share():
            share_xpaths = [
                '//*[contains(@content-desc, "Compartir") or contains(@content-desc, "Share") or contains(@content-desc, "Send")]',
            ]
            for xp in share_xpaths:
                if self.device.xpath(xp).exists:
                    self.device.xpath(xp).click()
                    time.sleep(3)
                    ahora_xp = '//*[contains(@text, "Compartir ahora") or contains(@text, "Share now") or contains(@text, "Share Now") or contains(@text, "SHARE NOW")]'
                    if self.device.xpath(ahora_xp).exists:
                        self.device.xpath(ahora_xp).click()
                        time.sleep(2)
                        return True
                    else:
                        self.device.press("back")
                        time.sleep(1)
                    break
            return False

        def _send_friend_requests(count=0):
            if count == 0:
                count = random.randint(1, 3)

            sent = 0
            # Ir a la pestana de amigos
            friends_xpaths = [
                '//*[contains(@content-desc, "Amigos") or contains(@content-desc, "Friends")]',
                '//*[contains(@content-desc, "Solicitudes") or contains(@content-desc, "Friend requests")]',
            ]
            for xp in friends_xpaths:
                if self.device.xpath(xp).wait(timeout=3):
                    self.device.xpath(xp).click()
                    time.sleep(3)
                    break
            else:
                # Ir via menu
                _go_to_feed()
                time.sleep(2)
                # Buscar "People you may know" en el feed
                pass

            # Buscar botones "Agregar" o "Add Friend"
            for _ in range(count * 2):
                add_xpaths = [
                    '//*[contains(@text, "Agregar") or contains(@text, "Add Friend") or contains(@text, "Add friend")]',
                    '//*[contains(@content-desc, "Agregar") or contains(@content-desc, "Add Friend")]',
                ]
                found = False
                for xp in add_xpaths:
                    elements = self.device.xpath(xp).all()
                    for el in elements:
                        try:
                            el.click()
                            sent += 1
                            found = True
                            time.sleep(random.uniform(2, 5))
                            if sent >= count:
                                break
                        except Exception:
                            pass
                    if sent >= count:
                        break
                if sent >= count:
                    break
                if not found:
                    _scroll("up", scale=0.5)
                    time.sleep(random.uniform(1, 3))

            if sent > 0:
                print(f"   👥 {sent} solicitud(es) de amistad enviadas")
            _go_to_feed()
            return sent

        # ── BROWSING METHODS ───────────────────────────────────

        def _browse_feed(minutos=8):
            print(f"[FB][{self.device_id}] 📰 Navegando Feed ~{minutos}min...")
            self.device.app_stop("com.facebook.katana")
            time.sleep(2)
            self.device.app_start("com.facebook.katana")
            time.sleep(8)
            _go_to_feed()

            deadline = time.time() + (minutos * 60)
            posts_vistos = 0
            shares = 0

            while time.time() < deadline:
                if detener_flag and detener_flag.is_set():
                    break

                roll = random.randint(1, 100)

                if roll <= 55:  # Scroll normal + espera (simula lectura)
                    wait = random.uniform(3, 15)
                    time.sleep(wait)
                    _scroll("up", speed=random.randint(400, 900))
                    posts_vistos += 1

                elif roll <= 75:  # Scroll + like (15-30% efectivo sobre posts scrolleados)
                    wait = random.uniform(2, 8)
                    time.sleep(wait)
                    if chance(70):  # 70% de los que paran, likean
                        _try_react()
                    _scroll("up")
                    posts_vistos += 1

                elif roll <= 82:  # Abrir comentarios (20% de posts)
                    if _open_comments():
                        # Scroll en comentarios 5-15s
                        scroll_time = random.uniform(5, 15)
                        t0 = time.time()
                        while time.time() - t0 < scroll_time:
                            _scroll("up", scale=0.3, speed=600)
                            time.sleep(random.uniform(0.5, 2))
                        # 30% like a comentarios
                        if chance(30):
                            liked = _like_random_comments()
                            if liked:
                                print(f"   💬 Like a {liked} comentario(s)")
                        self.device.press("back")
                        time.sleep(1)
                    _scroll("up")
                    posts_vistos += 1

                elif roll <= 87:  # Share (2-5%)
                    if _try_share():
                        shares += 1
                        print(f"   📤 Compartido (#{shares})")
                    _scroll("up")

                elif roll <= 92:  # Pausa humana
                    pause = random.randint(8, 30)
                    time.sleep(pause)

                elif roll <= 97:  # Scroll back + react
                    _scroll("down", scale=0.3)
                    time.sleep(random.uniform(1, 3))
                    if chance(60):
                        _try_react()

                else:  # Ver notificaciones + volver
                    notif_xp = '//*[contains(@content-desc, "Notificaciones") or contains(@content-desc, "Notifications")]'
                    if self.device.xpath(notif_xp).exists:
                        self.device.xpath(notif_xp).click()
                        time.sleep(random.randint(3, 8))
                        for _ in range(random.randint(1, 3)):
                            _scroll("up", scale=0.4)
                        self.device.press("back")
                        time.sleep(2)

                # Mini-descanso cada varios posts
                if posts_vistos > 0 and posts_vistos % random.randint(8, 15) == 0:
                    p = random.randint(10, 60)
                    time.sleep(p)

            return posts_vistos, shares

        def _browse_reels(minutos=5):
            print(f"[FB][{self.device_id}] 🎬 Navegando Reels ~{minutos}min...")
            if not _go_to_reels():
                return 0

            time.sleep(3)
            deadline = time.time() + (minutos * 60)
            reels_vistos = 0

            while time.time() < deadline:
                if detener_flag and detener_flag.is_set():
                    break

                # 40%: ver reel completo, 60%: skip rapido
                if chance(40):
                    watch = random.randint(15, 60)  # reel completo
                else:
                    watch = random.randint(2, 6)  # skip rapido

                time.sleep(watch)

                # 25% reaccionar
                if chance(25):
                    _try_react()

                # 10% abrir comentarios en reels
                if chance(10):
                    if _open_comments():
                        time.sleep(random.uniform(3, 8))
                        if chance(30):
                            _like_random_comments()
                        self.device.press("back")
                        time.sleep(1)

                # Siguiente reel
                try:
                    self.device.swipe_ext("up", scale=0.9)
                except Exception:
                    w, h = self.device.window_size()
                    self.device.swipe(w // 2, int(h * 0.7), w // 2, int(h * 0.3))
                time.sleep(random.uniform(1, 3))
                reels_vistos += 1

                if reels_vistos % random.randint(8, 15) == 0:
                    p = random.randint(10, 30)
                    time.sleep(p)

            return reels_vistos

        # ── MAIN LOOP ──────────────────────────────────────────

        session_min = random.randint(5, 12)
        break_min = random.randint(15, 45)

        print(f"[FB][{self.device_id}] 🔥 CALENTAMIENTO v2: sesion={session_min}min, descanso={break_min}min")

        # Rotar a cuenta inicial
        if indice_inicial >= 0:
            self.rotar_perfil_secuencial(indice_inicial, detener_flag)

        cuenta_actual = indice_inicial

        # BUCLE INFINITO DE SESIONES
        while True:
            if detener_flag and detener_flag.is_set():
                break

            # Construir plan aleatorio para esta sesion
            actividades = []

            # Siempre feed
            feed_min = random.randint(3, 8)
            actividades.append(("feed", feed_min))

            # ~70% reels
            if chance(70):
                actividades.append(("reels", random.randint(2, 5)))

            # ~50% mas feed despues de reels
            if chance(50):
                actividades.append(("feed", random.randint(1, 4)))

            # Friend requests (1-3 por sesion)
            actividades.append(("friends", 0))

            # Notificaciones al inicio o final
            if chance(40):
                actividades.insert(0, ("notifications", 0))
            else:
                actividades.append(("notifications", 0))

            random.shuffle([a for a in actividades if a[0] not in ("friends", "notifications")])

            print(f"[FB][{self.device_id}] Plan sesion: {[(a, m) for a, m in actividades]}")

            session_end = time.time() + (session_min * 60)

            for actividad, minutos in actividades:
                if time.time() >= session_end:
                    break
                if detener_flag and detener_flag.is_set():
                    break

                remaining = max(1, int((session_end - time.time()) / 60))

                if actividad == "feed":
                    dur = min(minutos, remaining)
                    if dur > 0:
                        _browse_feed(dur)
                elif actividad == "reels":
                    dur = min(minutos, remaining)
                    if dur > 0:
                        _browse_reels(dur)
                elif actividad == "friends":
                    _send_friend_requests()
                elif actividad == "notifications":
                    notif_xp = '//*[contains(@content-desc, "Notificaciones") or contains(@content-desc, "Notifications")]'
                    if self.device.xpath(notif_xp).exists:
                        self.device.xpath(notif_xp).click()
                        time.sleep(random.randint(3, 10))
                        for _ in range(random.randint(1, 4)):
                            _scroll("up", scale=0.4)
                        self.device.press("back")
                        time.sleep(2)

            # CERRAR APP y DESCANSAR
            print(f"[FB][{self.device_id}] 😴 Cerrando app. Descanso {break_min}min...")
            self.cerrar_facebook()
            time.sleep(5)  # asegurar cierre

            # Descanso real (app cerrada)
            if detener_flag and detener_flag.is_set():
                break

            break_end = time.time() + (break_min * 60)
            while time.time() < break_end:
                if detener_flag and detener_flag.is_set():
                    break
                time.sleep(min(30, break_end - time.time()))

            if detener_flag and detener_flag.is_set():
                break

            # Rotar a siguiente cuenta
            cuenta_actual += 1
            print(f"[FB][{self.device_id}] Nueva sesion: cuenta indice {cuenta_actual}")
            try:
                self.rotar_perfil_secuencial(cuenta_actual, detener_flag)
            except Exception as e:
                print(f"[FB][{self.device_id}] Error rotando cuenta: {e}")

            # Re-randomizar duraciones para esta sesion
            session_min = random.randint(5, 12)
            break_min = random.randint(15, 45)

        print(f"[FB][{self.device_id}] Calentamiento detenido")
        return cuenta_actual + 1

