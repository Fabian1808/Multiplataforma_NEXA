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
    QStackedWidget, QVBoxLayout, QWidget, QMessageBox, QScrollArea,
)

from hub.ui.common.design import Icon

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
# Sidebar nav item (icono + texto con estado activo/hover)
# ---------------------------------------------------------------------------
class _NavItem(QWidget):
    """Ítem de navegación del sidebar: icono lineal + etiqueta.

    Estado activo: barra de acento a la izquierda + fondo sutil, sin bloques
    pesados. Navegación limpia tipo SaaS.
    """

    def __init__(self, icon_name: str, text: str, page_key: str,
                 on_click, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_key = page_key
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        self._indicator = QFrame()
        self._indicator.setFixedSize(3, 20)
        self._indicator.setStyleSheet("border: none;")

        layout_ind = QVBoxLayout(self._indicator)

        self._icon = Icon(icon_name, 18)
        self._icon.set_color(Theme.text_secondary())
        self._label = QLabel(text)
        self._label.setFont(get_font(13, weight=600 if self._active else 400))

        lay.addWidget(self._indicator)
        lay.addWidget(self._icon)
        lay.addWidget(self._label)
        lay.addStretch()

        self._on_click = on_click
        self._apply_style()

    def _apply_style(self) -> None:
        if self._active:
            bg = Theme.active_bg()
            tx = ACCENT
            ind = ACCENT
            weight = 600
        else:
            bg = "transparent"
            tx = Theme.text() if not is_dark() else "#EDEDF3"
            ind = "transparent"
            weight = 400
        self._indicator.setStyleSheet(f"background-color: {ind}; border-radius: 2px; border: none;")
        self._icon.set_color(tx)
        self._label.setStyleSheet(f"color: {tx}; background: transparent; border: none;")
        self._label.setFont(get_font(13, weight=weight))
        self.setStyleSheet(
            f"_NavItem {{ background-color: {bg}; border-radius: 8px; }}"
        )

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_style()

    def mousePressEvent(self, event) -> None:
        if self._on_click:
            self._on_click(self._page_key)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # hover
        if not self._active:
            bg = Theme.hover_bg()
            self.setStyleSheet(f"_NavItem {{ background-color: {bg}; border-radius: 8px; }}")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style()
        super().leaveEvent(event)


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
        self._nav_buttons: dict[str, _NavItem] = {}
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

        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Logo ----
        logo_frame = QFrame()
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(20, 18, 20, 14)
        logo_layout.setSpacing(10)
        logo_icon = Icon("plugin", 22)
        logo_icon.set_color(ACCENT)
        logo_layout.addWidget(logo_icon)
        logo_text = QLabel("NEXA")
        logo_text.setFont(get_font(17, weight=700))
        logo_text.setStyleSheet(
            f"color: {Theme.text() if not is_dark() else '#FFFFFF'}; background: transparent; border: none;")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        outer.addWidget(logo_frame)

        # ---- Navegación (scrollable) ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        nav_widget = QWidget()
        nav_widget.setObjectName("sidebarNav")
        nav_widget.setStyleSheet(f"QWidget#sidebarNav {{ background: {Theme.sidebar_bg()}; }}")
        layout = QVBoxLayout(nav_widget)
        layout.setContentsMargins(12, 4, 12, 12)
        layout.setSpacing(2)

        # --- INICIO ---
        self._add_section_label(layout, "INICIO")
        self._add_nav_item(layout, "home", "Inicio", P_DASHBOARD)

        # --- HERRAMIENTAS ---
        self._add_section_label(layout, "HERRAMIENTAS")
        self._add_nav_item(layout, "grid", "Catálogo", P_CATALOG)
        self._add_nav_item(layout, "search", "Búsqueda", P_SEARCH)
        self._add_nav_item(layout, "apps", "Aplicaciones", P_APP)

        # --- OPERACIONES ---
        self._add_section_label(layout, "OPERACIONES")
        self._add_nav_item(layout, "file", "Propuestas", P_PROPOSALS)
        self._add_nav_item(layout, "list", "Solicitudes", P_REQUESTS)
        self._add_nav_item(layout, "book", "Conocimiento", P_KNOWLEDGE)
        self._add_nav_item(layout, "wrench", "Incidencias", P_ISSUES)

        # --- REPORTES ---
        self._add_section_label(layout, "REPORTES")
        self._add_nav_item(layout, "chart", "Reportes", P_REPORTS)
        self._add_nav_item(layout, "shield", "Auditoría", P_AUDIT)

        # --- ADMINISTRACIÓN (admin only) ---
        self._admin_section = self._build_admin_section(layout)

        layout.addStretch()
        scroll.setWidget(nav_widget)
        outer.addWidget(scroll, stretch=1)

        # ---- Acciones inferiores + Perfil ----
        outer.addWidget(self._build_bottom_panel())

        return sidebar

    def _build_admin_section(self, parent_layout: QVBoxLayout) -> QWidget | None:
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 6, 0, 0)
        section_layout.setSpacing(2)
        self._add_section_label_widget(section_layout, "ADMINISTRACIÓN")
        self._add_nav_item(section_layout, "users", "Gestión de Usuarios", P_USERS)
        self._add_nav_item(section_layout, "activity", "Comunidad", P_COMMUNITY)
        parent_layout.addWidget(section)
        section.setVisible(self._is_admin)
        return section

    def _add_section_label(self, layout: QVBoxLayout, text: str) -> None:
        lbl = QLabel(text)
        lbl.setFont(get_font(10, weight=700))
        lbl.setStyleSheet(NEXAStyles.sidebar_section_label())
        layout.addWidget(lbl)

    def _add_section_label_widget(self, layout: QVBoxLayout, text: str) -> None:
        lbl = QLabel(text)
        lbl.setFont(get_font(10, weight=700))
        lbl.setStyleSheet(NEXAStyles.sidebar_section_label())
        layout.addWidget(lbl)

    def _add_nav_item(self, layout: QVBoxLayout, icon: str, text: str, page_key: str) -> None:
        item = _NavItem(icon, text, page_key, self._navigate_to)
        item.set_active(page_key == P_DASHBOARD)
        layout.addWidget(item)
        self._nav_buttons[page_key] = item

    def _build_bottom_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("sidebarUser")
        panel.setStyleSheet(NEXAStyles.sidebar_user_box())
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(2)

        # Acciones: notificaciones / apariencia
        actions = QHBoxLayout()
        actions.setSpacing(4)

        notif_btn = Icon("bell", 17)
        notif_btn.set_color(Theme.text_secondary())
        notif_frame = QFrame()
        nf = QHBoxLayout(notif_frame)
        nf.setContentsMargins(8, 6, 8, 6)
        nf.addWidget(notif_btn)
        self._notif_badge = QLabel("")
        self._notif_badge.setFont(get_font(9, weight=700))
        self._notif_badge.setStyleSheet(
            f"background-color: {ACCENT}; color: #FFFFFF; border-radius: 8px; "
            "padding: 1px 5px; min-width: 14px; max-width: 14px;")
        self._notif_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notif_badge.hide()
        nf.addWidget(self._notif_badge)
        notif_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        notif_frame.setStyleSheet(f"QFrame {{ border: none; background: transparent; border-radius: 6px; }}")
        notif_frame.mousePressEvent = lambda e: self._navigate_to(P_NOTIFICATIONS)
        actions.addWidget(notif_frame)

        # Theme toggle (preferencias de apariencia)
        self._theme_icon = Icon("sun" if is_dark() else "moon", 17)
        self._theme_icon.set_color(Theme.text_secondary())
        self._theme_frame = QFrame()
        tf = QHBoxLayout(self._theme_frame)
        tf.setContentsMargins(8, 6, 8, 6)
        tf.addWidget(self._theme_icon)
        self._theme_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_frame.setStyleSheet(f"QFrame {{ border: none; background: transparent; border-radius: 6px; }}")
        self._theme_frame.mousePressEvent = lambda e: self._toggle_theme()
        actions.addWidget(self._theme_frame)

        actions.addStretch()
        v.addLayout(actions)

        # Lista de acciones texto (Preferencias / Apariencia)
        self._prefs_row = self._make_text_action("settings", "Preferencias")
        self._prefs_row.mousePressEvent = lambda e: self._navigate_to(P_NOTIFICATIONS)
        v.addWidget(self._prefs_row)

        # ---- Perfil ----
        profile = self._make_profile_row()
        v.addSpacing(6)
        v.addWidget(profile)

        return panel

    def _make_text_action(self, icon: str, text: str) -> QWidget:
        row = QWidget()
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setFixedHeight(34)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(8)
        ico = Icon(icon, 15)
        ico.set_color(Theme.text_secondary())
        lbl = QLabel(text)
        lbl.setFont(get_font(11))
        lbl.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        lay.addWidget(ico)
        lay.addWidget(lbl)
        lay.addStretch()
        return row

    def _make_profile_row(self) -> QWidget:
        row = QFrame()
        row.setObjectName("sidebarUserCard")
        row.setStyleSheet(
            f"QFrame#sidebarUserCard {{ background-color: {Theme.hover_bg()}; "
            f"border-radius: 10px; }}")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        avatar = QFrame()
        avatar.setFixedSize(34, 34)
        avatar.setStyleSheet(
            f"background-color: {ACCENT}; border-radius: 17px; border: none;")
        av_l = QVBoxLayout(avatar)
        av_l.setContentsMargins(0, 0, 0, 0)
        initial = QLabel((self._svc.user_name or "?")[0].upper())
        initial.setFont(get_font(13, weight=700))
        initial.setStyleSheet("color: #FFFFFF; background: transparent;")
        initial.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av_l.addWidget(initial)
        lay.addWidget(avatar)

        col = QVBoxLayout()
        col.setSpacing(0)
        name = QLabel(self._svc.user_name or "")
        name.setFont(get_font(12, weight=600))
        name.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        role = QLabel("Administrador" if self._is_admin else "Colaborador")
        role.setFont(get_font(10))
        role.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        col.addWidget(name)
        col.addWidget(role)
        lay.addLayout(col, stretch=1)

        logout_icon = Icon("logout", 16)
        logout_icon.set_color(Theme.text_secondary())
        lay.addWidget(logout_icon)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.mousePressEvent = lambda e: self._on_logout()
        return row

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

        # Título / breadcrumb
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        self._header_crumb = QLabel("NEXA Productivity Hub")
        self._header_crumb.setFont(get_font(10))
        self._header_crumb.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        title_col.addWidget(self._header_crumb)
        self._header_title = QLabel(_PAGE_TITLES.get(P_DASHBOARD, "Inicio"))
        self._header_title.setFont(get_font(16, weight=700))
        self._header_title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        title_col.addWidget(self._header_title)
        hlayout.addLayout(title_col)

        hlayout.addStretch()

        # Buscador global (componente moderno, no caja gigante)
        search_box = QWidget()
        search_box.setObjectName("globalSearch")
        search_box.setStyleSheet(f"""
            QWidget#globalSearch {{
                background-color: {Theme.input_bg()};
                border: 1px solid {Theme.border()};
                border-radius: 10px;
            }}
        """)
        s_lay = QHBoxLayout(search_box)
        s_lay.setContentsMargins(10, 0, 6, 0)
        s_lay.setSpacing(8)
        s_icon = Icon("search", 15)
        s_icon.set_color(Theme.text_muted())
        s_lay.addWidget(s_icon)
        self._header_search = QLineEdit()
        self._header_search.setPlaceholderText("Buscar...")
        self._header_search.setFont(get_font(12))
        self._header_search.setStyleSheet(
            f"QLineEdit {{ border: none; background: transparent; color: {Theme.text()}; "
            f"font-size: 12px; }}"
            f"QLineEdit::placeholder {{ color: {Theme.text_muted()}; }}")
        self._header_search.setFixedWidth(240)
        self._header_search.returnPressed.connect(self._on_header_search)
        s_lay.addWidget(self._header_search)
        kbd = QLabel("⌘K")
        kbd.setFont(get_font(9))
        kbd.setStyleSheet(f"color: {Theme.text_muted()}; background: {Theme.hover_bg()}; "
                          f"border-radius: 4px; padding: 2px 6px;")
        s_lay.addWidget(kbd)
        hlayout.addWidget(search_box)

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
        self._header_crumb.setText(self._page_crumb(page_key))

        # Highlight active button
        for key, item in self._nav_buttons.items():
            item.set_active(key == page_key)

        # Trigger data refresh
        self._refresh_page(page_key)

    def _page_crumb(self, page_key: str) -> str:
        return f"NEXA / {_PAGE_TITLES.get(page_key, '')}"

    def _show_access_denied(self) -> None:
        self._current_page = ""
        self._stack.setCurrentWidget(self._access_denied_label)
        self._header_title.setText("Acceso denegado")
        self._header_crumb.setText("NEXA / Acceso denegado")
        for item in self._nav_buttons.values():
            item.set_active(False)

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
                "recent_activity": [{"icon": "\u25cf", "text": e.get("description", ""), "time": e.get("timestamp", "")[:16], "color": "#FF5503"} for e in recent],
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
        if hasattr(self, "_theme_icon"):
            self._theme_icon.set_icon("sun" if self._theme_mode == "dark" else "moon")
            self._theme_icon.set_color(Theme.text_secondary())

    def apply_theme(self) -> None:
        if not self._pages:
            return
        self.setStyleSheet(f"QWidget {{ font-family: 'Segoe UI'; background-color: {Theme.bg()}; color: {Theme.text()}; }}")
        self._header_title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        if hasattr(self, "_header_crumb"):
            self._header_crumb.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        if hasattr(self, "_header_search"):
            self._header_search.setStyleSheet(
                f"QLineEdit {{ border: none; background: transparent; color: {Theme.text()}; "
                f"font-size: 12px; }}"
                f"QLineEdit::placeholder {{ color: {Theme.text_muted()}; }}")
        if hasattr(self, "_sidebar") and self._sidebar is not None:
            self._sidebar.setStyleSheet(NEXAStyles.sidebar())
        self._refresh_theme_button()
        for item in self._nav_buttons.values():
            item.set_active(item._page_key == self._current_page)
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
