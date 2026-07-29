from fastapi import APIRouter, HTTPException
from typing import List
from api.models.tarea_activa import TareaActiva
from api.services.tareas_service import tareas_service

router = APIRouter()

@router.get("/tareas/activas", response_model=List[TareaActiva])
async def obtener_tareas_activas():
    """
    Obtiene todas las tareas activas (en ejecución)
    
    Returns:
        Lista de tareas activas
    """
    try:
        tareas = await tareas_service.obtener_tareas_activas()
        return tareas
    except Exception as e:
        print(f"❌ Error obteniendo tareas activas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tareas/{tarea_id}", response_model=TareaActiva)
async def obtener_tarea(tarea_id: str):
    """
    Obtiene una tarea específica por su ID
    
    Args:
        tarea_id: ID de la tarea
        
    Returns:
        Tarea encontrada
    """
    try:
        tarea = await tareas_service.obtener_tarea(tarea_id)
        
        if not tarea:
            raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
        
        return tarea
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error obteniendo tarea {tarea_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tareas", response_model=List[TareaActiva])
async def obtener_todas_tareas():
    """
    Obtiene todas las tareas (incluidas completadas y fallidas)
    
    Returns:
        Lista de todas las tareas
    """
    try:
        tareas = await tareas_service.obtener_todas_tareas()
        return tareas
    except Exception as e:
        print(f"❌ Error obteniendo todas las tareas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tareas/{tarea_id}")
async def cancelar_tarea(tarea_id: str):
    """
    Envía la señal de detener a una tarea activa
    
    Args:
        tarea_id: ID de la tarea a cancelar
        
    Returns:
        Mensaje de confirmación
    """
    try:
        tarea = await tareas_service.obtener_tarea(tarea_id)
        
        if not tarea:
            raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
        
        if tarea.estado not in ["iniciando", "ejecutando"]:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede cancelar una tarea en estado '{tarea.estado}'"
            )
        
        dispositivos_notificados = tareas_service.detener_tarea(tarea_id)
        await tareas_service.actualizar_estado(tarea_id, "deteniendo")
        
        return {
            "message": f"Tarea {tarea_id} en proceso de detención ({dispositivos_notificados} dispositivos notificados)",
            "dispositivos_notificados": dispositivos_notificados
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error cancelando tarea {tarea_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tareas/detener-todas")
async def detener_todas_tareas():
    """Detiene todas las tareas activas de todas las plataformas."""
    try:
        detenidas = tareas_service.detener_todas()
        return {
            "message": f"{detenidas} tareas detenidas",
            "detenidas": detenidas,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
