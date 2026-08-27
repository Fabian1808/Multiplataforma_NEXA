"""Smoke test — Verifica que la GUI se puede crear."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


@pytest.fixture(scope="session")
def qt_app():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def services():
    from hub.core.service_container import ServiceContainer
    svc = ServiceContainer()
    yield svc
    svc.close()


def test_gui_shell_creation(qt_app, services):
    from hub.ui.shell import Shell
    shell = Shell(services)
    user_data = services.auth.get_user_by_username("fabian")
    assert user_data is not None
    shell.setup_ui(user_data)
    assert shell.windowTitle().startswith("NEXA Productivity Hub")
    assert shell._stack.count() == 16
    shell.close()


def test_service_container_users(services):
    users = services.auth.get_all_users()
    assert len(users) >= 20


def test_service_container_metrics(services):
    stats = services.metrics.get_stats()
    assert stats["total_executions"] >= 50
    assert stats["total_users"] >= 20


def test_service_container_audit(services):
    entries = services.audit.get_entries(limit=10)
    assert len(entries) > 0


def test_service_container_feed(services):
    posts = services.feed.get_feed()
    assert len(posts) >= 5


def test_service_container_projects(services):
    projects = services.projects.get_all_projects()
    assert len(projects) >= 3


def test_service_container_requests(services):
    requests = services.requests.get_all()
    assert len(requests) >= 10


def test_service_container_knowledge(services):
    articles = services.knowledge.get_all()
    assert len(articles) >= 3


def test_service_container_notifications(services):
    notifs = services.notifications.get_all(services.user_id)
    assert isinstance(notifs, list)


def test_workflow_engine(services):
    from hub.core.workflow_engine import WorkflowEngine
    transitions = services.workflow.get_available_transitions("nueva")
    assert "recibida" in transitions
    assert services.workflow.can_transition("nueva", "recibida")
    assert not services.workflow.can_transition("nueva", "completada")
