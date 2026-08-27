"""Modelos de datos — Usuario, Rol, Departamento y RBAC."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class PermissionAction(enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    APPROVE = "approve"
    ASSIGN = "assign"
    EXPORT = "export"


class PermissionModule(enum.Enum):
    USERS = "users"
    PROJECTS = "projects"
    REQUESTS = "requests"
    KNOWLEDGE = "knowledge"
    NOTIFICATIONS = "notifications"
    AUDIT = "audit"
    PLUGINS = "plugins"
    DEPARTMENTS = "departments"
    FEED = "feed"
    REPORTS = "reports"
    INTEGRATIONS = "integrations"
    SYSTEM = "system"


@dataclass
class Permission:
    id: str
    name: str
    module: str
    action: str
    description: str = ""
    created_at: str = ""


@dataclass
class Role:
    id: str
    name: str
    display_name: str
    description: str = ""
    is_active: bool = True
    permissions: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Department:
    id: str
    name: str
    code: str
    parent_id: str = ""
    manager_id: str = ""
    description: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""


@dataclass
class User:
    id: str
    username: str
    name: str
    email: str = ""
    password_hash: str = ""
    avatar_url: str = ""
    area: str = ""
    department_id: str = ""
    manager_id: str = ""
    role: str = "usuario"
    is_active: bool = True
    last_login: str = ""
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.name or self.username

    def has_permission(self, perm_name: str) -> bool:
        return perm_name in self.permissions or "system.manage" in self.permissions

    def has_role(self, role_name: str) -> bool:
        return role_name in self.roles

    def is_admin(self) -> bool:
        return "administrador" in self.roles or self.has_permission("system.manage")


@dataclass
class Session:
    id: str
    user_id: str
    token: str
    ip_address: str = ""
    user_agent: str = ""
    expires_at: str = ""
    created_at: str = ""
    is_active: bool = True
