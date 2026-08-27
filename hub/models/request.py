"""Modelos — Requests / Issues / Ideas."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime


class RequestType(enum.Enum):
    HELP = "ayuda"
    ISSUE = "problema"
    IDEA = "idea"


class RequestStatus(enum.Enum):
    NUEVA = "nueva"
    EN_REVISION = "en_revision"
    EN_DESARROLLO = "en_desarrollo"
    EN_PRUEBAS = "en_pruebas"
    RESUELTA = "resuelta"
    CERRADA = "cerrada"


class RequestPriority(enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


@dataclass
class Request:
    id: int = 0
    user_id: str = ""
    user_name: str = ""
    area: str = ""
    request_type: RequestType = RequestType.HELP
    title: str = ""
    description: str = ""
    frequency: str = ""
    time_per_execution: str = ""
    people_involved: str = ""
    tools_used: str = ""
    steps: str = ""
    current_problems: str = ""
    priority: RequestPriority = RequestPriority.MEDIA
    status: RequestStatus = RequestStatus.NUEVA
    owner: str = ""
    related_plugin_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    comments: list[str] = field(default_factory=list)
    solution: str = ""


@dataclass
class AutomationScore:
    weekly_hours: float = 0.0
    monthly_hours: float = 0.0
    yearly_hours: float = 0.0
    people_involved: int = 1
    complexity: str = "media"
    classification: str = "media"
    score: float = 0.0

    def calculate(self) -> None:
        self.monthly_hours = self.weekly_hours * 4
        self.yearly_hours = self.weekly_hours * 52
        impact = min(self.yearly_hours / 100, 20)
        people_factor = min(self.people_involved / 3, 3)
        complexity_map = {"baja": 0.5, "media": 1.0, "alta": 1.5}
        complexity_factor = complexity_map.get(self.complexity, 1.0)
        self.score = impact * people_factor * complexity_factor
        if self.score >= 3:
            self.classification = "alta"
        elif self.score >= 1:
            self.classification = "media"
        else:
            self.classification = "baja"
