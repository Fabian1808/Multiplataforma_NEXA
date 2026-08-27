"""Core — Notification Service. CRUD de notificaciones."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio de notificaciones in-app."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str = "",
        action_url: str = "",
        channel: str = "in_app",
        priority: str = "normal",
        related_entity_type: str = "",
        related_entity_id: str = "",
        created_by: str = "",
    ) -> int:
        now = datetime.now().isoformat()
        cursor = self._db.execute(
            """INSERT INTO notifications (user_id, notification_type, title, message, action_url, channel, priority, related_entity_type, related_entity_id, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, notification_type, title, message, action_url, channel, priority, related_entity_type, related_entity_id, now, created_by),
        )
        self._db.commit()
        return cursor.lastrowid or 0

    def get_all(self, user_id: str, unread_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        if unread_only:
            rows = self._db.fetchall(
                "SELECT * FROM notifications WHERE user_id = ? AND read = 0 ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
        else:
            rows = self._db.fetchall(
                "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
        return [dict(r) for r in rows]

    def get_unread_count(self, user_id: str) -> int:
        row = self._db.fetchone(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND read = 0",
            (user_id,),
        )
        return row["cnt"] if row else 0

    def mark_read(self, notification_id: int) -> None:
        now = datetime.now().isoformat()
        self._db.execute("UPDATE notifications SET read = 1, read_at = ? WHERE id = ?", (now, notification_id))
        self._db.commit()

    def mark_all_read(self, user_id: str) -> int:
        now = datetime.now().isoformat()
        self._db.execute("UPDATE notifications SET read = 1, read_at = ? WHERE user_id = ? AND read = 0", (now, user_id))
        self._db.commit()
        return self._db.execute("SELECT changes() as cnt").fetchone()["cnt"]

    def delete(self, notification_id: int) -> None:
        self._db.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
        self._db.commit()

    def delete_all(self, user_id: str) -> None:
        self._db.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
        self._db.commit()

    def get_by_type(self, user_id: str, notification_type: str) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM notifications WHERE user_id = ? AND notification_type = ? ORDER BY created_at DESC",
            (user_id, notification_type),
        )
        return [dict(r) for r in rows]

    def get_stats(self, user_id: str) -> dict[str, int]:
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ?", (user_id,))
        unread = self._db.fetchone("SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND read = 0", (user_id,))
        return {
            "total": total["cnt"] if total else 0,
            "unread": unread["cnt"] if unread else 0,
        }
