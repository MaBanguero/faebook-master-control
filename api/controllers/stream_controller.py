"""
Stream Controller — WebSocket para video + REST para stats de dispositivos.
"""

import asyncio
import concurrent.futures
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.utils.stream_manager import stream_manager

router = APIRouter()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


# ═══════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════

@router.get("/dispositivo/{device_id}/stats")
async def get_stats(device_id: str):
    """Obtiene stats en tiempo real del dispositivo."""
    return await stream_manager.get_stats(device_id)


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET — Streaming MJPEG
# ═══════════════════════════════════════════════════════════════

@router.websocket("/ws/stream/{device_id}")
async def stream_ws(ws: WebSocket, device_id: str):
    await ws.accept()

    # Iniciar stream en thread aparte para no bloquear el event loop
    loop = asyncio.get_event_loop()
    reader = await loop.run_in_executor(_executor, stream_manager.start_stream, device_id)
    stream_manager.add_viewer()

    try:
        while True:
            frame = await reader.read_frame()
            if frame is None:
                # Stream murió — intentar reiniciar
                await asyncio.sleep(1)
                reader = stream_manager.start_stream(device_id)
                continue

            try:
                await ws.send_bytes(frame)
            except Exception:
                break  # cliente desconectado

            # Yield control — no saturar
            await asyncio.sleep(0)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        stream_manager.remove_viewer()


# ═══════════════════════════════════════════════════════════════
# HEALTH DEL STREAM
# ═══════════════════════════════════════════════════════════════

@router.get("/stream/status")
async def stream_status():
    """Estado actual del stream."""
    active = stream_manager.get_active_device()
    return {
        "active": active is not None,
        "device": active,
    }
