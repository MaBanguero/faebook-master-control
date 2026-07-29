"""
StreamManager — Orquesta scrcpy + ffmpeg → MJPEG bajo demanda.
Solo 1 stream activo a la vez. Auto-kill tras 60s sin viewers.
"""

import os
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Any, Optional

TEMP_DIR = Path("/tmp/faebook_streams")
TEMP_DIR.mkdir(exist_ok=True)

STREAM_TIMEOUT = 60  # segundos sin viewer → kill


class StreamManager:
    """
    Singleton que gestiona el stream scrcpy.
    
    Pipeline:
      scrcpy --no-window --no-audio → /tmp/video.mkv
      ffmpeg lee el .mkv creciente → MJPEG → stdout
      Python lee frames JPEG → WebSocket → browser
    """

    _instance: Optional["StreamManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._active_device: Optional[str] = None
        self._scrcpy_proc: Optional[subprocess.Popen] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._video_path: Optional[Path] = None
        self._viewer_count: int = 0
        self._lock: threading.Lock = threading.Lock()
        self._timeout_handle: Any = None

    # ── Public API ────────────────────────────────────────────────

    def start_stream(self, device_id: str) -> "FrameReader":
        """Inicia o cambia el stream al dispositivo dado."""
        with self._lock:
            if self._active_device == device_id and self._ffmpeg_proc is not None:
                # Ya está transmitiendo este dispositivo
                return FrameReader(device_id)

            if self._active_device is not None:
                self._kill_pipeline()

            self._active_device = device_id
            self._start_pipeline(device_id)
            return FrameReader(device_id)

    def add_viewer(self):
        with self._lock:
            self._viewer_count += 1
            self._cancel_timeout()

    def remove_viewer(self):
        with self._lock:
            self._viewer_count = max(0, self._viewer_count - 1)
            if self._viewer_count == 0:
                self._schedule_timeout()

    def stop(self):
        with self._lock:
            self._kill_pipeline()
            self._active_device = None

    def get_active_device(self) -> Optional[str]:
        return self._active_device

    # ── Device stats ──────────────────────────────────────────────

    @staticmethod
    async def get_stats(device_id: str) -> dict[str, Any]:
        """Stats: CPU, RAM, batería, temperatura."""

        async def _adb_shell(cmd: str) -> str:
            proc = await asyncio.create_subprocess_exec(
                "adb", "-s", device_id, "shell", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode(errors="ignore").strip()

        stats = {"device_id": device_id}

        # CPU usage
        try:
            out = await _adb_shell("dumpsys cpuinfo | grep 'TOTAL' | head -1")
            if "%" in out:
                pct = out.split("%")[0].strip().split()[-1]
                stats["cpu_percent"] = float(pct.replace(",", "."))
        except Exception:
            stats["cpu_percent"] = 0

        # RAM
        try:
            out = await _adb_shell("cat /proc/meminfo | grep MemAvailable")
            kb = int("".join(c for c in out if c.isdigit()))
            total_out = await _adb_shell("cat /proc/meminfo | grep 'MemTotal'")
            total_kb = int("".join(c for c in total_out if c.isdigit()))
            stats["ram_mb"] = round(kb / 1024, 1)
            stats["ram_total_mb"] = round(total_kb / 1024, 1)
        except Exception:
            stats["ram_mb"] = 0
            stats["ram_total_mb"] = 0

        # Battery
        try:
            out = await _adb_shell("dumpsys battery")
            for line in out.split("\n"):
                line = line.strip()
                if line.startswith("level:"):
                    stats["battery_level"] = int(line.split(":")[1])
                elif line.startswith("temperature:"):
                    raw = int(line.split(":")[1])
                    stats["battery_temp"] = round(raw / 10, 1)
                elif line.startswith("status:"):
                    code = line.split(":")[1].strip()
                    status_map = {"2": "cargando", "3": "descargando", "4": "sin carga", "5": "llena"}
                    stats["battery_status"] = status_map.get(code, code)
        except Exception:
            stats["battery_level"] = 0

        # Model
        try:
            out = await _adb_shell("getprop ro.product.model")
            stats["model"] = out
        except Exception:
            stats["model"] = "-"

        # Screen on?
        try:
            out = await _adb_shell("dumpsys power | grep 'mWakefulness=' | head -1")
            stats["screen_on"] = "Awake" in out
        except Exception:
            stats["screen_on"] = False

        return stats

    # ── Internals ──────────────────────────────────────────────────

    def _start_pipeline(self, device_id: str):
        safe_id = device_id.replace(":", "_")
        self._video_path = TEMP_DIR / f"stream_{safe_id}.mkv"
        self._video_path.unlink(missing_ok=True)

        # Usar el script wrapper que maneja scrcpy + ffmpeg
        script = str(Path(__file__).parent.parent.parent / "stream_device.sh")
        self._ffmpeg_proc = subprocess.Popen(
            [script, device_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        # El script ya lanza scrcpy internamente; guardamos referencia vacía
        self._scrcpy_proc = None

    def _kill_pipeline(self):
        self._cancel_timeout()
        for proc in (self._ffmpeg_proc, self._scrcpy_proc):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        self._ffmpeg_proc = None
        self._scrcpy_proc = None

        if self._video_path:
            self._video_path.unlink(missing_ok=True)
            self._video_path = None

    def _schedule_timeout(self):
        if self._timeout_handle is not None:
            self._timeout_handle.cancel()
        self._timeout_handle = asyncio.get_event_loop().call_later(
            STREAM_TIMEOUT, self._on_timeout
        )

    def _cancel_timeout(self):
        if self._timeout_handle:
            self._timeout_handle.cancel()
            self._timeout_handle = None

    def _on_timeout(self):
        with self._lock:
            if self._viewer_count == 0:
                self._kill_pipeline()
                self._active_device = None


class FrameReader:
    """Lee frames JPEG del stdout de ffmpeg."""

    JPEG_SOI = b"\xff\xd8"
    JPEG_EOI = b"\xff\xd9"

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._buf = b""

    async def read_frame(self) -> Optional[bytes]:
        """Lee un frame JPEG completo. Retorna None si el stream murió."""
        mgr = StreamManager()
        proc = mgr._ffmpeg_proc
        if proc is None or proc.poll() is not None or proc.stdout is None:
            return None

        stdout = proc.stdout
        loop = asyncio.get_event_loop()

        while True:
            # Buscar un JPEG completo en el buffer
            soi = self._buf.find(self.JPEG_SOI)
            eoi = self._buf.find(self.JPEG_EOI, soi + 2) if soi >= 0 else -1

            if soi >= 0 and eoi > soi:
                frame = self._buf[soi : eoi + 2]
                self._buf = self._buf[eoi + 2 :]
                return frame

            # Leer más datos
            try:
                chunk = await loop.run_in_executor(None, stdout.read, 32768)
                if not chunk:
                    return None
                self._buf += chunk
            except Exception:
                return None


# Singleton helper
stream_manager = StreamManager()
