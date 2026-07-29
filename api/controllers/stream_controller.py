"""
Stream Controller — WebSocket bidireccional para video + control remoto.
"""

import asyncio
import concurrent.futures
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.utils.stream_manager import stream_manager
from api.utils.device_controller import DeviceController

router = APIRouter()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


# ═══════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════

@router.get("/dispositivo/{device_id}/stats")
async def get_stats(device_id: str):
    return await stream_manager.get_stats(device_id)


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET — Streaming MJPEG + Control Remoto
# ═══════════════════════════════════════════════════════════════

@router.websocket("/ws/stream/{device_id}")
async def stream_ws(ws: WebSocket, device_id: str):
    await ws.accept()

    # Iniciar stream y controlador
    loop = asyncio.get_event_loop()
    reader = await loop.run_in_executor(_executor, stream_manager.start_stream, device_id)
    controller = DeviceController(device_id)
    stream_manager.add_viewer()

    # Enviar screen info al cliente
    screen = controller.screen
    await ws.send_json({
        "type": "screen_info",
        "width": screen.width,
        "height": screen.height,
    })

    async def handle_commands():
        """Escucha comandos del cliente y los ejecuta."""
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    cmd = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                ctype = cmd.get("type", "")
                if ctype == "tap":
                    x, y = int(cmd["x"]), int(cmd["y"])
                    controller.tap(x, y)

                elif ctype == "swipe":
                    x1, y1 = int(cmd["x1"]), int(cmd["y1"])
                    x2, y2 = int(cmd["x2"]), int(cmd["y2"])
                    dur = int(cmd.get("duration", 300))
                    controller.swipe(x1, y1, x2, y2, dur)

                elif ctype == "longpress":
                    x, y = int(cmd["x"]), int(cmd["y"])
                    dur = int(cmd.get("duration", 800))
                    controller.long_press(x, y, dur)

                elif ctype == "key":
                    keycode = int(cmd["keycode"])
                    controller.key(keycode)

                elif ctype == "text":
                    controller.text(cmd["text"])

                elif ctype == "home":
                    controller.home()

                elif ctype == "back":
                    controller.back()

                elif ctype == "recents":
                    controller.recents()

                elif ctype == "enter":
                    controller.enter()

        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    # Lanzar handler de comandos en background
    cmd_task = asyncio.create_task(handle_commands())

    try:
        while True:
            frame = await reader.read_frame()
            if frame is None:
                await asyncio.sleep(1)
                reader = await loop.run_in_executor(
                    _executor, stream_manager.start_stream, device_id
                )
                continue

            try:
                await ws.send_bytes(frame)
            except Exception:
                break

            await asyncio.sleep(0)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        cmd_task.cancel()
        stream_manager.remove_viewer()


# ═══════════════════════════════════════════════════════════════
# HEALTH DEL STREAM
# ═══════════════════════════════════════════════════════════════

@router.get("/stream/status")
async def stream_status():
    active = stream_manager.get_active_device()
    return {
        "active": active is not None,
        "device": active,
    }


@router.post("/stream/stop")
async def stream_stop():
    """Forzar detención del stream actual (para cambio de dispositivo)."""
    stream_manager.stop()
    return {"stopped": True}
