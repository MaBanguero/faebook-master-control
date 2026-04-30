from pydantic import BaseModel
from typing import List, Literal

class LikesRequest(BaseModel):
    dispositivos_ids: List[str]
    tipo: Literal['positivo', 'negativo'] = 'positivo'  # Like o Dislike
    link_video: str
    link_videos: List[str] = []
    plataforma: Literal['youtube', 'tiktok']
    cantidad_likes: int = 1
    delay_entre_dispositivos: int = 10
    intentos_maximos: int = 5
    tiempo_espera_entre_ciclos: int = 30
    tiempo_reintento_caducado: int = 5
    tiempo_limite_ciclo: int = 300

class LikesResponse(BaseModel):
    success: bool
    message: str
    dispositivos_activados: List[str]
    tarea_id: str = None
