"""Core — Audit Service. Registra y consulta el registro de auditoría."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class AuditService:
    """Servicio de auditoría para registrar acciones en el sistema."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def log(
        self,
        user_id: str,
        action: str,
        module: str,
        entity_type: str = "",
        entity_id: str = "",
        entity_name: str = "",
        details: dict[str, Any] | str | None = None,
        ip_address: str = "",
    ) -> None:
        now = datetime.now().isoformat()
        if isinstance(details, dict):
            details_str = json.dumps(details, ensure_ascii=False, default=str)
        elif details is None:
            details_str = ""
        else:
            details_str = str(details)
        self._db.execute(
            """INSERT INTO audit_log (user_id, action, module, entity_type, entity_id, entity_name, details, ip_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, action, module, entity_type, str(entity_id), entity_name, details_str, ip_address, now),
        )
        self._db.commit()
        logger.debug("Audit: %s %s %s/%s by %s", action, module, entity_type, entity_id, user_id)

    def log_create(self, user_id: str, module: str, entity_type: str, entity_id: str, entity_name: str = "", **extra: Any) -> None:
        self.log(user_id, "create", module, entity_type, entity_id, entity_name, extra)

    def log_update(self, user_id: str, module: str, entity_type: str, entity_id: str, entity_name: str = "", changes: dict[str, Any] | None = None) -> None:
        self.log(user_id, "update", module, entity_type, entity_id, entity_name, changes or {})

    def log_delete(self, user_id: str, module: str, entity_type: str, entity_id: str, entity_name: str = "") -> None:
        self.log(user_id, "delete", module, entity_type, entity_id, entity_name)

    def log_view(self, user_id: str, module: str, entity_type: str, entity_id: str) -> None:
        self.log(user_id, "view", module, entity_type, entity_id)

    def log_login(self, user_id: str, ip_address: str = "") -> None:
        self.log(user_id, "login", "system", "user", user_id, ip_address=ip_address)

    def log_search(self, user_id: str, query: str, results_count: int) -> None:
        self.log(user_id, "search", "search", "query", query, details={"results": results_count})

    def get_entries(
        self,
        user_id: str | None = None,
        action: str | None = None,
        module: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if user_id:
            conditions.append("a.user_id = ?")
            params.append(user_id)
        if action:
            conditions.append("a.action = ?")
            params.append(action)
        if module:
            conditions.append("a.module = ?")
            params.append(module)
        if entity_type:
            conditions.append("a.entity_type = ?")
            params.append(entity_type)
        if entity_id:
            conditions.append("a.entity_id = ?")
            params.append(entity_id)
        if date_from:
            conditions.append("a.created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("a.created_at <= ?")
            params.append(date_to)
        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT a.*, u.name as user_name
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE {where}
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = self._db.fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_entry_count(
        self,
        user_id: str | None = None,
        action: str | None = None,
        module: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        conditions = []
        params: list[Any] = []
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if module:
            conditions.append("module = ?")
            params.append(module)
        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to)
        where = " AND ".join(conditions) if conditions else "1=1"
        row = self._db.fetchone(f"SELECT COUNT(*) as cnt FROM audit_log WHERE {where}", tuple(params))
        return row["cnt"] if row else 0

    def get_stats(self) -> dict[str, Any]:
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM audit_log")
        by_action = self._db.fetchall("SELECT action, COUNT(*) as cnt FROM audit_log GROUP BY action ORDER BY cnt DESC")
        by_module = self._db.fetchall("SELECT module, COUNT(*) as cnt FROM audit_log GROUP BY module ORDER BY cnt DESC")
        by_user = self._db.fetchall(
            "SELECT a.user_id, u.name, COUNT(*) as cnt FROM audit_log a LEFT JOIN users u ON a.user_id = u.id GROUP BY a.user_id ORDER BY cnt DESC LIMIT 10"
        )
        return {
            "total": total["cnt"] if total else 0,
            "by_action": {r["action"]: r["cnt"] for r in by_action},
            "by_module": {r["module"]: r["cnt"] for r in by_module},
            "by_user": [{"user_id": r["user_id"], "name": r["name"], "count": r["cnt"]} for r in by_user],
        }

    def clear_old_entries(self, days: int = 90) -> int:
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        self._db.execute("DELETE FROM audit_log WHERE created_at < ?", (cutoff,))
        self._db.commit()
        return self._db.execute("SELECT changes() as cnt").fetchone()["cnt"]
