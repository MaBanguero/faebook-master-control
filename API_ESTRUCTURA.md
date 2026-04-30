# Estructura de la API - YouTube/TikTok Master Control

## 📋 Resumen

Backend FastAPI para automatización de YouTube y TikTok usando dispositivos Android.

## 🗂️ Estructura de Directorios

```
api/
├── controllers/              # Endpoints de la API (FastAPI)
│   ├── dispositivo_controller.py   # Gestión de dispositivos
│   ├── tareas_controller.py        # Gestión de tareas
│   ├── likes_controller.py         # TODO: Automatización de likes
│   ├── comentarios_controller.py   # TODO: Automatización de comentarios
│   ├── compartidas_controller.py   # TODO: Automatización compartidas
│   └── suscripciones_controller.py # TODO: Automatización suscripciones
│
├── models/                   # Modelos Pydantic (request/response)
│   ├── dispositivo.py        # Dispositivo, DispositivoEstado
│   ├── likes.py              # LikesRequest, LikesResponse
│   ├── comentarios.py        # ComentariosRequest, ComentariosResponse
│   ├── compartidas.py        # CompartidaRequest, CompartidaResponse
│   ├── suscripciones.py      # SuscripcionesRequest, SuscripcionesResponse
│   └── tarea_activa.py       # TareaActiva, Metricas
│
├── services/                 # Lógica de negocio
│   ├── dispositivo_service.py      # Gestión de dispositivos con cache
│   ├── tareas_service.py           # Gestión de tareas en memoria
│   ├── likes_service.py            # TODO: Lógica de likes
│   ├── comentarios_service.py      # TODO: Lógica de comentarios
│   ├── compartidas_service.py      # TODO: Lógica de compartidas
│   └── suscripciones_service.py    # TODO: Lógica de suscripciones
│
└── utils/                    # Utilidades
    ├── adb_utils.py          # Gestor ADB estándar
    ├── adb_custom_server.py  # Servidor ADB personalizado
    └── youtube_tiktok_automation.py  # TODO: Automatización con UIAutomator2
```

## 🌐 Endpoints Disponibles

### Dispositivos (`/api/dispositivos`)
```python
GET    /api/dispositivos              # Lista todos los dispositivos
GET    /api/dispositivos/{id}         # Obtiene un dispositivo específico
POST   /api/dispositivos/{id}/comando # Ejecuta comando ADB en dispositivo
GET    /api/adb/status                # Verifica estado de ADB
```

### Tareas (`/api/tareas`)
```python
GET    /api/tareas/activas            # Tareas en ejecución
GET    /api/tareas/{id}               # Obtiene tarea específica por ID
GET    /api/tareas                    # Todas las tareas (incluidas completadas)
DELETE /api/tareas/{id}               # Cancela una tarea activa
```

### Likes (`/api/likes`) - TODO
```python
POST   /api/likes/iniciar             # Inicia automatización de likes
POST   /api/likes/detener             # Detiene automatización de likes
GET    /api/likes/estado              # Estado actual de likes
```

### Comentarios (`/api/comentarios`) - TODO
```python
POST   /api/comentarios/ejecutar      # Ejecuta automatización de comentarios
GET    /api/comentarios/estado        # Estado de comentarios
```

### Compartidas (`/api/compartidas`) - TODO
```python
POST   /api/compartidas/ejecutar      # Ejecuta automatización de compartidas
GET    /api/compartidas/estado        # Estado de compartidas
```

### Suscripciones (`/api/suscripciones`) - TODO
```python
POST   /api/suscripciones/ejecutar    # Ejecuta automatización de suscripciones
GET    /api/suscripciones/estado      # Estado de suscripciones
```

## 📝 Modelos de Datos

### Dispositivo
```python
{
  "id": "a1b2c3d4",              # Hash MD5 del ADB ID
  "nombre": "📡 Samsung (192.168.1.11:5555)",
  "estado": "inactivo",          # inactivo | en_tarea | trabajando | error
  "adb_id": "192.168.1.11:5555", # ID de ADB
  "ultima_actualizacion": "2025-11-13T10:30:00"
}
```

### LikesRequest
```python
{
  "dispositivos_ids": ["dev1", "dev2"],
  "tipo": "positivo",              # positivo | negativo
  "link_video": "https://youtube.com/watch?v=...",
  "plataforma": "youtube",         # youtube | tiktok
  "cantidad_likes": 5,
  "delay_entre_dispositivos": 10,
  "intentos_maximos": 5,
  "tiempo_espera_entre_ciclos": 30,
  "tiempo_reintento_caducado": 5,
  "tiempo_limite_ciclo": 300
}
```

### ComentariosRequest
```python
{
  "dispositivos_ids": ["dev1", "dev2"],
  "link_video": "https://youtube.com/watch?v=...",
  "plataforma": "youtube",         # youtube | tiktok
  "cantidad_comentarios": 3,
  "comentarios_personalizados": ["Comentario 1", "Comentario 2"],
  "delay_entre_comentarios": 15,
  "intentos_maximos": 5
}
```

### CompartidaRequest
```python
{
  "dispositivos_ids": ["dev1", "dev2"],
  "link_video": "https://youtube.com/watch?v=...",
  "plataforma": "youtube",         # youtube | tiktok
  "cantidad_compartidas": 3,
  "delay_entre_compartidas": 15,
  "intentos_maximos": 5
}
```

### SuscripcionesRequest
```python
{
  "dispositivos_ids": ["dev1", "dev2"],
  "perfil_objetivo": "https://youtube.com/@canal",
  "plataforma": "youtube",         # youtube | tiktok
  "cantidad_suscripciones": 1,
  "delay_entre_suscripciones": 10,
  "intentos_maximos": 5
}
```

### TareaActiva
```python
{
  "id": "uuid-v4",
  "tipo": "likes",                 # likes | comentarios | compartidas | suscripciones
  "estado": "ejecutando",          # iniciando | ejecutando | completada | fallida
  "dispositivos_ids": ["dev1", "dev2"],
  "metricas": {
    "total_esperado": 10,
    "exitosos": 7,
    "fallidos": 1,
    "en_proceso": 2
  },
  "config": { ... },               # Configuración original de la tarea
  "fecha_inicio": "2025-11-13T10:30:00",
  "fecha_fin": null
}
```

## 🔧 Servicios Principales

### DispositivoService (Singleton)
- Gestión de cache de dispositivos con refresh automático
- Búsqueda por ID hash o ADB ID
- Actualización de estados thread-safe
- Refresh interval: 10 segundos

### TareasService (Singleton)
- Gestión de tareas en memoria
- Creación y seguimiento de tareas
- Actualización de métricas en tiempo real
- Limpieza automática de tareas antiguas
- Manejo automático de estados de dispositivos

### CustomADBManager (Singleton)
- Servidor ADB con puerto personalizado (.env)
- Gestión de conexiones USB y Network
- Ejecución de comandos en dispositivos
- Detección automática de tipo de conexión

## 🎯 Flujo de una Tarea

1. **Frontend** envía request a `/api/likes/iniciar`
2. **Controller** valida request y crea tarea
3. **TareasService** registra tarea y marca dispositivos como "en_tarea"
4. **LikesService** ejecuta automatización en cada dispositivo
5. **Automation** usa UIAutomator2 para interactuar con YouTube/TikTok
6. **Service** actualiza métricas en tiempo real
7. **TareasService** finaliza tarea y restaura dispositivos a "inactivo"
8. **Frontend** recibe updates vía polling o websockets

## 🔐 Variables de Entorno (.env)

```env
# Servidor FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000

# Servidor ADB personalizado
CUSTOM_ADB_PORT=5037

# Configuración de automatización
CUENTAS_POR_DISPOSITIVO=5
```

## 📊 Estados de Dispositivo

- **inactivo**: Disponible para nuevas tareas
- **en_tarea**: Asignado a una tarea (no disponible)
- **trabajando**: Ejecutando operación actualmente
- **error**: Error en última operación

## 📊 Estados de Tarea

- **iniciando**: Tarea creada, dispositivos siendo preparados
- **ejecutando**: Automatización en progreso
- **completada**: Finalizada exitosamente
- **fallida**: Finalizada con errores o cancelada

## 🛠️ Próximos Pasos de Desarrollo

1. **Implementar controladores de automatización**:
   - `likes_controller.py`
   - `comentarios_controller.py`
   - `compartidas_controller.py`
   - `suscripciones_controller.py`

2. **Implementar servicios de automatización**:
   - `likes_service.py`
   - `comentarios_service.py`
   - `compartidas_service.py`
   - `suscripciones_service.py`

3. **Crear archivo de automatización**:
   - `youtube_tiktok_automation.py` (con UIAutomator2)
   - Definir XPaths para YouTube y TikTok
   - Implementar lógica de interacción

4. **Agregar WebSockets** para updates en tiempo real

5. **Implementar persistencia** (opcional):
   - Base de datos para tareas históricas
   - Logs de operaciones
   - Estadísticas de rendimiento
