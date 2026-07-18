"""Controlador Instagram — endpoints REST."""
from fastapi import APIRouter, HTTPException
from api.services.instagram_service import instagram_service
from api.services.tareas_service import tareas_service

router = APIRouter()


@router.post("/instagram/flujo-multi-cuenta/ejecutar")
async def ejecutar_flujo_multi_cuenta(request: dict):
    """
    Like + comentario + compartir en Instagram.

    Body:
    {
        "dispositivos_ids": ["98883833445a305730"],
        "link_post": "https://www.instagram.com/reel/...",
        "comentario": "🔥"                   // string → 1 cuenta
        "comentario": ["🔥", "👏", "💪"]      // list → N cuentas
        "comentario": ""                      // vacío → like + compartir
    }
    """
    dispositivos_ids = request.get("dispositivos_ids")
    link = request.get("link_post")
    comentario = request.get("comentario", "")
    cuentas_a_usar = request.get("cuentas_a_usar", 0)

    if not dispositivos_ids or not link:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids o link_post")

    tarea = await tareas_service.crear_tarea(
        tipo="ig_flujo_multi_cuenta",
        dispositivos_ids=dispositivos_ids,
        config={"link": link, "comentario": comentario},
        total_esperado=len(dispositivos_ids),
    )

    instagram_service.ejecutar_flujo_multi_cuenta(
        dispositivos_ids=dispositivos_ids,
        link=link,
        comentario=comentario,
        tarea_id=tarea.id,
        cuentas_a_usar=cuentas_a_usar,
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": "Iniciando flujo Instagram multi-cuenta",
    }


@router.post("/instagram/detener")
async def detener_instagram():
    instagram_service.detener_todos()
    return {"success": True, "message": "Workers Instagram detenidos"}


@router.post("/instagram/calentamiento/ejecutar")
async def ejecutar_calentamiento_instagram(request: dict):
    """
    Ejecuta calentamiento ultra-random de cuentas Instagram.

    Body:
    {
        "dispositivos_ids": ["98883833445a305730"]
    }
    """
    dispositivos_ids = request.get("dispositivos_ids")
    if not dispositivos_ids:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids")

    tarea = await tareas_service.crear_tarea(
        tipo="ig_calentamiento",
        dispositivos_ids=dispositivos_ids,
        config={},
        total_esperado=len(dispositivos_ids),
    )

    instagram_service.ejecutar_calentamiento(
        dispositivos_ids=dispositivos_ids,
        tarea_id=tarea.id,
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": "Calentamiento Instagram iniciado",
    }
