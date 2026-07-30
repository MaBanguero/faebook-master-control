"""
Logs Controller — WebSocket para streaming de logs en tiempo real.
"""

from fastapi import APIRouter, WebSocket
from api.utils.log_streamer import log_streamer

router = APIRouter()


@router.websocket("/ws/logs")
async def logs_ws(ws: WebSocket):
    await log_streamer.stream(ws)
