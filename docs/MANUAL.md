# 📖 Manual de Usuario — FaeBook Master Control

Sistema de automatización multi-plataforma para Facebook, TikTok e Instagram
vía dispositivos Android conectados por ADB/USB.

---

## 1. 🏠 Dashboard (Panel Principal)

**Ruta:** Pestaña **Dashboard** en el sidebar.

### Lo que ves:
| Elemento | Descripción |
|---|---|
| **Tarjetas de stats** | Total de dispositivos, tareas activas, completadas, plataformas (3) |
| **Grid de dispositivos** | Cada tarjeta muestra ID, nombre (modelo + ADB serial), estado actual |
| **Tareas activas** | Barra de progreso con % completado, éxitos/fallos, botón Cancelar |

### Estados de dispositivo:
- `inactivo` — Libre, listo para recibir tareas
- `en_tarea` / `trabajando` — Ejecutando una automatización
- `error` — Falló la última operación

### Flujo:
```
Servidor → ADB scan → 38 dispositivos → Cache → Polling cada 10s
                                                      ↓
                                            Frontend renderiza grid + stats
```

---

## 2. 📘 Facebook

**Ruta:** Pestaña **Facebook** en el sidebar.

### 2.1 Flujo Multi-Cuenta (Like + Comentario + Compartir)

**Paso a paso:**
1. Pega la **URL del post/reel** de Facebook
2. Escribe **comentarios** (1 por línea = 1 cuenta distinta). Déjalo vacío si solo quieres likes + compartir.
3. Selecciona los **dispositivos** (checkboxes). Solo los `inactivo` se pueden seleccionar.
4. (Opcional) **Cuentas a usar**: 0 = secuencial (avanza con cada ejecución), N = N cuentas al azar.
5. Haz clic en **🚀 Ejecutar Flujo Completo**

**Qué hace en cada dispositivo:**
```
1. Abre Facebook → va al link del reel
2. Rota a la cuenta correspondiente (índice secuencial o aleatorio)
3. Da LIKE (busca botón "reacciones")
4. Escribe + publica COMENTARIO
5. COMPARTE el post
6. Marca dispositivo como inactivo
```

### 2.2 Acciones Individuales

| Botón | Qué hace |
|---|---|
| **👍 Solo Likes** | Da like al link en los dispositivos seleccionados |
| **💬 Solo Comentarios** | Publica comentarios (1 por cuenta) |
| **📤 Solo Compartir** | Comparte el post |
| **🔄 Rotar Cuentas** | Cambia a la siguiente cuenta de Facebook en cada dispositivo |

### 2.3 Calentamiento 🔥

Simula comportamiento humano para evitar detección:
- Abre Facebook, navega el feed
- Scroll aleatorio, pausas variables
- Likes esporádicos a contenido del feed
- Cambia de cuenta periódicamente
- No comenta ni comparte (solo observa)

**Inicio:** Botón **Iniciar Calentamiento** → selecciona dispositivos.

---

## 3. 🎵 TikTok

**Ruta:** Pestaña **TikTok** en el sidebar.

### 3.1 Flujo Multi-Cuenta

**Paso a paso:**
1. Pega la **URL del video** de TikTok
2. Escribe **comentarios** (1 por línea). Vacío = solo likes + compartir.
3. Selecciona **dispositivos**
4. Haz clic en **🚀 Ejecutar Flujo Completo**

**Qué hace en cada dispositivo:**
```
1. Abre TikTok → va al video
2. Da LIKE (doble tap o botón)
3. Por cada comentario: cambia de cuenta, escribe, publica
4. COMPARTE el video
```

### 3.2 Calentamiento 🔥

Navega TikTok con comportamiento humano:
- Scroll vertical en el feed "Para Ti"
- Pausas aleatorias viendo videos (5-35 segundos)
- Likes y favoritos ocasionales
- Cambio de cuentas automático

---

## 4. 📸 Instagram

**Ruta:** Pestaña **Instagram** en el sidebar.

### 4.1 Flujo Multi-Cuenta

**Paso a paso:**
1. Pega la **URL del reel** de Instagram
2. Escribe **comentarios** (1 por línea)
3. Selecciona **dispositivos**
4. Haz clic en **🚀 Ejecutar Flujo Completo**

**Qué hace en cada dispositivo:**
```
1. Abre Instagram → va al reel
2. Da LIKE
3. Rota cuenta → publica COMENTARIO (1 por cuenta)
4. Compartir (desactivado por ahora — limitación de Instagram)
```

### 4.2 Calentamiento 🔥

Simula uso humano de Instagram:
- Navega reels, ve stories
- Scroll, pausas, likes aleatorios
- Cambio automático de cuentas

---

## 5. 🤖 Generador de Comentarios con IA

**Ruta:** Sección **🤖 Generar con IA** dentro de cada pestaña de plataforma.

**Paso a paso:**
1. Escribe el **tema del post** (ej: "Nuevo iPhone 17, reseña honesta")
2. Selecciona **cantidad** de comentarios (1-30)
3. Haz clic en **✨ Generar Comentarios**

**Flujo técnico:**
```
Frontend → POST /api/comentarios/generar
              ↓
  AICommentsService.generate_for_devices()
              ↓
  DeepSeek API (deepseek-chat) → JSON con comentarios
              ↓
  Si falla → plantilla local de respaldo
              ↓
  Rellena el textarea con los comentarios generados
```

**Prompt del sistema:**
> Eres un community manager senior. Escribe comentarios cortos, auténticos y variados con jerga natural. Solo devuelve JSON válido.

---

## 6. 📡 Streaming de Dispositivos

**Ruta:** Pestaña **Streaming** en el sidebar.

### Cómo usar:
1. Selecciona un dispositivo del **dropdown**
2. Espera **~15 segundos** (scrcpy inicializando)
3. El **video en vivo** aparece a pantalla completa
4. **Stats** (CPU, RAM, batería, temp) se actualizan cada 2s

### Pipeline técnico:
```
scrcpy --no-window → /tmp/faebook_streams/*.mkv
        ↓ (Python feeder thread)
ffmpeg → MJPEG → stdout
        ↓ (WebSocket)
Navegador → <img> actualizado por cada frame JPEG
```

### Optimizaciones:
- Solo **1 stream activo** a la vez (los demás se matan al cambiar)
- Auto-kill tras **60s sin viewer**
- 1080p @ 15fps, calidad JPEG q:v 3
- ~80 MB RAM por stream

---

## 7. 🧠 Generador de Comentarios IA

**Endpoint:** `POST /api/comentarios/generar`

```json
{
  "tema": "reseña del nuevo MacBook Pro M4",
  "cantidad": 5
}
```

**Respuesta:**
```json
{
  "comentarios": [
    "🔥 Qué bestia ese M4, vuela literal",
    "Justo ando viendo si upgradear mi M1...",
    "El diseño ni se toca, perfecto",
    "Ese trackpad es de otro planeta",
    "Cuánto sale en Colombia? Necesito uno ya"
  ]
}
```

**Configuración (variables de entorno `.env`):**
| Variable | Default | Descripción |
|---|---|---|
| `DEEPSEEK_API_KEY` | (requerido) | API key de DeepSeek |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Modelo a usar |
| `DEEPSEEK_TEMPERATURE` | `0.65` | Creatividad (0-1) |
| `DEEPSEEK_LANGUAGE` | `es` | Idioma objetivo |
| `DEEPSEEK_TONE` | `conversacional` | Tono de los comentarios |

---

## 8. 📊 API REST — Referencia Rápida

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/dispositivos` | Lista todos los dispositivos |
| `GET` | `/api/tareas` | Lista todas las tareas |
| `DELETE` | `/api/tareas/{id}` | Cancela una tarea |
| `POST` | `/api/facebook/flujo-multi-cuenta/ejecutar` | Flujo FB multi-cuenta |
| `POST` | `/api/likes/facebook/ejecutar` | Solo likes FB |
| `POST` | `/api/comentarios/facebook/ejecutar` | Solo comentarios FB |
| `POST` | `/api/compartir/facebook/ejecutar` | Solo compartir FB |
| `POST` | `/api/facebook/calentamiento/ejecutar` | Calentamiento FB |
| `POST` | `/api/tiktok/flujo-multi-cuenta/ejecutar` | Flujo TT multi-cuenta |
| `POST` | `/api/tiktok/calentamiento/ejecutar` | Calentamiento TT |
| `POST` | `/api/instagram/flujo-multi-cuenta/ejecutar` | Flujo IG multi-cuenta |
| `POST` | `/api/instagram/calentamiento/ejecutar` | Calentamiento IG |
| `POST` | `/api/comentarios/generar` | Generar comentarios IA |
| `GET` | `/api/dispositivo/{id}/stats` | Stats del dispositivo |
| `WS` | `/api/ws/stream/{id}` | Streaming MJPEG |
| `GET` | `/api/stream/status` | Estado del stream |

---

## 9. 🐛 Solución de Problemas

| Problema | Solución |
|---|---|
| **Dispositivo no aparece** | `adb devices`, verificar cable USB o WiFi |
| **Likes/comentarios no se ejecutan** | Verificar que uiautomator2 esté instalado: `python -m uiautomator2 init` |
| **Streaming no carga** | Esperar 15-20s (scrcpy tarda en inicializar). Ver `ps aux \| grep scrcpy` |
| **Servidor se cae (OOM)** | Cerrar pestañas del dashboard. El polling cada 10s con 38 disp es intensivo |
| **"device not online"** | Reiniciar ADB: `adb kill-server && adb start-server` |
| **Cuentas no rotan en FB** | Verificar que el dispositivo tenga cuentas guardadas en la app de Facebook |
| **Error 404 en comentarios** | Verificar que DeepSeek API key esté en `.env` |

---

## 10. 🚀 Inicio Rápido

```bash
# 1. Activar entorno virtual
cd faebook-master-control
source .venv/bin/activate

# 2. Verificar dispositivos
adb devices

# 3. Iniciar servidor
python main.py

# 4. Abrir dashboard
# Local:  http://localhost:8001
# Remoto: http://100.74.217.35:8001 (Tailscale)
```
