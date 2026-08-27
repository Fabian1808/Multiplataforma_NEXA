"""UI Shell — Ventana principal del NEXA Productivity Hub v2.0.

RBAC-based navigation, login flow, dark/light theme, all views integrated.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QMessageBox,
)

from hub import __app_name__, __version__
from hub.core.service_container import ServiceContainer
from hub.ui.auth.login_view import LoginView
from hub.ui.admin.admin_center_view import AdminCenterView
from hub.ui.admin.app_audit_view import AppAuditView
from hub.ui.admin.automation_proposal_view import AutomationProposalView
from hub.ui.admin.failure_detail_view import FailureDetailView
from hub.ui.admin.help_request_view import HelpRequestView
from hub.ui.admin.issue_report_view import IssueReportView
from hub.ui.admin.knowledge_view import KnowledgeBaseView
from hub.ui.admin.notification_view import NotificationView
from hub.ui.admin.requests_view import RequestsView
from hub.ui.admin.impact_dashboard_view import ImpactDashboardView
from hub.ui.admin.audit_log_view import AuditLogView
from hub.ui.admin.user_management_view import UserManagementView
from hub.ui.admin.feed_view import FeedView
from hub.ui.app_viewer.app_viewer import AppViewer
from hub.ui.catalog.catalog_view import CatalogView
from hub.ui.common.design import (
    Theme, NEXAStyles, ACCENT, get_font, make_shadow,
    save_theme, set_theme, is_dark, get_theme,
)
from hub.ui.dashboard.enhanced_dashboard_view import EnhancedDashboardView
from hub.ui.reports.reports_center_view import ReportsCenterView
from hub.ui.search.search_view import SearchView

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Page keys used as dict keys for the stacked widget and RBAC checks.
# ---------------------------------------------------------------------------
P_DASHBOARD = "dashboard"
P_CATALOG = "catalog"
P_SEARCH = "search"
P_APP = "app"
P_PROPOSALS = "proposals"
P_REQUESTS = "requests"
P_KNOWLEDGE = "knowledge"
P_ISSUES = "issues"
P_REPORTS = "reports"
P_AUDIT = "audit"
P_USERS = "users"
P_COMMUNITY = "community"
P_APP_AUDIT = "app_audit"
P_FAILURE_DETAIL = "failure_detail"
P_NOTIFICATIONS = "notifications"

_PAGE_TITLES: dict[str, str] = {
    P_DASHBOARD: "Inicio",
    P_CATALOG: "Catálogo",
    P_SEARCH: "Búsqueda",
    P_APP: "Aplicación",
    P_PROPOSALS: "Propuestas",
    P_REQUESTS: "Solicitudes",
    P_KNOWLEDGE: "Conocimiento",
    P_ISSUES: "Incidencias",
    P_REPORTS: "Reportes",
    P_AUDIT: "Auditoría",
    P_USERS: "Gestión de Usuarios",
    P_COMMUNITY: "Comunidad",
    P_APP_AUDIT: "Auditoría de Aplicaciones",
    P_FAILURE_DETAIL: "Detalle de Fallo",
    P_NOTIFICATIONS: "Notificaciones",
}

# Module key used for RBAC check_access(user_id, module, action).
_PAGE_MODULE: dict[str, str] = {
    P_DASHBOARD: "dashboard",
    P_CATALOG: "plugins",
    P_SEARCH: "plugins",
    P_APP: "plugins",
    P_PROPOSALS: "requests",
    P_REQUESTS: "requests",
    P_KNOWLEDGE: "knowledge",
    P_ISSUES: "requests",
    P_REPORTS: "reports",
    P_AUDIT: "audit",
    P_USERS: "users",
    P_COMMUNITY: "feed",
    P_APP_AUDIT: "plugins",
    P_FAILURE_DETAIL: "plugins",
    P_NOTIFICATIONS: "notifications",
}


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
class _BackgroundWorker(QThread):
    finished = Signal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            result = self._fn()
            self.finished.emit(result)
        except Exception:
            logger.exception("Background worker error")
            self.finished.emit(None)


# ---------------------------------------------------------------------------
# Main Shell (shown after login)
# ---------------------------------------------------------------------------
class Shell(QWidget):
    """Main application shell with RBAC-based navigation and login flow."""

    logout_requested = Signal()

    def __init__(self, services: ServiceContainer) -> None:
        super().__init__()
        self._svc = services
        self._workers: list[_BackgroundWorker] = []
        self._nav_buttons: dict[str, QPushButton] = {}
        self._current_user: dict[str, Any] | None = None
        self._is_admin: bool = False
        self._current_page: str = P_DASHBOARD
        self._theme_mode: str = get_theme()
        self._pages: dict[str, QWidget] = {}
        self._admin_section: QWidget | None = None

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------
    def _setup_window(self) -> None:
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)
        self.setStyleSheet(f"QWidget {{ font-family: 'Segoe UI'; }}")

    # ------------------------------------------------------------------
    # Full shell UI — called after successful login
    # ------------------------------------------------------------------
    def setup_ui(self, user_data: dict[str, Any]) -> None:
        """Build the complete shell UI after authentication."""
        self._current_user = user_data
        self._svc.current_user = user_data
        self._is_admin = "administrador" in user_data.get("roles", [])
        self._setup_window()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = self._create_sidebar()
        root.addWidget(self._sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._header = self._create_header()
        right_layout.addWidget(self._header)

        self._access_denied_label = QLabel("⚠ No tiene permisos para acceder a esta sección.")
        self._access_denied_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._access_denied_label.setFont(get_font(14))
        self._access_denied_label.setStyleSheet(f"color: {Theme.text_secondary()}; background: {Theme.bg()};")

        self._stack = QStackedWidget()
        self._build_pages()
        right_layout.addWidget(self._stack, stretch=1)

        root.addWidget(right_panel, stretch=1)
        self.apply_theme()

    # ------------------------------------------------------------------
    # Page construction
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Page construction — LAZY LOADING
    # Las vistas se crean solo la primera vez que el usuario navega a ellas.
    # ------------------------------------------------------------------
    def _build_pages(self) -> None:
        """Registra los constructores de páginas (no las crea todavía).

        Solo el Dashboard se crea de inmediato para mostrarlo al iniciar.
        El resto se instancia bajo demanda en _get_page().
        """
        # Registro de fábricas: se ejecutan solo cuando se necesitan
        self._page_factories: dict[str, Any] = {
            P_CATALOG:        self._create_catalog,
            P_SEARCH:         self._create_search,
            P_APP:            self._create_app_viewer,
            P_PROPOSALS:      self._create_proposals,
            P_REQUESTS:       self._create_requests,
            P_KNOWLEDGE:      self._create_knowledge,
            P_ISSUES:         self._create_issues,
            P_REPORTS:        self._create_reports,
            P_AUDIT:          self._create_audit,
            P_USERS:          self._create_users,
            P_COMMUNITY:      self._create_community,
            P_APP_AUDIT:      self._create_app_audit,
            P_FAILURE_DETAIL: self._create_failure_detail,
            P_NOTIFICATIONS:  self._create_notifications,
        }

        # Solo el Dashboard se crea eagerly (se muestra en login)
        dashboard = self._create_dashboard()
        self._pages[P_DASHBOARD] = dashboard
        self._stack.addWidget(dashboard)
        self._stack.addWidget(self._access_denied_label)
        self._stack.setCurrentWidget(dashboard)

    def _get_page(self, page_key: str) -> QWidget | None:
        """Devuelve la página, creándola si es la primera vez (lazy init)."""
        if page_key in self._pages:
            return self._pages[page_key]

        factory = self._page_factories.get(page_key)
        if factory is None:
            return None

        page = factory()
        self._pages[page_key] = page
        # Insertar antes del label de "acceso denegado" (último widget del stack)
        self._stack.insertWidget(self._stack.count() - 1, page)
        return page


    # --- individual page factories ---

    def _create_dashboard(self) -> EnhancedDashboardView:
        view = EnhancedDashboardView(user_name=self._svc.user_name)
        view.plugin_clicked.connect(self._on_plugin_clicked)
        return view

    def _create_catalog(self) -> CatalogView:
        view = CatalogView()
        view.plugin_clicked.connect(self._on_plugin_clicked)
        return view

    def _create_search(self) -> SearchView:
        view = SearchView()
        view.plugin_clicked.connect(self._on_plugin_clicked)
        return view

    def _create_app_viewer(self) -> AppViewer:
        view = AppViewer(self._svc.registry)
        view.back_clicked.connect(self._go_back)
        view.favorite_toggled.connect(self._on_favorite_toggled)
        return view

    def _create_proposals(self) -> AutomationProposalView:
        view = AutomationProposalView()
        view.submitted.connect(self._on_proposal_submitted)
        return view

    def _create_requests(self) -> RequestsView:
        return RequestsView()

    def _create_knowledge(self) -> KnowledgeBaseView:
        return KnowledgeBaseView()

    def _create_issues(self) -> IssueReportView:
        view = IssueReportView()
        view.submitted.connect(self._on_issue_submitted)
        return view

    def _create_reports(self) -> ReportsCenterView:
        return ReportsCenterView()

    def _create_audit(self) -> AuditLogView:
        return AuditLogView()

    def _create_users(self) -> UserManagementView:
        return UserManagementView()

    def _create_community(self) -> FeedView:
        return FeedView()

    def _create_app_audit(self) -> AppAuditView:
        view = AppAuditView()
        view.failure_clicked.connect(self._on_audit_failure_clicked)
        view.detail_clicked.connect(self._on_audit_failure_clicked)
        return view

    def _create_failure_detail(self) -> FailureDetailView:
        view = FailureDetailView()
        view.back_clicked.connect(lambda: self._navigate_to(P_APP_AUDIT))
        return view

    def _create_notifications(self) -> NotificationView:
        return NotificationView()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def _create_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet(NEXAStyles.sidebar())
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        # Logo
        logo_frame = QFrame()
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(4, 4, 4, 16)
        logo_icon = QLabel("\u26a1")
        logo_icon.setFont(get_font(22, bold=True))
        logo_icon.setStyleSheet(f"color: {ACCENT};")
        logo_layout.addWidget(logo_icon)
        logo_text = QLabel("NEXA")
        logo_text.setFont(get_font(16, bold=True))
        logo_text.setStyleSheet("color: #FFFFFF;")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        layout.addWidget(logo_frame)
        layout.addSpacing(8)

        # --- INICIO ---
        self._add_section_label(layout, "INICIO")
        self._add_nav_button(layout, "\U0001f3e0  Inicio", P_DASHBOARD)

        # --- HERRAMIENTAS ---
        self._add_section_label(layout, "HERRAMIENTAS")
        self._add_nav_button(layout, "\U0001f4da  Catálogo", P_CATALOG)
        self._add_nav_button(layout, "\U0001f50d  Búsqueda", P_SEARCH)
        self._add_nav_button(layout, "\U0001f4bb  Aplicaciones", P_APP)

        # --- OPERACIONES ---
        self._add_section_label(layout, "OPERACIONES")
        self._add_nav_button(layout, "\U0001f4dd  Propuestas", P_PROPOSALS)
        self._add_nav_button(layout, "\U0001f4cb  Solicitudes", P_REQUESTS)
        self._add_nav_button(layout, "\U0001f4d6  Conocimiento", P_KNOWLEDGE)
        self._add_nav_button(layout, "\U0001f527  Incidencias", P_ISSUES)

        # --- REPORTES ---
        self._add_section_label(layout, "REPORTES")
        self._add_nav_button(layout, "\U0001f4ca  Reportes", P_REPORTS)
        self._add_nav_button(layout, "\U0001f4d1  Auditoría", P_AUDIT)

        # --- ADMINISTRACIÓN (admin only) ---
        self._admin_section = self._build_admin_section(layout)

        # --- Spacer ---
        layout.addStretch()

        # --- ACCIONES (bottom) ---
        self._add_actions_section(layout)

        # --- User info ---
        user_label = QLabel(f"\U0001f464  {self._svc.user_name}")
        user_label.setFont(get_font(10))
        user_label.setStyleSheet("color: #CCCCCC; padding: 4px;")
        layout.addWidget(user_label)
        version_label = QLabel(f"v{__version__}")
        version_label.setFont(get_font(9))
        version_label.setStyleSheet("color: #888888;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        return sidebar

    def _build_admin_section(self, parent_layout: QVBoxLayout) -> QWidget | None:
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(4)
        self._add_section_label_widget(section_layout, "ADMINISTRACIÓN")
        self._add_nav_button_widget(section_layout, "\U0001f465  Gestión de Usuarios", P_USERS)
        self._add_nav_button_widget(section_layout, "\U0001f4ac  Comunidad", P_COMMUNITY)
        parent_layout.addWidget(section)
        section.setVisible(self._is_admin)
        return section

    def _add_section_label(self, layout: QVBoxLayout, text: str) -> None:
        lbl = QLabel(text)
        lbl.setFont(get_font(10, bold=True))
        lbl.setStyleSheet(NEXAStyles.sidebar_section_label())
        layout.addWidget(lbl)

    def _add_section_label_widget(self, layout: QVBoxLayout, text: str) -> None:
        lbl = QLabel(text)
        lbl.setFont(get_font(10, bold=True))
        lbl.setStyleSheet(NEXAStyles.sidebar_section_label())
        layout.addWidget(lbl)

    def _add_nav_button(self, layout: QVBoxLayout, text: str, page_key: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(NEXAStyles.sidebar_button(page_key == P_DASHBOARD))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, pk=page_key, b=btn: self._navigate_to(pk))
        layout.addWidget(btn)
        self._nav_buttons[page_key] = btn
        return btn

    def _add_nav_button_widget(self, layout: QVBoxLayout, text: str, page_key: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(NEXAStyles.sidebar_button(False))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, pk=page_key, b=btn: self._navigate_to(pk))
        layout.addWidget(btn)
        self._nav_buttons[page_key] = btn
        return btn

    def _add_actions_section(self, layout: QVBoxLayout) -> None:
        # Notification badge
        notif_row = QHBoxLayout()
        notif_btn = QPushButton("\U0001f514")
        notif_btn.setFont(get_font(14))
        notif_btn.setStyleSheet("border: none; background: transparent; color: #FFFFFF;")
        notif_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        notif_btn.clicked.connect(lambda: self._navigate_to(P_NOTIFICATIONS))
        notif_row.addWidget(notif_btn)
        self._notif_badge = QLabel("")
        self._notif_badge.setFont(get_font(9, bold=True))
        self._notif_badge.setStyleSheet(
            f"background-color: {ACCENT}; color: #FFFFFF; border-radius: 8px; "
            "padding: 1px 5px; min-width: 16px; max-width: 16px;"
        )
        self._notif_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notif_badge.hide()
        notif_row.addWidget(self._notif_badge)
        notif_row.addStretch()
        layout.addLayout(notif_row)

        # Theme toggle
        self._theme_btn = QPushButton()
        self._refresh_theme_button()
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self._theme_btn)

        # Logout button
        logout_btn = QPushButton("  \u2192  Cerrar sesión")
        logout_btn.setFont(get_font(10))
        logout_btn.setStyleSheet(NEXAStyles.ghost_button())
        logout_btn.setStyleSheet(
            "QPushButton { color: #CCCCCC; border: none; text-align: left; "
            "padding: 8px 16px; font-size: 11px; }"
            "QPushButton:hover { color: #FF5503; }"
        )
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(logout_btn)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def _create_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        header.setStyleSheet(NEXAStyles.header())
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(24, 0, 24, 0)
        hlayout.setSpacing(16)

        self._header_title = QLabel(_PAGE_TITLES.get(P_DASHBOARD, "Inicio"))
        self._header_title.setFont(get_font(16, bold=True))
        self._header_title.setStyleSheet(f"color: {Theme.text()};")
        hlayout.addWidget(self._header_title)
        hlayout.addStretch()

        self._header_search = QLineEdit()
        self._header_search.setPlaceholderText("Buscar herramientas, artículos...")
        self._header_search.setFont(get_font(12))
        self._header_search.setStyleSheet(NEXAStyles.search_input())
        self._header_search.setFixedWidth(300)
        self._header_search.returnPressed.connect(self._on_header_search)
        hlayout.addWidget(self._header_search)

        return header

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _navigate_to(self, page_key: str) -> None:
        # RBAC enforcement
        module = _PAGE_MODULE.get(page_key, page_key)
        if not self._svc.auth.check_access(self._svc.user_id, module, "ver"):
            self._show_access_denied()
            return

        page = self._get_page(page_key)
        if page is None:
            return

        self._current_page = page_key
        self._stack.setCurrentWidget(page)
        self._header_title.setText(_PAGE_TITLES.get(page_key, ""))

        # Highlight active button
        for key, btn in self._nav_buttons.items():
            btn.setStyleSheet(NEXAStyles.sidebar_button(key == page_key))

        # Trigger data refresh
        self._refresh_page(page_key)

    def _show_access_denied(self) -> None:
        self._current_page = ""
        self._stack.setCurrentWidget(self._access_denied_label)
        self._header_title.setText("Acceso denegado")
        for btn in self._nav_buttons.values():
            btn.setStyleSheet(NEXAStyles.sidebar_button(False))

    # ------------------------------------------------------------------
    # Data refresh per page
    # ------------------------------------------------------------------
    def _refresh_page(self, page_key: str) -> None:
        refreshers = {
            P_DASHBOARD: self._refresh_dashboard_bg,
            P_CATALOG: self._load_dashboard_catalog,
            P_KNOWLEDGE: self._refresh_knowledge,
            P_REQUESTS: self._refresh_requests,
            P_AUDIT: self._refresh_audit,
            P_USERS: self._refresh_users,
            P_COMMUNITY: self._refresh_feed,
            P_NOTIFICATIONS: self._refresh_notifications,
            P_REPORTS: self._refresh_reports,
            P_APP_AUDIT: self._refresh_app_audit,
        }
        refresher = refreshers.get(page_key)
        if refresher:
            refresher()

    def _refresh_dashboard_bg(self) -> None:
        def _work():
            stats = self._svc.metrics.get_stats()
            all_plugins = self._svc.catalog.get_all()
            top = sorted(all_plugins, key=lambda p: p.execution_count, reverse=True)[:6]
            fav_ids = self._svc.favorites.get_favorite_ids(self._svc.user_id)
            fav_tools = [{"name": p.name, "plugin_id": p.id, "category": p.category.value} for p in all_plugins if p.id in fav_ids][:6]
            app_health = self._svc.app_states.get_stats()
            pending = self._svc.requests.get_all()
            pending_count = len([r for r in pending if r.get("status") == "pendiente"])
            recent = self._svc.audit.get_entries(limit=5)
            return {
                "stats": stats,
                "top_plugins": [{"name": p.name, "executions": p.execution_count} for p in top],
                "favorites": fav_tools,
                "app_health": app_health,
                "pending_requests": pending_count,
                "recent_activity": [{"icon": "\U0001f4dd", "text": e.get("description", ""), "time": e.get("timestamp", "")[:16], "color": "#FF5503"} for e in recent],
            }
        worker = _BackgroundWorker(_work, self)
        worker.finished.connect(self._on_dashboard_loaded)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_dashboard_loaded(self, data) -> None:
        if data is None:
            return
        s = data["stats"]
        view = self._pages[P_DASHBOARD]
        view.update_kpi("executions", str(s["total_executions"]))
        view.update_kpi("tools", str(s["unique_plugins_used"]))
        view.update_kpi("users", str(s["total_users"]))
        view.update_kpi("projects", str(s["total_projects"]))
        view.update_kpi("requests", str(s["total_requests"]))
        view.update_kpi("articles", str(s["total_articles"]))
        view.update_kpi("posts", str(s["total_posts"]))
        view.update_kpi("incidents", str(s["open_incidents"]))
        view.set_popular_tools(data["top_plugins"])
        if data.get("favorites"):
            view.set_favorites(data["favorites"])
        if data.get("app_health"):
            view.set_app_health(data["app_health"])
        view.update_kpi("pending", str(data.get("pending_requests", 0)))
        if data.get("recent_activity"):
            view.set_activity(data["recent_activity"])

    def _load_dashboard_catalog(self) -> None:
        view = self._get_page(P_CATALOG)
        if view is None:
            return
        all_plugins = self._svc.catalog.get_all()
        fav_ids = self._svc.favorites.get_favorite_ids(self._svc.user_id)
        view.set_plugins(all_plugins)
        if hasattr(view, "set_favorites"):
            view.set_favorites(fav_ids)

    def _refresh_knowledge(self) -> None:
        view = self._get_page(P_KNOWLEDGE)
        if view is None:
            return
        articles = self._svc.knowledge.get_all()
        view.set_articles(articles)

    def _refresh_requests(self) -> None:
        view = self._get_page(P_REQUESTS)
        if view is None:
            return
        requests = self._svc.requests.get_all()
        view.set_requests(requests)

    def _refresh_audit(self) -> None:
        view = self._get_page(P_AUDIT)
        if view is None:
            return
        entries = self._svc.audit.get_entries(limit=200)
        count = self._svc.audit.get_entry_count()
        view.set_entries(entries, count)

    def _refresh_users(self) -> None:
        view = self._get_page(P_USERS)
        if view is None:
            return
        users = self._svc.auth.get_all_users()
        view.set_users(users)

    def _refresh_feed(self) -> None:
        view = self._get_page(P_COMMUNITY)
        if view is None:
            return
        posts = self._svc.feed.get_feed(self._svc.user_id)
        view.set_posts(posts)

    def _refresh_notifications(self) -> None:
        notifs = self._svc.notifications.get_all(self._svc.user_id)
        view = self._pages.get(P_NOTIFICATIONS)  # no forzar lazy-create desde notif badge
        if view is not None:
            view.set_notifications(notifs)
        count = len(notifs)
        if count > 0:
            self._notif_badge.setText(str(count))
            self._notif_badge.show()
        else:
            self._notif_badge.hide()

    def _refresh_reports(self) -> None:
        def _work():
            stats = self._svc.reports.get_stats(self._svc.user_id)
            reports = self._svc.reports.get_all(user_id=self._svc.user_id, limit=100)
            all_plugins = self._svc.catalog.get_all()
            plugin_names = {p.id: p.name for p in all_plugins}
            for r in reports:
                r["plugin_name"] = plugin_names.get(r.get("plugin_id", ""), r.get("plugin_id", ""))
            return {"stats": stats, "reports": reports, "plugins": all_plugins}
        worker = _BackgroundWorker(_work, self)
        worker.finished.connect(self._on_reports_loaded)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_reports_loaded(self, data) -> None:
        if data is None:
            return
        view = self._pages.get(P_REPORTS)
        if view is None:
            return
        if hasattr(view, "set_stats"):
            view.set_stats(data["stats"])
        if hasattr(view, "set_reports"):
            view.set_reports(data["reports"])
        plugin_names = [p.name for p in data.get("plugins", [])]
        if hasattr(view, "set_plugin_filter"):
            view.set_plugin_filter(plugin_names)

    def _refresh_app_audit(self) -> None:
        def _work():
            all_plugins = list(self._svc.registry.plugins.values())
            app_states = self._svc.app_states.get_all_states()
            state_map = {s["plugin_id"]: s for s in app_states}
            app_data = []
            for p in all_plugins:
                st = state_map.get(p.id, {"state": "activo", "failure_count": 0, "last_execution_at": "", "last_update_at": ""})
                app_data.append({
                    "plugin_id": p.id,
                    "name": p.name,
                    "state": st.get("state", "activo"),
                    "failure_count": st.get("failure_count", 0),
                    "last_execution_at": st.get("last_execution_at", ""),
                    "last_update_at": st.get("last_update_at", ""),
                })
            return app_data
        worker = _BackgroundWorker(_work, self)
        worker.finished.connect(self._on_app_audit_loaded)
        worker.finished.connect(lambda _: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_app_audit_loaded(self, data) -> None:
        if data is None:
            return
        view = self._pages.get(P_APP_AUDIT)

        if hasattr(view, "set_app_data"):
            view.set_app_data(data)

    def _cleanup_worker(self, worker: _BackgroundWorker) -> None:
        try:
            self._workers.remove(worker)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _on_plugin_clicked(self, plugin_id_or_query: str) -> None:
        desc = self._svc.registry.get(plugin_id_or_query)
        if desc:
            app_page = self._get_page(P_APP)
            if app_page:
                app_page.load_plugin(plugin_id_or_query)
            self._navigate_to(P_APP)
            self._header_title.setText(desc.name)
            self._svc.audit.log(
                self._svc.user_id, "view", "plugins", "plugin",
                plugin_id_or_query, desc.name,
            )
        else:
            results = self._svc.registry.search(plugin_id_or_query)
            search_page = self._get_page(P_SEARCH)
            if search_page:
                search_page.show_results(plugin_id_or_query, results)
            self._navigate_to(P_SEARCH)
            self._svc.opportunities.record_search(plugin_id_or_query, len(results))

    def _on_header_search(self) -> None:
        query = self._header_search.text().strip()
        if not query:
            return
        results = self._svc.registry.search(query)
        search_page = self._get_page(P_SEARCH)
        if search_page:
            search_page.show_results(query, results)
        self._navigate_to(P_SEARCH)
        self._svc.metrics.record_search(query, len(results), self._svc.user_id)
        self._svc.opportunities.record_search(query, len(results))

    def _go_back(self) -> None:
        self._navigate_to(P_DASHBOARD)

    def _on_favorite_toggled(self, plugin_id: str, is_favorite: bool) -> None:
        if is_favorite:
            self._svc.favorites.add_favorite(self._svc.user_id, plugin_id)
        else:
            self._svc.favorites.remove_favorite(self._svc.user_id, plugin_id)
        self._svc.audit.log(
            self._svc.user_id,
            "favorite" if is_favorite else "unfavorite",
            "plugins", "plugin", plugin_id,
        )
        self._load_dashboard_catalog()

    def _on_proposal_submitted(self, data: dict) -> None:
        req_id = self._svc.requests.create(
            user_id=self._svc.user_id, request_type="idea",
            title=data.get("task", ""), description=data.get("task", ""),
            area=self._svc.user_area, frequency=data.get("frequency", ""),
            tools_used=data.get("tools", ""), steps=data.get("steps", ""),
            created_by=self._svc.user_id,
        )
        self._svc.audit.log_create(self._svc.user_id, "requests", "request", str(req_id))

    def _on_issue_submitted(self, data: dict) -> None:
        req_id = self._svc.requests.create(
            user_id=self._svc.user_id, request_type="incidente",
            title=data.get("title", ""), description=data.get("what_happened", ""),
            area=self._svc.user_area, created_by=self._svc.user_id,
        )
        self._svc.audit.log_create(self._svc.user_id, "requests", "request", str(req_id))

    def _on_audit_failure_clicked(self, failure_id: str) -> None:
        view = self._get_page(P_FAILURE_DETAIL)
        if view and hasattr(view, "load_failure"):
            view.load_failure(failure_id)
        self._navigate_to(P_FAILURE_DETAIL)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def _toggle_theme(self) -> None:
        self._theme_mode = "light" if self._theme_mode == "dark" else "dark"
        set_theme(self._theme_mode)
        save_theme(self._theme_mode)
        self._refresh_theme_button()
        self.apply_theme()

    def _refresh_theme_button(self) -> None:
        icon = "\u2600\ufe0f" if self._theme_mode == "dark" else "\U0001f319"
        self._theme_btn.setText(f"  {icon}  {'Claro' if self._theme_mode == 'dark' else 'Oscuro'}")
        self._theme_btn.setFont(get_font(10))
        self._theme_btn.setStyleSheet(
            "QPushButton { color: #CCCCCC; border: none; text-align: left; "
            "padding: 8px 16px; font-size: 11px; }"
            "QPushButton:hover { color: #FF5503; }"
        )

    def apply_theme(self) -> None:
        if not self._pages:
            return
        self.setStyleSheet(f"QWidget {{ font-family: 'Segoe UI'; background-color: {Theme.bg()}; color: {Theme.text()}; }}")
        self._header_title.setStyleSheet(f"color: {Theme.text()};")
        if hasattr(self, "_header_search"):
            self._header_search.setStyleSheet(NEXAStyles.search_input())
        for key, page in self._pages.items():
            if hasattr(page, "refresh_style"):
                page.refresh_style()

    # ------------------------------------------------------------------
    # Login / Logout
    # ------------------------------------------------------------------
    def login_success(self, user_data: dict[str, Any]) -> None:
        """Slot: called by LoginView after successful authentication."""
        self.setup_ui(user_data)
        self._refresh_dashboard_bg()
        self._refresh_notifications()

    def _on_logout(self) -> None:
        reply = QMessageBox.question(
            self, "Cerrar sesión",
            "¿Está seguro que desea cerrar sesión?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            token = self._current_user.get("token", "") if self._current_user else ""
            if token:
                self._svc.auth.logout(token)
            self._disconnect_all()
            self._current_user = None
            self._is_admin = False
            self._svc.current_user = None
            self.logout_requested.emit()

    def _disconnect_all(self) -> None:
        for worker in list(self._workers):
            worker.quit()
            worker.wait(2000)
        self._workers.clear()
        self._nav_buttons.clear()
        self._pages.clear()

    # ------------------------------------------------------------------
    # Show / Close events
    # ------------------------------------------------------------------
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        # Verificar que _pages esté inicializado antes de hacer refresh
        # (puede dispararse durante la construcción del widget).
        if self._current_user and self._pages:
            self._refresh_dashboard_bg()
