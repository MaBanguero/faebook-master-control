from pydantic import BaseModel
from typing import List, Optional, Literal

class ComentariosRequest(BaseModel):
    dispositivos_ids: List[str]
    link_video: str
    plataforma: Literal['youtube', 'tiktok']
    contexto: str
    comentarios_por_dispositivo: int = 1
    comentarios_personalizados: List[str] = []
    ai_config: Optional[dict] = None

class ComentariosResponse(BaseModel):
    success: bool
    message: str
    tarea_id: str = None
    exitosos: int = 0
    fallidos: int = 0
    total_comentarios: int = 0
    detalles: List[dict] = []
