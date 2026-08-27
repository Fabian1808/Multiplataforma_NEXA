"""Core — Search Engine con SQLite FTS5."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from hub.infrastructure.database import Database
from hub.models.plugin import PluginDescriptor

logger = logging.getLogger(__name__)


class SearchEngine:
    """Motor de búsqueda full-text con SQLite FTS5."""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        if self._db:
            self._conn = self._db.connect()
        else:
            self._conn = sqlite3.connect(":memory:")
            self._conn.row_factory = sqlite3.Row
        self._init_fts(self._conn)
        return self._conn

    def _init_fts(self, conn: sqlite3.Connection) -> None:
        conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS plugin_fts USING fts5(
                plugin_id UNINDEXED,
                name,
                description,
                tags,
                synonyms,
                category,
                tokenize='porter unicode61'
            );
        """)

    def index_plugin(self, desc: PluginDescriptor) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM plugin_fts WHERE plugin_id = ?", (desc.id,))
        conn.execute(
            """INSERT INTO plugin_fts (plugin_id, name, description, tags, synonyms, category)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                desc.id,
                desc.name,
                desc.description,
                " ".join(desc.tags),
                " ".join(desc.synonyms),
                desc.category.value,
            ),
        )
        conn.commit()

    def index_all(self, plugins: list[PluginDescriptor]) -> None:
        for p in plugins:
            self.index_plugin(p)
        logger.info("FTS indexado: %d plugins", len(plugins))

    def search(self, query: str, limit: int = 20) -> list[tuple[str, float]]:
        if not query.strip():
            return []
        conn = self._get_conn()
        fts_tokens = [t for t in query.split() if t]
        fts_query = " OR ".join(f'"{t}"' for t in fts_tokens)
        try:
            rows = conn.execute(
                """SELECT plugin_id, rank FROM plugin_fts WHERE plugin_fts MATCH ? ORDER BY rank LIMIT ?""",
                (fts_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            logger.warning("FTS query falló, usando LIKE: %s", query)
            rows = conn.execute(
                """SELECT plugin_id, 0.0 as rank FROM plugin_fts
                   WHERE name LIKE ? OR description LIKE ? OR tags LIKE ? LIMIT ?""",
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [(row["plugin_id"], max(0.1, 1.0 / (1.0 + abs(row["rank"])))) for row in rows]

    def rebuild_index(self, plugins: list[PluginDescriptor]) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM plugin_fts")
        conn.commit()
        self.index_all(plugins)

    def close(self) -> None:
        if self._conn and not self._db:
            self._conn.close()
            self._conn = None
