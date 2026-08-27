"""Modelos de datos — Publicaciones, Likes y Comunidad."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class PostVisibility(enum.Enum):
    PUBLICO = "publico"
    AREA = "area"
    PRIVADO = "privado"


class PostType(enum.Enum):
    GENERAL = "general"
    LOGRO = "logro"
    NOTICIA = "noticia"
    SOLICITUD = "solicitud"
    PREGUNTA = "pregunta"
    TUTORIAL = "tutorial"


@dataclass
class Post:
    id: int = 0
    user_id: str = ""
    title: str = ""
    content: str = ""
    visibility: str = "publico"
    post_type: str = "general"
    tags: str = ""
    likes_count: int = 0
    comments_count: int = 0
    is_pinned: bool = False
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""
    author_name: str = ""
    author_area: str = ""
    is_liked: bool = False

    @property
    def type_label(self) -> str:
        labels = {
            "general": "General", "logro": "Logro", "noticia": "Noticia",
            "solicitud": "Solicitud", "pregunta": "Pregunta", "tutorial": "Tutorial",
        }
        return labels.get(self.post_type, self.post_type)

    @property
    def visibility_label(self) -> str:
        labels = {"publico": "Público", "area": "Mi Área", "privado": "Privado"}
        return labels.get(self.visibility, self.visibility)


@dataclass
class PostLike:
    post_id: int = 0
    user_id: str = ""
    created_at: str = ""
