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

    def __init__(self, device_id: str):
        """
        Inicializa la conexión con el dispositivo
        
        Args:
            device_id: ID del dispositivo ADB
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
        
        # PASO 2: Resetear dispositivo ANTES de conectar
        self._reset_device_services()
        
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

    def open_tiktok_link(self, link_link: str):
        """
        Abre un link de TikTok usando deep link
        
        Args:
            link_link: URL del link de TikTok
        """
        try:
            print(f"📱 [{self.device_id}] Abriendo TikTok link...")
            # Usar el deep link para abrir directamente en la app
            self.short_sleep(5)
            self.device.shell(f'am start -a android.intent.action.VIEW -d "{link_link}"')
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
        """
        try:
            print(f"[TT][{self.device_id}] Rotando cuenta de TikTok...")
            self.device.app_stop("com.zhiliaoapp.musically")
            self.random_sleep(2, 6)

            # Espera adicional entre segundos_min y segundos_max para simular descanso humano
            self.random_sleep(5, 15) #TODO PENDIENTE DE USAR segundos_min, segundos_max
    
            self.device.app_start("com.zhiliaoapp.musically")
            
            self.random_sleep(10, 15)

            perfil_xpath = '//*[@text="Perfil"]'
            perfil_fallback_xpath = '//*[@content-desc="Perfil"]'
            if not (self.click_element(perfil_xpath) or self.click_element(perfil_fallback_xpath) or self.click_element('//*[contains(@content-desc, "Profile")]')):
                print(f"[TT][{self.device_id}] No se encontró el botón 'Perfil'")
                return False
            
            self.random_sleep(5, 10)

            menu_perfil_xpath = '//*[@content-desc="Menú del perfil"]'
            if not (self.click_element(menu_perfil_xpath) or self.click_element('//*[@content-desc="Profile menu"]')):
                print(f"[TT][{self.device_id}] No se encontró el botón de menú del perfil")
                return False
            
            self.random_sleep(5, 10)
            
            settings_and_privacy_xpath = '//*[@text="Settings and privacy"]'
            ajustes_y_privacidad_xpath = '//*[@text="Ajustes y privacidad"]'
            if not (self.click_element(settings_and_privacy_xpath) or self.click_element(ajustes_y_privacidad_xpath)):
                print(f"[TT][{self.device_id}] No se encontró 'Settings and privacy' / 'Ajustes y privacidad'")
                return False
            
            self.random_sleep(5, 10)
            
            cambiar_cuenta_xpath = '//*[@text="Cambiar de cuenta"]'
            switch_account_xpath = '//*[@text="Switch account"]'
            if not (self.scroll_until_find(cambiar_cuenta_xpath, 5) or self.scroll_until_find(switch_account_xpath, 5)):  # Asegurar que el botón esté visible
                print (f"[TT][{self.device_id}] No se pudo hacer scroll hasta 'Cambiar de cuenta' / 'Switch account'")
                return False
            
            self.random_sleep(5, 10)
            
            if not (self.click_element(cambiar_cuenta_xpath) or self.click_element(switch_account_xpath)):
                print(f"[TT][{self.device_id}] No se encontró 'Cambiar de cuenta' / 'Switch account'")
                return False

            self.random_sleep(5, 10)

            cuenta_button_template = (
                "/hierarchy/android.widget.FrameLayout[1]/android.widget.LinearLayout[1]/android.widget.FrameLayout[1]/"
                "android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/"
                "android.view.ViewGroup[1]/android.widget.FrameLayout[1]/android.widget.FrameLayout[1]/"
                "android.widget.RelativeLayout[1]/android.widget.FrameLayout[2]/"
                "androidx.recyclerview.widget.RecyclerView[1]/android.widget.Button[{index}]"
            )

            def obtener_nombre_cuenta(xpath: str) -> Optional[str]:
                try:
                    if not self.element_exists(xpath):
                        return None
                    # El texto está en el TextView dentro del Button
                    text_xpath = f"{xpath}/android.widget.LinearLayout[1]/android.widget.TextView[1]"
                    if not self.element_exists(text_xpath):
                        print(f"[TT][{self.device_id}] No se encontró el TextView en {text_xpath}")
                        return None
                    nombre = self.device.xpath(text_xpath).get_text()
                    return (nombre or "").strip()
                except Exception as e:
                    print(f"[TT][{self.device_id}] No se pudo obtener el nombre de la cuenta en {xpath}: {e}")
                    return None

            def registrar_cuenta_actual():
                actual_xpath = cuenta_button_template.format(index=1)
                nombre = obtener_nombre_cuenta(actual_xpath)
                if nombre and nombre not in self.cuentas_usadas:
                    print(f"[TT][{self.device_id}] Registrando cuenta actual como usada: {nombre}")
                    self.cuentas_usadas.append(nombre)

            registrar_cuenta_actual()

            cuenta_seleccionada = False
            index = 1

            while True:
                button_xpath = cuenta_button_template.format(index=index)
                if not self.element_exists(button_xpath):
                    break

                nombre_cuenta = obtener_nombre_cuenta(button_xpath)

                if nombre_cuenta:
                    # Filtrar botones que no son cuentas reales
                    if nombre_cuenta.lower() in ["agregar cuenta", "add account"]:
                        print(f"[TT][{self.device_id}] Omitiendo '{nombre_cuenta}' (no es una cuenta)")
                        index += 1
                        continue

                    if nombre_cuenta not in self.cuentas_usadas:
                        print(f"[TT][{self.device_id}] Cambiando a la cuenta: {nombre_cuenta}")
                        if self.click_element(button_xpath):
                            self.cuentas_usadas.append(nombre_cuenta)
                            self.random_sleep(3, 5)
                            cuenta_seleccionada = True
                            break
                        else:
                            print(f"[TT][{self.device_id}] No se pudo seleccionar la cuenta {nombre_cuenta}")

                index += 1

            if not cuenta_seleccionada:
                print(f"[TT][{self.device_id}] No se encontraron cuentas disponibles sin usar en las visibles.")
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
            print(f"[TT][{self.device_id}] TikTok reiniciado.")
        except Exception as e:
            print(f"[TT][{self.device_id}] Error reiniciando TikTok: {e}")
           
##############################################################
# PROCESOS ESPECÍFICOS TIKTOK
##############################################################

    def proceso_calentamiento(self, detener_flag: Optional[threading.Event] = None):
        """Proceso de calentamiento en TikTok."""
        if not self._hay_cuentas_disponibles("calentamiento"):
            return
        session_seconds = random.randint(5 * 60, 60 * 60)
        break_seconds = random.randint(3 * 60, 60 * 60)
    
        comment_button_xpath = '//*[contains(@content-desc,"comentario")]'
        close_comments_xpath = '//*[@content-desc="Cerrar"]'
        follow_button_xpath = '//*[contains(@content-desc,"Seguir")]'
        favorite_button_xpath = '//*[contains(@content-desc,"Favoritos")]'
        comment_like_xpath = '//*[contains(@content-desc,"Me gusta")]'
    
        def chance(percent: float) -> bool:
            return random.random() * 100 < percent
    
        def revisar_comentarios():
            if not self.click_element(comment_button_xpath):
                print(f"[TT][{self.device_id}] Botón de comentarios no encontrado")
                return False
            self.random_sleep(2, 6)
            loops = random.randint(1, 3)
            for _ in range(loops):
                if self._should_stop(detener_flag, "calentamiento comentarios"):
                    break
                try:
                    self.device.swipe_ext("up", scale=0.8)
                except Exception as swipe_err:
                    print(f"[TT][{self.device_id}] Error haciendo scroll en comentarios: {swipe_err}")
                self.random_sleep(1, 3)
                if chance(30):
                    self.click_element(comment_like_xpath)
                    self.short_sleep(0.5)
            if not self.click_element(close_comments_xpath):
                print(f"[TT][{self.device_id}] No se pudo cerrar comentarios, usando BACK")
                self.press_back()
            self.short_sleep(1)
            return True
    
        def seleccionar_accion() -> str:
            roll = random.randint(1, 100)
            if roll <= 60:
                return "double_tap"
            if roll <= 80:
                return "like_and_comments"
            if roll <= 90:
                return "follow"
            return "favorite"
    
        print(f"[TT][{self.device_id}] Iniciando calentamiento durante {session_seconds // 60} minutos aprox.")
        session_end = time.time() + session_seconds
    
        try:
            self._restart_tiktok_app()
            
            while time.time() < session_end:
                if self._should_stop(detener_flag, "calentamiento FYP"):
                    break
                print(f"[TT][{self.device_id}] Viendo video en For You...")
                self.random_sleep(2, 30)
                accion = seleccionar_accion()
                print(f"[TT][{self.device_id}] Acción seleccionada: {accion}")
                
                es_un_live_xpath = '//*[@text="Pulsa para ver el LIVE"]'
                if not self.element_exists(es_un_live_xpath):
                    if accion == "double_tap":
                        self.double_tap()
                    elif accion == "like_and_comments":
                        revisar_comentarios()
                        self.double_tap()
                    elif accion == "follow":
                        if not self.click_element(follow_button_xpath):
                            print(f"[TT][{self.device_id}] Botón de seguir no disponible.")
                    elif accion == "favorite":
                        if not self.click_element(favorite_button_xpath):
                            print(f"[TT][{self.device_id}] Botón de guardar en favoritos no disponible.")
                    if self._should_stop(detener_flag, "calentamiento scroll feed"):
                        break
                    self.random_sleep(2, 5)
                else:
                    print(f"[TT][{self.device_id}] Video en LIVE detectado, omitiendo interacciones.")
                try:
                    self.device.swipe_ext("up", 0.9)
                except Exception as feed_err:
                    print(f"[TT][{self.device_id}] Error al pasar al siguiente video: {feed_err}")
                    self.short_sleep(2)
                self.random_sleep(1, 3)
            print(f"[TT][{self.device_id}] Calentamiento finalizado o tiempo agotado.")
        except Exception as e:
            print(f"[TT][{self.device_id}] Error en proceso de calentamiento: {e}")
            raise
        finally:
            try:
                self.device.app_stop("com.zhiliaoapp.musically")
            except Exception as stop_err:
                print(f"[TT][{self.device_id}] No se pudo cerrar TikTok correctamente: {stop_err}")
            if not (detener_flag and detener_flag.is_set()):
                print(f"[TT][{self.device_id}] Tomando descanso de {break_seconds // 60} minutos aprox.")
                break_end = time.time() + break_seconds
                while time.time() < break_end:
                    if detener_flag and detener_flag.is_set():
                        print(f"[TT][{self.device_id}] Descanso interrumpido por solicitud de detención.")
                        break
                    time.sleep(min(30, break_end - time.time()))
    
        self._post_proceso_rotacion("calentamiento", 5 * 60, 30 * 60, detener_flag)
        # Cerrar TikTok si está abierto
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
        comment_section_xpath = '//*[contains(@content-desc,"comentarios")]'
        add_comment_xpath = '//*[@text="Añadir comentario..."]'
        add_comment_xpath_alt = '//*[@text="Agregar comentario…"]'
        publish_comment_xpath = '//*[@content-desc="Publicar comentario"]'
    
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
    
                if not self.element_exists(comment_section_xpath):
                    print(f"[TT][{self.device_id}] Botón de comentarios no encontrado")
                    break
    
                if not self.click_element(comment_section_xpath):
                    print(f"[TT][{self.device_id}] No se pudo abrir la sección de comentarios")
                    break
    
                self.random_sleep(2, 4)

                # Intentar hacer click en el campo de comentario (probar ambos XPath)
                if not (self.click_element(add_comment_xpath) or self.click_element(add_comment_xpath_alt)):
                    print(f"[TT][{self.device_id}] Campo 'Añadir comentario...' no disponible o no clickeable")
                    break

                self.random_sleep(2, 4)

                # Escribir el comentario
                self.device.send_keys(comentario_actual, clear=True)
                self.short_sleep(1)

                # Intentar publicar
                if self.element_exists(publish_comment_xpath) and self.click_element(publish_comment_xpath):
                    publicados += 1
                    comentario_publicado = True
                    comentarios_pendientes.popleft()
                    print(f"[TT][{self.device_id}] Comentario publicado ({publicados} total)")
                else:
                    print(f"[TT][{self.device_id}] Botón de publicar no encontrado")
    
                self.device.set_fastinput_ime(False)
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
