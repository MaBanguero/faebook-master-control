from pydantic import BaseModel
from enum import Enum
from typing import Optional

class DispositivoEstado(str, Enum):
    INACTIVO = "inactivo"
    EN_TAREA = "en_tarea"
    TRABAJANDO = "trabajando"
    ERROR = "error"

class Dispositivo(BaseModel):
    id: str
    nombre: str
    estado: DispositivoEstado
    adb_id: Optional[str] = None
    ultima_actualizacion: Optional[str] = None
    
    class Config:
        use_enum_values = True
