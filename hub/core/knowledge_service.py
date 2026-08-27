"""Core — Knowledge Service. CRUD de artículos de conocimiento."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Servicio de base de conocimiento con versionado."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, title: str, content: str = "", summary: str = "", category: str = "",
               tags: str = "", author: str = "", plugin_id: str = "", status: str = "publicado",
               created_by: str = "") -> int:
        now = datetime.now().isoformat()
        cursor = self._db.execute(
            """INSERT INTO knowledge_articles (title, content, summary, category, tags, status, version, author, plugin_id, created_at, updated_at, created_by, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
            (title, content, summary, category, tags, status, author, plugin_id, now, now, created_by, created_by),
        )
        self._db.commit()
        return cursor.lastrowid or 0

    def get(self, article_id: int) -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT * FROM knowledge_articles WHERE id = ?", (article_id,))
        return dict(row) if row else None

    def get_all(self, category: str | None = None, status: str | None = None,
                author: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if author:
            conditions.append("author = ?")
            params.append(author)
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self._db.fetchall(
            f"SELECT * FROM knowledge_articles WHERE {where} ORDER BY updated_at DESC LIMIT ?",
            tuple(params) + (limit,),
        )
        return [dict(r) for r in rows]

    def update(self, article_id: int, **fields: Any) -> dict[str, Any] | None:
        allowed = {"title", "content", "summary", "category", "tags", "status", "author", "plugin_id"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get(article_id)
        now = datetime.now().isoformat()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [article_id]
        self._db.execute(f"UPDATE knowledge_articles SET {set_clause} WHERE id = ?", tuple(values))
        self._db.commit()
        return self.get(article_id)

    def delete(self, article_id: int) -> bool:
        self._db.execute("DELETE FROM knowledge_articles WHERE id = ?", (article_id,))
        self._db.commit()
        return True

    def increment_view(self, article_id: int) -> None:
        self._db.execute("UPDATE knowledge_articles SET view_count = view_count + 1 WHERE id = ?", (article_id,))
        self._db.commit()

    def increment_helpful(self, article_id: int) -> None:
        self._db.execute("UPDATE knowledge_articles SET helpful_count = helpful_count + 1 WHERE id = ?", (article_id,))
        self._db.commit()

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM knowledge_articles WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        )
        return [dict(r) for r in rows]

    def get_categories(self) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT category, COUNT(*) as cnt FROM knowledge_articles WHERE category != '' GROUP BY category ORDER BY cnt DESC"
        )
        return [{"category": r["category"], "count": r["cnt"]} for r in rows]
