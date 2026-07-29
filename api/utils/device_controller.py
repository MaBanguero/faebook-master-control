"""
DeviceController — Envía comandos de input al dispositivo vía ADB.
No requiere uiautomator2, solo adb shell input.
"""

import subprocess
import time
from dataclasses import dataclass
from typing import Tuple


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
            # Output: "Physical size: 1080x1920" or "Override size: 1080x1920"
            line = out.stdout.strip().split("\n")[-1]
            w, h = line.split(":")[-1].strip().split("x")
            return DeviceScreen(int(w), int(h))
        except Exception:
            return DeviceScreen(1080, 1920)


class DeviceController:
    """Controla un dispositivo Android mediante adb shell input."""

    def __init__(self, serial: str):
        self.serial = serial
        self._screen = None

    @property
    def screen(self) -> DeviceScreen:
        if self._screen is None:
            self._screen = DeviceScreen.get(self.serial)
        return self._screen

    def _adb(self, cmd: str) -> bool:
        try:
            r = subprocess.run(
                ["adb", "-s", self.serial, "shell"] + cmd.split(),
                capture_output=True, timeout=5
            )
            return r.returncode == 0
        except Exception:
            return False

    def tap(self, x: int, y: int):
        """Tap en coordenadas absolutas."""
        return self._adb(f"input tap {x} {y}")

    def long_press(self, x: int, y: int, duration_ms: int = 800):
        """Long press simulando swipe de 0 distancia."""
        return self._adb(f"input swipe {x} {y} {x} {y} {duration_ms}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Deslizar de (x1,y1) a (x2,y2)."""
        return self._adb(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def key(self, keycode: int):
        """Enviar keyevent (4=back, 3=home, 187=recents, 66=enter, 67=delete)."""
        return self._adb(f"input keyevent {keycode}")

    def text(self, text: str):
        """Escribir texto. Escapa caracteres especiales."""
        safe = text.replace(" ", "%s").replace("'", "\\'")
        return self._adb(f"input text '{safe}'")

    def home(self):
        return self.key(3)

    def back(self):
        return self.key(4)

    def recents(self):
        return self.key(187)

    def enter(self):
        return self.key(66)

    # ── Mapping browser coords → device coords ──────────────

    def map_tap(self, browser_x: int, browser_y: int,
                video_w: int, video_h: int) -> Tuple[int, int]:
        """Convierte coordenadas del navegador a coordenadas del dispositivo."""
        s = self.screen
        dx = int(browser_x / video_w * s.width)
        dy = int(browser_y / video_h * s.height)
        return dx, dy

    def map_swipe(self, bx1: int, by1: int, bx2: int, by2: int,
                  video_w: int, video_h: int) -> Tuple[int, int, int, int]:
        dx1, dy1 = self.map_tap(bx1, by1, video_w, video_h)
        dx2, dy2 = self.map_tap(bx2, by2, video_w, video_h)
        return dx1, dy1, dx2, dy2
