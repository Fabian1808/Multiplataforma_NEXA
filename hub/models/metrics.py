"""Modelos de datos — Métricas, Incidentes, Integraciones, SLA."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class IncidentSeverity(enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class IncidentStatus(enum.Enum):
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"


class IntegrationStatus(enum.Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ERROR = "error"
    CONFIGURANDO = "configurando"


@dataclass
class Incident:
    id: int = 0
    title: str = ""
    description: str = ""
    severity: str = "media"
    status: str = "abierto"
    reporter_id: str = ""
    assignee_id: str = ""
    related_plugin_id: str = ""
    related_request_id: int = 0
    resolution: str = ""
    resolved_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""

    @property
    def severity_label(self) -> str:
        labels = {"baja": "Baja", "media": "Media", "alta": "Alta", "critica": "Crítica"}
        return labels.get(self.severity, self.severity)

    @property
    def status_label(self) -> str:
        labels = {"abierto": "Abierto", "en_progreso": "En Progreso", "resuelto": "Resuelto", "cerrado": "Cerrado"}
        return labels.get(self.status, self.status)


@dataclass
class Integration:
    id: str = ""
    name: str = ""
    integration_type: str = ""
    status: str = "inactivo"
    config: str = ""
    description: str = ""
    last_sync_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""
    updated_by: str = ""

    @property
    def status_label(self) -> str:
        labels = {"activo": "Activo", "inactivo": "Inactivo", "error": "Error", "configurando": "Configurando"}
        return labels.get(self.status, self.status)


@dataclass
class SLAPolicy:
    id: str = ""
    name: str = ""
    priority: str = ""
    response_hours: int = 24
    resolution_hours: int = 72
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DailyMetric:
    id: int = 0
    date: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    dimension: str = ""
    created_at: str = ""


@dataclass
class MetricSnapshot:
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_searches: int = 0
    unique_plugins_used: int = 0
    total_users: int = 0
    total_projects: int = 0
    total_requests: int = 0
    total_articles: int = 0
    total_posts: int = 0
    open_incidents: int = 0
    pending_requests: int = 0
