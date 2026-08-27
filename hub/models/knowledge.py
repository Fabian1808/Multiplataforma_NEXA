"""Modelos — Knowledge Base articles."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KnowledgeArticle:
    id: int = 0
    title: str = ""
    content: str = ""
    category: str = ""
    author: str = ""
    plugin_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    tags: list[str] = field(default_factory=list)
    helpful_count: int = 0
