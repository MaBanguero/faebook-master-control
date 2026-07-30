"""
LogStreamer — Captura stdout/stderr del servidor y los transmite vía WebSocket.
Buffer circular de últimas 500 líneas + streaming en tiempo real.
"""

import sys
import asyncio
import threading
from collections import deque
from datetime import datetime
from typing import List, Set


class LogStreamer:
    """Singleton: captura print() + stderr, buffer circular + WebSocket broadcast."""

    MAX_LINES = 500

    def __init__(self):
        self._buffer: deque = deque(maxlen=self.MAX_LINES)
        self._clients: Set = set()
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop = None

    def start(self, loop: asyncio.AbstractEventLoop):
        """Inicia la captura de stdout/stderr."""
        self._loop = loop

        class TeeStream:
            def __init__(self, original, logster):
                self.original = original
                self.logster = logster

            def write(self, data):
                self.original.write(data)
                if data.strip():
                    self.logster._add_line(data.rstrip())

            def flush(self):
                self.original.flush()

        sys.stdout = TeeStream(sys.stdout, self)
        sys.stderr = TeeStream(sys.stderr, self)

    def _add_line(self, line: str):
        now = datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] {line}"
        with self._lock:
            self._buffer.append(entry)
        self._broadcast(entry)

    def _broadcast(self, entry: str):
        if self._loop is None:
            return
        dead = set()
        for client in list(self._clients):
            try:
                asyncio.run_coroutine_threadsafe(client.send_text(entry), self._loop)
            except Exception:
                dead.add(client)
        self._clients -= dead

    def get_recent(self, count: int = 100) -> List[str]:
        with self._lock:
            return list(self._buffer)[-count:]

    async def stream(self, ws):
        """WebSocket handler: envía historial + streaming."""
        await ws.accept()
        self._clients.add(ws)

        # Enviar últimas 100 líneas
        recent = self.get_recent(100)
        for line in recent:
            try:
                await ws.send_text(line)
            except Exception:
                break

        # Mantener vivo (los nuevos logs se envían vía broadcast)
        try:
            while True:
                await asyncio.sleep(30)
                await ws.send_text("")  # ping
        except Exception:
            pass
        finally:
            self._clients.discard(ws)


log_streamer = LogStreamer()
