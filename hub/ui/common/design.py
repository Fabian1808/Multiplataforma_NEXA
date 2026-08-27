"""UI Common — Design System NEXA v2.0. Tema claro/oscuro, componentes profesionales."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QFont, QPalette, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect, QSizeGrip,
)

ACCENT = "#FF5503"
ACCENT_HOVER = "#E64C00"
ACCENT_PRESSED = "#CC4200"
ACCENT_LIGHT = "#FF7A33"
ACCENT_BG = "#FFF3ED"

DARK_BG = "#1E1E2E"
DARK_SURFACE = "#2A2A3C"
DARK_CARD = "#32324A"
DARK_SIDEBAR = "#1A1A28"
DARK_HEADER = "#242436"
DARK_BORDER = "#3D3D55"
DARK_TEXT = "#E8E8F0"
DARK_TEXT_SECONDARY = "#A0A0B8"
DARK_TEXT_MUTED = "#6E6E88"

LIGHT_BG = "#F4F5F7"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_CARD = "#FFFFFF"
LIGHT_SIDEBAR = "#3B3B3B"
LIGHT_HEADER = "#FFFFFF"
LIGHT_BORDER = "#E4E6EA"
LIGHT_TEXT = "#1A1A2E"
LIGHT_TEXT_SECONDARY = "#5A5A72"
LIGHT_TEXT_MUTED = "#9898AC"

SUCCESS = "#2E7D32"
WARNING = "#F9A825"
ERROR = "#D32F2F"
INFO = "#1565C0"

STATUS_COLORS = {"operational": SUCCESS, "warning": WARNING, "error": ERROR, "info": INFO}
PLUGIN_STATUS_BADGES = {
    "oficial": ("Oficial", SUCCESS),
    "comunidad": ("Comunidad", INFO),
    "beta": ("Beta", WARNING),
    "deprecada": ("Deprecada", ERROR),
}

_APPDATA = os.environ.get("APPDATA", str(Path.home()))
_THEME_PATH = Path(_APPDATA) / "NEXA" / "ProductivityHub" / "theme.json"


def _load_theme() -> str:
    try:
        if _THEME_PATH.exists():
            with open(_THEME_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("mode", "light")
    except Exception:
        pass
    return "light"


def save_theme(mode: str) -> None:
    _THEME_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_THEME_PATH, "w", encoding="utf-8") as f:
        json.dump({"mode": mode}, f)


_current_theme: str = _load_theme()


def get_theme() -> str:
    return _current_theme


def set_theme(mode: str) -> None:
    global _current_theme
    _current_theme = mode
    save_theme(mode)


def is_dark() -> bool:
    return _current_theme == "dark"


def t(light: str, dark: str) -> str:
    return dark if is_dark() else light


def get_font(size: int = 12, bold: bool = False, italic: bool = False) -> QFont:
    font = QFont("Segoe UI", size)
    font.setBold(bold)
    font.setItalic(italic)
    return font


def get_icon_char(char: str, color: str = "", size: int = 16) -> QLabel:
    lbl = QLabel(char)
    lbl.setFont(get_font(size))
    lbl.setStyleSheet(f"color: {color or ACCENT}; background: transparent; border: none;")
    lbl.setFixedSize(size + 8, size + 8)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def make_shadow(parent: QWidget, blur: int = 20, offset_y: int = 4, color: str = "#00000030") -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(color))
    return shadow


class Theme:
    @staticmethod
    def bg() -> str: return t(LIGHT_BG, DARK_BG)
    @staticmethod
    def surface() -> str: return t(LIGHT_SURFACE, DARK_SURFACE)
    @staticmethod
    def card() -> str: return t(LIGHT_CARD, DARK_CARD)
    @staticmethod
    def sidebar_bg() -> str: return t(LIGHT_SIDEBAR, DARK_SIDEBAR)
    @staticmethod
    def header_bg() -> str: return t(LIGHT_HEADER, DARK_HEADER)
    @staticmethod
    def border() -> str: return t(LIGHT_BORDER, DARK_BORDER)
    @staticmethod
    def text() -> str: return t(LIGHT_TEXT, DARK_TEXT)
    @staticmethod
    def text_secondary() -> str: return t(LIGHT_TEXT_SECONDARY, DARK_TEXT_SECONDARY)
    @staticmethod
    def text_muted() -> str: return t(LIGHT_TEXT_MUTED, DARK_TEXT_MUTED)
    @staticmethod
    def accent() -> str: return ACCENT
    @staticmethod
    def accent_hover() -> str: return ACCENT_HOVER
    @staticmethod
    def success() -> str: return SUCCESS
    @staticmethod
    def warning() -> str: return WARNING
    @staticmethod
    def error() -> str: return ERROR
    @staticmethod
    def input_bg() -> str: return t("#FFFFFF", "#2A2A3C")
    @staticmethod
    def hover_bg() -> str: return t("#F0F0F5", "#3A3A50")
    @staticmethod
    def active_bg() -> str: return t("#E8E8F0", "#444460")


class NEXAStyles:
    SIDEBAR_WIDTH = 260
    HEADER_HEIGHT = 56
    CARD_BORDER_RADIUS = 10
    BUTTON_BORDER_RADIUS = 8
    SPACING_SM = 4
    SPACING_MD = 8
    SPACING_LG = 16
    SPACING_XL = 24
    PADDING_CARD = 18

    @staticmethod
    def sidebar() -> str:
        return f"""
            QWidget#sidebar {{
                background-color: {Theme.sidebar_bg()};
                min-width: {NEXAStyles.SIDEBAR_WIDTH}px;
                max-width: {NEXAStyles.SIDEBAR_WIDTH}px;
            }}
        """

    @staticmethod
    def header() -> str:
        return f"""
            QFrame#header {{
                background-color: {Theme.header_bg()};
                border-bottom: 2px solid {ACCENT};
                min-height: {NEXAStyles.HEADER_HEIGHT}px;
                max-height: {NEXAStyles.HEADER_HEIGHT}px;
            }}
        """

    @staticmethod
    def card() -> str:
        return f"""
            QFrame#card {{
                background-color: {Theme.card()};
                border: 1px solid {Theme.border()};
                border-radius: {NEXAStyles.CARD_BORDER_RADIUS}px;
                padding: {NEXAStyles.PADDING_CARD}px;
            }}
            QFrame#card:hover {{
                border-color: {ACCENT};
            }}
        """

    @staticmethod
    def card_no_hover() -> str:
        return f"""
            QFrame#card {{
                background-color: {Theme.card()};
                border: 1px solid {Theme.border()};
                border-radius: {NEXAStyles.CARD_BORDER_RADIUS}px;
                padding: {NEXAStyles.PADDING_CARD}px;
            }}
        """

    @staticmethod
    def primary_button() -> str:
        return f"""
            QPushButton {{
                background-color: {ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: {NEXAStyles.BUTTON_BORDER_RADIUS}px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {ACCENT_PRESSED}; }}
            QPushButton:disabled {{ background-color: {Theme.border()}; color: {Theme.text_muted()}; }}
        """

    @staticmethod
    def secondary_button() -> str:
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.text()};
                border: 1px solid {Theme.border()};
                border-radius: {NEXAStyles.BUTTON_BORDER_RADIUS}px;
                padding: 10px 22px;
                font-size: 13px;
            }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
            QPushButton:pressed {{ background-color: {Theme.hover_bg()}; }}
        """

    @staticmethod
    def ghost_button() -> str:
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.text_secondary()};
                border: none;
                border-radius: {NEXAStyles.BUTTON_BORDER_RADIUS}px;
                padding: 8px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ color: {ACCENT}; background-color: {Theme.hover_bg()}; }}
        """

    @staticmethod
    def danger_button() -> str:
        return f"""
            QPushButton {{
                background-color: {ERROR};
                color: #FFFFFF;
                border: none;
                border-radius: {NEXAStyles.BUTTON_BORDER_RADIUS}px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #B71C1C; }}
        """

    @staticmethod
    def search_input() -> str:
        return f"""
            QLineEdit {{
                border: 2px solid {Theme.border()};
                border-radius: {NEXAStyles.BUTTON_BORDER_RADIUS}px;
                padding: 10px 16px;
                font-size: 14px;
                background-color: {Theme.input_bg()};
                color: {Theme.text()};
                selection-background-color: {ACCENT};
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
            QLineEdit::placeholder {{ color: {Theme.text_muted()}; }}
        """

    @staticmethod
    def sidebar_button(active: bool = False) -> str:
        bg = Theme.active_bg() if active else "transparent"
        accent_border = f"border-left: 3px solid {ACCENT};" if active else "border: none;"
        return f"""
            QPushButton {{
                background-color: {bg};
                color: #FFFFFF;
                {accent_border}
                border-radius: 6px;
                padding: 10px 16px;
                text-align: left;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {Theme.hover_bg().replace(Theme.hover_bg(), '#444460' if is_dark() else '#555555')}; }}
        """

    @staticmethod
    def sidebar_section_label() -> str:
        return f"""
            QLabel {{
                color: {Theme.text_muted()};
                font-size: 10px;
                font-weight: bold;
                padding: 8px 16px 4px 16px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        """

    @staticmethod
    def badge(text: str, color: str) -> str:
        return f"""
            QLabel {{
                background-color: {color}18;
                color: {color};
                border: 1px solid {color}40;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
        """

    @staticmethod
    def kpi_card(color: str = ACCENT) -> str:
        return f"""
            QFrame {{
                background-color: {Theme.card()};
                border: 1px solid {Theme.border()};
                border-left: 4px solid {color};
                border-radius: 10px;
                padding: 16px;
            }}
        """

    @staticmethod
    def table() -> str:
        return f"""
            QTableWidget {{
                border: 1px solid {Theme.border()};
                border-radius: 8px;
                font-size: 12px;
                background-color: {Theme.card()};
                color: {Theme.text()};
                gridline-color: {Theme.border()};
                selection-background-color: {ACCENT}30;
            }}
            QTableWidget::item {{ padding: 8px; }}
            QTableWidget::item:selected {{ background-color: {ACCENT}20; color: {Theme.text()}; }}
            QHeaderView::section {{
                background-color: {Theme.hover_bg()};
                color: {Theme.text()};
                border: none;
                border-bottom: 2px solid {ACCENT};
                padding: 10px 8px;
                font-weight: bold;
                font-size: 11px;
            }}
        """

    @staticmethod
    def combo_box() -> str:
        return f"""
            QComboBox {{
                background-color: {Theme.input_bg()};
                color: {Theme.text()};
                border: 1px solid {Theme.border()};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                min-width: 120px;
            }}
            QComboBox:hover {{ border-color: {ACCENT}; }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Theme.card()};
                color: {Theme.text()};
                border: 1px solid {Theme.border()};
                selection-background-color: {ACCENT}30;
                padding: 4px;
            }}
        """

    @staticmethod
    def text_edit() -> str:
        return f"""
            QTextEdit {{
                background-color: {Theme.input_bg()};
                color: {Theme.text()};
                border: 1px solid {Theme.border()};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }}
            QTextEdit:focus {{ border-color: {ACCENT}; }}
        """

    @staticmethod
    def scroll_area() -> str:
        return f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.text_muted()};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ACCENT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 8px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {Theme.text_muted()};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {ACCENT};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
        """


class StatusBadge(QLabel):
    def __init__(self, status: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        label, color = PLUGIN_STATUS_BADGES.get(status, (status, Theme.text_muted()))
        self.setText(label)
        self.setStyleSheet(NEXAStyles.badge(label, color))


class HealthIndicator(QLabel):
    def __init__(self, status: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        color = STATUS_COLORS.get(status, Theme.text_muted())
        icons = {"operational": "\u25cf", "warning": "\u25cf", "error": "\u25cf"}
        icon = icons.get(status, "\u25cf")
        self.setText(f"{icon} {status.capitalize()}")
        self.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")


class KPIWidget(QFrame):
    def __init__(self, title: str, value: str = "0", icon: str = "", color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.kpi_card(color))
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 14, 16, 14)
        top = QHBoxLayout()
        if icon:
            icon_lbl = QLabel(icon)
            icon_lbl.setFont(get_font(20))
            icon_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            top.addWidget(icon_lbl)
        top.addStretch()
        layout.addLayout(top)
        self._value = QLabel(value)
        self._value.setFont(get_font(26, bold=True))
        self._value.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        layout.addWidget(self._value)
        self._title = QLabel(title)
        self._title.setFont(get_font(11))
        self._title.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        layout.addWidget(self._title)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class AppCard(QFrame):
    """Tarjeta de herramienta para catálogo y dashboard."""
    def __init__(self, plugin_id: str, name: str, description: str, category: str = "",
                 status: str = "oficial", execution_count: int = 0, is_favorite: bool = False,
                 parent: QWidget | None = None, on_click: Callable[[str], None] | None = None) -> None:
        super().__init__(parent)
        self.plugin_id = plugin_id
        self._on_click = on_click
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.card())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        top_row = QHBoxLayout()
        icon_frame = QFrame()
        icon_frame.setFixedSize(40, 40)
        icon_frame.setStyleSheet(f"background-color: {ACCENT}15; border-radius: 8px; border: none;")
        icon_lbl = QLabel("\u2699\ufe0f")
        icon_lbl.setFont(get_font(18))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"color: {ACCENT}; background: transparent; border: none;")
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(icon_lbl)
        top_row.addWidget(icon_frame)
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setFont(get_font(13, bold=True))
        name_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        name_lbl.setWordWrap(True)
        info.addWidget(name_lbl)
        cat_lbl = QLabel(category)
        cat_lbl.setFont(get_font(10))
        cat_lbl.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        info.addWidget(cat_lbl)
        top_row.addLayout(info, stretch=1)
        self._fav_btn = QPushButton("\u2606" if not is_favorite else "\u2605")
        self._fav_btn.setFont(get_font(16))
        self._fav_btn.setStyleSheet(f"border: none; color: {ACCENT if is_favorite else Theme.text_muted()}; background: transparent;")
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn.setFixedSize(32, 32)
        top_row.addWidget(self._fav_btn)
        layout.addLayout(top_row)
        desc = QLabel(description[:100] + ("..." if len(description) > 100 else ""))
        desc.setFont(get_font(11))
        desc.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        desc.setWordWrap(True)
        desc.setMaximumHeight(32)
        layout.addWidget(desc)
        bottom = QHBoxLayout()
        badge_label, badge_color = PLUGIN_STATUS_BADGES.get(status, (status, Theme.text_muted()))
        badge = QLabel(badge_label)
        badge.setStyleSheet(NEXAStyles.badge(badge_label, badge_color))
        bottom.addWidget(badge)
        bottom.addStretch()
        if execution_count > 0:
            exec_lbl = QLabel(f"\u25b6 {execution_count}")
            exec_lbl.setFont(get_font(10))
            exec_lbl.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
            bottom.addWidget(exec_lbl)
        layout.addLayout(bottom)

    def mousePressEvent(self, event) -> None:
        if self._on_click:
            self._on_click(self.plugin_id)
        super().mousePressEvent(event)


def setup_app_palette(app: QApplication) -> None:
    palette = QPalette()
    bg = QColor(Theme.bg())
    palette.setColor(QPalette.Window, bg)
    palette.setColor(QPalette.WindowText, QColor(Theme.text()))
    palette.setColor(QPalette.Base, QColor(Theme.input_bg()))
    palette.setColor(QPalette.AlternateBase, QColor(Theme.hover_bg()))
    palette.setColor(QPalette.Text, QColor(Theme.text()))
    palette.setColor(QPalette.Button, QColor(Theme.surface()))
    palette.setColor(QPalette.ButtonText, QColor(Theme.text()))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)


# ---------------------------------------------------------------------------
# Backward-compatible aliases — evaluados dinámicamente para respetar el tema.
# Se usan como funciones/propiedades en vistas antiguas.
# ---------------------------------------------------------------------------
def _text_primary() -> str: return Theme.text()
def _text_secondary() -> str: return Theme.text_secondary()
def _text_muted() -> str: return Theme.text_muted()
def _surface() -> str: return Theme.surface()
def _border() -> str: return Theme.border()

# Alias de cadena: solo usar en contextos donde el tema no cambia en runtime.
TEXT_PRIMARY = property(_text_primary) if False else Theme.text()  # noqa: SIM210
TEXT_SECONDARY = property(_text_secondary) if False else Theme.text_secondary()  # noqa: SIM210
TEXT_MUTED = property(_text_muted) if False else Theme.text_muted()  # noqa: SIM210
SURFACE = property(_surface) if False else Theme.surface()  # noqa: SIM210
BORDER = property(_border) if False else Theme.border()  # noqa: SIM210
DARK = DARK_SIDEBAR
SURFACE_VARIANT = DARK_SURFACE
