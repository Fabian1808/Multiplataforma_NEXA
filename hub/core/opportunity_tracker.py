"""Core — Opportunity Tracker."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class OpportunityTracker:
    def __init__(self, db: Database) -> None:
        self._db = db

    def record_search(self, query: str, results_count: int, user_id: str = "default") -> None:
        now = datetime.now().isoformat()
        self._db.execute(
            "INSERT INTO search_opportunities (query, results_count, user_id, searched_at, acknowledged) VALUES (?, ?, ?, ?, 0)",
            (query, results_count, user_id, now),
        )
        self._db.commit()

    def get_opportunities(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM search_opportunities WHERE acknowledged = 0 ORDER BY searched_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def acknowledge(self, opp_id: int) -> None:
        self._db.execute("UPDATE search_opportunities SET acknowledged = 1 WHERE id = ?", (opp_id,))
        self._db.commit()

    def get_stats(self) -> dict[str, Any]:
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM search_opportunities")
        pending = self._db.fetchone("SELECT COUNT(*) as cnt FROM search_opportunities WHERE acknowledged = 0")
        return {"total": total["cnt"] if total else 0, "pending": pending["cnt"] if pending else 0}
