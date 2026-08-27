"""Modelos de datos — Uso reciente."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RecentUsage:
    user_id: str
    plugin_id: str
    used_at: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
