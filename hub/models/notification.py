"""Modelos de datos — Notificaciones y Solicitudes."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class NotificationType(enum.Enum):
    REQUEST_CREATED = "request_created"
    REQUEST_ASSIGNED = "request_assigned"
    REQUEST_STATUS_CHANGED = "request_status_changed"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    COMMENT_ADDED = "comment_added"
    MENTION = "mention"
    LIKE_RECEIVED = "like_received"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    PROJECT_UPDATED = "project_updated"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_RESOLVED = "incident_resolved"
    HEALTH_CHECK_ALERT = "health_check_alert"
    SYSTEM_UPDATE = "system_update"
    WELCOME = "welcome"


class RequestType(enum.Enum):
    HELP = "ayuda"
    IDEA = "idea"
    ISSUE = "incidente"


class RequestStatus(enum.Enum):
    ENVIADA = "enviada"
    EN_REVISION = "en_revision"
    APROBADA = "aprobada"
    EN_DESARROLLO = "en_desarrollo"
    PRUEBAS = "pruebas"
    PUBLICADA = "publicada"
    RECHAZADA = "rechazada"
    CERRADA = "cerrada"


class WorkflowState(enum.Enum):
    NUEVA = "nueva"
    RECIBIDA = "recibida"
    EN_EVALUACION = "en_evaluacion"
    ASIGNADA = "asignada"
    EN_PROCESO = "en_proceso"
    EN_REVISION = "en_revision"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    COMPLETADA = "completada"
    CERRADA = "cerrada"


@dataclass
class Notification:
    id: int = 0
    user_id: str = ""
    notification_type: str = ""
    title: str = ""
    message: str = ""
    action_url: str = ""
    channel: str = "in_app"
    priority: str = "normal"
    related_entity_type: str = ""
    related_entity_id: str = ""
    read: bool = False
    read_at: str = ""
    created_at: str = ""
    created_by: str = ""

    @property
    def type_label(self) -> str:
        labels = {
            "request_created": "Solicitud Creada",
            "request_assigned": "Solicitud Asignada",
            "request_status_changed": "Estado Cambiado",
            "request_approved": "Solicitud Aprobada",
            "request_rejected": "Solicitud Rechazada",
            "comment_added": "Nuevo Comentario",
            "mention": "Mención",
            "like_received": "Like Recibido",
            "task_assigned": "Tarea Asignada",
            "task_completed": "Tarea Completada",
            "project_updated": "Proyecto Actualizado",
            "incident_created": "Incidente Creado",
            "incident_resolved": "Incidente Resuelto",
            "health_check_alert": "Alerta de Salud",
            "system_update": "Actualización del Sistema",
            "welcome": "Bienvenida",
        }
        return labels.get(self.notification_type, self.notification_type)


@dataclass
class Request:
    id: int = 0
    user_id: str = ""
    request_type: str = "ayuda"
    title: str = ""
    description: str = ""
    area: str = ""
    priority: str = "media"
    status: str = "enviada"
    assigned_to: str = ""
    workflow_state: str = "nueva"
    frequency: str = ""
    tools_used: str = ""
    steps: str = ""
    resolution_notes: str = ""
    resolved_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""

    @property
    def type_label(self) -> str:
        labels = {"ayuda": "Ayuda", "idea": "Idea/Automatización", "incidente": "Incidente"}
        return labels.get(self.request_type, self.request_type)

    @property
    def status_label(self) -> str:
        labels = {
            "enviada": "Enviada", "en_revision": "En Revisión",
            "aprobada": "Aprobada", "en_desarrollo": "En Desarrollo",
            "pruebas": "Pruebas", "publicada": "Publicada",
            "rechazada": "Rechazada", "cerrada": "Cerrada",
        }
        return labels.get(self.status, self.status)

    @property
    def workflow_label(self) -> str:
        labels = {
            "nueva": "Nueva", "recibida": "Recibida", "en_evaluacion": "En Evaluación",
            "asignada": "Asignada", "en_proceso": "En Proceso",
            "en_revision": "En Revisión", "aprobada": "Aprobada",
            "rechazada": "Rechazada", "completada": "Completada", "cerrada": "Cerrada",
        }
        return labels.get(self.workflow_state, self.workflow_state)
