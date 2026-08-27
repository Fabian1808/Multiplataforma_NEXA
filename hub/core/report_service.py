"""Core — Report Service. Centro de reportes corporativo."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any
from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, name: str, plugin_id: str = "", user_id: str = "", report_type: str = "general",
               period_start: str = "", period_end: str = "", records_count: int = 0,
               result_summary: str = "", observations: str = "", file_path: str = "",
               file_name: str = "", file_size: int = 0, created_by: str = "") -> int:
        now = datetime.now().isoformat()
        cursor = self._db.execute(
            """INSERT INTO reports (name, plugin_id, user_id, status, report_type, period_start, period_end,
               records_count, result_summary, observations, file_path, file_name, file_size, created_at, updated_at, created_by)
               VALUES (?, ?, ?, 'exitoso', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, plugin_id, user_id, report_type, period_start, period_end,
             records_count, result_summary, observations, file_path, file_name, file_size, now, now, created_by),
        )
        self._db.commit()
        return cursor.lastrowid or 0

    def get(self, report_id: int) -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT * FROM reports WHERE id = ?", (report_id,))
        return dict(row) if row else None

    def get_all(self, user_id: str | None = None, plugin_id: str | None = None,
                status: str | None = None, report_type: str | None = None,
                limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        conditions, params = [], []
        if user_id:
            conditions.append("user_id = ?"); params.append(user_id)
        if plugin_id:
            conditions.append("plugin_id = ?"); params.append(plugin_id)
        if status:
            conditions.append("status = ?"); params.append(status)
        if report_type:
            conditions.append("report_type = ?"); params.append(report_type)
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self._db.fetchall(
            f"SELECT r.*, u.name as user_name FROM reports r LEFT JOIN users u ON r.user_id = u.id WHERE {where} ORDER BY r.created_at DESC LIMIT ? OFFSET ?",
            tuple(params) + (limit, offset),
        )
        return [dict(r) for r in rows]

    def update(self, report_id: int, **fields: Any) -> dict[str, Any] | None:
        allowed = {"name", "status", "result_summary", "observations", "file_path", "file_name", "file_size"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get(report_id)
        now = datetime.now().isoformat()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [report_id]
        self._db.execute(f"UPDATE reports SET {set_clause} WHERE id = ?", tuple(values))
        self._db.commit()
        return self.get(report_id)

    def delete(self, report_id: int) -> bool:
        self._db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        self._db.commit()
        return True

    def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        where_user = "WHERE user_id = ?" if user_id else ""
        params = (user_id,) if user_id else ()
        total = self._db.fetchone(f"SELECT COUNT(*) as cnt FROM reports {where_user}", params)
        today = datetime.now().strftime("%Y-%m-%d")
        today_where = f"{'AND' if where_user else 'WHERE'} created_at >= ?"
        today_params = params + (today,) if params else (today,)
        today_count = self._db.fetchone(f"SELECT COUNT(*) as cnt FROM reports {where_user} {today_where}", today_params)
        ok = self._db.fetchone(f"SELECT COUNT(*) as cnt FROM reports {where_user} {'AND' if where_user else 'WHERE'} status = 'exitoso'", params)
        err = self._db.fetchone(f"SELECT COUNT(*) as cnt FROM reports {where_user} {'AND' if where_user else 'WHERE'} status = 'error'", params)
        return {
            "total": total["cnt"] if total else 0,
            "today": today_count["cnt"] if today_count else 0,
            "success": ok["cnt"] if ok else 0,
            "errors": err["cnt"] if err else 0,
        }

    def get_by_plugin(self, plugin_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM reports WHERE plugin_id = ? ORDER BY created_at DESC LIMIT ?",
            (plugin_id, limit),
        )
        return [dict(r) for r in rows]
