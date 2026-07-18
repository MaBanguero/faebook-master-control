"""
Controlador de IA — generación de comentarios vía DeepSeek.
"""
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.ai_comments_service import DeepSeekClient, AICommentOptions

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerarComentariosRequest(BaseModel):
    tema: str = Field(..., min_length=5, description="Tema o contexto del post")
    cantidad: int = Field(default=5, ge=1, le=30, description="Número de comentarios a generar")
    tono: str = Field(default="conversacional", description="Tono: conversacional, divertido, serio, motivacional")
    idioma: str = Field(default="es", description="Idioma: es, en, pt")


class GenerarComentariosResponse(BaseModel):
    success: bool
    comentarios: list[str]
    tema: str


@router.post("/comentarios/generar", response_model=GenerarComentariosResponse)
async def generar_comentarios(request: GenerarComentariosRequest):
    """
    Genera N comentarios usando DeepSeek AI basados en un tema.
    Los comentarios son variados, naturales y listos para usar en redes sociales.
    """
    client = DeepSeekClient()
    if not client.is_configured:
        raise HTTPException(status_code=500, detail="DeepSeek API key no configurada")

    options = AICommentOptions(
        temperature=0.8,
        max_tokens=min(request.cantidad * 100, 2000),
        language=request.idioma,
        tone=request.tono,
        max_length=200,
    )

    system_prompt = (
        "Eres un community manager experto. Genera comentarios breves, naturales y variados "
        "para redes sociales. Cada comentario debe ser auténtico, usar un tono humano, "
        "incluir emojis cuando sea apropiado, y NUNCA sonar como un bot. "
        "Varía la longitud (algunos cortos, otros más elaborados), "
        "el enfoque (pregunta, opinión, reacción, pregunta, anécdota corta) "
        "y el estilo. No uses hashtags. Responde EXCLUSIVAMENTE con un JSON válido."
    )

    user_prompt = (
        f"Genera exactamente {request.cantidad} comentarios para un post de redes sociales "
        f"sobre el siguiente tema: \"{request.tema}\".\n"
        f"Idioma: {request.idioma}. Tono: {request.tono}.\n"
        f"Cada comentario debe ser distinto, original y no mayor a 180 caracteres.\n"
        f"Devuelve EXCLUSIVAMENTE un JSON así: "
        f'{{"comentarios": ["comentario 1", "comentario 2", ...]}}'
    )

    payload = {
        "model": options.model,
        "temperature": options.temperature,
        "max_tokens": options.max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        response = client.generate(payload)
        choice = (response.get("choices") or [{}])[0]
        content = choice.get("message", {}).get("content", "")

        if not content:
            raise HTTPException(status_code=500, detail="DeepSeek no devolvió contenido")

        # Parsear JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Intentar extraer JSON de texto
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(content[start:end + 1])
            else:
                raise HTTPException(status_code=500, detail="No se pudo parsear la respuesta")

        comentarios = data.get("comentarios", [])
        if not comentarios:
            raise HTTPException(status_code=500, detail="DeepSeek no generó comentarios")

        # Limpiar y limitar
        comentarios = [c.strip() for c in comentarios if c.strip()][:request.cantidad]

        return GenerarComentariosResponse(
            success=True,
            comentarios=comentarios,
            tema=request.tema,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generando comentarios: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al generar comentarios: {str(e)}")
