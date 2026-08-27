"""Core — Metrics Collector. Registra métricas de uso en base de datos."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from hub.infrastructure.database import Database

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Recopila y consulta métricas de uso de la plataforma."""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db

    def record_execution(
        self,
        plugin_id: str,
        user_id: str = "default",
        success: bool = True,
        duration_seconds: float = 0.0,
        output_summary: str = "",
        error_message: str = "",
    ) -> None:
        now = datetime.now().isoformat()
        status = "exito" if success else "error"
        if self._db:
            self._db.execute(
                """INSERT INTO executions (plugin_id, user_id, status, started_at, finished_at, duration_seconds, output_summary, error_message, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (plugin_id, user_id, status, now, now, duration_seconds, output_summary, error_message, now, now),
            )
            self._db.commit()
        self._update_daily_metric("executions", 1.0, plugin_id)
        if not success:
            self._update_daily_metric("execution_errors", 1.0, plugin_id)
        logger.info("Métrica ejecución: plugin=%s éxito=%s duración=%.1fs", plugin_id, success, duration_seconds)

    def record_search(self, query: str, results_count: int, user_id: str = "default", latency_ms: float = 0.0) -> None:
        now = datetime.now().isoformat()
        if self._db:
            self._db.execute(
                """INSERT INTO searches (query, results_count, user_id, searched_at, latency_ms)
                   VALUES (?, ?, ?, ?, ?)""",
                (query, results_count, user_id, now, latency_ms),
            )
            self._db.commit()
        self._update_daily_metric("searches", 1.0)

    def record_notification_sent(self, notification_type: str, user_id: str) -> None:
        self._update_daily_metric("notifications_sent", 1.0, notification_type)

    def record_request_created(self, request_type: str) -> None:
        self._update_daily_metric("requests_created", 1.0, request_type)

    def record_post_created(self, user_id: str) -> None:
        self._update_daily_metric("posts_created", 1.0)

    def record_knowledge_published(self) -> None:
        self._update_daily_metric("knowledge_published", 1.0)

    def record_user_login(self, user_id: str) -> None:
        self._update_daily_metric("user_logins", 1.0)

    def get_stats(self) -> dict[str, Any]:
        if not self._db:
            return {"total_executions": 0, "successful_executions": 0, "failed_executions": 0, "total_searches": 0, "unique_plugins_used": 0}
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM executions")
        successful = self._db.fetchone("SELECT COUNT(*) as cnt FROM executions WHERE status = 'exito'")
        searches = self._db.fetchone("SELECT COUNT(*) as cnt FROM searches")
        plugins = self._db.fetchone("SELECT COUNT(DISTINCT plugin_id) as cnt FROM executions")
        users = self._db.fetchone("SELECT COUNT(*) as cnt FROM users WHERE is_active = 1")
        projects = self._db.fetchone("SELECT COUNT(*) as cnt FROM projects")
        requests = self._db.fetchone("SELECT COUNT(*) as cnt FROM requests")
        articles = self._db.fetchone("SELECT COUNT(*) as cnt FROM knowledge_articles")
        posts = self._db.fetchone("SELECT COUNT(*) as cnt FROM posts")
        incidents = self._db.fetchone("SELECT COUNT(*) as cnt FROM incidents WHERE status IN ('abierto', 'en_progreso')")
        pending = self._db.fetchone("SELECT COUNT(*) as cnt FROM requests WHERE status IN ('enviada', 'en_revision')")
        return {
            "total_executions": total["cnt"] if total else 0,
            "successful_executions": successful["cnt"] if successful else 0,
            "failed_executions": (total["cnt"] if total else 0) - (successful["cnt"] if successful else 0),
            "total_searches": searches["cnt"] if searches else 0,
            "unique_plugins_used": plugins["cnt"] if plugins else 0,
            "total_users": users["cnt"] if users else 0,
            "total_projects": projects["cnt"] if projects else 0,
            "total_requests": requests["cnt"] if requests else 0,
            "total_articles": articles["cnt"] if articles else 0,
            "total_posts": posts["cnt"] if posts else 0,
            "open_incidents": incidents["cnt"] if incidents else 0,
            "pending_requests": pending["cnt"] if pending else 0,
        }

    def get_plugin_stats(self, plugin_id: str) -> dict[str, Any]:
        if not self._db:
            return {"total_executions": 0, "successful": 0, "failed": 0, "total_duration_seconds": 0, "avg_duration_seconds": 0}
        total = self._db.fetchone("SELECT COUNT(*) as cnt FROM executions WHERE plugin_id = ?", (plugin_id,))
        successful = self._db.fetchone("SELECT COUNT(*) as cnt FROM executions WHERE plugin_id = ? AND status = 'exito'", (plugin_id,))
        duration = self._db.fetchone("SELECT COALESCE(SUM(duration_seconds), 0) as total, COALESCE(AVG(duration_seconds), 0) as avg FROM executions WHERE plugin_id = ?", (plugin_id,))
        return {
            "total_executions": total["cnt"] if total else 0,
            "successful": successful["cnt"] if successful else 0,
            "failed": (total["cnt"] if total else 0) - (successful["cnt"] if successful else 0),
            "total_duration_seconds": duration["total"] if duration else 0,
            "avg_duration_seconds": duration["avg"] if duration else 0,
        }

    def get_daily_trend(self, metric_name: str, days: int = 30) -> list[dict[str, Any]]:
        if not self._db:
            return []
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self._db.fetchall(
            "SELECT date, SUM(metric_value) as value FROM metrics_daily WHERE metric_name = ? AND date >= ? GROUP BY date ORDER BY date",
            (metric_name, start_date),
        )
        return [{"date": r["date"], "value": r["value"]} for r in rows]

    def get_executions_by_day(self, days: int = 30) -> list[dict[str, Any]]:
        return self.get_daily_trend("executions", days)

    def get_executions_by_status(self) -> dict[str, int]:
        if not self._db:
            return {}
        rows = self._db.fetchall("SELECT status, COUNT(*) as cnt FROM executions GROUP BY status")
        return {r["status"]: r["cnt"] for r in rows}

    def get_search_trend(self, days: int = 30) -> list[dict[str, Any]]:
        return self.get_daily_trend("searches", days)

    def get_top_plugins(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self._db:
            return []
        rows = self._db.fetchall(
            "SELECT plugin_id, COUNT(*) as exec_count, SUM(CASE WHEN status = 'exito' THEN 1 ELSE 0 END) as success_count FROM executions GROUP BY plugin_id ORDER BY exec_count DESC LIMIT ?",
            (limit,),
        )
        return [{"plugin_id": r["plugin_id"], "executions": r["exec_count"], "success_rate": r["success_count"] / max(r["exec_count"], 1)} for r in rows]

    def _update_daily_metric(self, metric_name: str, value: float, dimension: str = "") -> None:
        if not self._db:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().isoformat()
        self._db.execute(
            """INSERT INTO metrics_daily (date, metric_name, metric_value, dimension, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(date, metric_name, dimension) DO UPDATE SET metric_value = metric_value + ?""",
            (today, metric_name, value, dimension, now, value),
        )
        self._db.commit()
