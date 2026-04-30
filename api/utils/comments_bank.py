from __future__ import annotations

import random
from typing import List

COMMENTS_BANK: List[str] = [
    "Brutal este live!",
    "Saludos desde MX!",
    "Vamos con todo equipo!",
]


def get_random_comment(fallback: str = "Gran live!") -> str:
    """Devuelve un comentario aleatorio del banco o el fallback si está vacío."""
    if not COMMENTS_BANK:
        return fallback
    return random.choice(COMMENTS_BANK)
