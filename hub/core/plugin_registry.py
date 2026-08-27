"""Core — Plugin Registry. Auto-descubre y registra plugins desde plugins/."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Protocol

from hub.models.plugin import PluginCategory, PluginDescriptor, PluginStatus

logger = logging.getLogger(__name__)

_PLUGINS_DIR_NAME = "plugins"


class PluginWidgetFactory(Protocol):
    """Interfaz que toda GUI de plugin debe implementar."""

    def create_widget(self, parent: Any = None) -> Any: ...


class PluginRegistry:
    """Registra y gestiona plugins del Hub."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self._plugins_dir = self._base_dir / _PLUGINS_DIR_NAME
        self._descriptors: dict[str, PluginDescriptor] = {}
        self._factories: dict[str, PluginWidgetFactory] = {}
        self._loaded_modules: dict[str, Any] = {}

    @property
    def plugins(self) -> dict[str, PluginDescriptor]:
        return dict(self._descriptors)

    def discover(self) -> list[PluginDescriptor]:
        """Explora plugins/ y carga cada plugin.json válido."""
        discovered: list[PluginDescriptor] = []
        if not self._plugins_dir.is_dir():
            logger.warning("Directorio de plugins no encontrado: %s", self._plugins_dir)
            return discovered

        for plugin_dir in sorted(self._plugins_dir.iterdir()):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue

            manifest = plugin_dir / "plugin.json"
            if not manifest.exists():
                logger.debug("Omitiendo %s (sin plugin.json)", plugin_dir.name)
                continue

            try:
                desc = self._load_descriptor(manifest, plugin_dir)
                self._descriptors[desc.id] = desc
                discovered.append(desc)
                logger.info("Plugin registrado: %s v%s (%s)", desc.name, desc.version, desc.id)
            except Exception:
                logger.exception("Error cargando plugin desde %s", manifest)

        return discovered

    def register(self, descriptor: PluginDescriptor, factory: PluginWidgetFactory | None = None) -> None:
        """Registra un plugin programáticamente."""
        self._descriptors[descriptor.id] = descriptor
        if factory is not None:
            self._factories[descriptor.id] = factory
        logger.info("Plugin registrado manualmente: %s", descriptor.id)

    def get(self, plugin_id: str) -> PluginDescriptor | None:
        return self._descriptors.get(plugin_id)

    def get_factory(self, plugin_id: str) -> PluginWidgetFactory | None:
        return self._factories.get(plugin_id)

    def search(self, query: str, min_score: float = 0.2) -> list[tuple[PluginDescriptor, float]]:
        """Busca plugins por relevancia. Devuelve lista ordenada (desc, score)."""
        results: list[tuple[PluginDescriptor, float]] = []
        for desc in self._descriptors.values():
            score = desc.matches_query(query)
            if score >= min_score:
                results.append((desc, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def get_by_category(self, category: PluginCategory) -> list[PluginDescriptor]:
        return [p for p in self._descriptors.values() if p.category == category]

    def get_all_categories(self) -> list[PluginCategory]:
        cats = {p.category for p in self._descriptors.values()}
        return sorted(cats, key=lambda c: c.value)

    def _load_descriptor(self, manifest: Path, plugin_dir: Path) -> PluginDescriptor:
        with open(manifest, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        category_str = data.get("category", "Otro")
        try:
            category = PluginCategory(category_str)
        except ValueError:
            category = PluginCategory.OTHER

        status_str = data.get("status", "oficial")
        try:
            status = PluginStatus(status_str)
        except ValueError:
            status = PluginStatus.OFFICIAL

        return PluginDescriptor(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            category=category,
            tags=data.get("tags", []),
            owner=data.get("owner", "NEXA"),
            backup_owner=data.get("backup_owner", ""),
            area=data.get("area", ""),
            status=status,
            entrypoint=data.get("entrypoint", ""),
            icon=data.get("icon", ""),
            permissions=data.get("permissions", []),
            dependencies=data.get("dependencies", []),
            documentation_url=data.get("documentation_url", ""),
            synonyms=data.get("synonyms", []),
        )

    def load_plugin_module(self, plugin_id: str) -> Any:
        """Carga el módulo Python de un plugin (lazy)."""
        if plugin_id in self._loaded_modules:
            return self._loaded_modules[plugin_id]

        desc = self._descriptors.get(plugin_id)
        if not desc:
            raise KeyError(f"Plugin no registrado: {plugin_id}")

        plugin_dir = self._plugins_dir / plugin_id
        entrypoint = desc.entrypoint or "main"

        module_path = plugin_dir / f"{entrypoint}.py"
        if not module_path.exists():
            module_path = plugin_dir / entrypoint.replace(".", "/") / "__init__.py"
            if not module_path.exists():
                raise ImportError(
                    f"No se encontró el módulo '{entrypoint}' en {plugin_dir}"
                )

        try:
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_id}.{entrypoint}", str(module_path)
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"No se pudo crear spec para {module_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._loaded_modules[plugin_id] = module
            return module
        except Exception:
            logger.exception("Error importando módulo del plugin %s", plugin_id)
            raise
