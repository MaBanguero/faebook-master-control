from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, replace
from itertools import cycle
from typing import Dict, List, Sequence

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AICommentOptions:
    """
    Opciones base para la generacion de comentarios.
    Las lecturas desde variables de entorno permiten ajustar sin tocar el codigo.
    """

    model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    temperature: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.65"))
    max_tokens: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "800"))
    batch_size: int = int(os.getenv("DEEPSEEK_BATCH_SIZE", "8"))
    language: str = os.getenv("DEEPSEEK_LANGUAGE", "es")
    tone: str = os.getenv("DEEPSEEK_TONE", "conversacional")
    max_length: int = int(os.getenv("DEEPSEEK_COMMENT_MAX_LENGTH", "180"))


class DeepSeekClient:
    """
    Cliente HTTP minimalista para DeepSeek.
    Se mantiene independiente del resto de la app para facilitar pruebas.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url or os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com")
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, payload: dict) -> dict:
        if not self.is_configured:
            raise RuntimeError("DeepSeek API key is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(base_url=self.base_url, timeout=self.timeout, headers=headers) as client:
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()


class PromptBuilder:
    """
    Responsable de generar el prompt y parsear la respuesta JSON del modelo.
    """

    def __init__(self) -> None:
        self.system_prompt = (
            "You are a senior community manager. "
            "Write short, authentic and varied social-media comments following the provided context. Use bad ortography and slang when appropriate. "
            "Deliver only valid JSON with the shape "
            '{"comments":[{"device_id":"<id>","comments":["text1","text2"]}]} and nothing else.'
        )

    def build_payload(self, context: str, batch: List[dict], options: AICommentOptions) -> dict:
        clean_context = context.strip()
        if not clean_context:
            raise ValueError("El contexto no puede estar vacio")

        instructions = (
            "Genera comentarios naturales y distintos para cada dispositivo listado. "
            f"Idioma objetivo: {options.language}. Tono: {options.tone}. "
            f"Longitud maxima por comentario: {options.max_length} caracteres. "
            "No menciones que eres un asistente ni agregues explicaciones externas."
        )
        
        user_content = {
            "instructions": instructions,
            "context": clean_context,
            "devices": batch,
        }
        
        return {
            "model": options.model,
            "temperature": options.temperature,
            "max_tokens": options.max_tokens,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        }

    def parse_response(self, response: dict) -> List[dict]:
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content", "")
        if not content:
            return []

        data = self._extract_json(content)
        entries = data.get("comments") or data.get("items") or []
        parsed: List[dict] = []
        for entry in entries:
            device_id = entry.get("device_id") or entry.get("device") or entry.get("id")
            comments = entry.get("comments") or entry.get("responses") or []
            if not device_id or not isinstance(comments, list):
                continue
            normalized = [c.strip() for c in comments if isinstance(c, str) and c.strip()]
            if normalized:
                parsed.append({"device_id": device_id, "comments": normalized})
        return parsed

    def _extract_json(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning("No se pudo parsear la respuesta de DeepSeek: %s", content)
            return {"comments": []}


class AICommentsService:
    """
    Servicio independiente para orquestar la generacion de comentarios via DeepSeek.
    Puede reaprovecharse en cualquier controlador/plataforma.
    """

    def __init__(
        self,
        client: DeepSeekClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        default_options: AICommentOptions | None = None,
    ) -> None:
        self.client = client or DeepSeekClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.options = default_options or AICommentOptions()

    def generate_for_devices(
        self,
        dispositivos_ids: Sequence[str],
        contexto: str,
        comentarios_por_dispositivo: int,
        comentarios_personalizados: Sequence[str] | None = None,
        options: AICommentOptions | None = None,
    ) -> Dict[str, List[str]]:
        plan: Dict[str, List[str]] = {device_id: [] for device_id in dispositivos_ids}

        if comentarios_por_dispositivo <= 0 or not dispositivos_ids:
            return plan

        contexto_limpio = contexto.strip()
        if not contexto_limpio:
            raise ValueError("El contexto de comentarios no puede estar vacio")

        sanitized_manual = [
            comentario.strip()
            for comentario in (comentarios_personalizados or [])
            if isinstance(comentario, str) and comentario.strip()
        ]
        if sanitized_manual:
            manual_iter = cycle(sanitized_manual)
            for device_id in plan:
                while len(plan[device_id]) < min(comentarios_por_dispositivo, len(sanitized_manual)):
                    plan[device_id].append(next(manual_iter))

        pendientes = [device_id for device_id in dispositivos_ids if len(plan[device_id]) < comentarios_por_dispositivo]
        if not pendientes:
            return plan

        effective_options = options or self.options

        if not self.client.is_configured:
            logger.warning("DeepSeek API key missing, using plantilla local para comentarios.")
            self._fill_with_template(plan, pendientes, comentarios_por_dispositivo, contexto_limpio)
            return plan

        for batch in self._chunk_devices(pendientes, max(1, effective_options.batch_size)):
            batch_requirements = [
                {
                    "device_id": device_id,
                    "comments_needed": comentarios_por_dispositivo - len(plan[device_id]),
                }
                for device_id in batch
            ]
            payload = self.prompt_builder.build_payload(contexto_limpio, batch_requirements, effective_options)

            try:
                response = self.client.generate(payload)
                entries = self.prompt_builder.parse_response(response)
            except Exception as exc:  # noqa: BLE001
                logger.error("Fallo al solicitar comentarios en DeepSeek: %s", exc)
                self._fill_with_template(plan, batch, comentarios_por_dispositivo, contexto_limpio)
                continue

            if not entries:
                self._fill_with_template(plan, batch, comentarios_por_dispositivo, contexto_limpio)
                continue

            for entry in entries:
                device_id = entry.get("device_id")
                if not device_id or device_id not in plan:
                    continue
                for comment in entry.get("comments", []):
                    if len(plan[device_id]) >= comentarios_por_dispositivo:
                        break
                    plan[device_id].append(comment)

            incompletos = [dev for dev in batch if len(plan[dev]) < comentarios_por_dispositivo]
            if incompletos:
                self._fill_with_template(plan, incompletos, comentarios_por_dispositivo, contexto_limpio)

        return plan

    def override_options(self, overrides: dict | None) -> AICommentOptions:
        if not overrides:
            return self.options

        allowed_fields = {"model", "temperature", "max_tokens", "batch_size", "language", "tone", "max_length"}
        cleaned = {key: value for key, value in overrides.items() if key in allowed_fields and value is not None}
        if not cleaned:
            return self.options

        return replace(self.options, **cleaned)

    def _chunk_devices(self, dispositivos: Sequence[str], batch_size: int) -> List[List[str]]:
        size = max(1, batch_size)
        return [list(dispositivos[i : i + size]) for i in range(0, len(dispositivos), size)]

    def _fill_with_template(
        self,
        plan: Dict[str, List[str]],
        dispositivos: Sequence[str],
        comentarios_por_dispositivo: int,
        contexto: str,
    ) -> None:
        for device_id in dispositivos:
            restantes = comentarios_por_dispositivo - len(plan[device_id])
            for offset in range(restantes):
                plan[device_id].append(self._template_comment(contexto, offset))

    def _template_comment(self, contexto: str, offset: int) -> str:
        snippet = contexto.strip()[:80]
        suffix = (offset % 5) + 1
        return f"{snippet} #{suffix}"
