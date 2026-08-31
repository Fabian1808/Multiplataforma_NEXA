"""UI Shell — Ventana principal del NEXA Productivity Hub v2.0.

RBAC-based navigation, login flow, dark/light theme, all views integrated.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    Qt, Signal, QThread, QVariantAnimation, QEasingCurve,
)
from PySide6.QtGui import QShowEvent, QColor, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QMessageBox, QScrollArea,
    QSystemTrayIcon, QMenu
)

from hub import __app_name__, __version__
from hub.core.service_container import ServiceContainer
from hub.i18n import tr, get_lang, set_lang, on_lang_change, off_lang_change
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
    Theme,
    NEXAStyles,
    ACCENT,
    Icon,
    SvgIcon,
    get_font,
    is_dark,
    get_theme,
    set_theme,
    save_theme,
)
from hub.ui.dashboard.enhanced_dashboard_view import EnhancedDashboardView
from hub.ui.reports.reports_center_view import ReportsCenterView
from hub.ui.search.search_view import SearchView

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logo corporativo (assets/logo_brand.png). Si falta, se usa el wordmark NEXA.
# ---------------------------------------------------------------------------
_LOGO_PATH_CACHE: str | None = None


def _logo_path() -> str | None:
    global _LOGO_PATH_CACHE
    if _LOGO_PATH_CACHE is None:
        p = Path(__file__).resolve().parent.parent.parent / "assets" / "logo_brand.png"
        _LOGO_PATH_CACHE = str(p) if p.is_file() else None
    return _LOGO_PATH_CACHE


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
    P_DASHBOARD: tr("nav.dashboard"),
    P_CATALOG:   tr("nav.catalog"),
    P_SEARCH:    tr("nav.search"),
    P_APP:       tr("nav.app"),
    P_PROPOSALS: tr("nav.proposals"),
    P_REQUESTS:  tr("nav.requests"),
    P_KNOWLEDGE: tr("nav.knowledge"),
    P_ISSUES:    tr("nav.issues"),
    P_REPORTS:   tr("nav.reports"),
    P_AUDIT:     tr("nav.audit"),
    P_USERS:     tr("nav.users"),
    P_COMMUNITY: tr("nav.community"),
    P_APP_AUDIT: tr("nav.app_audit"),
    P_FAILURE_DETAIL: tr("nav.failure"),
    P_NOTIFICATIONS:  tr("nav.notifications"),
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
    """Ítem de navegación del sidebar.

    Estructura idéntica en todos los ítems: [accent 3px] [icono 20px] [gap 12px] Texto.
    Estados normal / hover (160 ms de transición) / activo (barra acento), foco de
    teclado visible y tooltip para accesibilidad y modo colapsado.
    """

    def __init__(self, icon_name: str, text: str, page_key: str,
                 on_click, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_key = page_key
        self._active = False
        self._hovered = False
        self._focused = False
        self._cur_bg = QColor(0, 0, 0, 0)
        self._comp: dict | None = None
        self._pending: dict | None = None
        self.setObjectName("navItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"Sección {text}")
        self.setToolTip(text)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(10, 0, 10, 0)
        self._layout.setSpacing(11)

        self._accent = QFrame()
        self._accent.setObjectName("accent")
        self._accent.setFixedSize(3, 20)

        self._icon = SvgIcon(icon_name, 20)
        self._icon.setFixedSize(24, 24)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(text)
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self._layout.addWidget(self._accent)
        self._layout.addWidget(self._icon)
        self._layout.addWidget(self._label)
        self._layout.addStretch()

        self._on_click = on_click

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)

        self.refresh_theme()

    # ------------------------------------------------------------------
    def _state(self) -> dict:
        if self._active:
            return {
                "bg":  QColor(Theme.sidebar_active_bg()),
                "tx":  Theme.sidebar_active(),
                "ic":  Theme.sidebar_active(),
                "acc": Theme.sidebar_active(),
                "w":   600,
            }
        if self._hovered:
            return {
                "bg":  QColor(Theme.sidebar_hover()),
                "tx":  Theme.sidebar_text(),
                "ic":  Theme.sidebar_text(),
                "acc": "transparent",
                "w":   500,
            }
        return {
            "bg":  QColor(0, 0, 0, 0),
            "tx":  Theme.sidebar_text(),
            "ic":  Theme.sidebar_icon(),
            "acc": "transparent",
            "w":   500,
        }

    def _apply_state(self, instant: bool = False) -> None:
        st = self._state()
        end = QColor(st["bg"])
        self._pending = st
        if instant or self._cur_bg == end:
            self._anim.stop()
            self._cur_bg = end
            self._comp = st
            self._render()
            return
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur_bg))
        self._anim.setEndValue(end)
        self._anim.start()

    def _on_anim_value(self, value) -> None:
        self._cur_bg = QColor(value)
        self._comp = self._pending or self._state()
        self._render()

    def _render(self) -> None:
        bg  = self._cur_bg.name(QColor.NameFormat.HexArgb)
        st  = self._comp or self._state()
        foc = (Theme.sidebar_active() + "66") if self._focused else "transparent"
        self._accent.setStyleSheet(
            f"QFrame#accent {{ background-color: {st['acc']}; border-radius: 2px; border: none; }}"
        )
        self._icon.set_color(st["ic"])
        self._label.setObjectName("navItemLabel")
        self._label.setStyleSheet(
            f"QLabel#navItemLabel {{ color: {st['tx']}; background: transparent; border: none; }}")
        self._label.setFont(get_font(13, weight=st["w"]))
        self.setStyleSheet(
            f"_NavItem#navItem {{ background-color: {bg};"
            f" border: 1px solid {foc}; border-radius: 8px; }}"
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def set_active(self, active: bool) -> None:
        if self._active == active:
            return
        self._active = active
        self._hovered = False
        self._apply_state()

    def refresh_theme(self) -> None:
        self._apply_state(instant=True)

    def set_collapsed(self, collapsed: bool) -> None:
        self._label.setVisible(not collapsed)
        if collapsed:
            self._accent.setVisible(False)
            self._layout.setContentsMargins(20, 0, 20, 0)
            self._layout.setSpacing(0)
        else:
            self._accent.setVisible(True)
            self._layout.setContentsMargins(10, 0, 10, 0)
            self._layout.setSpacing(11)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if self._on_click:
            self._on_click(self._page_key)
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self._on_click:
                self._on_click(self._page_key)
            event.accept()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event) -> None:  # hover
        if not self._active:
            self._hovered = True
            self._apply_state()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._apply_state()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self._focused = True
        self._render()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._focused = False
        self._render()
        super().focusOutEvent(event)


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

        self._access_denied_label = QLabel(tr("access.denied"))
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
        view.article_clicked.connect(self._on_search_article_clicked)
        return view

    def _create_app_viewer(self) -> AppViewer:
        view = AppViewer(self._svc.registry, launcher=self._svc.app_launcher)
        view.back_clicked.connect(self._go_back)
        view.favorite_toggled.connect(self._on_favorite_toggled)
        return view

    def _create_proposals(self) -> AutomationProposalView:
        view = AutomationProposalView()
        view.submitted.connect(self._on_proposal_submitted)
        return view

    def _create_requests(self) -> RequestsView:
        view = RequestsView()
        view.request_selected.connect(self._show_request_detail)
        return view

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
        view = UserManagementView(
            auth=self._svc.auth,
            audit=self._svc.audit,
            current_user_id=self._svc.user_id,
        )
        view.data_changed.connect(self._refresh_users)
        roles = [r["name"] for r in self._svc.auth.get_all_roles()]
        view.set_roles(roles)
        return view

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
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar.setStyleSheet(NEXAStyles.sidebar())
        self._sidebar = sidebar
        self._sidebar_collapsed = False
        self._sidebar_icons: list[Icon] = []
        self._hover_frames: list[QFrame] = []

        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_brand_row())
        outer.addWidget(self._build_nav_scroll(), stretch=1)
        outer.addWidget(self._build_bottom_panel())

        sidebar.setFixedWidth(NEXAStyles.SIDEBAR_WIDTH)
        return sidebar

    def _build_brand_row(self) -> QWidget:
        row = QWidget()
        row.setObjectName("sidebarBrand")
        self._brand_row_layout = QHBoxLayout(row)
        self._brand_row_layout.setContentsMargins(12, 12, 10, 12)
        self._brand_row_layout.setSpacing(8)

        self._logo_card = QFrame()
        self._logo_card.setObjectName("logoCard")
        self._logo_card.setFixedHeight(42)
        self._logo_card.setStyleSheet(NEXAStyles.logo_card())
        card_lay = QHBoxLayout(self._logo_card)
        card_lay.setContentsMargins(8, 4, 8, 4)
        card_lay.setSpacing(6)

        self._brand_logo = QLabel()
        self._brand_logo.setObjectName("brandLogo")
        if _logo_path():
            pm = QPixmap(_logo_path())
            pm = pm.scaledToHeight(32, Qt.TransformationMode.SmoothTransformation)
            self._brand_logo.setPixmap(pm)
            self._brand_logo.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        else:
            self._brand_logo.setText("NEXA")
            self._brand_logo.setFont(get_font(16, weight=700))
        self._brand_logo.setStyleSheet("QLabel#brandLogo { background: transparent; border: none; }")
        card_lay.addWidget(self._brand_logo)
        card_lay.addStretch()
        self._brand_row_layout.addWidget(self._logo_card, stretch=1)

        self._collapse_btn = self._make_icon_btn("menu", "Contraer menú", self._toggle_sidebar)
        self._collapse_btn_icon = self._collapse_btn.icon

        self._brand_row_layout.addWidget(self._collapse_btn)

        self._hover_frames.append(self._collapse_btn)
        return row

    def _build_nav_scroll(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(NEXAStyles.scroll_area())
        nav_widget = QWidget()
        nav_widget.setObjectName("sidebarNav")
        nav_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        nav_widget.setStyleSheet(f"QWidget#sidebarNav {{ background: {Theme.sidebar_bg()}; }}")
        self._nav_layout = layout = QVBoxLayout(nav_widget)
        layout.setContentsMargins(12, 6, 12, 16)
        layout.setSpacing(2)

        self._section_labels: list[QLabel] = []

        groups = [
            (tr("section.main"), [
                ("inicio",         tr("nav.dashboard"),   P_DASHBOARD),
                ("catalogo",       tr("nav.catalog"),     P_CATALOG),
                ("buscar",         tr("nav.search"),      P_SEARCH),
            ]),
            (tr("section.manage"), [
                ("propuestas",     tr("nav.proposals"),   P_PROPOSALS),
                ("solicitudes",    tr("nav.requests"),    P_REQUESTS),
                ("incidencias",    tr("nav.issues"),      P_ISSUES),
                ("comunidad",      tr("nav.community"),   P_COMMUNITY),
            ]),
        ]
        for title, items in groups:
            self._add_section_label(layout, title)
            for icon, text, page_key in items:
                self._add_nav_item(layout, icon, text, page_key)

        # --- ADMINISTRACIÓN (admin only) ---
        self._admin_section = self._build_admin_section(layout)

        layout.addStretch()
        scroll.setWidget(nav_widget)
        return scroll

    def _build_admin_section(self, parent_layout: QVBoxLayout) -> QWidget | None:
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 6, 0, 0)
        section_layout.setSpacing(2)
        self._add_section_label(section_layout, tr("section.admin"))
        self._add_nav_item(section_layout, "reportes",   tr("nav.reports"),  P_REPORTS)
        self._add_nav_item(section_layout, "auditoria",  tr("nav.audit"),    P_AUDIT)
        self._add_nav_item(section_layout, "usuarios",   tr("nav.users"),    P_USERS)
        parent_layout.addWidget(section)
        section.setVisible(self._is_admin)
        return section

    def _add_section_label(self, layout: QVBoxLayout, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sidebarSectionLabel")
        lbl.setFont(get_font(10, weight=600))
        lbl.setStyleSheet(NEXAStyles.sidebar_section_label())
        layout.addWidget(lbl)
        self._section_labels.append(lbl)
        return lbl

    def _add_nav_item(self, layout: QVBoxLayout, icon: str, text: str, page_key: str) -> _NavItem:
        item = _NavItem(icon, text, page_key, self._navigate_to)
        item.set_active(page_key == P_DASHBOARD)
        layout.addWidget(item)
        self._nav_buttons[page_key] = item
        return item

    # ------------------------------------------------------------------
    def _make_icon_btn(self, icon_name: str, tooltip: str, handler) -> QFrame:
        fr = QFrame()
        fr.setFixedSize(30, 30)
        fr.setCursor(Qt.CursorShape.PointingHandCursor)
        fr.setToolTip(tooltip)
        ico = SvgIcon(icon_name, 16)
        ico.set_color(Theme.sidebar_text_secondary())
        lay = QHBoxLayout(fr)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(ico, 0, Qt.AlignmentFlag.AlignCenter)
        fr.icon = ico
        fr.mousePressEvent = lambda e: handler()
        self._sidebar_icons.append(ico)
        self._hover_frames.append(fr)
        return fr

    def _build_theme_toggle(self) -> QWidget:
        """Pill sol/luna para el SIDEBAR (ya no se usa, mantenido por compatibilidad)."""
        self._pill_icons: dict[str, Icon] = {}
        self._theme_pill = QFrame()
        self._theme_pill.setObjectName("themePill")
        self._theme_pill.setFixedHeight(32)
        self._theme_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_pill.setToolTip(tr("header.theme_dark"))
        lay = QHBoxLayout(self._theme_pill)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pill_sun = self._make_pill_btn("sun", tr("header.theme_light"), lambda: self._set_theme("light"))
        self._pill_moon = self._make_pill_btn("moon", tr("header.theme_dark"), lambda: self._set_theme("dark"))
        lay.addWidget(self._pill_sun)
        lay.addWidget(self._pill_moon)
        self._hover_frames.append(self._theme_pill)
        return self._theme_pill

    def _make_pill_btn(self, icon_name: str, tooltip: str, handler) -> QFrame:
        fr = QFrame()
        fr.setFixedSize(26, 26)
        fr.setCursor(Qt.CursorShape.PointingHandCursor)
        fr.setToolTip(tooltip)
        ico = Icon(icon_name, 15)
        lay = QHBoxLayout(fr)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(ico, 0, Qt.AlignmentFlag.AlignCenter)
        fr.mousePressEvent = lambda e: handler()
        self._pill_icons[icon_name] = ico
        return fr

    # ------------------------------------------------------------------
    def _build_bottom_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("sidebarUser")
        panel.setStyleSheet(NEXAStyles.sidebar_user_box())
        self._sidebar_bottom = panel
        self._v_col = v = QVBoxLayout(panel)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(2)

        # Notificaciones
        self._actions_row = QWidget()
        actions = QHBoxLayout(self._actions_row)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)

        actions.addStretch()
        v.addWidget(self._actions_row)

        # ---- Perfil ----
        v.addSpacing(6)
        v.addWidget(self._make_profile_row())

        return panel

    def _make_text_action(self, icon: str, text: str) -> QWidget:
        row = QWidget()
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setFixedHeight(34)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(8)
        ico = Icon(icon, 15)
        ico.set_color(Theme.sidebar_text_secondary())
        self._sidebar_icons.append(ico)
        self._prefs_label = QLabel(text)
        self._prefs_label.setObjectName("prefsLabel")
        self._prefs_label.setFont(get_font(11))
        self._prefs_label.setStyleSheet(
            f"QLabel#prefsLabel {{ color: {Theme.sidebar_text_secondary()};"
            " background: transparent; border: none; }}")
        lay.addWidget(ico)
        lay.addWidget(self._prefs_label)
        lay.addStretch()
        self._hover_frames.append(row)
        return row

    def _make_profile_row(self) -> QWidget:
        row = QFrame()
        row.setObjectName("sidebarUserCard")
        self._profile_card = row
        self._profile_layout = QHBoxLayout(row)
        self._profile_layout.setContentsMargins(12, 10, 12, 10)
        self._profile_layout.setSpacing(10)

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
        self._profile_layout.addWidget(avatar)

        col = QVBoxLayout()
        col.setSpacing(0)
        self._profile_name = QLabel(self._svc.user_name or "")
        self._profile_name.setObjectName("profileName")
        self._profile_name.setFont(get_font(12, weight=600))
        self._profile_name.setStyleSheet(
            f"QLabel#profileName {{ color: {Theme.sidebar_text()}; background: transparent; border: none; }}")
        self._profile_role = QLabel("Administrador" if self._is_admin else "Colaborador")
        self._profile_role.setObjectName("profileRole")
        self._profile_role.setFont(get_font(10))
        self._profile_role.setStyleSheet(
            f"QLabel#profileRole {{ color: {Theme.sidebar_text_secondary()}; background: transparent; border: none; }}")
        col.addWidget(self._profile_name)
        col.addWidget(self._profile_role)
        self._profile_layout.addLayout(col, stretch=1)

        self._logout_icon = Icon("logout", 16)
        self._logout_icon.set_color(Theme.sidebar_text_secondary())
        self._sidebar_icons.append(self._logout_icon)
        self._profile_layout.addWidget(self._logout_icon)

        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.mousePressEvent = lambda e: self._on_logout()
        return row

    # ------------------------------------------------------------------
    # Sidebar: colapso / expansión responsive
    # ------------------------------------------------------------------
    def _toggle_sidebar(self) -> None:
        self._sidebar_collapsed = not self._sidebar_collapsed
        self._apply_collapsed_state(self._sidebar_collapsed)
        target = (NEXAStyles.SIDEBAR_COLLAPSED_WIDTH if self._sidebar_collapsed
                  else NEXAStyles.SIDEBAR_WIDTH)
        self._animate_sidebar_width(target)
        self._collapse_btn.setToolTip("Expandir menú" if self._sidebar_collapsed else "Contraer menú")
        # Cambiar icono: chevron-right cuando está colapsado, hamburger cuando está expandido
        if hasattr(self, "_collapse_btn_icon") and self._collapse_btn_icon:
            new_icon = "chevron-right" if self._sidebar_collapsed else "menu"
            self._collapse_btn_icon.set_icon(new_icon)


    def _animate_sidebar_width(self, target: int) -> None:
        anim = QVariantAnimation(self)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(self._sidebar.width())
        anim.setEndValue(target)
        anim.valueChanged.connect(lambda v: self._sidebar.setFixedWidth(int(v)))
        anim.finished.connect(lambda: self._sidebar.setFixedWidth(target))
        anim.start()

    def _apply_collapsed_state(self, collapsed: bool) -> None:
        for item in self._nav_buttons.values():
            item.set_collapsed(collapsed)
        for lbl in self._section_labels:
            lbl.setVisible(not collapsed)

        if hasattr(self, "_logo_card"):
            self._logo_card.setVisible(not collapsed)
        if collapsed:
            # contenido útil del sidebar colapsado = 72px
            self._brand_row_layout.setContentsMargins(21, 12, 21, 12)
            self._nav_layout.setContentsMargins(4, 6, 4, 16)
            self._actions_row.setVisible(False)
            self._profile_name.setVisible(False)
            self._profile_role.setVisible(False)
            self._logout_icon.setVisible(False)
            self._profile_layout.setContentsMargins(15, 6, 15, 6)
            self._v_col.setContentsMargins(4, 8, 4, 12)
        else:
            self._brand_row_layout.setContentsMargins(12, 12, 10, 12)
            self._nav_layout.setContentsMargins(12, 6, 12, 16)
            self._actions_row.setVisible(True)
            self._profile_name.setVisible(True)
            self._profile_role.setVisible(True)
            self._logout_icon.setVisible(True)
            self._profile_layout.setContentsMargins(12, 10, 12, 10)
            self._v_col.setContentsMargins(12, 10, 12, 12)
        self._refresh_sidebar_static()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def _create_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        header.setStyleSheet(NEXAStyles.header())
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(24, 0, 16, 0)
        hlayout.setSpacing(16)

        # Título / breadcrumb
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        self._header_crumb = QLabel("NEXA Productivity Hub")
        self._header_crumb.setFont(get_font(10))
        self._header_crumb.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        title_col.addWidget(self._header_crumb)
        self._header_title = QLabel(tr("nav.dashboard"))
        self._header_title.setFont(get_font(16, weight=700))
        self._header_title.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        title_col.addWidget(self._header_title)
        hlayout.addLayout(title_col)

        hlayout.addStretch()

        # Buscador global
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
        self._header_search.setPlaceholderText(tr("header.search_placeholder"))
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

        # ── Separador visual ──
        sep = QFrame()
        sep.setFixedSize(1, 28)
        sep.setStyleSheet(f"background: {Theme.border()}; border: none;")
        hlayout.addWidget(sep)

        # ── Botón TEMA (Luna / Sol) ──
        self._header_theme_btn = QFrame()
        self._header_theme_btn.setObjectName("headerThemeBtn")
        self._header_theme_btn.setFixedSize(36, 36)
        self._header_theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ht_lay = QHBoxLayout(self._header_theme_btn)
        ht_lay.setContentsMargins(0, 0, 0, 0)
        self._header_theme_icon = SvgIcon("moon" if not is_dark() else "sun", 18)
        self._header_theme_icon.set_color(Theme.text_secondary())
        ht_lay.addWidget(self._header_theme_icon, 0, Qt.AlignmentFlag.AlignCenter)
        tip = tr("header.theme_dark") if not is_dark() else tr("header.theme_light")
        self._header_theme_btn.setToolTip(tip)
        self._header_theme_btn.setStyleSheet(
            f"QFrame#headerThemeBtn {{ border-radius: 18px; background: transparent; border: none; }}"
            f" QFrame#headerThemeBtn:hover {{ background: {Theme.hover_bg()}; }}"
        )
        self._header_theme_btn.mousePressEvent = lambda e: self._toggle_theme()
        hlayout.addWidget(self._header_theme_btn)

        # ── Botón IDIOMA (ES | EN) ──
        self._lang_btn = QFrame()
        self._lang_btn.setObjectName("langBtn")
        self._lang_btn.setFixedHeight(32)
        self._lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_btn.setToolTip("Switch language / Cambiar idioma")
        lang_lay = QHBoxLayout(self._lang_btn)
        lang_lay.setContentsMargins(10, 0, 10, 0)
        lang_lay.setSpacing(4)
        globe_ico = None
        self._header_globe_icon = None

        self._lang_label = QLabel(get_lang().upper())
        self._lang_label.setFont(get_font(11, weight=600))
        self._lang_label.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        lang_lay.addWidget(self._lang_label)
        self._lang_btn.setStyleSheet(
            f"QFrame#langBtn {{ border-radius: 8px; background: transparent;"
            f" border: 1px solid {Theme.border()}; }}"
            f" QFrame#langBtn:hover {{ border-color: {ACCENT};"
            f" background: {Theme.hover_bg()}; }}"
        )
        self._lang_btn.mousePressEvent = lambda e: self._toggle_lang()
        hlayout.addWidget(self._lang_btn)

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
        # Refresh titles from i18n every time we navigate
        global _PAGE_TITLES
        _PAGE_TITLES = {
            P_DASHBOARD:      tr("nav.dashboard"),
            P_CATALOG:        tr("nav.catalog"),
            P_SEARCH:         tr("nav.search"),
            P_APP:            tr("nav.app"),
            P_PROPOSALS:      tr("nav.proposals"),
            P_REQUESTS:       tr("nav.requests"),
            P_KNOWLEDGE:      tr("nav.knowledge"),
            P_ISSUES:         tr("nav.issues"),
            P_REPORTS:        tr("nav.reports"),
            P_AUDIT:          tr("nav.audit"),
            P_USERS:          tr("nav.users"),
            P_COMMUNITY:      tr("nav.community"),
            P_APP_AUDIT:      tr("nav.app_audit"),
            P_FAILURE_DETAIL: tr("nav.failure"),
            P_NOTIFICATIONS:  tr("nav.notifications"),
        }
        self._header_title.setText(_PAGE_TITLES.get(page_key, ""))
        self._header_crumb.setText(self._page_crumb(page_key))

        # Highlight active button
        for key, item in self._nav_buttons.items():
            item.set_active(key == page_key)

        # Trigger data refresh
        self._refresh_page(page_key)

    def _page_crumb(self, page_key: str) -> str:
        prefix = tr("crumb.prefix")
        return f"{prefix} / {_PAGE_TITLES.get(page_key, '')}"

    def _show_access_denied(self) -> None:
        self._current_page = ""
        self._stack.setCurrentWidget(self._access_denied_label)
        self._access_denied_label.setText(tr("access.denied"))
        self._header_title.setText(tr("crumb.denied"))
        self._header_crumb.setText(f"{tr('crumb.prefix')} / {tr('crumb.denied')}")
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
            # Accesos directos: siempre destacar Horas Extras Masiva al inicio.
            destacados = all_plugins if isinstance(all_plugins, list) else list(all_plugins)
            he_pin = [p for p in destacados if p.id == "horas_extras_masiva"]
            resto = [p for p in destacados if p.id != "horas_extras_masiva"]
            shown = he_pin[:6] + [p for p in resto][:6]
            app_health = self._svc.app_states.get_stats()
            pending = self._svc.requests.get_all()
            pending_count = len([r for r in pending if r.get("status") == "pendiente"])
            recent = self._svc.audit.get_entries(limit=5)
            return {
                "stats": stats,
                "top_plugins": [{"name": p.name, "executions": p.execution_count} for p in top],
                "favorites": fav_tools,
                "shortcuts": shown,
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
        if data.get("shortcuts"):
            view.set_shortcuts(data["shortcuts"])
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

    def _show_request_detail(self, request_id: int) -> None:
        req = self._svc.requests.get(request_id)
        if not req:
            return
            
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox
        from hub.ui.common.design import Theme, NEXAStyles, get_font
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalle Solicitud #{request_id}")
        dlg.setFixedSize(500, 500)
        dlg.setStyleSheet(f"QDialog {{ background-color: {Theme.bg()}; }}")
        
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        
        title_lbl = QLabel(req.get("title") or "Sin título")
        title_lbl.setFont(get_font(16, bold=True))
        title_lbl.setStyleSheet(f"color: {Theme.text()};")
        layout.addWidget(title_lbl)
        
        meta = f"Tipo: {req.get('request_type')} | Área: {req.get('area')} | Usuario: {req.get('created_by')}"
        meta_lbl = QLabel(meta)
        meta_lbl.setFont(get_font(11))
        meta_lbl.setStyleSheet(f"color: {Theme.text_muted()};")
        layout.addWidget(meta_lbl)
        
        desc = QTextEdit()
        desc.setReadOnly(True)
        desc.setPlainText(req.get("description") or "Sin descripción")
        desc.setStyleSheet(f"background-color: {Theme.card()}; color: {Theme.text()}; border: 1px solid {Theme.border()}; border-radius: 8px; padding: 8px;")
        desc.setFont(get_font(11))
        layout.addWidget(desc)
        
        # Status
        status_row = QHBoxLayout()
        status_lbl = QLabel("Estado:")
        status_lbl.setFont(get_font(12, bold=True))
        status_lbl.setStyleSheet(f"color: {Theme.text()};")
        status_row.addWidget(status_lbl)
        
        status_combo = QComboBox()
        status_combo.setStyleSheet(NEXAStyles.combo_box())
        status_combo.setFont(get_font(11))
        statuses = ["enviada", "en_revision", "en_desarrollo", "pruebas", "aprobada", "cerrada"]
        status_combo.addItems([s.replace("_", " ").title() for s in statuses])
        
        current_status = req.get("status", "enviada")
        if current_status in statuses:
            status_combo.setCurrentIndex(statuses.index(current_status))
            
        status_row.addWidget(status_combo, stretch=1)
        layout.addLayout(status_row)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel = QPushButton("Cerrar")
        cancel.setStyleSheet(NEXAStyles.secondary_button())
        cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel)
        
        save = QPushButton("Guardar Cambios")
        save.setStyleSheet(NEXAStyles.primary_button())
        def on_save():
            new_status = statuses[status_combo.currentIndex()]
            if new_status != current_status:
                self._svc.requests.update(request_id, status=new_status)
                self._refresh_requests()
            dlg.accept()
            
        save.clicked.connect(on_save)
        btn_row.addWidget(save)
        
        layout.addLayout(btn_row)
        dlg.exec()

    def _refresh_audit(self) -> None:
        view = self._get_page(P_AUDIT)
        if view is None:
            return
        
        # Conectar el botón de cargar más si no está conectado
        try:
            view.load_more_clicked.disconnect()
        except Exception:
            pass
        view.load_more_clicked.connect(self._load_more_audit)
        
        # Mantener el estado de offset en la vista
        view._current_offset = 0
        view._current_limit = 50
        
        entries = self._svc.audit.get_entries(limit=view._current_limit, offset=view._current_offset)
        count = self._svc.audit.get_entry_count()
        view.set_entries(entries, count, append=False)

    def _load_more_audit(self) -> None:
        view = self._get_page(P_AUDIT)
        if view is None:
            return
            
        view._current_offset += view._current_limit
        entries = self._svc.audit.get_entries(limit=view._current_limit, offset=view._current_offset)
        count = self._svc.audit.get_entry_count()
        view.set_entries(entries, count, append=True)

    def _refresh_users(self) -> None:
        view = self._get_page(P_USERS)
        if view is None:
            return
        users = self._svc.auth.get_all_users(include_inactive=True)
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

    def _on_search_plugin_clicked(self, plugin_id: str) -> None:
        self._navigate_to(P_APP)
        app_page = self._get_page(P_APP)
        if app_page and hasattr(app_page, "load_plugin"):
            app_page.load_plugin(plugin_id)

    def _on_search_article_clicked(self, article_id: int) -> None:
        self._navigate_to(P_KNOWLEDGE)
        kb_page = self._get_page(P_KNOWLEDGE)
        if kb_page and hasattr(kb_page, "open_article_dialog"):
            kb_page.open_article_dialog(article_id)

    def _on_header_search(self) -> None:
        query = self._header_search.text().strip()
        if not query:
            return
        results = self._svc.registry.search(query)
        kb_results = self._svc.knowledge.search(query)
        
        search_page = self._get_page(P_SEARCH)
        if search_page:
            search_page.show_results(query, results, kb_results)
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
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Propuesta Enviada", "Tu propuesta ha sido enviada con éxito.\nEl equipo de desarrollo la evaluará pronto.")

    def _on_issue_submitted(self, data: dict) -> None:
        req_id = self._svc.requests.create(
            user_id=self._svc.user_id, request_type="incidente",
            title=data.get("title", ""), description=data.get("what_happened", ""),
            area=self._svc.user_area, created_by=self._svc.user_id,
        )
        self._svc.audit.log_create(self._svc.user_id, "requests", "request", str(req_id))
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Reporte Enviado", "Tu incidencia ha sido reportada con éxito.\nTe contactaremos en breve.")

    def _on_audit_failure_clicked(self, failure_id: str) -> None:
        view = self._get_page(P_FAILURE_DETAIL)
        if view and hasattr(view, "load_failure"):
            view.load_failure(failure_id)
        self._navigate_to(P_FAILURE_DETAIL)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def _set_theme(self, mode: str) -> None:
        if mode not in ("light", "dark") or mode == self._theme_mode:
            return
        self._theme_mode = mode
        set_theme(mode)
        save_theme(mode)
        from hub.ui.common.design import setup_app_palette
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            setup_app_palette(app)
        self.apply_theme()
        # Actualizar botón tema del header
        self._refresh_header_theme_btn()

    def _toggle_theme(self) -> None:
        self._set_theme("light" if self._theme_mode == "dark" else "dark")

    def _refresh_header_theme_btn(self) -> None:
        """Actualiza el icono y tooltip del botón tema en el header."""
        if not hasattr(self, "_header_theme_btn"):
            return
        dark = is_dark()
        icon_name = "sun" if dark else "moon"
        tip = tr("header.theme_light") if dark else tr("header.theme_dark")
        self._header_theme_icon.set_icon(icon_name)
        self._header_theme_icon.set_color(Theme.text_secondary())
        self._header_theme_btn.setToolTip(tip)
        self._header_theme_btn.setStyleSheet(
            f"QFrame#headerThemeBtn {{ border-radius: 18px; background: transparent; border: none; }}"
            f" QFrame#headerThemeBtn:hover {{ background: {Theme.hover_bg()}; }}"
        )

    def _show_preferences(self) -> None:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton
        from hub.i18n import get_lang
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Preferencias de Sistema")
        dlg.setFixedSize(320, 260)
        dlg.setStyleSheet(f"QDialog {{ background-color: {Theme.bg()}; }}")
        v = QVBoxLayout(dlg)
        v.setSpacing(15)
        
        # Tema
        lbl_theme = QLabel("Apariencia:")
        lbl_theme.setFont(get_font(12))
        lbl_theme.setStyleSheet(f"color: {Theme.text()};")
        v.addWidget(lbl_theme)
        
        cb_theme = QComboBox()
        cb_theme.setFont(get_font(12))
        cb_theme.setStyleSheet(NEXAStyles.combo_box())
        cb_theme.addItems(["Claro", "Oscuro"])
        cb_theme.setCurrentIndex(1 if self._theme_mode == "dark" else 0)
        v.addWidget(cb_theme)
        
        # Idioma
        lbl_lang = QLabel("Idioma / Language:")
        lbl_lang.setFont(get_font(12))
        lbl_lang.setStyleSheet(f"color: {Theme.text()};")
        v.addWidget(lbl_lang)
        
        cb_lang = QComboBox()
        cb_lang.setFont(get_font(12))
        cb_lang.setStyleSheet(NEXAStyles.combo_box())
        cb_lang.addItems(["Español", "English"])
        cb_lang.setCurrentIndex(0 if get_lang() == "es" else 1)
        v.addWidget(cb_lang)
        
        v.addStretch()
        btn = QPushButton("Guardar Cambios")
        btn.setStyleSheet(NEXAStyles.primary_button())
        btn.clicked.connect(lambda: self._apply_preferences(dlg, cb_theme.currentIndex(), cb_lang.currentIndex()))
        v.addWidget(btn)

    def _apply_preferences(self, dlg: QDialog, theme_idx: int, lang_idx: int) -> None:
        new_theme = "dark" if theme_idx == 1 else "light"
        new_lang = "es" if lang_idx == 0 else "en"
        
        if new_theme != self._theme_mode:
            self._theme_mode = new_theme
            self._svc.config.set("theme", self._theme_mode)
            self.apply_theme()
            
        if new_lang != get_lang():
            set_lang(new_lang)
            
        dlg.accept()
        
        dlg.exec()

    def _apply_preferences(self, dlg, theme_index: int) -> None:
        mode = "dark" if theme_index == 1 else "light"
        self._set_theme(mode)
        dlg.accept()

    def _toggle_lang(self) -> None:
        """Alterna entre idioma español e inglés."""
        new_lang = "en" if get_lang() == "es" else "es"
        set_lang(new_lang)
        self.apply_language()

    def apply_language(self) -> None:
        """Actualiza todos los textos de la UI al idioma activo."""
        # Actualizar label del botón de idioma
        if hasattr(self, "_lang_label"):
            self._lang_label.setText(get_lang().upper())
        # Actualizar placeholder del buscador
        if hasattr(self, "_header_search"):
            self._header_search.setPlaceholderText(tr("header.search_placeholder"))
        # Actualizar etiquetas de secciones del sidebar
        sec_texts = [
            tr("section.main"), tr("section.manage"),
            tr("section.knowledge"), tr("section.analytics"),
        ]
        if self._is_admin:
            sec_texts.append(tr("section.admin"))
        for i, lbl in enumerate(self._section_labels):
            if i < len(sec_texts):
                lbl.setText(sec_texts[i])
        # Actualizar textos de botones de navegación
        nav_keys = [
            (P_DASHBOARD, "nav.dashboard"),
            (P_CATALOG,   "nav.catalog"),
            (P_SEARCH,    "nav.search"),
            (P_APP,       "nav.app"),
            (P_PROPOSALS, "nav.proposals"),
            (P_REQUESTS,  "nav.requests"),
            (P_ISSUES,    "nav.issues"),
            (P_KNOWLEDGE, "nav.knowledge"),
            (P_COMMUNITY, "nav.community"),
            (P_REPORTS,   "nav.reports"),
            (P_AUDIT,     "nav.audit"),
            (P_USERS,     "nav.users"),
        ]
        for page_key, i18n_key in nav_keys:
            btn = self._nav_buttons.get(page_key)
            if btn:
                btn._label.setText(tr(i18n_key))
                btn.setToolTip(tr(i18n_key))
        # Actualizar título activo
        if self._current_page:
            self._header_title.setText(tr(f"nav.{self._current_page}") if f"nav.{self._current_page}" in [
                "nav.dashboard", "nav.catalog", "nav.search", "nav.app",
                "nav.proposals", "nav.requests", "nav.issues", "nav.knowledge",
                "nav.community", "nav.reports", "nav.audit", "nav.users",
                "nav.notifications",
            ] else _PAGE_TITLES.get(self._current_page, ""))
        # Actualizar perfil texto
        if hasattr(self, "_profile_role"):
            self._profile_role.setText(
                tr("role.admin") if self._is_admin else tr("role.collaborator")
            )
        if hasattr(self, "_prefs_label"):
            self._prefs_label.setText(tr("action.preferences"))
        # Actualizar tooltip del botón tema
        self._refresh_header_theme_btn()

    def _refresh_theme_button(self) -> None:
        """Actualiza el botón tema del sidebar (pill) - mantenido por compatibilidad."""
        if not hasattr(self, "_theme_pill"):
            return
        active = "sun" if self._theme_mode == "light" else "moon"
        for name, ico in self._pill_icons.items():
            ico.set_color("#FFFFFF" if name == active else Theme.sidebar_text_secondary())
        for btn, name in ((self._pill_sun, "sun"), (self._pill_moon, "moon")):
            if name == active:
                btn.setStyleSheet(
                    f"QFrame {{ background-color: {Theme.sidebar_active()}; "
                    "border-radius: 6px; border: none; }}")
            else:
                btn.setStyleSheet("QFrame { background: transparent; border: none; border-radius: 6px; }")
        # También actualizar el header
        self._refresh_header_theme_btn()

    def _refresh_sidebar_static(self) -> None:
        if not hasattr(self, "_sidebar") or self._sidebar is None:
            return
        self._sidebar.setStyleSheet(NEXAStyles.sidebar())
        nav = self._sidebar.findChild(QWidget, "sidebarNav")
        if nav is not None:
            nav.setStyleSheet(f"QWidget#sidebarNav {{ background: {Theme.sidebar_bg()}; }}")
        if hasattr(self, "_logo_card"):
            self._logo_card.setStyleSheet(NEXAStyles.logo_card())
        if hasattr(self, "_profile_card"):
            self._profile_card.setStyleSheet(NEXAStyles.sidebar_user_card())
        for ico in getattr(self, "_sidebar_icons", []):
            ico.set_color(Theme.sidebar_text_secondary())
        if hasattr(self, "_prefs_label"):
            self._prefs_label.setStyleSheet(
                f"QLabel#prefsLabel {{ color: {Theme.sidebar_text_secondary()};"
                " background: transparent; border: none; }}")
        if hasattr(self, "_profile_name"):
            self._profile_name.setStyleSheet(
                f"QLabel#profileName {{ color: {Theme.sidebar_text()}; background: transparent; border: none; }}")
        if hasattr(self, "_profile_role"):
            self._profile_role.setStyleSheet(
                f"QLabel#profileRole {{ color: {Theme.sidebar_text_secondary()};"
                " background: transparent; border: none; }}")
        self._refresh_theme_button()

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
        # Header theme button
        if hasattr(self, "_header_theme_icon"):
            self._header_theme_icon.set_color(Theme.text_secondary())
        if hasattr(self, "_header_theme_btn"):
            self._header_theme_btn.setStyleSheet(
                f"QFrame#headerThemeBtn {{ border-radius: 18px; background: transparent; border: none; }}"
                f" QFrame#headerThemeBtn:hover {{ background: {Theme.hover_bg()}; }}"
            )
        if hasattr(self, "_header_globe_icon") and self._header_globe_icon is not None:
            self._header_globe_icon.set_color(Theme.text_secondary())
        if hasattr(self, "_lang_label"):
            self._lang_label.setStyleSheet(
                f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        if hasattr(self, "_lang_btn"):
            self._lang_btn.setStyleSheet(
                f"QFrame#langBtn {{ border-radius: 8px; background: transparent;"
                f" border: 1px solid {Theme.border()}; }}"
                f" QFrame#langBtn:hover {{ border-color: {ACCENT};"
                f" background: {Theme.hover_bg()}; }}"
            )
        self._refresh_sidebar_static()
        if hasattr(self, "_access_denied_label"):
            self._access_denied_label.setStyleSheet(
                f"color: {Theme.text_secondary()}; background: {Theme.bg()};")
        for item in self._nav_buttons.values():
            item.set_active(item._page_key == self._current_page)
            item.refresh_theme()
        for key, page in self._pages.items():
            if hasattr(page, "refresh_style"):
                page.refresh_style()
        
        self._setup_system_tray()

    def _setup_system_tray(self) -> None:
        """Configura el ícono en la bandeja del sistema (System Tray)."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        from PySide6.QtGui import QIcon, QAction
        
        self._tray_icon = QSystemTrayIcon(self)
        # Generate an icon from the existing Theme logic or Icon utility
        tray_pixmap = Icon("hexagon").get_pixmap()
        self._tray_icon.setIcon(QIcon(tray_pixmap))
        self._tray_icon.setToolTip("NEXA Productivity Hub")
        
        tray_menu = QMenu(self)
        
        open_action = QAction("Abrir NEXA", self)
        open_action.triggered.connect(self.showNormal)
        open_action.triggered.connect(self.activateWindow)
        tray_menu.addAction(open_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Salir Completamente", self)
        quit_action.triggered.connect(self._force_quit)
        tray_menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(tray_menu)
        
        # Double click to restore
        def tray_activated(reason):
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                self.showNormal()
                self.activateWindow()
                
        self._tray_icon.activated.connect(tray_activated)
        self._tray_icon.show()
        
    def _force_quit(self) -> None:
        """Cierra la aplicación ignorando el closeEvent."""
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
        
    def closeEvent(self, event) -> None:
        """Sobreescribe el cierre para minimizar al System Tray si está habilitado."""
        if hasattr(self, "_tray_icon") and self._tray_icon.isVisible():
            event.ignore()
            self.hide()
            self._tray_icon.showMessage(
                "NEXA sigue activo",
                "La aplicación se está ejecutando en segundo plano.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            super().closeEvent(event)

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
            self, tr("action.logout_title"),
            tr("action.logout_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self, "_tray_icon"):
                self._tray_icon.hide()
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
