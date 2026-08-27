"""Core — Project Service. CRUD de proyectos y tareas."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class ProjectService:
    """Servicio de gestión de proyectos de automatización."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create_project(self, name: str, description: str = "", status: str = "planeacion",
                       priority: str = "media", owner_id: str = "", department_id: str = "",
                       start_date: str = "", end_date: str = "", tags: str = "",
                       created_by: str = "") -> str:
        now = datetime.now().isoformat()
        project_id = f"prj_{secrets.token_hex(8)}"
        self._db.execute(
            """INSERT INTO projects (id, name, description, status, priority, owner_id, department_id, start_date, end_date, tags, created_at, updated_at, created_by, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, name, description, status, priority, owner_id, department_id, start_date, end_date, tags, now, now, created_by, created_by),
        )
        self._db.commit()
        return project_id

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT * FROM projects WHERE id = ?", (project_id,))
        if not row:
            return None
        result = dict(row)
        tasks = self._db.fetchone("SELECT COUNT(*) as cnt FROM tasks WHERE project_id = ?", (project_id,))
        completed = self._db.fetchone("SELECT COUNT(*) as cnt FROM tasks WHERE project_id = ? AND status = 'completada'", (project_id,))
        result["task_count"] = tasks["cnt"] if tasks else 0
        result["completed_tasks"] = completed["cnt"] if completed else 0
        return result

    def get_all_projects(self, status: str | None = None, owner_id: str | None = None,
                         department_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if owner_id:
            conditions.append("owner_id = ?")
            params.append(owner_id)
        if department_id:
            conditions.append("department_id = ?")
            params.append(department_id)
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self._db.fetchall(
            f"SELECT * FROM projects WHERE {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params) + (limit,),
        )
        results = []
        for row in rows:
            r = dict(row)
            tasks = self._db.fetchone("SELECT COUNT(*) as cnt FROM tasks WHERE project_id = ?", (row["id"],))
            completed = self._db.fetchone("SELECT COUNT(*) as cnt FROM tasks WHERE project_id = ? AND status = 'completada'", (row["id"],))
            r["task_count"] = tasks["cnt"] if tasks else 0
            r["completed_tasks"] = completed["cnt"] if completed else 0
            results.append(r)
        return results

    def update_project(self, project_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"name", "description", "status", "priority", "owner_id", "department_id",
                    "start_date", "end_date", "progress", "tags"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_project(project_id)
        now = datetime.now().isoformat()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]
        self._db.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", tuple(values))
        self._db.commit()
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        self._db.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        self._db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self._db.commit()
        return True

    def create_task(self, project_id: str, title: str, description: str = "",
                    status: str = "pendiente", priority: str = "media",
                    assignee_id: str = "", due_date: str = "",
                    estimated_hours: float = 0.0, created_by: str = "") -> str:
        now = datetime.now().isoformat()
        task_id = f"tsk_{secrets.token_hex(8)}"
        self._db.execute(
            """INSERT INTO tasks (id, project_id, title, description, status, priority, assignee_id, due_date, estimated_hours, created_at, updated_at, created_by, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, project_id, title, description, status, priority, assignee_id, due_date, estimated_hours, now, now, created_by, created_by),
        )
        self._db.commit()
        return task_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not row:
            return None
        result = dict(row)
        if row["assignee_id"]:
            user = self._db.fetchone("SELECT name FROM users WHERE id = ?", (row["assignee_id"],))
            if user:
                result["assignee_name"] = user["name"]
        return result

    def get_project_tasks(self, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self._db.fetchall(
                "SELECT * FROM tasks WHERE project_id = ? AND status = ? ORDER BY created_at",
                (project_id, status),
            )
        else:
            rows = self._db.fetchall(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at",
                (project_id,),
            )
        results = []
        for row in rows:
            r = dict(row)
            if row["assignee_id"]:
                user = self._db.fetchone("SELECT name FROM users WHERE id = ?", (row["assignee_id"],))
                if user:
                    r["assignee_name"] = user["name"]
            results.append(r)
        return results

    def update_task(self, task_id: str, **fields: Any) -> dict[str, Any] | None:
        allowed = {"title", "description", "status", "priority", "assignee_id", "due_date",
                    "estimated_hours", "actual_hours"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_task(task_id)
        now = datetime.now().isoformat()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]
        self._db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", tuple(values))
        self._db.commit()
        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._db.commit()
        return True

    def get_stats(self) -> dict[str, Any]:
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM projects")
        by_status = self._db.fetchall("SELECT status, COUNT(*) as cnt FROM projects GROUP BY status")
        total_tasks = self._db.fetchone("SELECT COUNT(*) as cnt FROM tasks")
        return {
            "total_projects": total["cnt"] if total else 0,
            "by_status": {r["status"]: r["cnt"] for r in by_status},
            "total_tasks": total_tasks["cnt"] if total_tasks else 0,
        }
