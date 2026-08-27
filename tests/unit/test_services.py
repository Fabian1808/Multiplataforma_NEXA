"""Tests — Services: Knowledge, Requests, Notifications, Health, Opportunity."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from hub.core.health_check import HealthCheckService, HealthStatus
from hub.core.knowledge_service import KnowledgeService
from hub.core.notification_service import NotificationService
from hub.core.opportunity_tracker import OpportunityTracker
from hub.core.request_service import RequestService
from hub.infrastructure.database import Database
from hub.models.plugin import PluginCategory, PluginDescriptor, PluginStatus


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


class TestKnowledgeService:
    def test_create_and_get(self, db: Database) -> None:
        svc = KnowledgeService(db)
        article_id = svc.create("Test Article", content="Content here", category="Excel", author="Fabian")
        assert article_id > 0
        fetched = svc.get(article_id)
        assert fetched is not None
        assert fetched["title"] == "Test Article"

    def test_get_all(self, db: Database) -> None:
        svc = KnowledgeService(db)
        svc.create("A1", content="c1")
        svc.create("A2", content="c2")
        assert len(svc.get_all()) == 2

    def test_search(self, db: Database) -> None:
        svc = KnowledgeService(db)
        svc.create("Consolidar Excel", content="Cómo consolidar 50 archivos")
        svc.create("SAP HES", content="Descargar documentos SAP")
        results = svc.search("consolidar")
        assert len(results) == 1
        assert results[0]["title"] == "Consolidar Excel"

    def test_update(self, db: Database) -> None:
        svc = KnowledgeService(db)
        aid = svc.create("Old", content="Old content")
        svc.update(aid, title="New")
        assert svc.get(aid)["title"] == "New"

    def test_delete(self, db: Database) -> None:
        svc = KnowledgeService(db)
        aid = svc.create("Delete Me")
        svc.delete(aid)
        assert svc.get(aid) is None

    def test_empty_search(self, db: Database) -> None:
        svc = KnowledgeService(db)
        assert len(svc.search("nonexistent")) == 0


class TestRequestService:
    def test_create_and_get(self, db: Database) -> None:
        svc = RequestService(db)
        rid = svc.create("fabian", "ayuda", title="Help", description="Need help with Excel", area="Contracts")
        assert rid > 0
        fetched = svc.get(rid)
        assert fetched is not None
        assert fetched["user_id"] == "fabian"

    def test_update_status(self, db: Database) -> None:
        svc = RequestService(db)
        rid = svc.create("user1", "ayuda", description="Test")
        svc.update(rid, status="en_revision")
        assert svc.get(rid)["status"] == "en_revision"

    def test_get_stats(self, db: Database) -> None:
        svc = RequestService(db)
        svc.create("u1", "ayuda", description="R1")
        svc.create("u2", "idea", description="R2")
        svc.create("u3", "incidente", description="R3")
        stats = svc.get_stats()
        assert stats["total"] == 3

    def test_assign(self, db: Database) -> None:
        svc = RequestService(db)
        rid = svc.create("user1", "ayuda", description="Test")
        svc.update(rid, assigned_to="maria")
        assert svc.get(rid)["assigned_to"] == "maria"


class TestNotificationService:
    def test_create_and_get_unread(self, db: Database) -> None:
        svc = NotificationService(db)
        nid = svc.create("fabian", "welcome", "New Guide", "Check this out")
        assert nid > 0
        unread = svc.get_all("fabian", unread_only=True)
        assert len(unread) == 1
        assert unread[0]["title"] == "New Guide"

    def test_mark_read(self, db: Database) -> None:
        svc = NotificationService(db)
        nid = svc.create("fabian", "welcome", "Tool Ready")
        svc.mark_read(nid)
        assert len(svc.get_all("fabian", unread_only=True)) == 0

    def test_unread_count(self, db: Database) -> None:
        svc = NotificationService(db)
        svc.create("fabian", "system_update", "A")
        svc.create("fabian", "welcome", "B")
        assert svc.get_unread_count("fabian") == 2

    def test_mark_all_read(self, db: Database) -> None:
        svc = NotificationService(db)
        svc.create("fabian", "system_update", "A")
        svc.create("fabian", "welcome", "B")
        svc.mark_all_read("fabian")
        assert svc.get_unread_count("fabian") == 0


class TestHealthCheck:
    def test_check_plugin(self) -> None:
        svc = HealthCheckService()
        desc = PluginDescriptor(
            id="test", name="Test", description="", version="1.0.0",
            category=PluginCategory.OTHER, owner="Fabian", tags=["test"],
        )
        report = svc.check_plugin(desc)
        assert report.status == HealthStatus.OK
        assert report.plugin_name == "Test"

    def test_check_deprecated(self) -> None:
        svc = HealthCheckService()
        desc = PluginDescriptor(
            id="old", name="Old", description="", version="1.0.0",
            category=PluginCategory.OTHER, status=PluginStatus.DEPRECATED,
        )
        report = svc.check_plugin(desc)
        assert report.status == HealthStatus.WARNING

    def test_check_all(self) -> None:
        svc = HealthCheckService()
        plugins = [
            PluginDescriptor(id="a", name="A", description="", version="1.0.0", category=PluginCategory.OTHER),
            PluginDescriptor(id="b", name="B", description="", version="1.0.0", category=PluginCategory.OTHER, status=PluginStatus.DEPRECATED),
        ]
        reports = svc.check_all(plugins)
        assert len(reports) == 2


class TestOpportunityTracker:
    def test_record_search(self, db: Database) -> None:
        tracker = OpportunityTracker(db)
        tracker.record_search("validar contratos", 0)
        tracker.record_search("validar contratos", 0)
        opps = tracker.get_opportunities()
        assert len(opps) >= 1

    def test_acknowledge(self, db: Database) -> None:
        tracker = OpportunityTracker(db)
        tracker.record_search("test query", 0)
        opps = tracker.get_opportunities()
        assert len(opps) == 1
        tracker.acknowledge(opps[0]["id"])
        remaining = tracker.get_opportunities()
        assert len(remaining) == 0
