"""Core — Feed Service. Publicaciones de la comunidad corporativa."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class FeedService:
    """Servicio de feed/comunidad corporativo."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create_post(self, user_id: str, content: str, title: str = "",
                    visibility: str = "publico", post_type: str = "general",
                    tags: str = "", created_by: str = "") -> int:
        now = datetime.now().isoformat()
        cursor = self._db.execute(
            """INSERT INTO posts (user_id, title, content, visibility, post_type, tags, created_at, updated_at, created_by, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, content, visibility, post_type, tags, now, now, created_by, created_by),
        )
        self._db.commit()
        return cursor.lastrowid or 0

    def get_post(self, post_id: int, viewer_id: str = "") -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT * FROM posts WHERE id = ?", (post_id,))
        if not row:
            return None
        result = dict(row)
        user = self._db.fetchone("SELECT name, area FROM users WHERE id = ?", (row["user_id"],))
        if user:
            result["author_name"] = user["name"]
            result["author_area"] = user["area"]
        if viewer_id:
            liked = self._db.fetchone(
                "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
                (post_id, viewer_id),
            )
            result["is_liked"] = liked is not None
        else:
            result["is_liked"] = False
        return result

    def get_feed(self, user_id: str = "", visibility_filter: str = "publico",
                 post_type: str | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        conditions = ["visibility = ?"]
        params: list[Any] = [visibility_filter]
        if post_type:
            conditions.append("post_type = ?")
            params.append(post_type)
        where = " AND ".join(conditions)
        rows = self._db.fetchall(
            f"SELECT * FROM posts WHERE {where} ORDER BY is_pinned DESC, created_at DESC LIMIT ? OFFSET ?",
            tuple(params) + (limit, offset),
        )
        results = []
        for row in rows:
            result = dict(row)
            user = self._db.fetchone("SELECT name, area FROM users WHERE id = ?", (row["user_id"],))
            if user:
                result["author_name"] = user["name"]
                result["author_area"] = user["area"]
            if user_id:
                liked = self._db.fetchone(
                    "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
                    (row["id"], user_id),
                )
                result["is_liked"] = liked is not None
            else:
                result["is_liked"] = False
            results.append(result)
        return results

    def update_post(self, post_id: int, **fields: Any) -> dict[str, Any] | None:
        allowed = {"title", "content", "visibility", "post_type", "tags", "is_pinned"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_post(post_id)
        now = datetime.now().isoformat()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [post_id]
        self._db.execute(f"UPDATE posts SET {set_clause} WHERE id = ?", tuple(values))
        self._db.commit()
        return self.get_post(post_id)

    def delete_post(self, post_id: int) -> bool:
        self._db.execute("DELETE FROM post_likes WHERE post_id = ?", (post_id,))
        self._db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        self._db.commit()
        return True

    def toggle_like(self, post_id: int, user_id: str) -> bool:
        existing = self._db.fetchone(
            "SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?",
            (post_id, user_id),
        )
        now = datetime.now().isoformat()
        if existing:
            self._db.execute("DELETE FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            self._db.execute("UPDATE posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
            self._db.commit()
            return False
        else:
            self._db.execute("INSERT INTO post_likes (post_id, user_id, created_at) VALUES (?, ?, ?)", (post_id, user_id, now))
            self._db.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
            self._db.commit()
            return True

    def get_post_count(self) -> int:
        row = self._db.fetchone("SELECT COUNT(*) as cnt FROM posts")
        return row["cnt"] if row else 0

    def get_user_posts(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(r) for r in rows]

    def get_trending_tags(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT tags FROM posts WHERE tags != '' ORDER BY created_at DESC LIMIT 100"
        )
        tag_counts: dict[str, int] = {}
        for row in rows:
            for tag in row["tags"].split(","):
                tag = tag.strip()
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"tag": t, "count": c} for t, c in sorted_tags]
