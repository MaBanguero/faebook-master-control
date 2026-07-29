"""
Connectivity Controller — Endpoints REST para verificación de conectividad.
"""

import asyncio
from fastapi import APIRouter

from api.services.connectivity_service import connectivity_service
from api.services.dispositivo_service import dispositivo_service

router = APIRouter()


@router.post("/conectividad/verificar")
async def verificar_conectividad(request: dict = None):
    """
    Verifica conectividad en todos los dispositivos o en los especificados.
    
    Body opcional:
    {
        "dispositivos_ids": ["adb_id1", ...],  // opcional, si no: todos
        "fast": true/false                       // solo ping si true
    }
    """
    req = request or {}
    fast = req.get("fast", False)
    ids = req.get("dispositivos_ids")

    if ids:
        devices = ids
    else:
        # Obtener todos del servicio de dispositivos
        devices = [d.adb_id for d in dispositivo_service.obtener_dispositivos() if d.adb_id]

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None, lambda: connectivity_service.verify_all(devices, fast=fast)
    )

    return {
        "total": len(results),
        "online": sum(1 for r in results.values() if r.online),
        "internet": sum(1 for r in results.values() if r.internet),
        "dispositivos": [
            {
                "adb_id": r.adb_id,
                "online": r.online,
                "latency_ms": round(r.latency_ms, 1),
                "ssid": r.ssid,
                "link_speed": r.link_speed,
                "rssi": r.rssi,
                "frequency": r.frequency,
                "internet": r.internet,
                "error": r.error,
            }
            for r in results.values()
        ]
    }


@router.get("/conectividad/estado")
async def estado_conectividad():
    """Estado cacheado de conectividad de todos los dispositivos."""
    cached = connectivity_service.get_all_cached()
    if not cached:
        return {"cached": False, "online": 0, "internet": 0, "dispositivos": []}

    return {
        "cached": True,
        "online": sum(1 for r in cached.values() if r.online),
        "internet": sum(1 for r in cached.values() if r.internet),
        "dispositivos": [
            {
                "adb_id": r.adb_id,
                "online": r.online,
                "internet": r.internet,
                "ssid": r.ssid,
                "link_speed": r.link_speed,
                "latency_ms": round(r.latency_ms, 1),
            }
            for r in cached.values()
        ]
    }
