"""
InteractionTracker — Registro persistente de interacciones por cuenta.
Soporta múltiples acciones por link (like, comment, share).

Estructura en data/interactions.json:
{
    "<adb_id>": {
        "<nombre_cuenta>": {
            "<hash_link>": {
                "actions": ["like", "comment", "share"],
                "timestamp": "2026-07-29T22:00:00"
            }
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
        return hashlib.md5(link.encode()).hexdigest()[:12]

    def is_interacted(
        self, adb_id: str, account_name: str, link: str, action: str
    ) -> bool:
        """¿Esta cuenta ya ejecutó esta acción específica en este link?"""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            account_data = device_data.get(account_name, {})
            entry = account_data.get(link_hash)
            if entry is None:
                return False
            return action in entry.get("actions", [])

    def has_all_actions(
        self, adb_id: str, account_name: str, link: str
    ) -> bool:
        """¿Esta cuenta ya completó like + share en este link?"""
        return (
            self.is_interacted(adb_id, account_name, link, "like")
            and self.is_interacted(adb_id, account_name, link, "share")
        )

    def get_available_accounts(
        self, adb_id: str, link: str, action: str = "like"
    ) -> List[str]:
        """Cuentas que AÚN NO han ejecutado `action` en `link`."""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            return [
                name for name in device_data
                if link_hash not in device_data[name]
                or action not in device_data[name][link_hash].get("actions", [])
            ]

    def get_missing_actions(
        self, adb_id: str, account_name: str, link: str
    ) -> List[str]:
        """Lista de acciones pendientes para esta cuenta en este link."""
        all_actions = ["like", "share"]
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            account_data = device_data.get(account_name, {})
            entry = account_data.get(link_hash) or {"actions": []}
            done = set(entry.get("actions", []))
            return [a for a in all_actions if a not in done]

    def record(
        self, adb_id: str, account_name: str, link: str, action: str
    ):
        """Registra que la cuenta ejecutó `action` en `link` (acumulativo)."""
        link_hash = self._hash_link(link)
        now = datetime.now(timezone.utc).isoformat()
        with self._rw_lock:
            device_data = self._data.setdefault(adb_id, {})
            account_data = device_data.setdefault(account_name, {})
            entry = account_data.setdefault(link_hash, {"actions": [], "timestamp": now})
            if action not in entry["actions"]:
                entry["actions"].append(action)
            entry["timestamp"] = now
            self._save()

    def record_batch(
        self, adb_id: str, account_names: List[str], link: str, action: str
    ):
        """Registra múltiples cuentas con la misma acción."""
        link_hash = self._hash_link(link)
        now = datetime.now(timezone.utc).isoformat()
        with self._rw_lock:
            device_data = self._data.setdefault(adb_id, {})
            for name in account_names:
                account_data = device_data.setdefault(name, {})
                entry = account_data.setdefault(link_hash, {"actions": [], "timestamp": now})
                if action not in entry["actions"]:
                    entry["actions"].append(action)
                entry["timestamp"] = now
            self._save()

    def remove(
        self, adb_id: str, account_name: str, link: str, action: str = None
    ):
        """Elimina un registro. Si action=None, borra todo el link para esa cuenta."""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            account_data = device_data.get(account_name, {})
            if action is None:
                account_data.pop(link_hash, None)
            elif link_hash in account_data:
                entry = account_data[link_hash]
                if action in entry["actions"]:
                    entry["actions"].remove(action)
                if not entry["actions"]:
                    account_data.pop(link_hash, None)
            if not account_data:
                device_data.pop(account_name, None)
            if not device_data:
                self._data.pop(adb_id, None)
            self._save()

    def get_stats(self, adb_id: str, link: str) -> dict:
        """Estadísticas por link."""
        link_hash = self._hash_link(link)
        with self._rw_lock:
            device_data = self._data.get(adb_id, {})
            total = len(device_data)
            with_like = with_share = with_both = 0
            for links in device_data.values():
                entry = links.get(link_hash, {})
                actions = set(entry.get("actions", []))
                if "like" in actions and "share" in actions:
                    with_both += 1
                elif "like" in actions:
                    with_like += 1
                elif "share" in actions:
                    with_share += 1
            return {
                "total_known": total,
                "with_like": with_like,
                "with_share": with_share,
                "with_both": with_both,
                "available": total - with_both,
            }

    # ── Persistencia ──────────────────────────────────────────────

    def _load(self):
        try:
            if self._file_path.exists():
                with open(self._file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Migrar formato viejo → nuevo si es necesario
                self._data = self._migrate(loaded)
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _migrate(self, data: dict) -> dict:
        """Convierte formato viejo {"action": "like"} → {"actions": ["like"]}."""
        for device_id, accounts in data.items():
            for account_name, links in accounts.items():
                for link_hash, entry in links.items():
                    if isinstance(entry, dict) and "action" in entry and "actions" not in entry:
                        entry["actions"] = [entry.pop("action")]
        return data

    def _save(self):
        try:
            tmp = str(self._file_path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, str(self._file_path))
        except OSError:
            pass


# Singleton
tracker = InteractionTracker()
