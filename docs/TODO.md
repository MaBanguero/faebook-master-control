# 🚧 Tareas Pendientes — FaeBook Master Control

Última actualización: 2026-07-28

---

## 🔴 Tracking de Interacciones

- [x] InteractionTracker con persistencia JSON por nombre de cuenta
- [x] FacebookAutomator: método `rotar_a_cuenta(nombre)`
- [x] Facebook: _worker_like con tracking
- [x] Facebook: _worker_flujo_multi_cuenta con tracking
- [x] Facebook: _worker_flujo_completo con tracking
- [ ] **TikTok**: integrar tracker en `_worker_flujo_multi_cuenta` y `_worker_calentamiento`
- [ ] **Instagram**: integrar tracker en `_worker_flujo` y `_worker_calentamiento`
- [ ] Endpoint API: `GET /api/tracking/{adb_id}/stats` — cuentas usadas/disponibles por link
- [ ] Endpoint API: `DELETE /api/tracking/{adb_id}/{cuenta}/{link}` — limpiar registro manual
- [ ] Endpoint API: `DELETE /api/tracking/clear` — limpiar todo el tracking
- [ ] Frontend: mostrar cuentas disponibles/usadas en el panel de estadísticas
- [ ] Soportar acciones adicionales en tracker: `comment`, `share` (actualmente solo `like`)

---

## 🟡 Estabilidad del Servidor  

- [x] Reducir polling de 3s a 10s (evitar OOM)
- [x] Saltar `reset_all_devices` en startup (38 disp saturan RAM)
- [ ] Mover `custom_adb_manager` stderr a archivo de log (evitar spam en stdout)
- [ ] Limpiar tareas antiguas automáticamente (>24h)
- [ ] Monitoreo de memoria: alerta si pasa de 500MB

---

## 🟢 Frontend / UX

- [x] Dashboard responsive con sidebar colapsable (mobile)
- [x] Streaming fullscreen sin scroll
- [x] Nombre completo de dispositivo en checkboxes
- [ ] Panel de Tracking en Dashboard: tabla de interacciones por dispositivo
- [ ] Botón "Limpiar tracking" con confirmación
- [ ] Indicador visual de tareas en ejecución en el sidebar (badge de notificación)
- [ ] Barra de búsqueda/filtro en la lista de dispositivos

---

## 🔵 Automatización

- [ ] Reintentos automáticos en likes fallidos (máx 3 intentos)
- [ ] Reporte post-ejecución: resumen de éxitos/fallos por cuenta
- [ ] Calentamiento programable (cron) vía API
- [ ] Soporte para ejecución secuencial (no paralela) en modo "batería baja"
- [ ] Instagram: habilitar compartir (actualmente desactivado)

---

## ⚪ Infraestructura

- [x] Script `stream_device.sh` wrapper scrcpy+ffmpeg
- [x] Endpoint WebSocket `/api/ws/stream/{device_id}`
- [x] Tailscale acceso remoto
- [ ] Dockerfile para despliegue portable
- [ ] Healthcheck automático de dispositivos (ping ADB cada 60s)
- [ ] Backup automático de `data/interactions.json` a GitHub
