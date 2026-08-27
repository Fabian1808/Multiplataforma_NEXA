"""Modelos de datos del Hub — Plugin Descriptor."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class PluginStatus(enum.Enum):
    OFFICIAL = "oficial"
    COMMUNITY = "comunidad"
    BETA = "beta"
    DEPRECATED = "deprecada"


class PluginCategory(enum.Enum):
    AUTOMATION = "Automatización"
    EXCEL = "Excel"
    PDF = "PDF"
    SAP = "SAP"
    REPORTS = "Reportes"
    FILES = "Archivos"
    OUTLOOK = "Outlook"
    KNOWLEDGE = "Conocimiento"
    OTHER = "Otro"


@dataclass
class PluginDescriptor:
    """Metadata completa de un plugin registrado en el Hub."""

    id: str
    name: str
    description: str
    version: str
    category: PluginCategory
    tags: list[str] = field(default_factory=list)
    owner: str = "NEXA"
    backup_owner: str = ""
    area: str = ""
    status: PluginStatus = PluginStatus.OFFICIAL
    entrypoint: str = ""
    icon: str = ""
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    documentation_url: str = ""
    health_status: str = "operational"
    execution_count: int = 0
    user_count: int = 0
    avg_rating: float = 0.0
    estimated_hours_saved: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    changelog: list[dict[str, Any]] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)

    def matches_query(self, query: str) -> float:
        """Puntuación de relevancia para búsqueda. 0.0 = sin match, 1.0 = match perfecto."""
        q = query.lower().strip()
        if not q:
            return 0.0

        score = 0.0

        if q == self.name.lower():
            return 1.0

        if q in self.name.lower():
            score = max(score, 0.9)

        if q in self.description.lower():
            score = max(score, 0.7)

        for tag in self.tags:
            if q in tag.lower():
                score = max(score, 0.8)

        for syn in self.synonyms:
            if q in syn.lower():
                score = max(score, 0.75)

        if q in self.category.value.lower():
            score = max(score, 0.5)

        words = q.split()
        name_lower = self.name.lower()
        desc_lower = self.description.lower()
        tag_text = " ".join(self.tags).lower()
        all_text = f"{name_lower} {desc_lower} {tag_text}"
        matched_words = sum(1 for w in words if w in all_text)
        if matched_words > 0:
            word_score = 0.3 + 0.4 * (matched_words / len(words))
            score = max(score, word_score)

        return score

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category.value,
            "tags": self.tags,
            "owner": self.owner,
            "backup_owner": self.backup_owner,
            "area": self.area,
            "status": self.status.value,
            "entrypoint": self.entrypoint,
            "icon": self.icon,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "documentation_url": self.documentation_url,
            "health_status": self.health_status,
            "execution_count": self.execution_count,
            "user_count": self.user_count,
            "avg_rating": self.avg_rating,
            "estimated_hours_saved": self.estimated_hours_saved,
            "last_updated": self.last_updated.isoformat(),
            "created_at": self.created_at.isoformat(),
            "changelog": self.changelog,
            "synonyms": self.synonyms,
        }
