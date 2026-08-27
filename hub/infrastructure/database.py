"""Infrastructure — Database SQLite con schema completo de plataforma corporativa."""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 4

_CREATE_TABLES = """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT DEFAULT '',
        password_hash TEXT DEFAULT '',
        avatar_url TEXT DEFAULT '',
        area TEXT DEFAULT '',
        department_id TEXT DEFAULT '',
        manager_id TEXT DEFAULT '',
        role TEXT DEFAULT 'usuario',
        is_active INTEGER DEFAULT 1,
        last_login TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS departments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        parent_id TEXT DEFAULT '',
        manager_id TEXT DEFAULT '',
        description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS roles (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS permissions (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        module TEXT NOT NULL,
        action TEXT NOT NULL,
        description TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id TEXT NOT NULL,
        permission_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (role_id, permission_id),
        FOREIGN KEY (role_id) REFERENCES roles(id),
        FOREIGN KEY (permission_id) REFERENCES permissions(id)
    );

    CREATE TABLE IF NOT EXISTS user_roles (
        user_id TEXT NOT NULL,
        role_id TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        assigned_by TEXT DEFAULT '',
        PRIMARY KEY (user_id, role_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        token TEXT UNIQUE NOT NULL,
        ip_address TEXT DEFAULT '',
        user_agent TEXT DEFAULT '',
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'planeacion',
        priority TEXT DEFAULT 'media',
        owner_id TEXT DEFAULT '',
        department_id TEXT DEFAULT '',
        start_date TEXT DEFAULT '',
        end_date TEXT DEFAULT '',
        progress INTEGER DEFAULT 0,
        tags TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'pendiente',
        priority TEXT DEFAULT 'media',
        assignee_id TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        estimated_hours REAL DEFAULT 0,
        actual_hours REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT '',
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        request_type TEXT NOT NULL,
        title TEXT DEFAULT '',
        description TEXT DEFAULT '',
        area TEXT DEFAULT '',
        priority TEXT DEFAULT 'media',
        status TEXT DEFAULT 'enviada',
        assigned_to TEXT DEFAULT '',
        workflow_state TEXT DEFAULT 'nueva',
        frequency TEXT DEFAULT '',
        tools_used TEXT DEFAULT '',
        steps TEXT DEFAULT '',
        resolution_notes TEXT DEFAULT '',
        resolved_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        parent_id INTEGER DEFAULT 0,
        is_deleted INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS knowledge_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        summary TEXT DEFAULT '',
        category TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        status TEXT DEFAULT 'publicado',
        version INTEGER DEFAULT 1,
        author TEXT DEFAULT '',
        plugin_id TEXT DEFAULT '',
        view_count INTEGER DEFAULT 0,
        helpful_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        notification_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT DEFAULT '',
        action_url TEXT DEFAULT '',
        channel TEXT DEFAULT 'in_app',
        priority TEXT DEFAULT 'normal',
        related_entity_type TEXT DEFAULT '',
        related_entity_id TEXT DEFAULT '',
        read INTEGER DEFAULT 0,
        read_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        created_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        user_id TEXT DEFAULT 'default',
        status TEXT DEFAULT 'exito',
        started_at TEXT DEFAULT '',
        finished_at TEXT DEFAULT '',
        duration_seconds REAL DEFAULT 0,
        output_summary TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ratings (
        plugin_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        helpful INTEGER DEFAULT 1,
        time_saved_minutes INTEGER DEFAULT 0,
        comment TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        PRIMARY KEY (plugin_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS favorites (
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (user_id, plugin_id)
    );

    CREATE TABLE IF NOT EXISTS recent_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        used_at TEXT NOT NULL,
        duration_seconds REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        results_count INTEGER DEFAULT 0,
        user_id TEXT DEFAULT 'default',
        session_id TEXT DEFAULT '',
        latency_ms REAL DEFAULT 0,
        searched_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS search_opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        results_count INTEGER DEFAULT 0,
        user_id TEXT DEFAULT 'default',
        searched_at TEXT NOT NULL,
        acknowledged INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        action TEXT NOT NULL,
        module TEXT NOT NULL,
        entity_type TEXT DEFAULT '',
        entity_id TEXT DEFAULT '',
        entity_name TEXT DEFAULT '',
        details TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS integrations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        integration_type TEXT NOT NULL,
        status TEXT DEFAULT 'inactivo',
        config TEXT DEFAULT '',
        description TEXT DEFAULT '',
        last_sync_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        color TEXT DEFAULT '#FF5503',
        usage_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        title TEXT DEFAULT '',
        content TEXT NOT NULL,
        visibility TEXT DEFAULT 'publico',
        post_type TEXT DEFAULT 'general',
        tags TEXT DEFAULT '',
        likes_count INTEGER DEFAULT 0,
        comments_count INTEGER DEFAULT 0,
        is_pinned INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS post_likes (
        post_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (post_id, user_id),
        FOREIGN KEY (post_id) REFERENCES posts(id)
    );

    CREATE TABLE IF NOT EXISTS sla_policies (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        priority TEXT NOT NULL,
        response_hours INTEGER DEFAULT 24,
        resolution_hours INTEGER DEFAULT 72,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        severity TEXT DEFAULT 'media',
        status TEXT DEFAULT 'abierto',
        reporter_id TEXT DEFAULT '',
        assignee_id TEXT DEFAULT '',
        related_plugin_id TEXT DEFAULT '',
        related_request_id INTEGER DEFAULT 0,
        resolution TEXT DEFAULT '',
        resolved_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        updated_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS metrics_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL DEFAULT 0,
        dimension TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE(date, metric_name, dimension)
    );

    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        plugin_id TEXT DEFAULT '',
        user_id TEXT NOT NULL,
        status TEXT DEFAULT 'exitoso',
        report_type TEXT DEFAULT 'general',
        period_start TEXT DEFAULT '',
        period_end TEXT DEFAULT '',
        records_count INTEGER DEFAULT 0,
        result_summary TEXT DEFAULT '',
        observations TEXT DEFAULT '',
        file_path TEXT DEFAULT '',
        file_name TEXT DEFAULT '',
        file_size INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        created_by TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS app_states (
        plugin_id TEXT PRIMARY KEY,
        state TEXT DEFAULT 'activo',
        failure_count INTEGER DEFAULT 0,
        last_execution_at TEXT DEFAULT '',
        last_update_at TEXT DEFAULT '',
        last_user_id TEXT DEFAULT '',
        paused_by TEXT DEFAULT '',
        paused_at TEXT DEFAULT '',
        pause_reason TEXT DEFAULT '',
        maintenance_message TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS failed_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        user_id TEXT DEFAULT '',
        error_type TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        severity TEXT DEFAULT 'media',
        status TEXT DEFAULT 'abierto',
        assignee_id TEXT DEFAULT '',
        resolution TEXT DEFAULT '',
        resolved_at TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS user_favorites (
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        PRIMARY KEY (user_id, plugin_id)
    );

    CREATE TABLE IF NOT EXISTS recent_plugins (
        user_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        accessed_at TEXT NOT NULL,
        access_count INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, plugin_id)
    );
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
    "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
    "CREATE INDEX IF NOT EXISTS idx_users_department ON users(department_id);",
    "CREATE INDEX IF NOT EXISTS idx_departments_parent ON departments(parent_id);",
    "CREATE INDEX IF NOT EXISTS idx_departments_code ON departments(code);",
    "CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);",
    "CREATE INDEX IF NOT EXISTS idx_role_permissions_perm ON role_permissions(permission_id);",
    "CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);",
    "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);",
    "CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);",
    "CREATE INDEX IF NOT EXISTS idx_projects_department ON projects(department_id);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);",
    "CREATE INDEX IF NOT EXISTS idx_requests_user ON requests(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);",
    "CREATE INDEX IF NOT EXISTS idx_requests_type ON requests(request_type);",
    "CREATE INDEX IF NOT EXISTS idx_requests_assigned ON requests(assigned_to);",
    "CREATE INDEX IF NOT EXISTS idx_comments_entity ON comments(entity_type, entity_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_articles(category);",
    "CREATE INDEX IF NOT EXISTS idx_knowledge_status ON knowledge_articles(status);",
    "CREATE INDEX IF NOT EXISTS idx_knowledge_author ON knowledge_articles(author);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(user_id, read);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);",
    "CREATE INDEX IF NOT EXISTS idx_executions_plugin ON executions(plugin_id);",
    "CREATE INDEX IF NOT EXISTS idx_executions_user ON executions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);",
    "CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_recent_usage_user ON recent_usage(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_recent_usage_plugin ON recent_usage(plugin_id);",
    "CREATE INDEX IF NOT EXISTS idx_searches_query ON searches(query);",
    "CREATE INDEX IF NOT EXISTS idx_searches_user ON searches(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_opportunities_query ON search_opportunities(query);",
    "CREATE INDEX IF NOT EXISTS idx_opportunities_ack ON search_opportunities(acknowledged);",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_module ON audit_log(module);",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_date ON audit_log(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_integrations_type ON integrations(integration_type);",
    "CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(post_type);",
    "CREATE INDEX IF NOT EXISTS idx_posts_visibility ON posts(visibility);",
    "CREATE INDEX IF NOT EXISTS idx_post_likes_post ON post_likes(post_id);",
    "CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);",
    "CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);",
    "CREATE INDEX IF NOT EXISTS idx_incidents_assignee ON incidents(assignee_id);",
    "CREATE INDEX IF NOT EXISTS idx_metrics_daily_date ON metrics_daily(date);",
    "CREATE INDEX IF NOT EXISTS idx_metrics_daily_name ON metrics_daily(metric_name);",
    "CREATE INDEX IF NOT EXISTS idx_reports_plugin ON reports(plugin_id);",
    "CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);",
    "CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type);",
    "CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_app_states_state ON app_states(state);",
    "CREATE INDEX IF NOT EXISTS idx_failed_exec_plugin ON failed_executions(plugin_id);",
    "CREATE INDEX IF NOT EXISTS idx_failed_exec_user ON failed_executions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_failed_exec_severity ON failed_executions(severity);",
    "CREATE INDEX IF NOT EXISTS idx_failed_exec_status ON failed_executions(status);",
    "CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_recent_plugins_user ON recent_plugins(user_id);",
]


class Database:
    """Capa de persistencia SQLite con schema completo de plataforma corporativa."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path:
            self._db_path = db_path
        else:
            appdata = os.environ.get("APPDATA", str(Path.home()))
            self._db_path = Path(appdata) / "NEXA" / "ProductivityHub" / "data" / "nexus.db"
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

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
        if self._conn:
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
        try:
            row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            current = row["version"] if row else 0
        except sqlite3.OperationalError:
            current = 0
        if current < SCHEMA_VERSION:
            existing = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'schema_version'").fetchall()
            if existing:
                logger.info("Schema obsoleto (v%d), recreando...", current)
                self._drop_all_tables(conn)
            conn.executescript(_CREATE_TABLES)
            conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            conn.commit()
            self._create_indexes(conn)
            logger.info("Schema inicializado: v%d", SCHEMA_VERSION)
        else:
            self._create_indexes(conn)

    def _drop_all_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA foreign_keys=OFF")
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for t in tables:
            conn.execute(f"DROP TABLE IF EXISTS [{t['name']}]")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        for sql in _INDEXES:
            conn.execute(sql)
        conn.commit()
