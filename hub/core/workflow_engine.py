"""Core — Workflow Engine. Máquina de estados para solicitudes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)

WORKFLOW_TRANSITIONS: dict[str, list[str]] = {
    "nueva": ["recibida", "rechazada"],
    "recibida": ["en_evaluacion", "rechazada"],
    "en_evaluacion": ["asignada", "rechazada"],
    "asignada": ["en_proceso", "rechazada"],
    "en_proceso": ["en_revision"],
    "en_revision": ["aprobada", "en_proceso", "rechazada"],
    "aprobada": ["completada"],
    "rechazada": [],
    "completada": ["cerrada"],
    "cerrada": [],
}

STATUS_MAP = {
    "nueva": "enviada",
    "recibida": "en_revision",
    "en_evaluacion": "en_revision",
    "asignada": "en_desarrollo",
    "en_proceso": "en_desarrollo",
    "en_revision": "pruebas",
    "aprobada": "publicada",
    "rechazada": "rechazada",
    "completada": "publicada",
    "cerrada": "cerrada",
}


class WorkflowEngine:
    """Motor de workflow para gestionar el ciclo de vida de solicitudes."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def get_available_transitions(self, current_state: str) -> list[str]:
        return WORKFLOW_TRANSITIONS.get(current_state, [])

    def can_transition(self, current_state: str, target_state: str) -> bool:
        return target_state in WORKFLOW_TRANSITIONS.get(current_state, [])

    def transition(self, request_id: int, target_state: str, user_id: str, notes: str = "") -> dict[str, Any] | None:
        row = self._db.fetchone("SELECT * FROM requests WHERE id = ?", (request_id,))
        if not row:
            return None
        current = row["workflow_state"]
        if not self.can_transition(current, target_state):
            logger.warning("Transición inválida: %s -> %s para request %d", current, target_state, request_id)
            return None
        now = datetime.now().isoformat()
        new_status = STATUS_MAP.get(target_state, row["status"])
        update_fields: dict[str, Any] = {
            "workflow_state": target_state,
            "status": new_status,
            "updated_at": now,
            "updated_by": user_id,
        }
        if notes:
            update_fields["resolution_notes"] = notes
        if target_state in ("aprobada", "completada", "cerrada"):
            update_fields["resolved_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = list(update_fields.values()) + [request_id]
        self._db.execute(f"UPDATE requests SET {set_clause} WHERE id = ?", tuple(values))
        self._db.commit()
        logger.info("Workflow: request %d %s -> %s por %s", request_id, current, target_state, user_id)
        return dict(row) | update_fields

    def assign(self, request_id: int, assignee_id: str, assigned_by: str) -> bool:
        now = datetime.now().isoformat()
        self._db.execute(
            "UPDATE requests SET assigned_to = ?, workflow_state = 'asignada', status = 'en_desarrollo', updated_at = ?, updated_by = ? WHERE id = ?",
            (assignee_id, now, assigned_by, request_id),
        )
        self._db.commit()
        return True

    def get_workflow_history(self, request_id: int) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM audit_log WHERE entity_type = 'request' AND entity_id = ? ORDER BY created_at",
            (str(request_id),),
        )
        return [dict(r) for r in rows]

    def get_requests_by_state(self, state: str) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM requests WHERE workflow_state = ? ORDER BY created_at DESC",
            (state,),
        )
        return [dict(r) for r in rows]

    def get_board_data(self) -> dict[str, list[dict[str, Any]]]:
        board: dict[str, list[dict[str, Any]]] = {}
        for state in WORKFLOW_TRANSITIONS:
            board[state] = self.get_requests_by_state(state)
        return board
