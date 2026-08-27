"""Modelos — Search opportunities (búsquedas sin resultado)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SearchOpportunity:
    id: int = 0
    query: str = ""
    results_count: int = 0
    user_id: str = ""
    searched_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
