"""
Conecta a WiFi oculta usando uiautomator2 + ADB input (más fiable).
"""

import sys
import time
import uiautomator2 as u2

SSID = "granja"
PASSWORD = "12345678"


def connect_hidden(serial: str) -> bool:
    d = None
    try:
        d = u2.connect(serial)
        print(f"[{serial}] Conectado vía uiautomator2")

        # 1. Abrir WiFi settings
        d.shell("am start -a android.settings.WIFI_SETTINGS")
        time.sleep(3)

        # Debug: ver qué hay en pantalla
        xml = d.dump_hierarchy()
        print(f"[{serial}] Pantalla WiFi abierta. Buscando 'Add network'...")

        # 2. Hacer scroll y buscar "Add network" / "Agregar red"
        # Primero ver si ya es visible sin scroll
        add_clicked = False

        for attempt in range(4):
            for label in ["Add network", "Agregar red", "Añadir red", "Add"]:
                el = d(text=label)
                if el.exists(timeout=1):
                    el.click()
                    add_clicked = True
                    print(f"[{serial}] Botón '{label}' encontrado y clickeado")
                    break
            if add_clicked:
                break
            # Scroll hacia abajo (último elemento suele estar al fondo)
            d.swipe(500, 900, 500, 200, steps=20)
            time.sleep(1.5)

        if not add_clicked:
            # Probar por content-desc
            for label in ["Add network", "Agregar red"]:
                el = d(description=label)
                if el.exists(timeout=1):
                    el.click()
                    add_clicked = True
                    break

        if not add_clicked:
            # Probar botón "+" o icono flotante
            # En Samsung puede estar en menu overflow
            d.press("menu")
            time.sleep(1)
            xml = d.dump_hierarchy()
            if "Add network" in xml or "Agregar" in xml:
                for label in ["Add network", "Agregar red", "Advanced", "Avanzado"]:
                    el = d(textContains=label)
                    if el.exists(timeout=1):
                        el.click()
                        add_clicked = True
                        break
            if not add_clicked:
                d.press("back")  # cerrar menu

        if not add_clicked:
            print(f"[{serial}] ❌ No se encontró botón 'Add network'")
            # DUMP para debuggear
            xml = d.dump_hierarchy()
            print(f"[{serial}] Jerarquía: {xml[:500]}...")
            d.press("home")
            return False

        time.sleep(2)

        # 3. Ahora estamos en la pantalla de agregar red
        xml = d.dump_hierarchy()
        print(f"[{serial}] Pantalla add network. Jerarquía parcial: {xml[:300]}")

        # Escribir SSID usando input text (más fiable que set_text)
        d.shell("input text '%s'" % SSID)
        time.sleep(0.5)

        # 4. Navegar al campo de seguridad (tab)
        d.shell("input keyevent 61")  # KEYCODE_TAB
        time.sleep(0.5)

        # Seleccionar WPA2 PSK con keyevents
        d.shell("input keyevent 61")  # Otro tab (puede ser dropdown)
        time.sleep(0.3)
        d.shell("input keyevent 20")  # DPAD_DOWN para abrir dropdown
        time.sleep(0.5)
        # Navegar a WPA2 PSK (suele ser la 2da opcion)
        for _ in range(2):
            d.shell("input keyevent 20")  # DPAD_DOWN
            time.sleep(0.2)
        d.shell("input keyevent 66")  # ENTER para seleccionar
        time.sleep(0.5)

        # 5. Tab al campo de password
        d.shell("input keyevent 61")  # KEYCODE_TAB
        time.sleep(0.3)
        # Escribir password
        d.shell("input text '%s'" % PASSWORD)
        time.sleep(0.3)

        # 6. Tab hasta Save/Guardar y ENTER
        for _ in range(3):
            d.shell("input keyevent 61")  # KEYCODE_TAB
            time.sleep(0.2)
        d.shell("input keyevent 66")  # ENTER
        time.sleep(5)

        # 7. Verificar conexión
        out = d.shell("dumpsys wifi | grep 'mWifiInfo' | head -1")
        print(f"[{serial}] WiFi info: {out.strip()[:120]}")
        
        if SSID.lower() in out.lower():
            print(f"[{serial}] ✅ Conectado a '{SSID}'")
            d.press("home")
            return True

        # Verificar en redes guardadas
        nets = d.shell("dumpsys wifi | grep 'SSID:' | grep -i granja")
        if nets:
            print(f"[{serial}] ✅ Red '{SSID}' agregada: {nets.strip()[:100]}")
            d.press("home")
            return True

        print(f"[{serial}] ⚠️  Red agregada, verificar conexión manualmente")
        d.press("home")
        return True

    except Exception as e:
        print(f"[{serial}] ❌ Error: {e}")
        if d:
            try:
                d.press("home")
            except:
                pass
        return False


def main():
    if len(sys.argv) < 2:
        print("Uso: python connect_wifi.py <serial1> <serial2> ...")
        sys.exit(1)

    serials = sys.argv[1:]
    print(f"Conectando {len(serials)} dispositivos a red oculta '{SSID}'...\n")

    results = {}
    for i, serial in enumerate(serials):
        print(f"\n--- [{i+1}/{len(serials)}] {serial} ---")
        ok = connect_hidden(serial)
        results[serial] = "✅" if ok else "❌"
        time.sleep(2)

    print(f"\n{'='*50}")
    print(f"RESULTADOS ({SSID}):")
    for serial, status in results.items():
        print(f"  {status} {serial}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
