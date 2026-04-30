from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid

class Metricas(BaseModel):
    """Métricas de una tarea activa"""
    total_esperado: int = 0
    exitosos: int = 0
    fallidos: int = 0
    en_proceso: int = 0

class TareaActiva(BaseModel):
    """Modelo de tarea activa en el sistema"""
    id: str
    tipo: str  # "comentarios" | "compartidas" | "likes" | "suscripciones"
    estado: str  # "iniciando" | "ejecutando" | "completada" | "fallida"
    dispositivos_ids: List[str]
    metricas: Metricas
    config: Dict[str, Any]  # Configuración original de la tarea
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    
    @staticmethod
    def crear(tipo: str, dispositivos_ids: List[str], config: Dict[str, Any], total_esperado: int = 0) -> 'TareaActiva':
        """
        Crea una nueva tarea activa
        
        Args:
            tipo: Tipo de tarea ("comentarios", "compartidas", "likes", "suscripciones")
            dispositivos_ids: Lista de IDs de dispositivos
            config: Configuración original de la tarea
            total_esperado: Total de operaciones esperadas
            
        Returns:
            Nueva instancia de TareaActiva
        """
        return TareaActiva(
            id=str(uuid.uuid4()),
            tipo=tipo,
            estado="iniciando",
            dispositivos_ids=dispositivos_ids,
            metricas=Metricas(total_esperado=total_esperado),
            config=config,
            fecha_inicio=datetime.now()
        )
    
    def actualizar_metrica(self, metrica: str, incremento: int = 1):
        """
        Actualiza una métrica específica
        
        Args:
            metrica: Nombre de la métrica ("exitosos", "fallidos", "en_proceso")
            incremento: Valor a incrementar (puede ser negativo)
        """
        if metrica == "exitosos":
            self.metricas.exitosos += incremento
        elif metrica == "fallidos":
            self.metricas.fallidos += incremento
        elif metrica == "en_proceso":
            self.metricas.en_proceso += incremento
    
    def finalizar(self, exito: bool = True):
        """
        Finaliza la tarea
        
        Args:
            exito: Si la tarea se completó exitosamente
        """
        self.estado = "completada" if exito else "fallida"
        self.fecha_fin = datetime.now()
    
    def obtener_progreso(self) -> float:
        """
        Calcula el progreso de la tarea (0-100)
        
        Returns:
            Porcentaje de progreso
        """
        if self.metricas.total_esperado == 0:
            return 0.0
        
        completados = self.metricas.exitosos + self.metricas.fallidos
        return (completados / self.metricas.total_esperado) * 100
