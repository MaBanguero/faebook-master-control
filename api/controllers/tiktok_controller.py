"""
Controlador TikTok — endpoints REST para automatización de TikTok.
"""
from fastapi import APIRouter, HTTPException

from api.services.tiktok_service import tiktok_service
from api.services.tareas_service import tareas_service

router = APIRouter()


@router.post("/tiktok/flujo-multi-cuenta/ejecutar")
async def ejecutar_flujo_multi_cuenta(request: dict):
    """
    Ejecuta el flujo completo (like + comentario + compartir) en múltiples cuentas.

    1 comentario = 1 cuenta. Sin repeticiones.
    Si no hay comentarios, hace like + compartir en todas las cuentas.

    Body:
    {
        "dispositivos_ids": ["98883833445a305730"],
        "link_post": "https://www.tiktok.com/@user/video/123",
        "comentario": "🔥"                   // string → 1 cuenta
        "comentario": ["🔥", "👏", "💪"]      // list → N cuentas
        "comentario": ""                      // vacío → like + compartir en todas
    }
    """
    dispositivos_ids = request.get("dispositivos_ids")
    link = request.get("link_post")
    comentario = request.get("comentario", "")
    cuentas_a_usar = request.get("cuentas_a_usar", 0)

    if not dispositivos_ids or not link:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids o link_post")

    tarea = await tareas_service.crear_tarea(
        tipo="tt_flujo_multi_cuenta",
        dispositivos_ids=dispositivos_ids,
        config={
            "link": link,
            "comentario": comentario,
        },
        total_esperado=len(dispositivos_ids),
    )

    tiktok_service.ejecutar_flujo_multi_cuenta(
        dispositivos_ids=dispositivos_ids,
        link=link,
        comentario=comentario,
        tarea_id=tarea.id,
        cuentas_a_usar=cuentas_a_usar,
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": f"Iniciando flujo TikTok multi-cuenta",
    }


@router.post("/tiktok/detener")
async def detener_tiktok():
    """Detiene todos los workers TikTok en ejecución."""
    tiktok_service.detener_todos()
    return {"success": True, "message": "Workers TikTok detenidos"}


@router.post("/tiktok/calentamiento/ejecutar")
async def ejecutar_calentamiento_tiktok(request: dict):
    """
    Ejecuta calentamiento ultra-random de cuentas TikTok.

    Body:
    {
        "dispositivos_ids": ["98883833445a305730"]
    }
    """
    dispositivos_ids = request.get("dispositivos_ids")
    if not dispositivos_ids:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids")

    tarea = await tareas_service.crear_tarea(
        tipo="tt_calentamiento",
        dispositivos_ids=dispositivos_ids,
        config={},
        total_esperado=len(dispositivos_ids),
    )

    tiktok_service.ejecutar_calentamiento(
        dispositivos_ids=dispositivos_ids,
        tarea_id=tarea.id,
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": "Calentamiento TikTok iniciado",
    }
