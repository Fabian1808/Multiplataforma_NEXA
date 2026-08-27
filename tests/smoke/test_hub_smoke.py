"""Smoke test — Verifica que el Hub se puede importar y los plugins se descubren."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from hub.core.plugin_registry import PluginRegistry
from hub.core.catalog_service import CatalogService
from hub.core.search_engine import SearchEngine
from hub.infrastructure.database import Database


def test_hub_imports() -> None:
    import hub
    assert hub.__version__ == "2.0.0"
    assert hub.__app_name__ == "NEXA Productivity Hub"


def test_plugin_discovery() -> None:
    base_dir = Path(__file__).resolve().parent.parent.parent
    registry = PluginRegistry(base_dir)
    discovered = registry.discover()
    plugin_ids = [p.id for p in discovered]
    assert "horas_extras" in plugin_ids, f"Plugin horas_extras no encontrado en: {plugin_ids}"
    assert "sap_automation" in plugin_ids, f"Plugin sap_automation no encontrado en: {plugin_ids}"
    assert "_template" not in plugin_ids, "_template no debe ser registrado"


def test_catalog_search_integration() -> None:
    base_dir = Path(__file__).resolve().parent.parent.parent
    registry = PluginRegistry(base_dir)
    registry.discover()
    catalog = CatalogService(registry)
    all_p = catalog.get_all()
    assert len(all_p) >= 2


def test_database_init() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "test.db")
        conn = db.connect()
        assert conn is not None
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "favorites" in tables
        assert "executions" in tables
        assert "audit_log" in tables
        assert "posts" in tables
        assert "projects" in tables
        db.close()


def test_search_engine_fts() -> None:
    import tempfile
    from hub.models.plugin import PluginDescriptor, PluginCategory
    with tempfile.TemporaryDirectory() as td:
        engine = SearchEngine()
        p = PluginDescriptor(
            id="sap", name="Automatización SAP", description="descarga masiva documentos",
            version="1.0.0", category=PluginCategory.SAP, tags=["sap", "hes"],
            synonyms=["ml81n", "sp01"],
        )
        engine.index_plugin(p)
        results = engine.search("sap")
        assert len(results) >= 1
        engine.close()
