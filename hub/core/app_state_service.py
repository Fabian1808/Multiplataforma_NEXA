"""Core — App State Service. Estado y salud de aplicaciones/herramientas."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any
from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)

class AppStateService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_state(self, plugin_id: str) -> dict[str, Any]:
        row = self._db.fetchone("SELECT * FROM app_states WHERE plugin_id = ?", (plugin_id,))
        if row:
            return dict(row)
        now = datetime.now().isoformat()
        self._db.execute(
            "INSERT OR IGNORE INTO app_states (plugin_id, state, created_at, updated_at) VALUES (?, 'activo', ?, ?)",
            (plugin_id, now, now),
        )
        self._db.commit()
        return {"plugin_id": plugin_id, "state": "activo", "failure_count": 0}

    def set_state(self, plugin_id: str, state: str, user_id: str = "", reason: str = "") -> None:
        now = datetime.now().isoformat()
        existing = self.get_state(plugin_id)
        updates: dict[str, Any] = {"state": state, "updated_at": now}
        if state == "pausado":
            updates["paused_by"] = user_id
            updates["paused_at"] = now
            updates["pause_reason"] = reason
        elif state == "activo":
            updates["paused_by"] = ""
            updates["paused_at"] = ""
            updates["pause_reason"] = ""
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self._db.execute(f"UPDATE app_states SET {set_clause} WHERE plugin_id = ?", tuple(list(updates.values()) + [plugin_id]))
        self._db.commit()

    def record_execution(self, plugin_id: str, user_id: str, success: bool) -> None:
        now = datetime.now().isoformat()
        self._db.execute(
            "UPDATE app_states SET last_execution_at = ?, last_user_id = ?, updated_at = ? WHERE plugin_id = ?",
            (now, user_id, now, plugin_id),
        )
        if not success:
            self._db.execute("UPDATE app_states SET failure_count = failure_count + 1 WHERE plugin_id = ?", (plugin_id,))
        self._db.commit()

    def record_failure(self, plugin_id: str, user_id: str, error_type: str, error_message: str, severity: str = "media") -> int:
        now = datetime.now().isoformat()
        cursor = self._db.execute(
            """INSERT INTO failed_executions (plugin_id, user_id, error_type, error_message, severity, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'abierto', ?, ?)""",
            (plugin_id, user_id, error_type, error_message, severity, now, now),
        )
        self._db.execute("UPDATE app_states SET failure_count = failure_count + 1, updated_at = ? WHERE plugin_id = ?", (now, plugin_id))
        self._db.commit()
        return cursor.lastrowid or 0

    def get_failures(self, plugin_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if plugin_id:
            rows = self._db.fetchall(
                "SELECT f.*, u.name as user_name FROM failed_executions f LEFT JOIN users u ON f.user_id = u.id WHERE f.plugin_id = ? ORDER BY f.created_at DESC LIMIT ?",
                (plugin_id, limit),
            )
        else:
            rows = self._db.fetchall(
                "SELECT f.*, u.name as user_name FROM failed_executions f LEFT JOIN users u ON f.user_id = u.id ORDER BY f.created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    def resolve_failure(self, failure_id: int, resolution: str, assignee_id: str = "") -> None:
        now = datetime.now().isoformat()
        self._db.execute(
            "UPDATE failed_executions SET status = 'resuelto', resolution = ?, resolved_at = ?, assignee_id = ?, updated_at = ? WHERE id = ?",
            (resolution, now, assignee_id, now, failure_id),
        )
        self._db.commit()

    def get_all_states(self) -> list[dict[str, Any]]:
        rows = self._db.fetchall("SELECT * FROM app_states ORDER BY updated_at DESC")
        return [dict(r) for r in rows]

    def get_failure_count(self, plugin_id: str) -> int:
        row = self._db.fetchone("SELECT COUNT(*) as cnt FROM failed_executions WHERE plugin_id = ? AND status = 'abierto'", (plugin_id,))
        return row["cnt"] if row else 0

    def get_stats(self) -> dict[str, Any]:
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM app_states")
        active = self._db.fetchone("SELECT COUNT(*) as cnt FROM app_states WHERE state = 'activo'")
        paused = self._db.fetchone("SELECT COUNT(*) as cnt FROM app_states WHERE state = 'pausado'")
        maintenance = self._db.fetchone("SELECT COUNT(*) as cnt FROM app_states WHERE state = 'mantenimiento'")
        problems = self._db.fetchone("SELECT COUNT(*) as cnt FROM app_states WHERE state = 'con_problemas'")
        total_failures = self._db.fetchone("SELECT COUNT(*) as cnt FROM failed_executions WHERE status = 'abierto'")
        return {
            "total": total["cnt"] if total else 0,
            "active": active["cnt"] if active else 0,
            "paused": paused["cnt"] if paused else 0,
            "maintenance": maintenance["cnt"] if maintenance else 0,
            "problems": problems["cnt"] if problems else 0,
            "open_failures": total_failures["cnt"] if total_failures else 0,
        }
