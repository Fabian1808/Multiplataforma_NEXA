"""Modelos de datos — Proyectos y Tareas."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ProjectStatus(enum.Enum):
    PLANEACION = "planeacion"
    EN_PROGRESO = "en_progreso"
    EN_PAUSA = "en_pausa"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


class TaskStatus(enum.Enum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    EN_REVISION = "en_revision"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


class Priority(enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


@dataclass
class Project:
    id: str = ""
    name: str = ""
    description: str = ""
    status: str = "planeacion"
    priority: str = "media"
    owner_id: str = ""
    department_id: str = ""
    start_date: str = ""
    end_date: str = ""
    progress: int = 0
    tags: str = ""
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""
    task_count: int = 0
    completed_tasks: int = 0

    @property
    def progress_label(self) -> str:
        labels = {
            "planeacion": "Planeación",
            "en_progreso": "En Progreso",
            "en_pausa": "En Pausa",
            "completado": "Completado",
            "cancelado": "Cancelado",
        }
        return labels.get(self.status, self.status)

    @property
    def priority_label(self) -> str:
        labels = {"baja": "Baja", "media": "Media", "alta": "Alta", "critica": "Crítica"}
        return labels.get(self.priority, self.priority)


@dataclass
class Task:
    id: str = ""
    project_id: str = ""
    title: str = ""
    description: str = ""
    status: str = "pendiente"
    priority: str = "media"
    assignee_id: str = ""
    due_date: str = ""
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""
    assignee_name: str = ""

    @property
    def status_label(self) -> str:
        labels = {
            "pendiente": "Pendiente", "en_progreso": "En Progreso",
            "en_revision": "En Revisión", "completada": "Completada",
            "cancelada": "Cancelada",
        }
        return labels.get(self.status, self.status)
