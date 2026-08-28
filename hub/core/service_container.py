"""Core — Service Container. Inyección de dependencias centralizada."""

from __future__ import annotations

import logging
from typing import Any

from hub.infrastructure.database import Database
from hub.core.auth_service import AuthService
from hub.core.audit_service import AuditService
from hub.core.catalog_service import CatalogService
from hub.core.config_service import ConfigService
from hub.core.feed_service import FeedService
from hub.core.health_check import HealthCheckService
from hub.core.knowledge_service import KnowledgeService
from hub.core.metrics_collector import MetricsCollector
from hub.core.notification_service import NotificationService
from hub.core.opportunity_tracker import OpportunityTracker
from hub.core.plugin_registry import PluginRegistry
from hub.core.project_service import ProjectService
from hub.core.request_service import RequestService
from hub.core.search_engine import SearchEngine
from hub.core.workflow_engine import WorkflowEngine
from hub.core.report_service import ReportService
from hub.core.app_state_service import AppStateService
from hub.core.favorites_service import FavoritesService
from hub.core.app_launcher_service import AppLauncherService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Contenedor centralizado de servicios con inyección de dependencias."""

    def __init__(self) -> None:
        self._db = Database()
        self.db = self._db
        self.auth = AuthService(self._db)
        self.audit = AuditService(self._db)
        self.config = ConfigService()
        self.registry = PluginRegistry()
        try:
            self.registry.discover()
        except Exception:
            logger.exception("Error descubriendo plugins al iniciar")
        self.catalog = CatalogService(self.registry)
        self.search = SearchEngine(self._db)
        self.metrics = MetricsCollector(self._db)
        self.knowledge = KnowledgeService(self._db)
        self.requests = RequestService(self._db)
        self.notifications = NotificationService(self._db)
        self.health = HealthCheckService(self._db)
        self.opportunities = OpportunityTracker(self._db)
        self.feed = FeedService(self._db)
        self.projects = ProjectService(self._db)
        self.workflow = WorkflowEngine(self._db)
        self.reports = ReportService(self._db)
        self.app_states = AppStateService(self._db)
        self.favorites = FavoritesService(self._db)
        self.app_launcher = AppLauncherService()
        self.current_user: dict[str, Any] | None = None
        self._ensure_demo_user()
        self._seed_demo_data()

    def _ensure_demo_user(self) -> None:
        existing = self.auth.get_user_by_username("fabian")
        if existing:
            self.current_user = existing
            return
        user = self.auth.create_user(
            username="fabian",
            name="Fabian",
            email="fabian@nexa.com",
            password="1234",
            area="Contratos",
            role="administrador",
            created_by="system",
        )
        self.current_user = user
        self.audit.log_login(user["id"], "demo")
        logger.info("Usuario demo creado: fabian (password: 1234)")

    def _seed_demo_data(self) -> None:
        try:
            from hub.demo_data import seed_demo_data
            seed_demo_data(self._db)
        except Exception:
            logger.exception("Error seeding demo data")

        try:
            from datetime import datetime
            import random

            _PLUGIN_IDS = ["horas_extras", "sap_automation", "sap_module", "excel_macros", "email_automation",
                           "report_generator", "data_validator", "backup_tool", "scheduler", "document_parser"]

            existing_users = self._db.fetchall("SELECT id FROM users")
            if not existing_users:
                return

            existing_reports = self._db.fetchone("SELECT COUNT(*) as cnt FROM reports")
            if existing_reports and existing_reports["cnt"] > 0:
                logger.info("Demo data extendida ya existe, saltando seed")
                return

            for plugin_id in _PLUGIN_IDS:
                self.app_states.get_state(plugin_id)

            demo_user = self.current_user
            if demo_user:
                for plugin_id in random.sample(_PLUGIN_IDS, min(3, len(_PLUGIN_IDS))):
                    self.app_states.record_execution(plugin_id, demo_user["id"], success=True)

                for plugin_id in random.sample(_PLUGIN_IDS, min(2, len(_PLUGIN_IDS))):
                    self.app_states.record_failure(
                        plugin_id, demo_user["id"],
                        error_type="timeout",
                        error_message="Tiempo de ejecución excedido",
                        severity="media"
                    )

                for i in range(5):
                    self.reports.create(
                        name=f"Reporte Demo {i+1}",
                        plugin_id=_PLUGIN_IDS[i % len(_PLUGIN_IDS)],
                        user_id=demo_user["id"],
                        report_type=random.choice(["general", "ejecutivo", "detallado"]),
                        records_count=random.randint(50, 500),
                        result_summary=f"Resumen del reporte {i+1}",
                        created_by=demo_user["id"]
                    )

                for plugin_id in random.sample(_PLUGIN_IDS, min(4, len(_PLUGIN_IDS))):
                    self.favorites.add_favorite(demo_user["id"], plugin_id)

            logger.info("Demo data extendida generada (app_states, reports, favorites)")
        except Exception:
            logger.exception("Error generando demo data extendida")

    @property
    def user_id(self) -> str:
        if self.current_user:
            return self.current_user["id"]
        return "default"

    @property
    def user_name(self) -> str:
        if self.current_user:
            return self.current_user.get("name", "Usuario")
        return "Usuario"

    @property
    def user_area(self) -> str:
        if self.current_user:
            return self.current_user.get("area", "")
        return ""

    @property
    def is_admin(self) -> bool:
        if self.current_user:
            return "administrador" in self.current_user.get("roles", [])
        return False

    def close(self) -> None:
        try:
            self._db.close()
        except Exception:
            pass
        try:
            self.search.close()
        except Exception:
            pass
