"""Core — Health Check Service con historial."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from hub.infrastructure.database import Database
from hub.models.plugin import PluginDescriptor

logger = logging.getLogger(__name__)


class HealthStatus:
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class HealthReport:
    def __init__(self, plugin_id: str, plugin_name: str, status: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.plugin_id = plugin_id
        self.plugin_name = plugin_name
        self.status = status
        self.message = message
        self.details = details or {}


class HealthCheckService:
    """Servicio de health check con persistencia de historial."""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db

    def check_all(self, plugins: list[PluginDescriptor]) -> list[HealthReport]:
        reports = []
        for p in plugins:
            report = self.check_plugin(p)
            reports.append(report)
        self._save_reports(reports)
        return reports

    def check_plugin(self, plugin: PluginDescriptor) -> HealthReport:
        issues = []
        if not plugin.version:
            issues.append("Sin versión definida")
        if not plugin.owner:
            issues.append("Sin autor definido")
        if not plugin.tags:
            issues.append("Sin etiquetas")
        if plugin.status.value == "error":
            issues.append("Plugin en estado de error")
        if plugin.execution_count > 0 and hasattr(plugin, 'error_count') and plugin.error_count > 0:
            rate = plugin.error_count / plugin.execution_count
            if rate > 0.3:
                issues.append(f"Tasa de error alta: {rate:.0%}")
        if issues:
            status = HealthStatus.WARNING if len(issues) <= 2 else HealthStatus.ERROR
            message = "; ".join(issues)
        else:
            status = HealthStatus.OK
            message = "Plugin operativo"
        return HealthReport(plugin.id, plugin.name, status, message, {"issues": issues})

    def _save_reports(self, reports: list[HealthReport]) -> None:
        if not self._db:
            return
        now = datetime.now().isoformat()
        for r in reports:
            self._db.execute(
                """INSERT INTO metrics_daily (date, metric_name, metric_value, dimension, created_at)
                   VALUES (?, 'health_status', ?, ?, ?)
                   ON CONFLICT(date, metric_name, dimension) DO UPDATE SET metric_value = ?""",
                (now[:10], 1.0 if r.status == HealthStatus.OK else 0.0, r.plugin_id, now, 1.0 if r.status == HealthStatus.OK else 0.0),
            )
        self._db.commit()

    def get_history(self, plugin_id: str | None = None, days: int = 30) -> list[dict[str, Any]]:
        if not self._db:
            return []
        from datetime import timedelta
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        if plugin_id:
            rows = self._db.fetchall(
                "SELECT * FROM metrics_daily WHERE metric_name = 'health_status' AND dimension = ? AND date >= ? ORDER BY date",
                (plugin_id, start),
            )
        else:
            rows = self._db.fetchall(
                "SELECT * FROM metrics_daily WHERE metric_name = 'health_status' AND date >= ? ORDER BY date",
                (start,),
            )
        return [dict(r) for r in rows]

    def get_health_summary(self) -> dict[str, Any]:
        if not self._db:
            return {"total_checks": 0, "healthy": 0, "unhealthy": 0}
        today = datetime.now().strftime("%Y-%m-%d")
        total = self._db.fetchone(
            "SELECT COUNT(DISTINCT dimension) as cnt FROM metrics_daily WHERE metric_name = 'health_status' AND date = ?",
            (today,),
        )
        healthy = self._db.fetchone(
            "SELECT COUNT(*) as cnt FROM metrics_daily WHERE metric_name = 'health_status' AND metric_value = 1.0 AND date = ?",
            (today,),
        )
        return {
            "total_plugins": total["cnt"] if total else 0,
            "healthy": healthy["cnt"] if healthy else 0,
            "unhealthy": (total["cnt"] if total else 0) - (healthy["cnt"] if healthy else 0),
        }
