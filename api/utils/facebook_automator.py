import time
import random
from traceback import print_tb

import uiautomator2 as u2


class FacebookAutomator:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device = u2.connect(device_id)

    def abrir_facebook_link(self, link: str):
        """Abre el Reel mediante deep link"""
        self.device.shell(f'am start -a android.intent.action.VIEW -d "{link}"')
        time.sleep(6)

    def proceso_like_facebook(self, link: str, detener_flag=None):
        try:
            self.abrir_facebook_link(link)
            # Tiempo de espera aleatorio para carga inicial
            time.sleep(random.randint(3, 5))

            # Clic de limpieza para asegurar el foco en la app
            #self.device.click(0.5, 0.3)

            selectores = [
                '//android.widget.Button[contains(@content-desc, "reacciones") or contains(@content-desc, "reactions")]',
                '//android.widget.Button[@content-desc="Me gusta" or @content-desc="Like"]',
                '//android.view.ViewGroup[@content-desc="Me gusta" or @content-desc="Like"]',
                '//android.widget.ViewGroup[contains(@content-desc, "reacciones") or contains(@content-desc, "reactions")]',
                '//android.widget.Button[contains(@content-desc, "Like button") or contains(@content-desc, "Botón Me gusta") or contains(@content-desc, "react") or contains(@content-desc, "reaccionar")]'
            ]

            # --- Lógica de Búsqueda con Scroll (5 intentos) ---
            for intento in range(5):
                if detener_flag and detener_flag.is_set(): return False

                print(f"Buscando botón de Like/Reacción... Intento {intento + 1}")

                for xpath in selectores:
                    if self.device.xpath(xpath).exists:
                        print(f"¡Botón de Like encontrado en el intento {intento + 1}!")
                        self.device.xpath(xpath).click()
                        return True  # Retorna inmediatamente al tener éxito

                # Si no se encuentra en la vista actual, scroll suave
                print("Botón de Like no visible, realizando scroll suave...")
                # Swipe de abajo hacia arriba (0.7 -> 0.3) con duración para que sea humano
                self.device.swipe(0.5, 0.7, 0.5, 0.4, duration=0.6)
                time.sleep(2)  # Pausa para refrescar el árbol de UI

            print("No se encontró el botón de Like tras 5 intentos de scroll.")
            return False

        except Exception as e:
            print(f"Error Like: {e}")
            return False

    def proceso_comentario_reels(self, link: str, texto: str, detener_flag=None):
        try:
            self.abrir_facebook_link(link)
            time.sleep(3)

            selectores_abrir = [
                '//android.widget.Button[@content-desc="Comentar" or @content-desc="Comment"]',
                '//android.widget.Button[contains(@content-desc, "comentario") or contains(@content-desc, "comment")]',
                '//android.view.ViewGroup[contains(@content-desc, "comentario") or contains(@content-desc, "comment")]',
                '//android.widget.ImageView[contains(@content-desc, "comentario") or contains(@content-desc, "comment")]'
            ]

            seccion_abierta = False

            # --- Lógica de Búsqueda con Scroll (5 intentos) ---
            for intento in range(5):
                if detener_flag and detener_flag.is_set(): return False

                print(f"Buscando botón de comentario... Intento {intento + 1}")

                # Verificar si alguno de los selectores existe en la pantalla actual
                for xpath in selectores_abrir:
                    if self.device.xpath(xpath).exists:
                        print(f"¡Comentar encontrado en el intento {intento + 1}!")
                        self.device.xpath(xpath).click()
                        seccion_abierta = True
                        break

                if seccion_abierta:
                    break  # Salimos del bucle de intentos de scroll

                # Si no se encontró, realizamos un scroll suave hacia abajo
                # (x_inicio, y_inicio, x_fin, y_fin, duracion_en_segundos)
                print("Botón no visible, realizando scroll suave...")
                self.device.swipe(0.5, 0.7, 0.5, 0.3, duration=0.5)
                time.sleep(2)  # Pausa para que carguen los elementos tras el scroll

            # --- Proceso de escritura del comentario ---
            if seccion_abierta:
                time.sleep(3)
                campo = '//android.widget.EditText'
                if self.device.xpath(campo).exists:
                    self.device.xpath(campo).set_text(str(texto))
                    time.sleep(2)

                    btn_enviar = '//android.widget.ImageView[contains(@content-desc, "Enviar") or contains(@content-desc, "Send")]'
                    btn_enviar_alt = '//android.widget.Button[@content-desc="Enviar" or @content-desc="Send"]'

                    if self.device.xpath(btn_enviar).exists:
                        self.device.xpath(btn_enviar).click()
                    elif self.device.xpath(btn_enviar_alt).exists:
                        self.device.xpath(btn_enviar_alt).click()
                    else:
                        self.device.press("enter")

                    print("Comentario enviado con éxito")
                    return True

            print("No se pudo encontrar el botón de comentario tras 5 intentos.")
            return False

        except Exception as e:
            print(f"Error Comentario: {e}")
            return False

    def rotar_perfil_secuencial(self, indice_objetivo: int, detener_flag=None):
        """Secuencia con reinicio: Cierra, abre y navega hasta el cambio de cuenta"""
        try:
            print(f"🔄 [{self.device_id}] Reiniciando App para rotación limpia...")

            # PASO 0: Cierre y apertura forzada
            self.device.app_stop("com.facebook.katana")
            time.sleep(2)
            self.device.app_start("com.facebook.katana")
            time.sleep(8)  # Espera de carga inicial

            # Paso 1: Menú Lateral (Path validado)
            xpath_inicio ="//android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout[1]/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.FrameLayout[2]/android.widget.LinearLayout[1]/android.widget.FrameLayout[6]"
            if self.device.xpath(xpath_inicio).wait(5):
                self.device.xpath(xpath_inicio).click()
                time.sleep(4)

            # Paso 2: ViewPager (Puente hacia Meta)
            xpath_viewpager = "//android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout[1]/android.widget.FrameLayout/androidx.viewpager.widget.ViewPager/android.widget.FrameLayout/android.widget.FrameLayout[1]/android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/androidx.recyclerview.widget.RecyclerView/android.view.ViewGroup[1]/android.view.ViewGroup/android.view.ViewGroup/android.widget.Button[3]/android.view.ViewGroup"
            if self.device.xpath(xpath_viewpager).exists:
                self.device.xpath(xpath_viewpager).click()
                time.sleep(4)

            # Paso 3: Selección por Índice en RecyclerView
            xpath_lista = '//androidx.recyclerview.widget.RecyclerView/android.view.ViewGroup'
            nodos = self.device.xpath(xpath_lista).all()
            if len(nodos) > 0:
                indice_real = (indice_objetivo % len(nodos)) + 1
                selector_final = f'{xpath_lista}[{indice_real}]'
                self.device.xpath(selector_final).click()
                print(f"👤 [{self.device_id}] Perfil {indice_real} seleccionado.")
                time.sleep(10)
                return True

            return False
        except Exception as e:
            print(f"Error Rotación: {e}")
            return False

    def proceso_compartir_post(self, link: str, detener_flag=None):
        try:
            # 1. Abrimos el link y esperamos a que cargue sin tocar la pantalla
            self.abrir_facebook_link(link)
            print("Cargando link... Esperando renderizado.")
            time.sleep(random.randint(7, 10))

            if "reel" in link.lower():
                print("Tipo detectado: REEL. Usando búsqueda por contiene (contains).")
                btn_compartir = '//*[contains(@content-desc, "Compartir") or contains(@content-desc, "Share")]'
            else:
                print("Tipo detectado: POST. Usando búsqueda por palabra exacta.")
                btn_compartir = '//*[@content-desc="Compartir" or @content-desc="Share"]'

            btn_compartir_ahora = '//*[contains(@text, "Compartir ahora") or contains(@text, "Share now")]'
            btn_escribir_post = '//*[contains(@text, "Escribir publicación") or contains(@text, "Write post") or contains(@text, "Create post")]'
            btn_publicar_final = '//*[@text="PUBLICAR" or @text="POST" or @text="SHARE"]'

            compartir_encontrado = False

            # --- Lógica de Búsqueda con Scroll (5 intentos) ---
            for intento in range(5):
                if detener_flag and detener_flag.is_set(): return False

                print(f"Buscando botón Compartir (Intento {intento + 1})...")

                # Verificamos existencia directamente con el selector
                if self.device.xpath(btn_compartir).exists:
                    print(f"¡Botón Compartir encontrado! Haciendo clic.")
                    time.sleep(1)
                    self.device.xpath(btn_compartir).click()
                    compartir_encontrado = True
                    break

                # Si no existe, hacemos scroll suave desde la mitad
                print("Botón no encontrado, realizando scroll...")
                self.device.swipe(0.5, 0.5, 0.5, 0.2, duration=0.6)
                time.sleep(3)

            # --- Acciones posteriores tras el clic exitoso ---
            if compartir_encontrado:
                time.sleep(4)
                if detener_flag and detener_flag.is_set(): return False

                # Opción 1: Compartir ahora
                if self.device.xpath(btn_compartir_ahora).exists:
                    self.device.xpath(btn_compartir_ahora).click()
                    print(f"✅ [{self.device_id}] Compartido directamente.")
                    return True

                # Opción 2: Escribir publicación
                if self.device.xpath(btn_escribir_post).exists:
                    self.device.xpath(btn_escribir_post).click()
                    time.sleep(5)

                    if self.device.xpath(btn_publicar_final).exists:
                        self.device.xpath(btn_publicar_final).click()
                        print(f"✅ [{self.device_id}] Compartido mediante publicación.")
                        return True

            print(f"❌ [{self.device_id}] No se pudo encontrar el botón Compartir.")
            return False

        except Exception as e:
            print(f"Error Compartir FB: {e}")
            return False

    def cerrar_facebook(self):
        """Cierra forzosamente la aplicación de Facebook"""
        print(f"🛑 [{self.device_id}] Cerrando Facebook...")
        self.device.app_stop("com.facebook.katana")
        time.sleep(2)

    def ejecutar_flujo_completo_fb(self, link: str, texto_comentario: str, detener_flag=None):
        """
        Ejecuta Like, Comentario y Compartir en una sola secuencia.
        Cierra la app después de cada acción exitosa o fallida.
        """
        print(f"🚀 Iniciando flujo completo para el dispositivo: {self.device_id}")

        # 1. EJECUTAR LIKE
        print("\n--- PASO 1: LIKE ---")
        self.proceso_like_facebook(link, detener_flag)
        time.sleep(6)
        self.cerrar_facebook()
        if detener_flag and detener_flag.is_set(): return False

        # 2. EJECUTAR COMENTARIO
        print("\n--- PASO 2: COMENTARIO ---")
        self.proceso_comentario_reels(link, texto_comentario, detener_flag)
        time.sleep(6)
        self.cerrar_facebook()
        #if detener_flag and detener_flag.is_set(): return False

        # 3. EJECUTAR COMPARTIR
        print("\n--- PASO 3: COMPARTIR ---")
        self.proceso_compartir_post(link, detener_flag)
        time.sleep(6)
        self.cerrar_facebook()

        print(f"\n✅ [{self.device_id}] Flujo completo finalizado.")
        return True