"""Core — Request Service. CRUD de solicitudes con workflow."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class RequestService:
    """Servicio de solicitudes (help, issues, automation proposals)."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, user_id: str, request_type: str, title: str = "", description: str = "",
               area: str = "", priority: str = "media", frequency: str = "",
               tools_used: str = "", steps: str = "", created_by: str = "") -> int:
        now = datetime.now().isoformat()
        cursor = self._db.execute(
            """INSERT INTO requests (user_id, request_type, title, description, area, priority, status, workflow_state, frequency, tools_used, steps, created_at, updated_at, created_by, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, 'enviada', 'nueva', ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, request_type, title, description, area, priority, frequency, tools_used, steps, now, now, created_by, created_by),
        )
        self._db.commit()
        return cursor.lastrowid or 0

    def get(self, request_id: int) -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT * FROM requests WHERE id = ?", (request_id,))
        return dict(row) if row else None

    def get_all(self, user_id: str | None = None, status: str | None = None,
                request_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if request_type:
            conditions.append("request_type = ?")
            params.append(request_type)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self._db.fetchall(
            f"SELECT * FROM requests WHERE {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def update(self, request_id: int, **fields: Any) -> dict[str, Any] | None:
        allowed = {"title", "description", "area", "priority", "status", "assigned_to", "workflow_state",
                    "frequency", "tools_used", "steps", "resolution_notes"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get(request_id)
        now = datetime.now().isoformat()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [request_id]
        self._db.execute(f"UPDATE requests SET {set_clause} WHERE id = ?", tuple(values))
        self._db.commit()
        return self.get(request_id)

    def delete(self, request_id: int) -> bool:
        self._db.execute("DELETE FROM requests WHERE id = ?", (request_id,))
        self._db.commit()
        return True

    def get_stats(self) -> dict[str, Any]:
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM requests")
        by_status = self._db.fetchall("SELECT status, COUNT(*) as cnt FROM requests GROUP BY status")
        by_type = self._db.fetchall("SELECT request_type, COUNT(*) as cnt FROM requests GROUP BY request_type")
        return {
            "total": total["cnt"] if total else 0,
            "by_status": {r["status"]: r["cnt"] for r in by_status},
            "by_type": {r["request_type"]: r["cnt"] for r in by_type},
        }
