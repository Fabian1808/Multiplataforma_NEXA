"""Modelos de datos — Ejecuciones y valoraciones."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AppExecution:
    id: str
    plugin_id: str
    user_id: str
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    success: bool = True
    duration_seconds: float = 0.0
    error_message: str = ""


@dataclass
class AppRating:
    plugin_id: str
    user_id: str
    helpful: bool = True
    time_saved_minutes: int = 0
    comment: str = ""
    created_at: datetime = field(default_factory=datetime.now)
