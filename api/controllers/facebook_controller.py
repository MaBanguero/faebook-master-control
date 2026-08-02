from fastapi import APIRouter, HTTPException
from api.services.facebook_service import facebook_service
from api.services.tareas_service import tareas_service

router = APIRouter()


@router.post("/cuentas/facebook/cambiar")
async def cambiar_cuentas_facebook(request: dict):
    dispositivos_ids = request.get('dispositivos_ids', [])
    if not dispositivos_ids:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids")

    # CORRECCIÓN: Se añade el argumento 'config' que faltaba
    tarea = await tareas_service.crear_tarea(
        tipo="fb_cambio_cuenta",
        dispositivos_ids=dispositivos_ids,
        config={"accion": "rotacion_secuencial"},  # Parámetro ahora presente
        total_esperado=len(dispositivos_ids)
    )

    facebook_service.ejecutar_cambio_cuentas(dispositivos_ids, tarea.id)
    return {"success": True, "tarea_id": tarea.id}


@router.post("/likes/facebook/ejecutar")
async def ejecutar_likes(request: dict):
    dispositivos_ids = request.get('dispositivos_ids', [])
    link = request.get('link_post', '')

    tarea = await tareas_service.crear_tarea(
        tipo="fb_likes",
        dispositivos_ids=dispositivos_ids,
        config={"link": link},
        total_esperado=len(dispositivos_ids)
    )

    facebook_service.ejecutar_likes(dispositivos_ids, link, tarea.id)
    return {"success": True, "tarea_id": tarea.id}


@router.post("/comentarios/facebook/ejecutar")
async def ejecutar_comentarios(request: dict):
    # Recibimos los datos
    dispositivos_ids = request.get('dispositivos_ids', [])
    link = request.get('link_post', '')
    textos = request.get('comentario', []) # Clave del frontend

    # Limpiamos comentarios vacíos para no contar líneas en blanco como comentarios válidos
    comentarios_validos = [t for t in textos if t.strip()]

    # El 'zip' es la clave: si dispositivos_ids tiene 2 y comentarios_validos tiene 1,
    # la lista resultante tendrá solo 1 elemento.
    emparejamientos = list(zip(dispositivos_ids, comentarios_validos))

    if not emparejamientos:
        return {"success": False, "detail": "Faltan dispositivos o comentarios para iniciar."}

    # Extraemos las listas finales (ahora tienen el mismo tamaño exacto)
    d_finales = [p[0] for p in emparejamientos]
    c_finales = [p[1] for p in emparejamientos]

    # La tarea se crea solo con los que realmente van a ejecutar
    tarea = await tareas_service.crear_tarea(
        tipo="fb_comentarios",
        dispositivos_ids=d_finales,
        config={"link": link, "comentarios": c_finales},
        total_esperado=len(d_finales)
    )

    # Enviamos al service
    facebook_service.ejecutar_comentarios(d_finales, link, c_finales, tarea.id)

    return {
        "success": True,
        "tarea_id": tarea.id,
        "ejecuciones_reales": len(d_finales)
    }

@router.post("/compartir/facebook/ejecutar")
async def ejecutar_compartir(request: dict):
    dispositivos_ids = request.get('dispositivos_ids', [])
    link = request.get('link_post', '')

    if not dispositivos_ids or not link:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids o link_post")

    tarea = await tareas_service.crear_tarea(
        tipo="fb_compartir",
        dispositivos_ids=dispositivos_ids,
        config={"link": link},
        total_esperado=len(dispositivos_ids)
    )

    facebook_service.ejecutar_compartir(dispositivos_ids, link, tarea.id)
    return {"success": True, "tarea_id": tarea.id}


@router.post("/facebook/flujo-completo/ejecutar")
async def ejecutar_flujo_completo(request: dict):
    dispositivos_ids = request.get('dispositivos_ids', [])
    link = request.get('link_post', '')
    comentario = request.get('comentario', '') # Un solo comentario o el principal

    if not dispositivos_ids or not link:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids o link_post")

    # 1. Creamos la tarea en la base de datos para seguimiento
    tarea = await tareas_service.crear_tarea(
        tipo="fb_flujo_completo",
        dispositivos_ids=dispositivos_ids,
        config={
            "link": link,
            "comentario": comentario,
            "acciones": ["like", "comentario", "compartir"]
        },
        total_esperado=len(dispositivos_ids)
    )

    # 2. Llamamos al servicio para iniciar la ejecución en segundo plano
    # Asegúrate de que facebook_service tenga implementado este método
    facebook_service.ejecutar_flujo_completo(
        dispositivos_ids=dispositivos_ids,
        link=link,
        comentario=comentario,
        tarea_id=tarea.id
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": "Iniciando secuencia: Like -> Comentario -> Compartir"
    }


@router.post("/facebook/flujo-multi-cuenta/ejecutar")
async def ejecutar_flujo_multi_cuenta(request: dict):
    """
    Ejecuta el flujo completo (like + comentario + compartir) en múltiples cuentas.

    Parámetros:
        - dispositivos_ids: lista de IDs de dispositivos
        - link_post: URL del reel/post
        - comentario: texto del comentario
        - cuentas_a_usar: (opcional) número de cuentas a usar.
          0 = modo secuencial (1 cuenta, avanza con cada llamada)
          N > 0 = selecciona N cuentas al azar. Si N > disponibles, usa todas.
    """
    dispositivos_ids = request.get('dispositivos_ids', [])
    link = request.get('link_post', '')
    comentario = request.get('comentario', '')
    cuentas_a_usar = request.get('cuentas_a_usar', 0)

    if not dispositivos_ids or not link:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids o link_post")

    tarea = await tareas_service.crear_tarea(
        tipo="fb_flujo_multi_cuenta",
        dispositivos_ids=dispositivos_ids,
        config={
            "link": link,
            "comentario": comentario,
            "cuentas_a_usar": cuentas_a_usar,
            "acciones": ["like", "comentario", "compartir"]
        },
        total_esperado=len(dispositivos_ids)
    )

    facebook_service.ejecutar_flujo_multi_cuenta(
        dispositivos_ids=dispositivos_ids,
        link=link,
        comentario=comentario,
        tarea_id=tarea.id,
        cuentas_a_usar=cuentas_a_usar
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": f"Iniciando flujo multi-cuenta (cuentas_a_usar={cuentas_a_usar})"
    }


@router.post("/facebook/calentamiento/ejecutar")
async def ejecutar_calentamiento_facebook(request: dict):
    """
    Ejecuta calentamiento ultra-random de cuentas Facebook.

    Body:
    {
        "dispositivos_ids": ["98883833445a305730"]
    }
    """
    dispositivos_ids = request.get("dispositivos_ids")
    if not dispositivos_ids:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids")

    tarea = await tareas_service.crear_tarea(
        tipo="fb_calentamiento",
        dispositivos_ids=dispositivos_ids,
        config={},
        total_esperado=len(dispositivos_ids),
    )

    facebook_service.ejecutar_calentamiento(
        dispositivos_ids=dispositivos_ids,
        tarea_id=tarea.id,
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": "Calentamiento Facebook iniciado",
    }


@router.post("/facebook/retencion/ejecutar")
async def ejecutar_retencion_reels(request: dict):
    """
    Ejecuta retención de Reels en múltiples dispositivos.

    Body:
    {
        "dispositivos_ids": ["98883833..."],
        "duracion_sesion_min": 8,
        "descanso_entre_cuentas_min": 20
    }
    """
    from api.services.retencion_reels_service import retencion_service

    dispositivos_ids = request.get("dispositivos_ids", [])
    duracion_sesion_min = request.get("duracion_sesion_min", 8)
    descanso_entre_cuentas_min = request.get("descanso_entre_cuentas_min", 20)

    if not dispositivos_ids:
        raise HTTPException(status_code=400, detail="Faltan dispositivos_ids")

    tarea = await tareas_service.crear_tarea(
        tipo="fb_retencion_reels",
        dispositivos_ids=dispositivos_ids,
        config={
            "duracion_sesion_min": duracion_sesion_min,
            "descanso_entre_cuentas_min": descanso_entre_cuentas_min,
        },
        total_esperado=len(dispositivos_ids),
    )

    retencion_service.ejecutar(
        dispositivos_ids=dispositivos_ids,
        tarea_id=tarea.id,
        duracion_sesion_min=duracion_sesion_min,
        descanso_entre_cuentas_min=descanso_entre_cuentas_min,
    )

    return {
        "success": True,
        "tarea_id": tarea.id,
        "message": f"Retención Reels iniciada ({len(dispositivos_ids)} dispositivos)",
    }


@router.post("/facebook/retencion/detener")
async def detener_retencion_reels(request: dict = None):
    """
    Detiene todas las tareas de retención de Reels.
    Body opcional: {"dispositivos_ids": [...]} para detener solo algunos.
    """
    from api.services.retencion_reels_service import retencion_service

    req = request or {}
    dispositivos_ids = req.get("dispositivos_ids")

    detenidos = retencion_service.detener(dispositivos_ids)
    return {
        "success": True,
        "detenidos": detenidos,
        "message": f"{detenidos} dispositivos detenidos",
    }