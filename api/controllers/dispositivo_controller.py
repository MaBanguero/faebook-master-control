from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from api.models import Dispositivo
from api.services.dispositivo_service import DispositivoService

# Modelos para requests
class ComandoADBRequest(BaseModel):
    comando: str

class ComandoADBResponse(BaseModel):
    success: bool
    stdout: str
    stderr: str
    dispositivo: str

router = APIRouter()
dispositivo_service = DispositivoService()

@router.get("/dispositivos", response_model=List[Dispositivo])
async def get_dispositivos():
    """
    Obtiene la lista de todos los dispositivos disponibles
    """
    try:
        dispositivos = dispositivo_service.obtener_dispositivos()
        return dispositivos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dispositivos/{dispositivo_id}", response_model=Dispositivo)
async def get_dispositivo(dispositivo_id: str):
    """
    Obtiene información de un dispositivo específico
    """
    try:
        dispositivo = dispositivo_service.obtener_dispositivo(dispositivo_id)
        if not dispositivo:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        return dispositivo
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dispositivos/{dispositivo_id}/comando", response_model=ComandoADBResponse)
async def ejecutar_comando(dispositivo_id: str, request: ComandoADBRequest):
    """
    Ejecuta un comando ADB en un dispositivo específico
    """
    try:
        resultado = dispositivo_service.ejecutar_comando_adb(dispositivo_id, request.comando)
        
        return ComandoADBResponse(
            success=resultado['success'],
            stdout=resultado.get('stdout', ''),
            stderr=resultado.get('stderr', ''),
            dispositivo=resultado.get('dispositivo', 'Unknown')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/adb/status")
async def get_adb_status():
    """
    Verifica el estado de ADB en el sistema
    """
    try:
        from api.utils.adb_utils import ADBManager
        is_available = ADBManager.is_adb_available()
        
        return {
            "adb_available": is_available,
            "message": "ADB está disponible" if is_available else "ADB no está disponible en el sistema"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
