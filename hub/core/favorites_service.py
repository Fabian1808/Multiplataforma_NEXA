"""Core — Favorites Service. Gestión de favoritos de usuarios."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any
from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)

class FavoritesService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add_favorite(self, user_id: str, plugin_id: str) -> bool:
        now = datetime.now().isoformat()
        try:
            self._db.execute(
                "INSERT OR IGNORE INTO user_favorites (user_id, plugin_id, created_at) VALUES (?, ?, ?)",
                (user_id, plugin_id, now),
            )
            self._db.commit()
            return True
        except Exception:
            logger.exception("Error adding favorite")
            return False

    def remove_favorite(self, user_id: str, plugin_id: str) -> bool:
        self._db.execute(
            "DELETE FROM user_favorites WHERE user_id = ? AND plugin_id = ?",
            (user_id, plugin_id),
        )
        self._db.commit()
        return True

    def is_favorite(self, user_id: str, plugin_id: str) -> bool:
        row = self._db.fetchone(
            "SELECT 1 FROM user_favorites WHERE user_id = ? AND plugin_id = ?",
            (user_id, plugin_id),
        )
        return row is not None

    def get_favorites(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT plugin_id, created_at FROM user_favorites WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]

    def get_favorite_ids(self, user_id: str) -> list[str]:
        rows = self._db.fetchall(
            "SELECT plugin_id FROM user_favorites WHERE user_id = ?",
            (user_id,),
        )
        return [r["plugin_id"] for r in rows]

    def clear_favorites(self, user_id: str) -> bool:
        self._db.execute("DELETE FROM user_favorites WHERE user_id = ?", (user_id,))
        self._db.commit()
        return True

    def get_favorites_count(self, user_id: str) -> int:
        row = self._db.fetchone(
            "SELECT COUNT(*) as cnt FROM user_favorites WHERE user_id = ?",
            (user_id,),
        )
        return row["cnt"] if row else 0
