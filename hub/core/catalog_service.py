"""Core — Catalog Service."""

from __future__ import annotations

import logging
from typing import Any

from hub.core.plugin_registry import PluginRegistry
from hub.models.plugin import PluginDescriptor

logger = logging.getLogger(__name__)


class CatalogService:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def get_all(self) -> list[PluginDescriptor]:
        return list(self._registry.plugins.values())

    def get_by_category(self, category: str) -> list[PluginDescriptor]:
        return [p for p in self._registry.plugins.values() if p.category.value == category]

    def get_popular(self, limit: int = 10) -> list[PluginDescriptor]:
        return sorted(self.get_all(), key=lambda p: p.execution_count, reverse=True)[:limit]

    def record_rating(self, plugin_id: str, user_id: str, helpful: int, time_saved: int, comment: str = "") -> None:
        plugin = self._registry.get(plugin_id)
        if plugin:
            plugin.execution_count += 1

    def get_stats(self) -> dict[str, Any]:
        all_p = self.get_all()
        return {
            "total": len(all_p),
            "active": sum(1 for p in all_p if p.status.value == "active"),
            "categories": len(set(p.category.value for p in all_p)),
        }
