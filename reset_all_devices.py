"""
Script para resetear el servicio uiautomator2 en todos los dispositivos
Versión para YouTube/TikTok Master Control
"""
import subprocess
import time
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
CUSTOM_ADB_PORT = int(os.getenv('CUSTOM_ADB_PORT', '5037'))
ADB_PATH = 'adb'

def reset_device(serial: str):
    """Reset completo de uiautomator2 en un dispositivo"""
    try:
        print(f"\n🔄 Reseteando {serial}...")
        
        # 1. Force-stop apps de uiautomator2
        subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', serial, 'shell', 'am', 'force-stop', 'com.github.uiautomator'],
            capture_output=True, 
            timeout=5
        )
        subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', serial, 'shell', 'am', 'force-stop', 'com.github.uiautomator.test'],
            capture_output=True, 
            timeout=5
        )
        print(f"   ✅ Apps uiautomator cerradas")
        
        # 2. Matar todos los procesos relacionados
        subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', serial, 'shell', 'pkill', '-9', 'uiautomator'],
            capture_output=True, 
            timeout=5
        )
        subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', serial, 'shell', 'pkill', '-9', 'atd'],
            capture_output=True, 
            timeout=5
        )
        print(f"   ✅ Procesos uiautomator/atd detenidos")
        
        # 3. Limpiar servicio de accesibilidad
        subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', serial, 'shell', 'settings', 'put', 'secure', 'enabled_accessibility_services', 'null'],
            capture_output=True, 
            timeout=5
        )
        print(f"   ✅ Accessibility services limpiados")
        
        # 4. Limpiar archivos temporales
        subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', serial, 'shell', 'rm', '-rf', '/data/local/tmp/minicap*'],
            capture_output=True, 
            timeout=5
        )
        subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), '-s', serial, 'shell', 'rm', '-rf', '/data/local/tmp/minitouch*'],
            capture_output=True, 
            timeout=5
        )
        print(f"   ✅ Cache temporal limpiado")
        
        print(f"✅ {serial} reseteado exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error en {serial}: {e}")
        return False

def get_connected_devices():
    """Obtiene dispositivos conectados"""
    try:
        result = subprocess.run(
            [ADB_PATH, '-P', str(CUSTOM_ADB_PORT), 'devices'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        devices = []
        for line in result.stdout.strip().split('\n')[1:]:
            if line.strip() and '\tdevice' in line:
                device_id = line.split('\t')[0]
                devices.append(device_id)
        
        return devices
    except:
        return []

def main():
    print('=' * 60)
    print('🔄 RESET DE DISPOSITIVOS - YOUTUBE/TIKTOK MASTER CONTROL')
    print('=' * 60)
    print()
    
    print('📱 Detectando dispositivos conectados...')
    devices = get_connected_devices()
    
    if not devices:
        print('⚠️  No hay dispositivos conectados')
        print('   Verifica que estén conectados por USB o WiFi')
        return
    
    print(f'✅ {len(devices)} dispositivo(s) detectado(s)')
    print()
    
    success = 0
    for serial in devices:
        if reset_device(serial):
            success += 1
        time.sleep(0.5)
    
    print()
    print('=' * 60)
    print(f'✅ Reset completado: {success}/{len(devices)} dispositivos')
    print('=' * 60)
    print()
    print('💡 Los dispositivos están listos para usar')
    print()

if __name__ == '__main__':
    main()
