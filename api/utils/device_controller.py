"""
DeviceController — Envía comandos de input al dispositivo vía ADB.
Usa una conexión shell persistente para mínima latencia.
"""

import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceScreen:
    width: int
    height: int

    @staticmethod
    def get(serial: str) -> "DeviceScreen":
        try:
            out = subprocess.run(
                ["adb", "-s", serial, "shell", "wm", "size"],
                capture_output=True, text=True, timeout=5
            )
            line = out.stdout.strip().split("\n")[-1]
            w, h = line.split(":")[-1].strip().split("x")
            return DeviceScreen(int(w), int(h))
        except Exception:
            return DeviceScreen(1080, 1920)


class DeviceController:
    """Controla un dispositivo Android mediante shell ADB persistente (baja latencia)."""

    _shell_procs: dict = {}  # serial → Popen
    _lock = threading.Lock()

    def __init__(self, serial: str):
        self.serial = serial
        self._screen = None
        self._ensure_shell()

    @property
    def screen(self) -> DeviceScreen:
        if self._screen is None:
            self._screen = DeviceScreen.get(self.serial)
        return self._screen

    def _ensure_shell(self):
        """Abre una shell ADB persistente si no existe."""
        with DeviceController._lock:
            if self.serial not in DeviceController._shell_procs:
                proc = subprocess.Popen(
                    ["adb", "-s", self.serial, "shell"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True, bufsize=1,
                )
                time.sleep(0.3)  # esperar que la shell abra
                DeviceController._shell_procs[self.serial] = proc

    def _send(self, cmd: str):
        """Envía comando por la shell persistente (sin esperar respuesta)."""
        proc = DeviceController._shell_procs.get(self.serial)
        if proc is None or proc.poll() is not None:
            self._ensure_shell()
            proc = DeviceController._shell_procs.get(self.serial)
        if proc:
            try:
                proc.stdin.write(cmd + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                del DeviceController._shell_procs[self.serial]
                self._ensure_shell()

    @classmethod
    def close_all(cls):
        """Cierra todas las shells persistentes."""
        with cls._lock:
            for proc in cls._shell_procs.values():
                try:
                    proc.terminate()
                except Exception:
                    pass
            cls._shell_procs.clear()

    # ── Comandos ────────────────────────────────────────────

    def tap(self, x: int, y: int):
        self._send(f"input tap {x} {y}")

    def long_press(self, x: int, y: int, duration_ms: int = 800):
        self._send(f"input swipe {x} {y} {x} {y} {duration_ms}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        self._send(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def key(self, keycode: int):
        self._send(f"input keyevent {keycode}")

    def text(self, text: str):
        safe = text.replace(" ", "%s").replace("'", "\\'")
        self._send(f"input text '{safe}'")

    def home(self):
        self.key(3)

    def back(self):
        self.key(4)

    def recents(self):
        self.key(187)

    def enter(self):
        self.key(66)
