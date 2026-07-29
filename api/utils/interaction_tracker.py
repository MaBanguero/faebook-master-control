"""
InteractionTracker — Registro persistente de interacciones por cuenta.

Estructura en data/interactions.json:
{
    "<adb_id>": {
        "<nombre_cuenta>": {
            "<hash_link>": {"action": "like", "timestamp": "2026-07-28T22:00:00"}
        }
    }
}

Thread-safe. Sobrevive reinicios del servidor.
"""

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set


class InteractionTracker:
    """Singleton que persiste qué cuentas ya interactuaron con qué links."""

    _instance: Optional["InteractionTracker"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._data: Dict[str, Dict[str, Dict[str, dict]]] = {}
        self._rw_lock = threading.Lock()
        self._file_path = Path(__file__).parent.parent.parent / "data" / "interactions.json"
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    # ── Public API ────────────────────────────────────────────────

    @staticmethod
    def _hash_link(link: str) -> str:
        """Hash corto del link para clave de diccionario."""
        return hashlib.md5(link.encode()).hexdigest()[:12]

    def get_available_accounts(
        self, adb_id: str, link: str, action: str
    ) -> List[str]:
        """
        Devuelve los nombres de cuentas que AÚN NO han ejecutado `action` en `link`.

        Si no se conocen las cuentas del dispositivo, retorna lista vacía.
        Usar junto con automator.obtener_cuentas() para conocer el universo total.
        """
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            available = []
            for account_name in device_data:
                account_links = device_data[account_name]
                if link_hash not in account_links:
                    available.append(account_name)
            return available

    def get_interacted_accounts(
        self, adb_id: str, link: str, action: str
    ) -> Set[str]:
        """Devuelve nombres de cuentas que YA interactuaron."""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            return {
                name
                for name, links in device_data.items()
                if link_hash in links and links[link_hash].get("action") == action
            }

    def is_interacted(
        self, adb_id: str, account_name: str, link: str, action: str
    ) -> bool:
        """¿Esta cuenta ya ejecutó esta acción en este link?"""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            account_data = device_data.get(account_name, {})
            return link_hash in account_data

    def record(
        self, adb_id: str, account_name: str, link: str, action: str
    ):
        """Registra que la cuenta ejecutó la acción en el link."""
        link_hash = self._hash_link(link)
        now = datetime.now(timezone.utc).isoformat()
        with self._rw_lock:
            device_data = self._data.setdefault(adb_id, {})
            account_data = device_data.setdefault(account_name, {})
            account_data[link_hash] = {
                "action": action,
                "timestamp": now,
            }
            self._save()

    def record_batch(
        self, adb_id: str, account_names: List[str], link: str, action: str
    ):
        """Registra múltiples cuentas de una vez (una sola escritura a disco)."""
        link_hash = self._hash_link(link)
        now = datetime.now(timezone.utc).isoformat()
        with self._rw_lock:
            device_data = self._data.setdefault(adb_id, {})
            for name in account_names:
                account_data = device_data.setdefault(name, {})
                account_data[link_hash] = {
                    "action": action,
                    "timestamp": now,
                }
            self._save()

    def remove(
        self, adb_id: str, account_name: str, link: str
    ):
        """Elimina el registro de interacción (para corrección manual)."""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            account_data = device_data.get(account_name, {})
            account_data.pop(link_hash, None)
            if not account_data:
                device_data.pop(account_name, None)
            if not device_data:
                self._data.pop(adb_id, None)
            self._save()

    def get_stats(self, adb_id: str, link: str, action: str) -> dict:
        """Estadísticas: total de cuentas conocidas, interactuadas, disponibles."""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            total = len(device_data)
            interacted = sum(
                1 for links in device_data.values()
                if link_hash in links and links[link_hash].get("action") == action
            )
            return {
                "total_known": total,
                "interacted": interacted,
                "available": total - interacted,
            }

    # ── Persistencia ──────────────────────────────────────────────

    def _load(self):
        try:
            if self._file_path.exists():
                with open(self._file_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self):
        try:
            tmp = str(self._file_path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, str(self._file_path))
        except OSError:
            pass  # no bloquear la operación si falla el guardado


# Singleton
tracker = InteractionTracker()
