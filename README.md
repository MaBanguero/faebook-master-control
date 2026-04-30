# YouTube/TikTok Master Control - Python Backend

Sistema de automatización para YouTube y TikTok usando dispositivos Android.

## 🚀 Inicio Rápido

### 1. Crear entorno virtual e instalar dependencias

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Edita el archivo `.env` con tu configuración:

```env
# Puerto del servidor FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000

# Puerto del servidor ADB personalizado
CUSTOM_ADB_PORT=5037

# Configuración de automatización
CUENTAS_POR_DISPOSITIVO=5
```

### 3. Conectar dispositivos

Conecta tus dispositivos Android vía USB o WiFi (ADB over Network).

Para WiFi, primero conecta por USB y ejecuta:
```bash
adb tcpip 5555
adb connect 192.168.1.XX:5555
```

### 4. Iniciar servidor

```bash
# Opción 1: Usando script BAT (Windows)
start.bat

# Opción 2: Directamente con Python
python main.py

# Opción 3: Con Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

El servidor estará disponible en: `http://localhost:8000`

## 📱 Gestión de Dispositivos

### Resetear dispositivos (si hay problemas con UIAutomator2)

```bash
# Opción 1: Script BAT (Windows)
reset_devices.bat

# Opción 2: Script Python
python reset_all_devices.py
```

## 🛠️ Estructura del Proyecto

```
youtube-tiktok-master-control-python/
├── api/
│   ├── controllers/     # Endpoints de la API
│   ├── models/          # Modelos Pydantic
│   ├── services/        # Lógica de negocio
│   └── utils/           # Utilidades (ADB, automation)
├── main.py              # Punto de entrada
├── requirements.txt     # Dependencias Python
├── .env                 # Variables de entorno
└── reset_all_devices.py # Reset de UIAutomator2
```

## 📡 API Endpoints

### Dispositivos
- `GET /api/dispositivos` - Lista todos los dispositivos
- `GET /api/dispositivos/{id}` - Obtiene un dispositivo específico
- `POST /api/dispositivos/{id}/comando` - Ejecuta comando ADB
- `GET /api/adb/status` - Estado de ADB

### Tareas
- `GET /api/tareas/activas` - Tareas en ejecución
- `GET /api/tareas/{id}` - Obtiene tarea específica
- `DELETE /api/tareas/{id}` - Cancela una tarea

### Automatización (TODO)
- `POST /api/likes/iniciar` - Iniciar likes
- `POST /api/comentarios/ejecutar` - Ejecutar comentarios
- `POST /api/compartidas/ejecutar` - Ejecutar compartidas
- `POST /api/suscripciones/ejecutar` - Ejecutar suscripciones

## 🔧 Requisitos

- Python 3.8+
- ADB (Android Debug Bridge) instalado en `C:\adb\adb.exe`
- Dispositivos Android con depuración USB habilitada
- UIAutomator2 instalado en los dispositivos

## 📝 Notas

- El servidor ADB personalizado usa el puerto configurado en `.env` (default: 5037)
- Los dispositivos deben tener UIAutomator2 instalado
- Si hay problemas de conexión, ejecuta `reset_devices.bat`

## 🐛 Solución de Problemas

### "Error: device not found"
- Verifica que los dispositivos estén conectados: `adb devices`
- Reinicia el servidor ADB: `adb kill-server && adb start-server`

### "UIAutomator2 not working"
- Ejecuta el script de reset: `reset_devices.bat`
- Reinstala UIAutomator2 en el dispositivo

### Puerto ADB en uso
- Cambia `CUSTOM_ADB_PORT` en `.env` a otro puerto (ej: 5038)
- Reinicia el servidor
