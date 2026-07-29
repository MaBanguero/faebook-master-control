"""
ConnectivityService — Cache de resultados y verificaciones masivas.
"""

import threading
from typing import Dict, Optional
from api.utils.connectivity_checker import ConnectivityChecker, ConnectivityResult


class ConnectivityService:
    """Singleton. Cachea resultados y permite consultas rápidas."""

    _instance: Optional["ConnectivityService"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._cache: Dict[str, ConnectivityResult] = {}
        self._rw_lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────

    def verify_all(self, devices: list[str], fast: bool = False) -> Dict[str, ConnectivityResult]:
        """Verifica TODOS los dispositivos (paralelo con threads)."""
        results: Dict[str, ConnectivityResult] = {}
        threads = []

        def _worker(serial: str):
            r = ConnectivityChecker.check(serial, fast=fast)
            with self._rw_lock:
                self._cache[serial] = r
                results[serial] = r

        for s in devices:
            t = threading.Thread(target=_worker, args=(s,), daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=30)

        return results

    def verify_one(self, serial: str) -> ConnectivityResult:
        """Verifica un solo dispositivo y cachea."""
        r = ConnectivityChecker.check(serial)
        with self._rw_lock:
            self._cache[serial] = r
        return r

    def get_cached(self, serial: str) -> Optional[ConnectivityResult]:
        with self._rw_lock:
            return self._cache.get(serial)

    def get_all_cached(self) -> Dict[str, ConnectivityResult]:
        with self._rw_lock:
            return dict(self._cache)

    def esta_conectado(self, serial: str) -> bool:
        """¿Tiene internet? Usa cache si existe."""
        r = self.get_cached(serial)
        if r:
            return r.internet
        # Verificar al vuelo
        r = ConnectivityChecker.check(serial, fast=True)
        with self._rw_lock:
            self._cache[serial] = r
        return r.internet

    def is_online(self, serial: str) -> bool:
        """¿Responde al ping? (más rápido que internet)."""
        r = self.get_cached(serial)
        if r:
            return r.online
        r = ConnectivityChecker.check(serial, fast=True)
        with self._rw_lock:
            self._cache[serial] = r
        return r.online

    def clear_cache(self):
        with self._rw_lock:
            self._cache.clear()


connectivity_service = ConnectivityService()
