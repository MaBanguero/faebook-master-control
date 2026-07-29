"""
ConnectivityChecker — Verifica conectividad sin necesidad de root.
Tres niveles: ping, WiFi info, HTTP real.
"""

import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConnectivityResult:
    adb_id: str
    online: bool = False
    latency_ms: float = 0.0
    ssid: str = ""
    link_speed: str = ""
    rssi: int = 0
    frequency: str = ""
    internet: bool = False
    error: str = ""
    timestamp: float = field(default_factory=time.time)


class ConnectivityChecker:
    """Verifica conectividad de un dispositivo Android via ADB."""

    @staticmethod
    def _adb(serial: str, cmd: str, timeout: float = 8) -> str:
        try:
            r = subprocess.run(
                ["adb", "-s", serial, "shell", cmd],
                capture_output=True, text=True, timeout=timeout
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except (subprocess.TimeoutExpired, Exception):
            return ""

    # ── Nivel 1: Ping ─────────────────────────────────────────

    @staticmethod
    def check_ping(serial: str) -> tuple[bool, float]:
        """Retorna (online, latency_ms)."""
        out = ConnectivityChecker._adb(serial, "ping -c 2 -W 4 8.8.8.8", timeout=10)
        if not out:
            return False, 0.0
        # Parsear avg rtt
        m = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", out)
        if m:
            return True, float(m.group(1))
        # Fallback: si hay "2 received"
        if "2 received" in out or "1 received" in out:
            return True, 0.0
        return False, 0.0

    # ── Nivel 2: WiFi info ────────────────────────────────────

    @staticmethod
    def check_wifi(serial: str) -> dict:
        """Extrae SSID, link speed, RSSI, frequency de dumpsys wifi."""
        out = ConnectivityChecker._adb(serial, "dumpsys wifi | grep -E 'mWifiInfo|SSID|Link speed|RSSI|Frequency' | head -5", timeout=5)
        result = {"ssid": "", "link_speed": "", "rssi": 0, "frequency": ""}
        if not out:
            return result
        # SSID
        m = re.search(r"SSID:\s*([^,]+)", out)
        if m:
            result["ssid"] = m.group(1).strip()
        # Link speed
        m = re.search(r"Link speed:\s*(\d+)\s*Mbps", out)
        if m:
            result["link_speed"] = f"{m.group(1)} Mbps"
        # RSSI
        m = re.search(r"RSSI:\s*(-?\d+)", out)
        if m:
            result["rssi"] = int(m.group(1))
        # Frequency
        m = re.search(r"Frequency:\s*(\d+)\s*MHz", out)
        if m:
            freq_mhz = int(m.group(1))
            result["frequency"] = f"{freq_mhz/1000:.1f} GHz" if freq_mhz > 1000 else f"{freq_mhz} MHz"
        return result

    # ── Nivel 3: HTTP (internet real) ─────────────────────────

    @staticmethod
    def check_internet(serial: str) -> bool:
        """
        Verifica conectividad real a internet usando dumpsys connectivity.
        Android valida la conexión automáticamente — si aparece 'VALIDATED',
        el dispositivo tiene acceso a internet.
        """
        out = ConnectivityChecker._adb(
            serial,
            "dumpsys connectivity | grep -E 'VALIDATED|INTERNET.*VALIDATED' | head -1",
            timeout=5
        )
        return "VALIDATED" in out

    # ── Full check ────────────────────────────────────────────

    @staticmethod
    def check(serial: str, fast: bool = False) -> ConnectivityResult:
        """
        Verificación completa del dispositivo.
        fast=True → solo ping (más rápido, para escaneo masivo).
        """
        result = ConnectivityResult(adb_id=serial)

        # Ping siempre
        online, latency = ConnectivityChecker.check_ping(serial)
        result.online = online
        result.latency_ms = latency

        if not online:
            result.error = "Sin respuesta al ping"
            return result

        if fast:
            result.internet = True
            return result

        # WiFi info
        wifi = ConnectivityChecker.check_wifi(serial)
        result.ssid = wifi["ssid"]
        result.link_speed = wifi["link_speed"]
        result.rssi = wifi["rssi"]
        result.frequency = wifi["frequency"]

        # Internet real
        result.internet = ConnectivityChecker.check_internet(serial)
        if not result.internet:
            result.error = "Sin acceso a internet (HTTP 204 falló)"

        return result
