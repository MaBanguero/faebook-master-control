from pydantic import BaseModel
from typing import List, Optional, Literal

class CompartidaRequest(BaseModel):
    dispositivos_ids: List[str]
    link_video: str
    plataforma: Literal['youtube', 'tiktok']
    cantidad_compartidas: int = 3
    delay_entre_compartidas: int = 15
    intentos_maximos: int = 5

class CompartidaResponse(BaseModel):
    success: bool
    total: int
    exitosos: int
    fallidos: int
    detalles: List[dict]
    tarea_id: Optional[str] = None
