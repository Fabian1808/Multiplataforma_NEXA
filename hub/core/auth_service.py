"""Core — Authentication & RBAC Service."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)

_DEFAULT_PERMISSIONS = [
    ("perm_users_read", "users", "read", "Ver usuarios"),
    ("perm_users_create", "users", "create", "Crear usuarios"),
    ("perm_users_update", "users", "update", "Editar usuarios"),
    ("perm_users_delete", "users", "delete", "Eliminar usuarios"),
    ("perm_projects_read", "projects", "read", "Ver proyectos"),
    ("perm_projects_create", "projects", "create", "Crear proyectos"),
    ("perm_projects_update", "projects", "update", "Editar proyectos"),
    ("perm_projects_delete", "projects", "delete", "Eliminar proyectos"),
    ("perm_requests_read", "requests", "read", "Ver solicitudes"),
    ("perm_requests_create", "requests", "create", "Crear solicitudes"),
    ("perm_requests_update", "requests", "update", "Gestionar solicitudes"),
    ("perm_requests_approve", "requests", "approve", "Aprobar solicitudes"),
    ("perm_requests_assign", "requests", "assign", "Asignar solicitudes"),
    ("perm_knowledge_read", "knowledge", "read", "Ver artículos"),
    ("perm_knowledge_create", "knowledge", "create", "Crear artículos"),
    ("perm_knowledge_update", "knowledge", "update", "Editar artículos"),
    ("perm_knowledge_delete", "knowledge", "delete", "Eliminar artículos"),
    ("perm_knowledge_publish", "knowledge", "publish", "Publicar artículos"),
    ("perm_notifications_read", "notifications", "read", "Ver notificaciones"),
    ("perm_audit_read", "audit", "read", "Ver auditoría"),
    ("perm_audit_export", "audit", "export", "Exportar auditoría"),
    ("perm_plugins_read", "plugins", "read", "Ver plugins"),
    ("perm_plugins_manage", "plugins", "manage", "Gestionar plugins"),
    ("perm_departments_read", "departments", "read", "Ver departamentos"),
    ("perm_departments_manage", "departments", "manage", "Gestionar departamentos"),
    ("perm_feed_read", "feed", "read", "Ver publicaciones"),
    ("perm_feed_create", "feed", "create", "Crear publicaciones"),
    ("perm_reports_read", "reports", "read", "Ver reportes"),
    ("perm_reports_export", "reports", "export", "Exportar reportes"),
    ("perm_integrations_read", "integrations", "read", "Ver integraciones"),
    ("perm_integrations_manage", "integrations", "manage", "Gestionar integraciones"),
    ("perm_system_manage", "system", "manage", "Administrar sistema"),
]

_DEFAULT_ROLES = [
    ("rol_admin", "administrador", "Administrador", "Acceso total al sistema"),
    ("rol_gestor", "gestor", "Gestor", "Gestiona solicitudes y proyectos"),
    ("rol_usuario", "usuario", "Usuario", "Usuario estándar"),
]

_ROLE_PERMS = {
    "administrador": [p[0] for p in _DEFAULT_PERMISSIONS],
    "gestor": [
        "perm_users_read", "perm_projects_read", "perm_projects_create", "perm_projects_update",
        "perm_requests_read", "perm_requests_create", "perm_requests_update",
        "perm_requests_approve", "perm_requests_assign",
        "perm_knowledge_read", "perm_knowledge_create", "perm_knowledge_update", "perm_knowledge_publish",
        "perm_notifications_read", "perm_audit_read",
        "perm_plugins_read", "perm_departments_read",
        "perm_feed_read", "perm_feed_create",
        "perm_reports_read", "perm_reports_export",
    ],
    "usuario": [
        "perm_users_read", "perm_projects_read",
        "perm_requests_read", "perm_requests_create",
        "perm_knowledge_read", "perm_knowledge_create",
        "perm_notifications_read",
        "perm_plugins_read",
        "perm_feed_read", "perm_feed_create",
    ],
}


class AuthService:
    """Servicio de autenticación y control de acceso basado en roles."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        now = datetime.now().isoformat()
        for pid, module, action, desc in _DEFAULT_PERMISSIONS:
            self._db.execute(
                "INSERT OR IGNORE INTO permissions (id, name, module, action, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (pid, f"{module}.{action}", module, action, desc, now),
            )
        for rid, name, display, desc in _DEFAULT_ROLES:
            self._db.execute(
                "INSERT OR IGNORE INTO roles (id, name, display_name, description, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (rid, name, display, desc, now, now),
            )
        for role_name, perm_ids in _ROLE_PERMS.items():
            role_row = self._db.fetchone("SELECT id FROM roles WHERE name = ?", (role_name,))
            if role_row:
                for pid in perm_ids:
                    self._db.execute(
                        "INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_at) VALUES (?, ?, ?)",
                        (role_row["id"], pid, now),
                    )
        self._db.commit()

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        user = self._db.fetchone("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
        if not user:
            return None
        if user["password_hash"] and user["password_hash"] != self._hash_password(password):
            return None
        now = datetime.now().isoformat()
        self._db.execute("UPDATE users SET last_login = ?, updated_at = ? WHERE id = ?", (now, now, user["id"]))
        token = secrets.token_hex(32)
        session_id = secrets.token_hex(16)
        expires = (datetime.now() + timedelta(hours=8)).isoformat()
        self._db.execute(
            "INSERT INTO sessions (id, user_id, token, expires_at, created_at, is_active) VALUES (?, ?, ?, ?, ?, 1)",
            (session_id, user["id"], token, expires, now),
        )
        self._db.commit()
        user_data = self._load_user_full(user["id"])
        user_data["token"] = token
        logger.info("Usuario autenticado: %s", username)
        return user_data

    def logout(self, token: str) -> None:
        self._db.execute("UPDATE sessions SET is_active = 0 WHERE token = ?", (token,))
        self._db.commit()

    def validate_token(self, token: str) -> dict[str, Any] | None:
        session = self._db.fetchone(
            "SELECT s.*, u.id as uid FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ? AND s.is_active = 1 AND s.expires_at > ?",
            (token, datetime.now().isoformat()),
        )
        if not session:
            return None
        return self._load_user_full(session["uid"])

    def create_user(self, username: str, name: str, email: str, password: str,
                    area: str = "", department_id: str = "", role: str = "usuario",
                    created_by: str = "") -> dict[str, Any]:
        now = datetime.now().isoformat()
        user_id = f"usr_{secrets.token_hex(8)}"
        self._db.execute(
            """INSERT INTO users (id, username, name, email, password_hash, area, department_id, role, is_active, created_at, updated_at, created_by, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
            (user_id, username, name, email, self._hash_password(password), area, department_id, role, now, now, created_by, created_by),
        )
        role_row = self._db.fetchone("SELECT id FROM roles WHERE name = ?", (role,))
        if role_row:
            self._db.execute(
                "INSERT OR IGNORE INTO user_roles (user_id, role_id, assigned_at, assigned_by) VALUES (?, ?, ?, ?)",
                (user_id, role_row["id"], now, created_by),
            )
        self._db.commit()
        return self._load_user_full(user_id)

    def update_user(self, user_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"name", "email", "area", "department_id", "manager_id", "role", "is_active", "avatar_url"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self._load_user_full(user_id)
        now = datetime.now().isoformat()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        self._db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", tuple(values))
        if "role" in updates:
            role_row = self._db.fetchone("SELECT id FROM roles WHERE name = ?", (updates["role"],))
            if role_row:
                self._db.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
                self._db.execute(
                    "INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (?, ?, ?)",
                    (user_id, role_row["id"], now),
                )
        self._db.commit()
        return self._load_user_full(user_id)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._load_user_full(user_id)

    def get_all_users(self) -> list[dict[str, Any]]:
        rows = self._db.fetchall("SELECT id FROM users WHERE is_active = 1 ORDER BY name")
        return [self._load_user_full(r["id"]) for r in rows]

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT id FROM users WHERE username = ?", (username,))
        if not row:
            return None
        return self._load_user_full(row["id"])

    def has_permission(self, user_id: str, permission_name: str) -> bool:
        user = self._load_user_full(user_id)
        if not user:
            return False
        return permission_name in user.get("permissions", []) or "system.manage" in user.get("permissions", [])

    def check_access(self, user_id: str, module: str, action: str) -> bool:
        perm_name = f"{module}.{action}"
        return self.has_permission(user_id, perm_name)

    def _load_user_full(self, user_id: str) -> dict[str, Any] | None:
        user = self._db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            return None
        result = dict(user)
        role_rows = self._db.fetchall(
            "SELECT r.name, r.display_name FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = ?",
            (user_id,),
        )
        result["roles"] = [r["name"] for r in role_rows]
        result["role_display_names"] = [r["display_name"] for r in role_rows]
        perm_rows = self._db.fetchall(
            "SELECT p.name FROM role_permissions rp JOIN permissions p ON rp.permission_id = p.id JOIN user_roles ur ON rp.role_id = ur.role_id WHERE ur.user_id = ?",
            (user_id,),
        )
        result["permissions"] = [p["name"] for p in perm_rows]
        return result

    def get_all_roles(self) -> list[dict[str, Any]]:
        rows = self._db.fetchall("SELECT * FROM roles WHERE is_active = 1 ORDER BY name")
        return [dict(r) for r in rows]

    def get_all_permissions(self) -> list[dict[str, Any]]:
        rows = self._db.fetchall("SELECT * FROM permissions ORDER BY module, action")
        return [dict(r) for r in rows]

    def get_role_permissions(self, role_id: str) -> list[str]:
        rows = self._db.fetchall(
            "SELECT p.name FROM role_permissions rp JOIN permissions p ON rp.permission_id = p.id WHERE rp.role_id = ?",
            (role_id,),
        )
        return [r["name"] for r in rows]

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()
