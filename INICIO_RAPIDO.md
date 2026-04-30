# Inicio Rápido - YouTube/TikTok Master Control

## 🚀 Setup en 3 Pasos

### 1. Configurar Entorno Virtual
```bash
# Ejecutar script de configuración automática
setup_venv.bat
```

Esto creará el entorno virtual e instalará todas las dependencias automáticamente.

### 2. Conectar Dispositivos Android

#### Opción A: USB
1. Habilita "Depuración USB" en tu dispositivo Android
2. Conecta el dispositivo por USB
3. Acepta el prompt de depuración en el dispositivo

#### Opción B: WiFi (ADB over Network)
1. Primero conecta por USB
2. Ejecuta en terminal:
   ```bash
   adb tcpip 5555
   adb connect 192.168.1.XX:5555
   ```
3. Ahora puedes desconectar el USB

### 3. Iniciar Servidor
```bash
# Ejecutar servidor
start.bat
```

El servidor estará disponible en: http://localhost:8000

## 📱 Comandos Útiles

### Ver dispositivos conectados
```bash
adb devices
```

### Resetear dispositivos (si hay problemas)
```bash
reset_devices.bat
```

### Verificar estado del servidor
```bash
curl http://localhost:8000/health
```

## 🔧 Estructura de Archivos Importante

```
youtube-tiktok-master-control-python/
├── setup_venv.bat         # ⚙️ Setup automático del entorno
├── start.bat              # ▶️ Iniciar servidor
├── reset_devices.bat      # 🔄 Resetear dispositivos
├── main.py                # 🎯 Punto de entrada
├── requirements.txt       # 📦 Dependencias
├── .env                   # ⚙️ Configuración
└── api/                   # 📁 Código de la API
    ├── controllers/       # 🌐 Endpoints
    ├── models/            # 📝 Modelos de datos
    ├── services/          # 🔧 Lógica de negocio
    └── utils/             # 🛠️ Utilidades (ADB)
```

## 🎯 Próximos Pasos

Una vez que el servidor esté corriendo:

1. **Frontend**: Inicia el proyecto Next.js
   ```bash
   cd ../youtube-tiktok-master-control-nextjs
   npm install
   npm run dev
   ```

2. **Verificar dispositivos**: Ve a http://localhost:3000 y verifica que tus dispositivos aparezcan

3. **Configurar automatización**: Selecciona dispositivos y configura tu primera tarea de likes, comentarios o suscripciones

## ⚠️ Solución de Problemas Comunes

### "Python no encontrado"
- Instala Python 3.8+ desde [python.org](https://python.org)
- Asegúrate de marcar "Add to PATH" durante la instalación

### "ADB no encontrado"
- Descarga Android Platform Tools
- Extrae en `C:\adb\`
- Verifica con: `C:\adb\adb.exe version`

### "Device unauthorized"
- Desconecta y reconecta el dispositivo USB
- Acepta el prompt "Allow USB debugging" en el dispositivo
- Marca "Always allow from this computer"

### "UIAutomator2 not working"
1. Ejecuta `reset_devices.bat`
2. Si persiste, reinstala UIAutomator2:
   ```python
   import uiautomator2 as u2
   u2.connect("device_id").app_install("https://github.com/openatx/android-uiautomator-server/releases/download/2.0.0/app-uiautomator.apk")
   ```

## 📞 ¿Necesitas Ayuda?

- Revisa los logs del servidor (aparecen en la terminal)
- Verifica el estado de ADB: `adb devices`
- Asegúrate de que el puerto 8000 no esté en uso
