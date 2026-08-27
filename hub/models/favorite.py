"""Modelos de datos — Favoritos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Favorite:
    user_id: str
    plugin_id: str
    created_at: datetime = field(default_factory=datetime.now)
