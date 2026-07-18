import os
import time
import random
import subprocess
import threading
from collections import deque
from typing import Optional, List
from dotenv import load_dotenv
import asyncio

# Cargar variables de entorno
load_dotenv()

# Configurar el puerto ADB desde .env (por defecto 5037)
CUSTOM_ADB_PORT = int(os.getenv('CUSTOM_ADB_PORT', '5037'))
os.environ['ANDROID_ADB_SERVER_PORT'] = str(CUSTOM_ADB_PORT)

# Ahora importar uiautomator2
import uiautomator2 as u2
from api.utils.comments_bank import get_random_comment

class TiktokAutomator:
    """Clase para automatización de TikTok con uiautomator2"""

    def __init__(self, device_id: str, skip_reset: bool = False):
        """
        Inicializa la conexión con el dispositivo
        
        Args:
            device_id: ID del dispositivo ADB
            skip_reset: Si True, omite el reset de servicios (ya se hizo en el startup)
        """
        self.device_id = device_id
        self.device: Optional[u2.Device] = None
        self.cuentas_usadas: List[str] = []  # Tracking de cuentas usadas en esta sesión
        self.sin_cuentas_disponibles = False
        
        # Leer número de cuentas desde variable de entorno (default: 5)
        self.cuentas_por_dispositivo = int(os.getenv('CUENTAS_POR_DISPOSITIVO', '5'))
        print(f"⚙️ [{self.device_id}] Configuración: {self.cuentas_por_dispositivo} cuentas por dispositivo")
        
        # PASO 1: Verificar que el dispositivo esté online
        if not self.verificar_y_reconectar():
            raise Exception(f"Dispositivo {self.device_id} no disponible")
        
        # PASO 2: Resetear dispositivo ANTES de conectar (solo si no se omitió)
        if not skip_reset:
            self._reset_device_services()
        else:
            print(f"⏩ [{self.device_id}] Reset omitido (ya realizado en startup)")
        
        # PASO 3: Conectar con uiautomator2
        self.connect()

    def _reset_device_services(self):
        """Resetea los servicios UIAutomator2 antes de conectar"""
        try:
            import subprocess
            ADB_PATH = 'adb'
            
            # Force-stop apps
            subprocess.run(
                [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'am', 'force-stop', 'com.github.uiautomator'],
                capture_output=True, timeout=5
            )
            
            # Matar procesos
            subprocess.run(
                [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'pkill', '-9', 'uiautomator'],
                capture_output=True, timeout=5
            )
            subprocess.run(
                [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'pkill', '-9', 'atd'],
                capture_output=True, timeout=5
            )
            
            # Limpiar accessibility services (KEY para "already registered")
            subprocess.run(
                [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', self.device_id, 'shell', 'settings', 'put', 'secure', 'enabled_accessibility_services', 'null'],
                capture_output=True, timeout=5
            )
            
            # Pequeña pausa para que los cambios tomen efecto
            time.sleep(0.5)
            
        except Exception as e:
            # No fallar si el reset falla, solo advertir
            print(f"⚠️ [{self.device_id}] Advertencia al resetear servicios: {e}")
    
    def connect(self):
        """Conecta con el dispositivo via uiautomator2"""
        try:
            self.device = u2.connect(self.device_id)
            print(f"✅ [{self.device_id}] Conectado via uiautomator2")
        except Exception as e:
            print(f"❌ [{self.device_id}] Error conectando: {e}")
            raise

    def verificar_y_reconectar(self) -> bool:
        """
        Verifica si el dispositivo está online y reconecta si es necesario
        
        Returns:
            True si el dispositivo está online, False si no se pudo reconectar
        """
        try:
            import subprocess
            ADB_PATH = r'adb'
            
            # Verificar si el dispositivo está online
            result = subprocess.run(
                [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), 'devices'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            devices_output = result.stdout
            
            # Verificar si nuestro dispositivo aparece como "device" (online)
            if f"{self.device_id}\tdevice" in devices_output:
                print(f"✅ [{self.device_id}] Dispositivo online")
                return True
            
            # Si no está online, intentar reconectar
            print(f"⚠️ [{self.device_id}] Dispositivo no online, intentando reconectar...")
            
            # Si es USB, solo necesitamos esperar
            if ":" not in self.device_id:
                print(f"🔌 [{self.device_id}] Dispositivo USB, esperando reconexión...")
                time.sleep(3)
                
                # Verificar de nuevo
                result = subprocess.run(
                    [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), 'devices'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if f"{self.device_id}\tdevice" in result.stdout:
                    print(f"✅ [{self.device_id}] Reconectado exitosamente")
                    # Reconectar uiautomator2
                    self.device = u2.connect(self.device_id)
                    return True
            else:
                # Si es WiFi, intentar reconectar
                print(f"📡 [{self.device_id}] Dispositivo WiFi, intentando reconectar...")
                subprocess.run(
                    [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), 'connect', self.device_id],
                    capture_output=True,
                    timeout=10
                )
                time.sleep(2)
                
                # Verificar de nuevo
                result = subprocess.run(
                    [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), 'devices'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if f"{self.device_id}\tdevice" in result.stdout:
                    print(f"✅ [{self.device_id}] Reconectado exitosamente")
                    # Reconectar uiautomator2
                    self.device = u2.connect(self.device_id)
                    return True
            
            print(f"❌ [{self.device_id}] No se pudo reconectar el dispositivo")
            return False
            
        except Exception as e:
            print(f"❌ [{self.device_id}] Error verificando conexión: {e}")
            return False
        
    ##############################################################
    # UTILERÍA COPY PASTE
    ##############################################################

    def random_sleep(self, min_seconds: int, max_seconds: int):
        """
        Sleep aleatorio para simular comportamiento humano
        
        Args:
            min_seconds: Mínimo de segundos
            max_seconds: Máximo de segundos
        """
        sleep_time = random.randint(min_seconds, max_seconds)
        print(f"💤 [{self.device_id}] Esperando {sleep_time} segundos...")
        time.sleep(sleep_time)
    
    def short_sleep(self, seconds: float = 2.0):
        """Sleep corto entre acciones"""
        time.sleep(seconds)

    def _dismiss_open_with_dialog(self) -> bool:
        """Descarta el modal 'Abrir con' si aparece al abrir un link."""
        try:
            # Buscar el texto "Abrir con" o "Open with" en el diálogo
            abrir_con = '//*[contains(@text,"Abrir con")]'
            open_with = '//*[contains(@text,"Open with")]'
            dialog_title = '//*[contains(@resource-id,"alertTitle") or contains(@resource-id,"title")]'

            # Esperar un momento a que aparezca el diálogo
            self.short_sleep(1.5)

            if self.element_exists(abrir_con) or self.element_exists(open_with):
                print(f"📋 [{self.device_id}] Detectado modal 'Abrir con'")

                # Opción 1: Tocar "TikTok" en la lista de apps
                tiktok_item = (
                    '//*[@text="TikTok"] | '
                    '//*[contains(@text,"TikTok")] | '
                    '//*[contains(@content-desc,"TikTok")]'
                )
                if self.element_exists(tiktok_item):
                    # Hacer doble tap o click normal sobre TikTok
                    self.short_sleep(0.5)
                    self.device.xpath(tiktok_item).click()
                    print(f"   ✅ TikTok seleccionado en modal")

                # Opción 2: Tocar "Solo una vez" o "Just once"
                solo_una_vez = '//*[contains(@text,"Solo una vez") or contains(@text,"Just once")]'
                siempre = '//*[contains(@text,"Siempre") or contains(@text,"Always")]'
                if self.element_exists(siempre):
                    self.device.xpath(siempre).click()
                    print(f"   ✅ 'Siempre' seleccionado")
                elif self.element_exists(solo_una_vez):
                    self.device.xpath(solo_una_vez).click()
                    print(f"   ✅ 'Solo una vez' seleccionado")

                self.random_sleep(1, 2)
                return True

            return False  # No se encontró el modal
        except Exception as e:
            print(f"⚠️ [{self.device_id}] Error descartando modal: {e}")
            return False

    def _dismiss_tiktok_modals(self, max_attempts: int = 4) -> bool:
        """
        Descarta modales comunes de TikTok: 'Guardar datos', 'Acceso a contactos',
        'Notificaciones', 'Sincronizar contactos', y otros diálogos de onboarding.

        Deniega todos los permisos y omite todas las pantallas de configuración.

        Args:
            max_attempts: Número máximo de intentos (cada iteración descarta UN modal)

        Returns:
            True si al menos un modal fue descartado, False si no se encontró ninguno
        """
        dismissed_any = False

        # Mapeo de textos de modal → textos del botón para descartar (ES + EN)
        # Cada entrada: (textos_del_modal, textos_del_boton_dismiss)
        modal_patterns = [
            # Guardar datos / Data Saver
            (
                ["Guardar datos", "Ahorrar datos", "Modo de ahorro", "ahorrar datos",
                 "Data Saver", "Save data", "Data saving"],
                ["Ahora no", "Omitir", "Saltar", "Not now", "Skip", "No, gracias",
                 "No thanks", "Desactivado", "Cancelar", "Cancel"]
            ),
            # Contactos / Contacts
            (
                ["Acceder a tus contactos", "Sincronizar contactos", "Encontrar amigos",
                 "Tus contactos", "Sincroniza tus contactos", "acceso a contactos",
                 "Access your contacts", "Find friends", "Sync contacts",
                 "Upload contacts", "Find your friends"],
                ["Denegar", "Ahora no", "Omitir", "Saltar", "Deny", "Not now",
                 "Skip", "No permitir", "Don't allow", "Cancelar", "Cancel"]
            ),
            # Notificaciones / Notifications
            (
                ["Activar notificaciones", "Recibir notificaciones",
                 "Permitir notificaciones", "notificaciones push",
                 "Turn on notifications", "Enable notifications",
                 "Get notifications", "Stay in the loop"],
                ["Ahora no", "Omitir", "Saltar", "Not now", "Skip",
                 "No, gracias", "Maybe later", "Cancelar", "Cancel"]
            ),
            # Perfil / Profile setup (find friends, interests, etc.)
            (
                ["Completa tu perfil", "Elige tus intereses",
                 "Personaliza tu experiencia", "Sigue a personas",
                 "Crea tu perfil", "Configura tu cuenta",
                 "Complete your profile", "Pick your interests"],
                ["Omitir", "Saltar", "Ahora no", "Skip", "Not now",
                 "Maybe later", "Cancelar", "Cancel"]
            ),
            # Generic deny-able permissions
            (
                ["Permitir", "Permiso", "Permission",
                 "Acceder a", "Access your", "Quiere acceder"],
                ["Denegar", "Deny", "Ahora no", "Not now",
                 "No permitir", "Don't allow"]
            ),
        ]

        for attempt in range(max_attempts):
            dismissed_this_round = False

            try:
                # Dump hierarchy once per attempt
                xml = self.device.dump_hierarchy()

                for modal_texts, dismiss_texts in modal_patterns:
                    # Check if any modal text is present
                    modal_found = False
                    for mt in modal_texts:
                        if mt.lower() in xml.lower():
                            modal_found = True
                            break

                    if not modal_found:
                        continue

                    # Modal detected → find and click the dismiss button
                    print(f"[TT][{self.device_id}] Modal detectado (intento {attempt+1})")

                    # Try each dismiss text
                    for dt in dismiss_texts:
                        # Try by text
                        el = self.device(text=dt)
                        if el.exists(timeout=0.5):
                            print(f"   🚫 [{self.device_id}] Clickeando '{dt}' para descartar modal")
                            el.click()
                            dismissed_any = True
                            dismissed_this_round = True
                            self.short_sleep(1.5)
                            break

                        # Try by content-desc
                        el = self.device(description=dt)
                        if el.exists(timeout=0.5):
                            print(f"   🚫 [{self.device_id}] Clickeando '{dt}' (desc) para descartar modal")
                            el.click()
                            dismissed_any = True
                            dismissed_this_round = True
                            self.short_sleep(1.5)
                            break

                    if dismissed_this_round:
                        break  # Re-scan hierarchy after dismissing

                # Also try pressing BACK if a modal might be present but no button found
                if not dismissed_this_round:
                    # Check for common Android permission dialog patterns
                    permission_dialogs = [
                        'com.android.permissioncontroller',
                        'com.google.android.permissioncontroller',
                        'grantPermissions',
                        'permission_allow_button',
                        'permission_deny_button',
                    ]
                    for pd in permission_dialogs:
                        if pd in xml and not dismissed_this_round:
                            # Try to find and click Deny button via common resource-IDs
                            deny_rids = [
                                'com.android.permissioncontroller:id/permission_deny_button',
                                'com.android.packageinstaller:id/permission_deny_button',
                                'android:id/button2',
                            ]
                            for rid in deny_rids:
                                el = self.device(resourceId=rid)
                                if el.exists(timeout=0.5):
                                    print(f"   🚫 [{self.device_id}] Denegando permiso Android (rid={rid})")
                                    el.click()
                                    dismissed_any = True
                                    dismissed_this_round = True
                                    self.short_sleep(1.5)
                                    break
                            if dismissed_this_round:
                                break

                # If nothing to dismiss, we're done
                if not dismissed_this_round:
                    break

                # Small sleep between attempts to let UI settle
                self.short_sleep(1)

            except Exception as e:
                print(f"⚠️ [{self.device_id}] Error descartando modales: {e}")
                continue

        if dismissed_any:
            print(f"[TT][{self.device_id}] Modales descartados. Continuando flujo...")

        return dismissed_any

    def open_tiktok_link(self, link_link: str):
        """
        Abre un link de TikTok usando deep link
        
        Args:
            link_link: URL del link de TikTok
        """
        try:
            print(f"📱 [{self.device_id}] Abriendo TikTok link...")
            self.short_sleep(3)

            # Método 1: Abrir con el package explícito para evitar el modal "Abrir con"
            self.device.shell(
                f'am start -a android.intent.action.VIEW -d "{link_link}" '
                f'com.zhiliaoapp.musically'
            )

            # Método 2 (fallback): si falla el package explícito, usar monkey
            # self.device.shell(f'monkey -p com.zhiliaoapp.musically 1')

            # Descartar modal "Abrir con" si aparece de todos modos
            self._dismiss_open_with_dialog()
            # Descartar modales de onboarding/permisos
            self._dismiss_tiktok_modals()

            print(f"✅ [{self.device_id}] Link abierto")
            self.random_sleep(2,4)
            self.device.set_orientation("natural")
            self.random_sleep(5, 10)

        except Exception as e:
            print(f"❌ [{self.device_id}] Error abriendo link: {e}")
            raise
    
    def scroll_until_find(self, xpath: str, max_scrolls: int = 10) -> bool:
        """
        Hace scroll hacia arriba hasta encontrar un elemento
        
        Args:
            xpath: XPath del elemento a buscar
            max_scrolls: Máximo número de scrolls
            
        Returns:
            True si encontró el elemento, False si no
        """
        print(f"🔍 [{self.device_id}] Buscando elemento: {xpath}")
        
        for i in range(max_scrolls):
            try:
                # Verificar si el elemento existe
                if self.device.xpath(xpath).exists:
                    print(f"✅ [{self.device_id}] Elemento encontrado")
                    return True
                
                # Hacer swipe up (scroll down en la pantalla)
                print(f"⬆️ [{self.device_id}] Scroll {i+1}/{max_scrolls}")
                self.device.swipe_ext("up", scale=0.6)
                self.short_sleep(1.5)
                
            except Exception as e:
                print(f"⚠️ [{self.device_id}] Error en scroll: {e}")
                continue
        
        print(f"❌ [{self.device_id}] Elemento no encontrado después de {max_scrolls} scrolls")
        return False
    
    def long_click_element(self, xpath: str = None, duration: float = 3.0, x: int = None, y: int = None) -> bool:
        """
        Hace long click en un elemento por xpath o coordenadas
        
        Args:
            xpath: XPath del elemento (opcional si se proporcionan coordenadas)
            duration: Duración del click en segundos
            x: Coordenada X (opcional, requiere Y)
            y: Coordenada Y (opcional, requiere X)
            
        Returns:
            True si tuvo éxito, False si no
        """
        try:
            # Si se proporcionan coordenadas, usarlas
            if x is not None and y is not None:
                print(f"👆 [{self.device_id}] Long click en coordenadas ({x}, {y}) por {duration}s...")
                self.device.long_click(x, y, duration)
                return True
            
            # Si no hay coordenadas, usar xpath
            if xpath:
                element = self.device.xpath(xpath)
                if element.exists:
                    print(f"👆 [{self.device_id}] Long click ({duration}s)...")
                    # uiautomator2: usar long_click() sin parámetros
                    element.long_click()
                    self.short_sleep(duration)  # Esperar después del long click
                    return True
                else:
                    print(f"❌ [{self.device_id}] Elemento no existe para long click")
                    return False
            
            print(f"❌ [{self.device_id}] Debe proporcionar xpath o coordenadas (x, y)")
            return False
            
        except Exception as e:
            print(f"❌ [{self.device_id}] Error en long click: {e}")
            return False

    def double_tap(self):
        """
        Hace doble tap en el centro de la pantalla usando el método nativo de uiautomator2
        """
        try:
            width, height = self.device.window_size()
            x = width // 2
            y = height // 2
            print(f"👆👆 [{self.device_id}] Doble tap en ({x}, {y})...")
            self.device.double_click(x, y)
            return True
        except Exception as e:
            print(f"❌ [{self.device_id}] Error en doble tap: {e}")
            return False    
    
    def click_element(self, xpath: str) -> bool:
        """
        Hace click en un elemento
        
        Args:
            xpath: XPath del elemento
            
        Returns:
            True si tuvo éxito, False si no
        """
        try:
            element = self.device.xpath(xpath)
            if element.exists:
                print(f"👆 [{self.device_id}] Click en elemento")
                element.click()
                return True
            else:
                print(f"❌ [{self.device_id}] Elemento {xpath} no existe para click")
                return False
        except Exception as e:
            print(f"❌ [{self.device_id}] Error en click: {e}")
            return False
    
    def element_exists(self, xpath: str) -> bool:
        """
        Verifica si un elemento existe
        
        Args:
            xpath: XPath del elemento
            
        Returns:
            True si existe, False si no
        """
        try:
            return self.device.xpath(xpath).exists
        except:
            return False
        
    def resource_exists(self, resource_id: str) -> bool:
        """
        Verifica si un elemento existe por resource-id
        
        Args:
            resource_id: Resource ID del elemento
            
        Returns:
            True si existe, False si no
        """
        try:
            return self.device(resourceId=resource_id).exists
        except:
            return False
    
    def get_element_text(self, xpath: str = None, resource_id: str = None) -> Optional[str]:
        """
        Obtiene el texto de un elemento por xpath o resource-id
        
        Args:
            xpath: XPath del elemento (opcional)
            resource_id: Resource ID del elemento (opcional)
            
        Returns:
            Texto del elemento o None si no existe
        """
        try:
            if resource_id:
                element = self.device(resourceId=resource_id)
                if element.exists:
                    text = element.info.get('text', '')
                    print(f"📝 [{self.device_id}] Texto obtenido de resource-id: '{text}'")
                    return text
            elif xpath:
                element = self.device.xpath(xpath)
                if element.exists:
                    text = element.get_text()
                    print(f"📝 [{self.device_id}] Texto obtenido de xpath: '{text}'")
                    return text
            
            print(f"❌ [{self.device_id}] Elemento no existe para obtener texto")
            return None
            
        except Exception as e:
            print(f"❌ [{self.device_id}] Error obteniendo texto: {e}")
            return None
    
    def parse_duration_to_seconds(self, duration_str: str) -> int:
        """
        Convierte una duración en formato MM:SS o HH:MM:SS a segundos totales
        
        Args:
            duration_str: String de duración (ej: "12:10", "1:05:30", " / 12:10")
            
        Returns:
            Segundos totales
        """
        try:
            # Limpiar el string (quitar espacios, " / ", etc)
            duration_str = duration_str.strip().replace(" / ", "").replace("/", "").strip()
            
            # Separar por ":"
            parts = duration_str.split(":")
            
            if len(parts) == 2:
                # Formato MM:SS
                minutes = int(parts[0])
                seconds = int(parts[1])
                total_seconds = minutes * 60 + seconds
            elif len(parts) == 3:
                # Formato HH:MM:SS
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                total_seconds = hours * 3600 + minutes * 60 + seconds
            else:
                print(f"⚠️ [{self.device_id}] Formato de duración no reconocido: {duration_str}")
                return 0
            
            print(f"⏱️ [{self.device_id}] Duración: {duration_str} = {total_seconds} segundos")
            return total_seconds
            
        except Exception as e:
            print(f"❌ [{self.device_id}] Error parseando duración: {e}")
            return 0
    
    def press_back(self):
        """Presiona el botón back"""
        try:
            print(f"◀️ [{self.device_id}] Presionando BACK")
            self.device.press("back")
            self.short_sleep(1)
        except Exception as e:
            print(f"❌ [{self.device_id}] Error presionando back: {e}")
    
    def swipe_down_until_find(self, xpath: str, max_swipes: int = 5) -> bool:
        """
        Hace swipe de ARRIBA hacia ABAJO hasta encontrar un elemento
        
        Args:
            xpath: XPath del elemento a buscar
            max_swipes: Máximo número de swipes
            
        Returns:
            True si encontró el elemento, False si no
        """
        print(f"🔍 [{self.device_id}] Buscando elemento con swipe down: {xpath}")
        
        for i in range(max_swipes):
            try:
                # Verificar si el elemento existe
                if self.device.xpath(xpath).exists:
                    print(f"✅ [{self.device_id}] Elemento encontrado")
                    return True
                
                # Hacer swipe down (de arriba hacia abajo)
                print(f"⬇️ [{self.device_id}] Swipe down {i+1}/{max_swipes}")
                self.device.swipe_ext("down", scale=0.3)  # Swipe ligero
                self.short_sleep(1)
                
            except Exception as e:
                print(f"⚠️ [{self.device_id}] Error en swipe: {e}")
                continue
        
        print(f"❌ [{self.device_id}] Elemento no encontrado después de {max_swipes} swipes")
        return False
    
    def cambiar_cuenta(self, segundos_min, segundos_max) -> bool:
        """
        Cambia de cuenta en TikTok evitando repetir usuarios ya utilizados.
        Usa resource-IDs y content-desc reales obtenidos del dump de UI.
        """
        try:
            print(f"[TT][{self.device_id}] Rotando cuenta de TikTok...")
            self.device.app_stop("com.zhiliaoapp.musically")
            self.random_sleep(2, 6)
            self.random_sleep(segundos_min, segundos_max)
            self.device.app_start("com.zhiliaoapp.musically")
            self.random_sleep(10, 15)
            # Descarta modales de permisos/onboarding post-login
            self._dismiss_tiktok_modals()

            # 1. Click en Perfil (resource-id o content-desc)
            perfil_rid = 'com.zhiliaoapp.musically:id/lfl'
            if not (
                self.device(resourceId=perfil_rid).exists and self.device(resourceId=perfil_rid).click()
                or self.click_element('//*[@content-desc="Perfil"]')
            ):
                print(f"[TT][{self.device_id}] No se encontró el botón 'Perfil'")
                return False
            self.random_sleep(5, 10)

            # 2. Click en Menú del perfil
            if not self.click_element('//*[@content-desc="Menú del perfil"]'):
                print(f"[TT][{self.device_id}] No se encontró 'Menú del perfil'")
                return False
            self.random_sleep(5, 10)

            # 3. Click en Ajustes y privacidad (content-desc, no text)
            if not (
                self.click_element('//*[@content-desc="Ajustes y privacidad"]')
                or self.click_element('//*[@text="Ajustes y privacidad"]')
            ):
                print(f"[TT][{self.device_id}] No se encontró 'Ajustes y privacidad'")
                return False
            self.random_sleep(5, 10)

            # 4. Scroll hasta "Cambiar de cuenta" (necesita hasta 10 scrolls)
            cambiar_cuenta_xpath = '//*[@text="Cambiar de cuenta"]'
            if not self.scroll_until_find(cambiar_cuenta_xpath, max_scrolls=10):
                print(f"[TT][{self.device_id}] No se encontró 'Cambiar de cuenta' tras scroll")
                return False
            self.random_sleep(2, 4)

            if not self.click_element(cambiar_cuenta_xpath):
                print(f"[TT][{self.device_id}] No se pudo clickear 'Cambiar de cuenta'")
                return False
            self.random_sleep(5, 10)

            # 5. Seleccionar una cuenta no usada
            # Los botones de cuenta tienen resource-id j7i y content-desc = nombre de usuario
            cuenta_rid = 'com.zhiliaoapp.musically:id/j7i'
            if not self.device(resourceId=cuenta_rid).exists:
                print(f"[TT][{self.device_id}] No se encontraron botones de cuenta")
                return False

            cuenta_seleccionada = False
            for btn in self.device(resourceId=cuenta_rid):
                nombre = (btn.info.get('contentDescription') or '').strip()
                if not nombre:
                    continue
                # Saltar "Agregar cuenta"
                if nombre.lower() in ['agregar cuenta', 'add account']:
                    continue
                if nombre not in self.cuentas_usadas:
                    print(f"[TT][{self.device_id}] Cambiando a la cuenta: {nombre}")
                    btn.click()
                    self.cuentas_usadas.append(nombre)
                    self.random_sleep(3, 5)
                    cuenta_seleccionada = True
                    break

            if not cuenta_seleccionada:
                print(f"[TT][{self.device_id}] Todas las cuentas ya fueron usadas")
                return False

            print(f"[TT][{self.device_id}] Cambio de cuenta completado.")
            return True

        except Exception as e:
            print(f"[TT][{self.device_id}] Error cambiando de cuenta: {e}")
            return False

    def _should_stop(self, detener_flag: Optional[threading.Event], contexto: str) -> bool:
        """
        Verifica si se solicitó detener el proceso actual.
        """
        if detener_flag and detener_flag.is_set():
            print(f"[TT][{self.device_id}] Detención solicitada durante {contexto}. Abortando proceso.")
            return True
        return False

    def _hay_cuentas_disponibles(self, proceso: str) -> bool:
        """
        Comprueba si aún hay cuentas disponibles para continuar el proceso.
        """
        if self.sin_cuentas_disponibles:
            print(f"[TT][{self.device_id}] Sin cuentas disponibles para continuar {proceso}.")
            return False
        return True

    def _post_proceso_rotacion(self, proceso: str, segundos_min: int, segundos_max: int, detener_flag: Optional[threading.Event]):
        """
        Maneja la rotación de cuentas después de finalizar un proceso.
        """
        if detener_flag and detener_flag.is_set():
            return
        if self.sin_cuentas_disponibles:
            return
        if len(self.cuentas_usadas) >= self.cuentas_por_dispositivo:
            print(f"[TT][{self.device_id}] Límite de cuentas alcanzado tras {proceso}.")
            self.sin_cuentas_disponibles = True
            return
        if not self.cambiar_cuenta(segundos_min, segundos_max):
            print(f"[TT][{self.device_id}] No se pudo cambiar de cuenta al finalizar {proceso}.")
            self.sin_cuentas_disponibles = True
    
    def _restart_tiktok_app(self):
        """Reinicia la aplicación TikTok en el dispositivo."""
        try:
            print(f"[TT][{self.device_id}] Reiniciando TikTok...")
            self.device.app_stop("com.zhiliaoapp.musically")
            self.random_sleep(5, 10)
            self.device.app_start("com.zhiliaoapp.musically")
            self.random_sleep(5, 10)
            # Descarta modales de onboarding/permisos
            self._dismiss_tiktok_modals()
            print(f"[TT][{self.device_id}] TikTok reiniciado.")
        except Exception as e:
            print(f"[TT][{self.device_id}] Error reiniciando TikTok: {e}")
           
##############################################################
# PROCESOS ESPECÍFICOS TIKTOK
##############################################################

    def proceso_calentamiento(self, detener_flag: Optional[threading.Event] = None):
        """
        Calentamiento de cuenta TikTok ultra-random.
        Simula comportamiento humano real: FYP, Following, búsquedas,
        likes, comentarios (solo leer), follows, favoritos, shares.
        Sesiones variables, descansos aleatorios, rotación de cuentas.
        """
        if not self._hay_cuentas_disponibles("calentamiento"):
            return

        session_seconds = random.randint(5 * 60, 45 * 60)
        break_seconds = random.randint(5 * 60, 45 * 60)

        # ── Selectores ──
        comment_button_xpath = '//*[contains(@content-desc,"comentario")]'
        close_comments_xpath = '//*[@content-desc="Cerrar"]'
        follow_button_xpath = '//*[contains(@content-desc,"Seguir")]'
        favorite_button_xpath = '//*[contains(@content-desc,"Favoritos")]'
        comment_like_xpath = '//*[contains(@content-desc,"Me gusta")]'
        share_button_xpath = '//*[contains(@content-desc,"Compartir")]'
        search_button_xpath = '//*[contains(@content-desc,"Buscar") or contains(@content-desc,"Search")]'
        following_tab = '//*[@text="Siguiendo" or @text="Following"]'
        fyp_tab = '//*[@text="Para ti" or @text="For You"]'

        def chance(pct: float) -> bool:
            return random.random() * 100 < pct

        def revisar_comentarios():
            """Abre comentarios, hace scroll, likea algunos, cierra."""
            if not self.click_element(comment_button_xpath):
                return False
            self.random_sleep(2, 6)
            loops = random.randint(1, 5)
            for _ in range(loops):
                if self._should_stop(detener_flag, "tt-warm-comments"):
                    break
                try:
                    self.device.swipe_ext("up", scale=random.uniform(0.5, 0.9))
                except Exception:
                    pass
                self.random_sleep(1, 4)
                # ~25% dar like a algún comentario
                if chance(25):
                    self.click_element(comment_like_xpath)
                    self.short_sleep(0.5)
                # ~10% scroll rápido (simula desinterés)
                if chance(10):
                    try:
                        self.device.swipe_ext("up", scale=0.9)
                    except Exception:
                        pass
                    self.short_sleep(0.5)
            if not self.click_element(close_comments_xpath):
                self.press_back()
            self.short_sleep(1)
            return True

        def _human_pause():
            """Pausa de duración random (3-45s) simulando distracción."""
            p = random.randint(3, 45)
            print(f"[TT][{self.device_id}] Pausa humana {p}s...")
            time.sleep(p)

        def seleccionar_accion() -> str:
            """Distribución de acciones con pesos realistas."""
            roll = random.randint(1, 100)
            if roll <= 50:       return "double_tap"
            if roll <= 65:       return "like_and_comments"
            if roll <= 72:       return "follow"
            if roll <= 78:       return "favorite"
            if roll <= 84:       return "share"
            if roll <= 90:       return "pause"       # No hacer nada
            if roll <= 95:       return "scroll_back"  # Volver a ver
            return "fast_scroll"                      # Pasar rápido

        def _go_to_following():
            """Cambia a la pestaña 'Siguiendo'."""
            if self.click_element(following_tab):
                print(f"[TT][{self.device_id}] 📋 Cambiado a Following")
                return True
            return False

        def _go_to_fyp():
            """Vuelve a la pestaña 'Para ti'."""
            if self.click_element(fyp_tab):
                return True
            return False

        def _do_search():
            """Hace una búsqueda random y scrollea resultados."""
            if not self.click_element(search_button_xpath):
                return
            self.random_sleep(2, 4)
            # Búsquedas genéricas para calentamiento
            busquedas = [
                "música", "comedia", "baile", "cocina", "deportes",
                "viajes", "tecnología", "animales", "motivación", "tendencias",
                "music", "comedy", "dance", "cooking", "sports",
                "travel", "tech", "animals", "motivation", "trending",
            ]
            query = random.choice(busquedas)
            try:
                self.device.send_keys(query, clear=True)
                self.short_sleep(1)
                self.device.press("enter")
            except Exception:
                pass
            self.random_sleep(3, 6)
            # Scroll en resultados
            for _ in range(random.randint(2, 6)):
                try:
                    self.device.swipe_ext("up", scale=random.uniform(0.3, 0.7))
                except Exception:
                    pass
                time.sleep(random.uniform(1, 4))
            self.press_back()
            self.short_sleep(1)

        print(f"[TT][{self.device_id}] 🔥 CALENTAMIENTO TT: {session_seconds // 60}min sesión, {break_seconds // 60}min descanso")
        session_end = time.time() + session_seconds

        try:
            self._restart_tiktok_app()

            # Plan de actividades por bloques
            videos_vistos = 0
            in_following = False

            while time.time() < session_end:
                if self._should_stop(detener_flag, "tt-warm-main"):
                    break

                # ~15% cambiar entre FYP y Following
                if chance(15):
                    if in_following:
                        _go_to_fyp()
                        in_following = False
                    else:
                        if _go_to_following():
                            in_following = True
                    self.random_sleep(1, 3)

                # ~10% hacer búsqueda (solo en FYP)
                if chance(10) and not in_following:
                    _do_search()
                    self.random_sleep(2, 4)

                # ~5% pausa larga (como si el usuario dejó el teléfono)
                if chance(5):
                    long_pause = random.randint(30, 120)
                    print(f"[TT][{self.device_id}] Pausa larga {long_pause}s...")
                    time.sleep(long_pause)

                # Mirar video actual
                watch_time = random.randint(2, 30)
                es_live = self.element_exists('//*[@text="Pulsa para ver el LIVE"]')
                if not es_live:
                    print(f"[TT][{self.device_id}] Video {watch_time}s...")
                    time.sleep(watch_time)

                    accion = seleccionar_accion()
                    print(f"[TT][{self.device_id}] Acción: {accion}")

                    if accion == "double_tap":
                        self.double_tap()
                    elif accion == "like_and_comments":
                        revisar_comentarios()
                        self.double_tap()
                    elif accion == "follow":
                        self.click_element(follow_button_xpath)
                    elif accion == "favorite":
                        self.click_element(favorite_button_xpath)
                    elif accion == "share":
                        if self.click_element(share_button_xpath):
                            self.random_sleep(2, 3)
                            # ~50% repost, ~50% cancelar
                            if chance(50):
                                repost_xpath = '//*[@content-desc="Compartir"]'
                                self.click_element(repost_xpath)
                                self.short_sleep(1)
                            else:
                                self.press_back()
                    elif accion == "pause":
                        _human_pause()
                    elif accion == "scroll_back":
                        try:
                            self.device.swipe_ext("down", scale=0.4)
                        except Exception:
                            pass
                        time.sleep(3)
                        self.double_tap()
                    elif accion == "fast_scroll":
                        pass  # Solo pasa rápido, sin interacción

                    # Siguiente video
                    try:
                        self.device.swipe_ext("up", scale=random.uniform(0.6, 0.95))
                    except Exception:
                        pass
                    self.random_sleep(1, 3)
                    videos_vistos += 1
                else:
                    print(f"[TT][{self.device_id}] LIVE detectado — omitiendo")
                    try:
                        self.device.swipe_ext("up", 0.9)
                    except Exception:
                        pass
                    self.short_sleep(2)

                # Mini-descanso cada ~10 videos
                if videos_vistos > 0 and videos_vistos % random.randint(8, 14) == 0:
                    mini = random.randint(10, 60)
                    print(f"[TT][{self.device_id}] Mini-descanso {mini}s...")
                    time.sleep(mini)

            print(f"[TT][{self.device_id}] Calentamiento finalizado ({videos_vistos} videos)")

        except Exception as e:
            print(f"[TT][{self.device_id}] Error en calentamiento: {e}")
            raise
        finally:
            try:
                self.device.app_stop("com.zhiliaoapp.musically")
            except Exception:
                pass
            if not (detener_flag and detener_flag.is_set()):
                print(f"[TT][{self.device_id}] 😴 Descanso {break_seconds // 60}min...")
                break_end = time.time() + break_seconds
                while time.time() < break_end:
                    if detener_flag and detener_flag.is_set():
                        break
                    time.sleep(min(30, break_end - time.time()))

        self._post_proceso_rotacion("calentamiento", 5 * 60, 30 * 60, detener_flag)
        self.device.app_stop("com.zhiliaoapp.musically")
        self.random_sleep(2, 5)
    
    
    def proceso_comentarios(
        self,
        link_post: str,
        comentarios: List[str],
        detener_flag: Optional[threading.Event] = None
    ) -> int:
        """Proceso de comentarios en un post de TikTok usando comentarios generados por IA."""
        if not self._hay_cuentas_disponibles("comentarios"):
            return 0
    
        comentarios_pendientes = deque(
            (comentario or "").strip() for comentario in comentarios or [] if (comentario or "").strip()
        )
    
        if not comentarios_pendientes:
            print(f"[TT][{self.device_id}] No se recibieron comentarios (IA) para publicar")
            return 0
    
        publicados = 0
        # Resource-IDs reales (verificados con dump de UI)
        comment_btn_rid = 'com.zhiliaoapp.musically:id/di5'   # Botón "Leer o agregar comentarios"
        comment_input_rid = 'com.zhiliaoapp.musically:id/de5'  # EditText "Agregar comentario…"
    
        while comentarios_pendientes and self._hay_cuentas_disponibles("comentarios"):
            if self._should_stop(detener_flag, "comentarios"):
                print(f"[TT][{self.device_id}] Detención solicitada; se detiene el proceso de comentarios.")
                break
    
            comentario_actual = comentarios_pendientes[0]
            comentario_publicado = False
    
            try:
                self._restart_tiktok_app()
                print(f"[TT][{self.device_id}] Intentando publicar comentario: {comentario_actual}")
                self.open_tiktok_link(link_post)
                self.random_sleep(16, 60)
    
                # 1. Click en botón de comentarios
                if not self.device(resourceId=comment_btn_rid).exists:
                    print(f"[TT][{self.device_id}] Botón de comentarios no encontrado")
                    break
                self.device(resourceId=comment_btn_rid).click()
                self.random_sleep(2, 4)
    
                # 2. Click en campo de texto
                input_field = self.device(resourceId=comment_input_rid)
                if not input_field.exists:
                    print(f"[TT][{self.device_id}] Campo de comentario no encontrado")
                    break
                input_field.click()
                self.random_sleep(1, 2)
    
                # 3. Escribir y enviar con ENTER
                self.device.send_keys(comentario_actual, clear=True)
                self.short_sleep(1)
                self.device.press("enter")
                self.short_sleep(2)
    
                publicados += 1
                comentario_publicado = True
                comentarios_pendientes.popleft()
                print(f"[TT][{self.device_id}] Comentario publicado ({publicados} total)")
    
                self.random_sleep(3, 6)
    
            except Exception as e:
                print(f"[TT][{self.device_id}] Error en proceso de comentarios: {e}")
                raise
            finally:
                self.device.press("home")
                self.short_sleep(2)
    
            if not comentario_publicado:
                comentarios_pendientes.rotate(-1)
    
            if not self._post_proceso_rotacion("comentarios", 15, 60, detener_flag):
                break
    
        print(f"[TT][{self.device_id}] Proceso de comentarios finalizado ({publicados} publicados)")
        return publicados
    
    def proceso_views(self, link_post: str, detener_flag: Optional[threading.Event] = None) -> int:
        """Proceso de reproducciones en un post de TikTok."""
        if not self._hay_cuentas_disponibles("views"):
            return 0
    
        if not link_post:
            print(f"[TT][{self.device_id}] No se proporcionó link para el proceso de views")
            return 0
    
        vistas_realizadas = 0
    
        while self._hay_cuentas_disponibles("views"):
            if self._should_stop(detener_flag, "views inicio"):
                break
            try:
                self._restart_tiktok_app()
                print(f"[TT][{self.device_id}] Abriendo post para views: {link_post}")
                self.open_tiktok_link(link_post)
                watch_seconds = random.randint(15, 60)
                print(f"[TT][{self.device_id}] Manteniendo la reproducción durante {watch_seconds} segundos.")
                end_time = time.time() + watch_seconds
                while time.time() < end_time:
                    if self._should_stop(detener_flag, "views reproduccion"):
                        break
                    remaining = end_time - time.time()
                    self.short_sleep(min(15, max(1, remaining)))
                vistas_realizadas += 1
                print(f"[TT][{self.device_id}] Proceso de views completado para esta cuenta.")
            except Exception as e:
                print(f"[TT][{self.device_id}] Error en proceso de views: {e}")
                raise
            finally:
                self.device.press("home")
                self.short_sleep(2)
    
            if not self._post_proceso_rotacion("views", 5 * 60, 15 * 60, detener_flag):
                break
    
        return vistas_realizadas
    
    def proceso_maximizar_perfil_views(self, link_post: str, detener_flag: Optional[threading.Event] = None) -> int:
        """Proceso para maximizar las views de un perfil de TikTok."""
        if not self._hay_cuentas_disponibles("maximizar perfil views"):
            return 0
    
        if not link_post:
            print(f"[TT][{self.device_id}] No se proporcionó link de perfil para maximizar views")
            return 0
    
        first_video_xpath = "//android.widget.GridView/android.widget.FrameLayout[1]"
        share_button_xpath = '//*[contains(@content-desc,"Compartir")]'
        repost_option_xpath = '//*[@content-desc="Compartir"]'
        favourite_button_xpath = '//*[contains(@content-desc,"Favoritos")]'
        perfil_markers = [
            '//*[@text="Siguiendo"]',
            '//*[@text="Seguidores"]',
            '//*[@text="Me gusta"]'
        ]
    
        def chance(percent: float) -> bool:
            return random.random() * 100 < percent

        def save_favourite() -> bool:
            if self.click_element(favourite_button_xpath):
                print(f"[TT][{self.device_id}] Reel guardado en Favoritos")
                self.short_sleep(1)
                return True
            print(f"[TT][{self.device_id}] Botón de Favoritos no disponible")
            return False

        def realizar_repost() -> bool:
            if not self.click_element(share_button_xpath):
                print(f"[TT][{self.device_id}] Botón de compartir no disponible para repost")
                return False
            self.random_sleep(2, 4)
            if self.click_element(repost_option_xpath):
                print(f"[TT][{self.device_id}] Reel compartido como repost")
                self.random_sleep(1, 2)
                return True
            print(f"[TT][{self.device_id}] Opción de repost no disponible en este perfil")
            self.press_back()
            return False
    
        def regreso_a_perfil() -> bool:
            return all(self.element_exists(xpath) for xpath in perfil_markers)
    
        perfiles_procesados = 0
    
        while self._hay_cuentas_disponibles("maximizar perfil views"):
            if self._should_stop(detener_flag, "max perfil inicio"):
                break
    
            try:
                self._restart_tiktok_app()
                print(f"[TT][{self.device_id}] Abriendo perfil: {link_post}")
                self.open_tiktok_link(link_post)
                self.random_sleep(2, 6)

                random_index = random.randint(1, 3)
                random_video_xpath = f"//android.widget.GridView/android.widget.FrameLayout[{random_index}]"
                random_video_xpath_alt = f"//androidx.recyclerview.widget.RecyclerView/android.widget.FrameLayout[{random_index}]"
                if not (self.click_element(random_video_xpath) or self.click_element(random_video_xpath_alt)):
                    print(f"[TT][{self.device_id}] No se pudo abrir video aleatorio {random_index}")
                    break
    
                while True:
                    if self._should_stop(detener_flag, "max perfil video loop"):
                        break
    
                    watch_seconds = random.randint(15, 60)
                    print(f"[TT][{self.device_id}] Reproduciendo video del perfil por {watch_seconds} segundos")
                    end_video = time.time() + watch_seconds
                    while time.time() < end_video:
                        if self._should_stop(detener_flag, "max perfil reproduccion"):
                            break
                        remaining = end_video - time.time()
                        self.short_sleep(min(15, max(1, remaining)))
    
                    acciones_realizadas: List[str] = []
                    if chance(70):
                        self.double_tap()
                        acciones_realizadas.append("double tap")
    
                    if chance(25):
                        if save_favourite():
                            acciones_realizadas.append("favorito")
    
                    if chance(50):
                        if realizar_repost():
                            acciones_realizadas.append("repost")
    
                    if not acciones_realizadas:
                        print(f"[TT][{self.device_id}] Reel visto sin interacción para simular comportamiento orgánico")
                    else:
                        print(f"[TT][{self.device_id}] Acciones realizadas: {', '.join(acciones_realizadas)}")
    
                    self.random_sleep(1, 3)
                    try:
                        self.device.swipe_ext("up", 0.9)
                    except Exception as feed_err:
                        print(f"[TT][{self.device_id}] Error al pasar al siguiente video del perfil: {feed_err}")
                        self.short_sleep(2)
    
                    self.random_sleep(2, 4)
    
                    if regreso_a_perfil():
                        print(f"[TT][{self.device_id}] Se detectó regreso al perfil, no hay más videos en el carrete.")
                        break
    
                perfiles_procesados += 1
                print(f"[TT][{self.device_id}] Proceso de maximizar perfil views completado para esta cuenta.")
    
            except Exception as e:
                print(f"[TT][{self.device_id}] Error en proceso de maximizar perfil views: {e}")
                raise
            finally:
                self.device.press("home")
                self.short_sleep(2)
    
            if not self._post_proceso_rotacion("maximizar perfil views", 5 * 60, 10 * 60, detener_flag):
                break
    
        return perfiles_procesados
    
    def proceso_compartidas(self, link_post: str, detener_flag: Optional[threading.Event] = None) -> int:
        """Proceso de compartidas en un post de TikTok."""
        if not self._hay_cuentas_disponibles("compartidas"):
            return 0
    
        if not link_post:
            print(f"[TT][{self.device_id}] No se proporcionó link para compartidas")
            return 0
    
        compartir_xpath = '//*[contains(@content-desc,"Compartir")]'
        story_xpath = '//*[contains(@content-desc,"Story")]'
        story_confirm_xpath = '//*[contains(@text, "Story")]'
        repost_xpath = '//*[@content-desc="Compartir"]'
        close_popup_xpath = '//*[@content-desc="Cerrar"]'
    
        compartidas_realizadas = 0

        while self._hay_cuentas_disponibles("compartidas"):
            if self._should_stop(detener_flag, "compartidas inicio"):
                break
            try:
                self._restart_tiktok_app()
                print(f"[TT][{self.device_id}] Abriendo post para compartidas: {link_post}")
                self.open_tiktok_link(link_post)
                self.random_sleep(30, 60)
    
                if not self.click_element(compartir_xpath):
                    print(f"[TT][{self.device_id}] Botón de compartir no encontrado")
                    break
    
                self.random_sleep(2, 4)
                compartida_exitosa = False
    
                if random.random() < 0.5:
                    if self.click_element(story_xpath):
                        self.random_sleep(10, 15)
                        if self.click_element(story_confirm_xpath):
                            compartida_exitosa = True
                            self.random_sleep(5, 10)
                            print(f"[TT][{self.device_id}] Compartido en Story")
                    else:
                        print(f"[TT][{self.device_id}] Opción Story no disponible")
                else:
                    if self.click_element(repost_xpath):
                        compartida_exitosa = True
                        print(f"[TT][{self.device_id}] Compartido como repost")
                    else:
                        print(f"[TT][{self.device_id}] Opción de repost no disponible")
    
                if self.element_exists(close_popup_xpath):
                    self.click_element(close_popup_xpath)
                    self.short_sleep(1)
    
                if compartida_exitosa:
                    compartidas_realizadas += 1
                    print(f"[TT][{self.device_id}] Proceso de compartidas finalizado para esta cuenta.")
                else:
                    print(f"[TT][{self.device_id}] No se logró compartir en esta cuenta.")
    
            except Exception as e:
                print(f"[TT][{self.device_id}] Error en proceso de compartidas: {e}")
                raise
            finally:
                self.device.press("home")
                self.short_sleep(2)
    
            if not self._post_proceso_rotacion("compartidas", 15, 60, detener_flag):
                break
    
        return compartidas_realizadas
    
    def proceso_likes(self, link_post: str, detener_flag: Optional[threading.Event] = None) -> int:
        """Proceso de likes en un post de TikTok."""
        if not self._hay_cuentas_disponibles("likes"):
            return 0
    
        if not link_post:
            print(f"[TT][{self.device_id}] No se proporcionó link para likes")
            return 0
    
        likes_realizados = 0
    
        while self._hay_cuentas_disponibles("likes"):
            if self._should_stop(detener_flag, "likes inicio"):
                break
            try:
                self._restart_tiktok_app()
                print(f"[TT][{self.device_id}] Abriendo post para likes: {link_post}")
                self.open_tiktok_link(link_post)
                watch_seconds = random.randint(15, 60)
                print(f"[TT][{self.device_id}] Observando video {watch_seconds} segundos aprox. antes de dar like")
                end_time = time.time() + watch_seconds
                while time.time() < end_time:
                    if self._should_stop(detener_flag, "likes reproduccion"):
                        break
                    remaining = end_time - time.time()
                    self.short_sleep(min(15, max(1, remaining)))
                self.double_tap()
                likes_realizados += 1
                self.random_sleep(1, 3)
                try:
                    self.device.swipe_ext("up", scale=random.uniform(0.6, 0.9))
                except Exception as e:
                    print(f"[TT][{self.device_id}] Error al hacer scroll después de like: {e}")
                print(f"[TT][{self.device_id}] Proceso de likes finalizado para esta cuenta.")
            except Exception as e:
                print(f"[TT][{self.device_id}] Error en proceso de likes: {e}")
                raise
            finally:
                self.device.press("home")
                self.short_sleep(2)
    
            if not self._post_proceso_rotacion("likes", 15, 60, detener_flag):
                break
    
        return likes_realizados
    
    def proceso_follows(self, link_perfil: str, detener_flag: Optional[threading.Event] = None) -> int:
        """Proceso de follows en un perfil de TikTok."""
        if not self._hay_cuentas_disponibles("follows"):
            return 0
    
        if not link_perfil:
            print(f"[TT][{self.device_id}] No se proporcionó link de perfil para follows")
            return 0
    
        follow_button_xpath = '//*[@text="Seguir"]'
        follow_button_xpath_alt = '//*[contains(@content-desc, "Seguir")]'
        follows_realizados = 0
    
        while self._hay_cuentas_disponibles("follows"):
            if self._should_stop(detener_flag, "follows inicio"):
                break
            try:
                self._restart_tiktok_app()
                print(f"[TT][{self.device_id}] Abriendo perfil para follow: {link_perfil}")
                self.open_tiktok_link(link_perfil)
                self.random_sleep(2, 6)
                random_index = random.randint(1, 3)
                random_video_xpath = f"//android.widget.GridView/android.widget.FrameLayout[{random_index}]"
                random_video_xpath_alt = f"//androidx.recyclerview.widget.RecyclerView/android.widget.FrameLayout[{random_index}]"
                if not (self.click_element(random_video_xpath) or self.click_element(random_video_xpath_alt)):
                    print(f"[TT][{self.device_id}] No se pudo abrir video aleatorio {random_index}")
                    # Seguir desde perfil
                    if not (self.click_element(follow_button_xpath) or self.click_element(follow_button_xpath_alt)):
                        print(f"[TT][{self.device_id}] Botón de seguir no encontrado o ya se sigue al perfil.")
                    break
                self.random_sleep(1, 60)
                self.double_tap()
                self.short_sleep(1)
                self.press_back()
                self.short_sleep(1)
                if self.click_element(follow_button_xpath) or self.click_element(follow_button_xpath_alt):
                    follows_realizados += 1
                    print(f"[TT][{self.device_id}] Follow realizado correctamente.")
                else:
                    print(f"[TT][{self.device_id}] Botón de seguir no encontrado o ya se sigue al perfil.")
            except Exception as e:
                print(f"[TT][{self.device_id}] Error en proceso de follows: {e}")
                raise
            finally:
                self.device.press("home")
                self.short_sleep(2)
    
            if not self._post_proceso_rotacion("follows", 15, 60, detener_flag):
                break
    
        return follows_realizados
    
    def proceso_interaccion_live(self, link_live: str, detener_flag: Optional[threading.Event] = None) -> int:
        """Proceso de interacción dentro de un live de TikTok."""
        if not self._hay_cuentas_disponibles("interaccion live"):
            return 0
    
        if not link_live:
            print(f"[TT][{self.device_id}] No se proporcionó link para live")
            return 0
    
        comment_box_xpath = '//*[@text="Escribe algo..."]'
        share_button_xpath = '//*[contains(@content-desc,"Compartir")]'
        story_xpath = '//*[contains(@content-desc,"Story")]'
        story_confirm_xpath = '//*[@text="Tu Story"]'
        repost_xpath = '//*[@content-desc="Compartir"]'
    
        def delay_between_actions():
            self.short_sleep(random.uniform(2, 6))
    
        def ejecutar_double_taps():
            taps = random.randint(3, 15)
            print(f"[TT][{self.device_id}] Ejecutando {taps} double taps en el live")
            for _ in range(taps):
                if self._should_stop(detener_flag, "live double tap"):
                    break
                self.double_tap()
                self.short_sleep(random.uniform(0.3, 0.8))
    
        def enviar_comentario():
            if not self.click_element(comment_box_xpath):
                print(f"[TT][{self.device_id}] Caja de comentarios no disponible")
                return
            comentario = get_random_comment()
            self.device.send_keys(comentario, clear=True)
            self.short_sleep(0.5)
            try:
                self.device.press("enter")
                print(f"[TT][{self.device_id}] Comentario enviado: {comentario}")
            except Exception as e:
                print(f"[TT][{self.device_id}] No se pudo enviar comentario: {e}")
    
        def compartir_live():
            if not self.click_element(share_button_xpath):
                print(f"[TT][{self.device_id}] Botón de compartir no disponible")
                return
            self.random_sleep(2, 4)
            if random.random() < 0.5:
                if self.click_element(story_xpath):
                    self.random_sleep(2, 4)
                    self.click_element(story_confirm_xpath)
                    print(f"[TT][{self.device_id}] Live compartido en Story")
                else:
                    print(f"[TT][{self.device_id}] Opción Story no disponible")
            else:
                if not self.click_element(repost_xpath):
                    print(f"[TT][{self.device_id}] Opción de repost no disponible")
                else:
                    print(f"[TT][{self.device_id}] Live compartido como repost")
    
        action_weights = [("double_tap", 80), ("comment", 20), ("share", 10)]
    
        def elegir_accion() -> str:
            total = sum(weight for _, weight in action_weights)
            roll = random.randint(1, total)
            cumulative = 0
            for action, weight in action_weights:
                cumulative += weight
                if roll <= cumulative:
                    return action
            return "double_tap"
    
        sesiones_realizadas = 0
    
        while self._hay_cuentas_disponibles("interaccion live"):
            if self._should_stop(detener_flag, "live inicio"):
                break
            try:
                self._restart_tiktok_app()
                session_seconds = random.randint(5 * 60, 30 * 60)
                break_seconds = random.randint(3 * 60, 15 * 60)
                session_end = time.time() + session_seconds
                print(f"[TT][{self.device_id}] Iniciando sesión de live por {session_seconds // 60} min aprox.")
                self.open_tiktok_link(link_live)
                self.random_sleep(3, 6)
                while time.time() < session_end:
                    if self._should_stop(detener_flag, "live loop"):
                        break
                    delay_between_actions()
                    action = elegir_accion()
                    if action == "double_tap":
                        ejecutar_double_taps()
                    elif action == "comment":
                        enviar_comentario()
                    else:
                        compartir_live()
                sesiones_realizadas += 1
                print(f"[TT][{self.device_id}] Sesión de live completada para esta cuenta.")
                if self._should_stop(detener_flag, "live descanso"):
                    break
                print(f"[TT][{self.device_id}] Descanso de {break_seconds // 60} min aprox. antes de rotar cuenta")
                break_end = time.time() + break_seconds
                while time.time() < break_end:
                    if detener_flag and detener_flag.is_set():
                        print(f"[TT][{self.device_id}] Descanso interrumpido por detención")
                        break
                    time.sleep(min(30, break_end - time.time()))
            except Exception as e:
                print(f"[TT][{self.device_id}] Error en proceso de interacción live: {e}")
                raise
            finally:
                self.device.press("home")
                self.short_sleep(2)
    
            if not self._post_proceso_rotacion("interaccion live", 1 * 60, 3 * 60, detener_flag):
                break
    
        return sesiones_realizadas
