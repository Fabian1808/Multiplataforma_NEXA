"""Infrastructure — Database SQLite con motor de migraciones basado en archivos."""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# La versión actual del esquema está dictada por el número más alto en la carpeta migrations.
# No necesitamos definirla a fuego aquí, pero sí la usamos como referencia mínima si lo deseamos.


class Database:
    """Capa de persistencia SQLite con schema completo de plataforma corporativa y migraciones."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path:
            self._db_path = db_path
        else:
            appdata = os.environ.get("APPDATA", str(Path.home()))
            self._db_path = Path(appdata) / "NEXA" / "ProductivityHub" / "data" / "nexus.db"
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        
        # Ruta donde viven las migraciones (.sql)
        import sys as _sys
        if getattr(_sys, "frozen", False):
            self._migrations_dir = Path(_sys._MEIPASS) / "hub" / "infrastructure" / "migrations"
        else:
            self._migrations_dir = Path(__file__).resolve().parent / "migrations"

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            # synchronous=NORMAL: más rápido que FULL, seguro con WAL ante
            # fallos del OS (solo puede perder la última transacción incompleta).
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA cache_size=-8000")   # 8 MB de caché
            self._conn.execute("PRAGMA temp_store=MEMORY")
            self._init_schema()
            logger.info("Database conectada: %s", self._db_path)
        return self._conn

    def close(self) -> None:
        with self._lock:
            if not self._conn:
                return
            try:
                self._conn.commit()
            except Exception:
                pass
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self.connect().execute(sql, params)

    def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        with self._lock:
            return self.connect().executemany(sql, params)

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        try:
            with self._lock:
                return self.connect().execute(sql, params).fetchone()
        except sqlite3.OperationalError:
            logger.exception("Error en fetchone: %s", sql[:120])
            return None

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        try:
            with self._lock:
                return self.connect().execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            logger.exception("Error en fetchall: %s", sql[:120])
            return []

    def commit(self) -> None:
        if self._conn:
            with self._lock:
                self._conn.commit()

    def _init_schema(self) -> None:
        conn = self._conn
        if conn is None:
            return

        # Nos aseguramos que la tabla de versionamiento exista
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
        conn.commit()

        try:
            row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
            current_version = row["version"] if row else 0
        except sqlite3.OperationalError:
            current_version = 0

        # Encontrar todas las migraciones en la carpeta
        if not self._migrations_dir.exists():
            logger.warning("No se encontró el directorio de migraciones: %s", self._migrations_dir)
            return

        migration_files = sorted(self._migrations_dir.glob("*.sql"))
        applied_any = False

        for mig_file in migration_files:
            # Los archivos deben seguir el patrón "001_name.sql"
            try:
                mig_version = int(mig_file.stem.split("_")[0])
            except ValueError:
                logger.warning("Archivo de migración ignorado por formato inválido: %s", mig_file.name)
                continue

            if mig_version > current_version:
                logger.info("Aplicando migración v%d: %s", mig_version, mig_file.name)
                try:
                    with open(mig_file, "r", encoding="utf-8") as f:
                        sql_script = f.read()
                    
                    conn.executescript(sql_script)
                    conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (mig_version,))
                    conn.commit()
                    
                    current_version = mig_version
                    applied_any = True
                except Exception as e:
                    logger.error("Error aplicando migración %s: %s", mig_file.name, e)
                    conn.rollback()
                    raise

        if applied_any:
            logger.info("Schema actualizado a la versión v%d", current_version)
        else:
            logger.info("Schema actualizado (v%d)", current_version)
