"""Tests — Plugin Registry, Catalog, Search, Auth, Audit, Workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from hub.core.catalog_service import CatalogService
from hub.core.plugin_registry import PluginRegistry
from hub.core.search_engine import SearchEngine
from hub.infrastructure.database import Database
from hub.core.auth_service import AuthService
from hub.core.audit_service import AuditService
from hub.core.workflow_engine import WorkflowEngine
from hub.core.metrics_collector import MetricsCollector
from hub.core.request_service import RequestService
from hub.core.knowledge_service import KnowledgeService
from hub.core.notification_service import NotificationService
from hub.core.feed_service import FeedService
from hub.core.project_service import ProjectService
from hub.models.plugin import PluginCategory, PluginDescriptor, PluginStatus


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_dir = plugins_dir / "test_plugin"
    plugin_dir.mkdir()
    manifest = {
        "id": "test_plugin",
        "name": "Test Plugin",
        "description": "A test plugin for unit testing",
        "version": "1.0.0",
        "category": "Automatización",
        "tags": ["test", "demo"],
        "synonyms": ["prueba", "ejemplo"],
        "owner": "Tester",
        "status": "oficial",
        "entrypoint": "main",
    }
    with open(plugin_dir / "plugin.json", "w") as f:
        json.dump(manifest, f)
    return tmp_path


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


@pytest.fixture
def registry(base_dir: Path) -> PluginRegistry:
    return PluginRegistry(base_dir)


@pytest.fixture
def catalog(registry: PluginRegistry) -> CatalogService:
    return CatalogService(registry)


class TestPluginDescriptor:
    def test_matches_exact_name(self) -> None:
        desc = PluginDescriptor(id="he", name="Horas Extras", description="validación", version="1.0.0", category=PluginCategory.AUTOMATION)
        assert desc.matches_query("Horas Extras") == 1.0

    def test_matches_name_contains(self) -> None:
        desc = PluginDescriptor(id="he", name="Sistema de Horas Extras", description="validación", version="1.0.0", category=PluginCategory.AUTOMATION)
        score = desc.matches_query("horas extras")
        assert score >= 0.8

    def test_matches_description(self) -> None:
        desc = PluginDescriptor(id="he", name="Tool X", description="consolidar archivos excel", version="1.0.0", category=PluginCategory.EXCEL)
        score = desc.matches_query("consolidar excel")
        assert score >= 0.5

    def test_matches_tag(self) -> None:
        desc = PluginDescriptor(id="he", name="Tool X", description="", version="1.0.0", category=PluginCategory.EXCEL, tags=["excel", "comparar"])
        score = desc.matches_query("comparar")
        assert score >= 0.7

    def test_matches_synonym(self) -> None:
        desc = PluginDescriptor(id="he", name="Tool X", description="", version="1.0.0", category=PluginCategory.SAP, synonyms=["sap", "ml81n"])
        score = desc.matches_query("ml81n")
        assert score >= 0.7

    def test_no_match(self) -> None:
        desc = PluginDescriptor(id="he", name="Tool X", description="nothing relevant", version="1.0.0", category=PluginCategory.OTHER)
        assert desc.matches_query("xyzabc123") == 0.0

    def test_to_dict(self) -> None:
        desc = PluginDescriptor(id="t", name="T", description="D", version="1.0.0", category=PluginCategory.EXCEL)
        d = desc.to_dict()
        assert d["id"] == "t"
        assert d["category"] == "Excel"


class TestPluginRegistry:
    def test_discover(self, registry: PluginRegistry) -> None:
        discovered = registry.discover()
        assert len(discovered) == 1
        assert discovered[0].id == "test_plugin"

    def test_get(self, registry: PluginRegistry) -> None:
        registry.discover()
        desc = registry.get("test_plugin")
        assert desc is not None
        assert desc.name == "Test Plugin"

    def test_search(self, registry: PluginRegistry) -> None:
        registry.discover()
        results = registry.search("test")
        assert len(results) >= 1
        assert results[0][0].id == "test_plugin"

    def test_search_no_results(self, registry: PluginRegistry) -> None:
        registry.discover()
        results = registry.search("zzz_nonexistent_zzz")
        assert len(results) == 0

    def test_register_manual(self) -> None:
        reg = PluginRegistry(Path("/nonexistent"))
        desc = PluginDescriptor(id="manual", name="Manual", description="", version="1.0.0", category=PluginCategory.OTHER)
        reg.register(desc)
        assert reg.get("manual") is not None


class TestCatalogService:
    def test_total_plugins(self, catalog: CatalogService) -> None:
        catalog._registry.discover()
        all_p = catalog.get_all()
        assert len(all_p) == 1

    def test_get_by_category(self, catalog: CatalogService) -> None:
        catalog._registry.discover()
        result = catalog.get_by_category("Automatización")
        assert len(result) >= 1


class TestSearchEngine:
    def test_index_and_search(self, tmp_path: Path) -> None:
        engine = SearchEngine()
        desc = PluginDescriptor(
            id="he", name="Horas Extras", description="validación de horas",
            version="1.0.0", category=PluginCategory.AUTOMATION,
            tags=["horas", "extras"], synonyms=["rainbow"],
        )
        engine.index_plugin(desc)
        results = engine.search("horas")
        assert len(results) >= 1
        assert results[0][0] == "he"
        engine.close()

    def test_index_all(self, tmp_path: Path) -> None:
        engine = SearchEngine()
        plugins = [
            PluginDescriptor(id="a", name="Alpha", description="test alpha", version="1.0.0", category=PluginCategory.EXCEL),
            PluginDescriptor(id="b", name="Beta", description="test beta", version="1.0.0", category=PluginCategory.SAP),
        ]
        engine.index_all(plugins)
        results = engine.search("test")
        assert len(results) == 2
        engine.close()

    def test_rebuild_index(self, tmp_path: Path) -> None:
        engine = SearchEngine()
        p1 = PluginDescriptor(id="x", name="X", description="x", version="1.0.0", category=PluginCategory.OTHER)
        engine.index_plugin(p1)
        engine.rebuild_index([p1])
        results = engine.search("x")
        assert len(results) >= 1
        engine.close()


class TestAuthService:
    def test_create_user(self, db: Database) -> None:
        auth = AuthService(db)
        user = auth.create_user("test_user", "Test User", "test@test.com", "pass123", area="TI", role="usuario")
        assert user is not None
        assert user["username"] == "test_user"
        assert user["name"] == "Test User"

    def test_authenticate(self, db: Database) -> None:
        auth = AuthService(db)
        auth.create_user("auth_user", "Auth User", "auth@test.com", "secret", role="usuario")
        result = auth.authenticate("auth_user", "secret")
        assert result is not None
        assert result["username"] == "auth_user"

    def test_authenticate_wrong_password(self, db: Database) -> None:
        auth = AuthService(db)
        auth.create_user("auth_user2", "Auth User 2", "auth2@test.com", "secret", role="usuario")
        result = auth.authenticate("auth_user2", "wrong")
        assert result is None

    def test_has_permission(self, db: Database) -> None:
        auth = AuthService(db)
        user = auth.create_user("perm_user", "Perm User", "perm@test.com", "", role="administrador")
        assert auth.has_permission(user["id"], "system.manage")

    def test_check_access(self, db: Database) -> None:
        auth = AuthService(db)
        user = auth.create_user("access_user", "Access User", "acc@test.com", "", role="usuario")
        assert auth.check_access(user["id"], "requests", "create")
        assert not auth.check_access(user["id"], "users", "delete")

    def test_get_all_users(self, db: Database) -> None:
        auth = AuthService(db)
        auth.create_user("u1", "User 1", "u1@test.com", "", role="usuario")
        auth.create_user("u2", "User 2", "u2@test.com", "", role="usuario")
        users = auth.get_all_users()
        assert len(users) >= 2


class TestAuditService:
    def test_log_entry(self, db: Database) -> None:
        audit = AuditService(db)
        audit.log("user1", "create", "requests", "request", "1", "Test Request")
        entries = audit.get_entries(user_id="user1")
        assert len(entries) == 1
        assert entries[0]["action"] == "create"

    def test_get_stats(self, db: Database) -> None:
        audit = AuditService(db)
        audit.log("u1", "create", "module1", "entity", "1")
        audit.log("u1", "update", "module1", "entity", "1")
        stats = audit.get_stats()
        assert stats["total"] == 2

    def test_filters(self, db: Database) -> None:
        audit = AuditService(db)
        audit.log("u1", "create", "requests", "request", "1")
        audit.log("u1", "view", "knowledge", "article", "5")
        entries = audit.get_entries(module="requests")
        assert len(entries) == 1


class TestWorkflowEngine:
    def test_available_transitions(self, db: Database) -> None:
        wf = WorkflowEngine(db)
        transitions = wf.get_available_transitions("nueva")
        assert "recibida" in transitions

    def test_can_transition(self, db: Database) -> None:
        wf = WorkflowEngine(db)
        assert wf.can_transition("nueva", "recibida")
        assert not wf.can_transition("nueva", "completada")

    def test_transition(self, db: Database) -> None:
        req_svc = RequestService(db)
        req_id = req_svc.create("user1", "ayuda", "Test", "Desc")
        wf = WorkflowEngine(db)
        result = wf.transition(req_id, "recibida", "user1")
        assert result is not None
        updated = req_svc.get(req_id)
        assert updated["workflow_state"] == "recibida"

    def test_invalid_transition(self, db: Database) -> None:
        req_svc = RequestService(db)
        req_id = req_svc.create("user1", "ayuda", "Test", "Desc")
        wf = WorkflowEngine(db)
        result = wf.transition(req_id, "completada", "user1")
        assert result is None


class TestMetricsCollector:
    def test_record_execution(self, db: Database) -> None:
        mc = MetricsCollector(db)
        mc.record_execution("plugin1", "user1", True, 5.0)
        stats = mc.get_stats()
        assert stats["total_executions"] >= 1

    def test_record_search(self, db: Database) -> None:
        mc = MetricsCollector(db)
        mc.record_search("test query", 3, "user1")
        stats = mc.get_stats()
        assert stats["total_searches"] >= 1

    def test_get_plugin_stats(self, db: Database) -> None:
        mc = MetricsCollector(db)
        mc.record_execution("plugin1", "user1", True, 2.0)
        mc.record_execution("plugin1", "user1", True, 4.0)
        stats = mc.get_plugin_stats("plugin1")
        assert stats["total_executions"] == 2
        assert stats["avg_duration_seconds"] == 3.0


class TestRequestService:
    def test_create_and_get(self, db: Database) -> None:
        svc = RequestService(db)
        req_id = svc.create("user1", "ayuda", "Title", "Desc", area="TI")
        req = svc.get(req_id)
        assert req is not None
        assert req["title"] == "Title"

    def test_get_all(self, db: Database) -> None:
        svc = RequestService(db)
        svc.create("u1", "ayuda", "R1", "D1")
        svc.create("u2", "idea", "R2", "D2")
        all_req = svc.get_all()
        assert len(all_req) >= 2

    def test_update(self, db: Database) -> None:
        svc = RequestService(db)
        req_id = svc.create("u1", "ayuda", "R", "D")
        svc.update(req_id, status="aprobada", priority="alta")
        req = svc.get(req_id)
        assert req["status"] == "aprobada"
        assert req["priority"] == "alta"


class TestKnowledgeService:
    def test_create_and_get(self, db: Database) -> None:
        svc = KnowledgeService(db)
        art_id = svc.create("Article", "Content", category="SAP")
        art = svc.get(art_id)
        assert art is not None
        assert art["title"] == "Article"

    def test_search(self, db: Database) -> None:
        svc = KnowledgeService(db)
        svc.create("Guía SAP", "Contenido SAP", category="SAP")
        results = svc.search("SAP")
        assert len(results) >= 1


class TestFeedService:
    def test_create_post(self, db: Database) -> None:
        svc = FeedService(db)
        post_id = svc.create_post("user1", "Hello world", title="Test")
        assert post_id > 0

    def test_get_feed(self, db: Database) -> None:
        svc = FeedService(db)
        svc.create_post("user1", "Post 1")
        svc.create_post("user2", "Post 2")
        feed = svc.get_feed()
        assert len(feed) >= 2

    def test_toggle_like(self, db: Database) -> None:
        svc = FeedService(db)
        post_id = svc.create_post("user1", "Like test")
        liked = svc.toggle_like(post_id, "user2")
        assert liked is True
        liked_again = svc.toggle_like(post_id, "user2")
        assert liked_again is False


class TestProjectService:
    def test_create_project(self, db: Database) -> None:
        svc = ProjectService(db)
        proj_id = svc.create_project("My Project", description="Test")
        proj = svc.get_project(proj_id)
        assert proj is not None
        assert proj["name"] == "My Project"

    def test_create_task(self, db: Database) -> None:
        svc = ProjectService(db)
        proj_id = svc.create_project("P1")
        task_id = svc.create_task(proj_id, "Task 1")
        task = svc.get_task(task_id)
        assert task is not None
        assert task["title"] == "Task 1"


class TestNotificationService:
    def test_create_and_get(self, db: Database) -> None:
        svc = NotificationService(db)
        notif_id = svc.create("user1", "welcome", "Welcome!", "Bienvenido")
        assert notif_id > 0
        notifs = svc.get_all("user1")
        assert len(notifs) >= 1

    def test_mark_read(self, db: Database) -> None:
        svc = NotificationService(db)
        svc.create("user1", "welcome", "Welcome!")
        notifs = svc.get_all("user1", unread_only=True)
        assert len(notifs) >= 1
        svc.mark_read(notifs[0]["id"])
        unread = svc.get_all("user1", unread_only=True)
        assert len(unread) == 0

    def test_unread_count(self, db: Database) -> None:
        svc = NotificationService(db)
        svc.create("user1", "test", "T1")
        svc.create("user1", "test", "T2")
        count = svc.get_unread_count("user1")
        assert count >= 2
