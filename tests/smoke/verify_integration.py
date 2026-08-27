"""Quick integration verification script."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")
from hub.core.plugin_registry import PluginRegistry
from hub.core.catalog_service import CatalogService
from hub.core.config_service import ConfigService
from hub.core.search_engine import SearchEngine
from hub.core.metrics_collector import MetricsCollector

base = Path(".")
registry = PluginRegistry(base)
discovered = registry.discover()
print(f"Plugins descubiertos: {len(discovered)}")
for p in discovered:
    print(f"  - {p.name} v{p.version} [{p.category.value}] ({p.status.value})")
    print(f"    Tags: {p.tags}")
    print(f"    Synonyms: {p.synonyms}")

catalog = CatalogService(registry)
print(f"\nTotal en catalogo: {catalog.total_plugins}")
print(f"Categorias: {[c.value for c in catalog.get_categories()]}")

with tempfile.TemporaryDirectory() as tmpdir:
    search = SearchEngine(Path(tmpdir) / "nexus.db")
    search.index_all(list(registry.plugins.values()))

    queries = ["horas extras", "sap", "excel", "rainbow", "hes", "descargar"]
    for q in queries:
        results = registry.search(q)
        print(f'\nBuscar "{q}": {len(results)} resultado(s)')
        for desc, score in results[:3]:
            print(f"  {desc.name} (score: {score:.2f})")

    config = ConfigService(Path(tmpdir) / "config.json")
    config.add_favorite("horas_extras")
    config.add_recent("sap_automation")
    print(f"\nFavoritos: {config.get_favorites()}")
    print(f"Recientes: {config.get_recent()}")

    metrics = MetricsCollector()
    metrics.record_execution("horas_extras", success=True, duration_seconds=120)
    metrics.record_execution("sap_automation", success=False, duration_seconds=30)
    print(f"\nMetricas: {metrics.get_stats()}")
    print(f"Plugin stats: {metrics.get_plugin_stats('horas_extras')}")

    search.close()

print("\n[OK] Todo funciona correctamente")
