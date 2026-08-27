"""Modelos de datos — Auditoría, Comentarios, Etiquetas."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class AuditAction(enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    EXPORT = "export"
    APPROVE = "approve"
    REJECT = "reject"
    ASSIGN = "assign"
    EXECUTE = "execute"
    SEARCH = "search"
    RATE = "rate"
    FAVORITE = "favorite"
    UNFAVORITE = "unfavorite"
    PUBLISH = "publish"
    ARCHIVE = "archive"


@dataclass
class AuditEntry:
    id: int = 0
    user_id: str = ""
    action: str = ""
    module: str = ""
    entity_type: str = ""
    entity_id: str = ""
    entity_name: str = ""
    details: str = ""
    ip_address: str = ""
    created_at: str = ""

    @property
    def action_label(self) -> str:
        labels = {
            "create": "Creó", "update": "Actualizó", "delete": "Eliminó",
            "login": "Inició sesión", "logout": "Cerró sesión",
            "view": "Consultó", "export": "Exportó",
            "approve": "Aprobó", "reject": "Rechazó",
            "assign": "Asignó", "execute": "Ejecutó",
            "search": "Buscó", "rate": "Calificó",
            "favorite": "Agregó a favoritos", "unfavorite": "Removió de favoritos",
            "publish": "Publicó", "archive": "Archivó",
        }
        return labels.get(self.action, self.action)


@dataclass
class Comment:
    id: int = 0
    entity_type: str = ""
    entity_id: str = ""
    user_id: str = ""
    content: str = ""
    parent_id: int = 0
    is_deleted: bool = False
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""
    author_name: str = ""


@dataclass
class Tag:
    id: int = 0
    name: str = ""
    color: str = "#FF5503"
    usage_count: int = 0
    created_at: str = ""


@dataclass
class Attachment:
    id: int = 0
    entity_type: str = ""
    entity_id: str = ""
    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    mime_type: str = ""
    uploaded_by: str = ""
    created_at: str = ""
