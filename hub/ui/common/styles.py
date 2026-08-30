from __future__ import annotations
import json
import math
import os
import re
from pathlib import Path
from typing import Callable
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QColor, QFont, QPalette, QIcon, QPixmap, QPainter, QPen, QBrush,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)

from .theme import *

# ---------------------------------------------------------------------------
# Tipografía
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"


def get_font(size: int = 12, bold: bool = False, italic: bool = False,
             weight: int = -1) -> QFont:
    font = QFont(FONT_FAMILY, size)
    font.setBold(bold)
    font.setItalic(italic)
    if weight >= 0:
        font.setWeight(QFont.Weight(int(weight)))
    return font


class NEXAStyles:
    SIDEBAR_WIDTH            = 256
    SIDEBAR_COLLAPSED_WIDTH  = 72
    HEADER_HEIGHT            = 56
    CARD_RADIUS              = 12
    BUTTON_RADIUS            = 8
    INPUT_RADIUS             = 8
    PADDING_CARD             = 16

    @staticmethod
    def sidebar() -> str:
        # El ancho lo controla el widget (permite animar colapso/expansión).
        return (
            f"QWidget#sidebar {{"
            f" background-color: {Theme.sidebar_bg()};"
            f" border-right: 1px solid {Theme.sidebar_border()}; }}"
        )

    @staticmethod
    def header() -> str:
        return (
            f"QFrame#header {{"
            f" background-color: {Theme.header_bg()};"
            f" border-bottom: 1px solid {Theme.border()};"
            f" min-height: {NEXAStyles.HEADER_HEIGHT}px;"
            f" max-height: {NEXAStyles.HEADER_HEIGHT}px; }}"
        )

    @staticmethod
    def _card_base(hover: bool) -> str:
        r  = NEXAStyles.CARD_RADIUS
        hv = (
            f" QFrame#card:hover {{ background-color: {Theme.card_elevated()};"
            f" border-color: {ACCENT}55; }}"
        ) if hover else ""
        return (
            f"QFrame#card {{ background-color: {Theme.card()};"
            f" border: 1px solid {Theme.border()}; border-radius: {r}px; }}{hv}"
        )

    @staticmethod
    def card()          -> str: return NEXAStyles._card_base(True)
    @staticmethod
    def card_no_hover() -> str: return NEXAStyles._card_base(False)

    @staticmethod
    def card_hover() -> str:
        r = NEXAStyles.CARD_RADIUS
        return (
            f"QFrame#card {{ background-color: {Theme.card_elevated()};"
            f" border: 1px solid {ACCENT}55; border-radius: {r}px; }}"
        )

    # ── Botones ─────────────────────────────────────────────────────────────
    @staticmethod
    def primary_button() -> str:
        r = NEXAStyles.BUTTON_RADIUS
        return (
            f"QPushButton {{ background-color: {ACCENT}; color: #FFFFFF; border: none;"
            f" border-radius: {r}px; padding: 9px 20px; font-family: 'Segoe UI';"
            f" font-size: 13px; font-weight: 600; }}"
            f" QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
            f" QPushButton:pressed {{ background-color: {ACCENT_PRESSED}; }}"
            f" QPushButton:focus {{ outline: none; }}"
            f" QPushButton:disabled {{ background-color: {Theme.hover_bg()};"
            f" color: {Theme.text_muted()}; }}"
        )

    @staticmethod
    def secondary_button() -> str:
        r    = NEXAStyles.BUTTON_RADIUS
        hbg  = ACCENT_BG if not is_dark() else DARK_HOVER
        return (
            f"QPushButton {{ background-color: transparent; color: {Theme.text()};"
            f" border: 1px solid {Theme.border_strong()}; border-radius: {r}px;"
            f" padding: 8px 18px; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }}"
            f" QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT};"
            f" background-color: {hbg}; }}"
            f" QPushButton:pressed {{ background-color: {Theme.hover_bg()}; }}"
            f" QPushButton:disabled {{ color: {Theme.text_muted()}; border-color: {Theme.border()}; }}"
        )

    @staticmethod
    def ghost_button() -> str:
        r = NEXAStyles.BUTTON_RADIUS
        return (
            f"QPushButton {{ background-color: transparent; color: {Theme.text_secondary()};"
            f" border: none; border-radius: {r}px; padding: 7px 14px;"
            f" font-size: 12px; font-weight: 500; }}"
            f" QPushButton:hover {{ color: {ACCENT}; background-color: {Theme.hover_bg()}; }}"
            f" QPushButton:pressed {{ background-color: {Theme.active_bg()}; }}"
        )

    @staticmethod
    def danger_button() -> str:
        r = NEXAStyles.BUTTON_RADIUS
        return (
            f"QPushButton {{ background-color: {ERROR}; color: #FFFFFF; border: none;"
            f" border-radius: {r}px; padding: 9px 20px; font-size: 13px; font-weight: 600; }}"
            f" QPushButton:hover {{ background-color: #B91C1C; }}"
            f" QPushButton:pressed {{ background-color: #991B1B; }}"
        )

    @staticmethod
    def icon_button() -> str:
        return (
            f"QPushButton {{ background-color: transparent; border: none;"
            f" border-radius: 8px; padding: 6px; }}"
            f" QPushButton:hover {{ background-color: {Theme.hover_bg()}; }}"
            f" QPushButton:pressed {{ background-color: {Theme.active_bg()}; }}"
        )

    # ── Inputs ──────────────────────────────────────────────────────────────
    @staticmethod
    def _input_base(padding: str = "9px 14px") -> str:
        r   = NEXAStyles.INPUT_RADIUS
        foc = t(LIGHT_INPUT_FOCUS, DARK_INPUT_FOCUS)
        return (
            f"QLineEdit {{ border: 1px solid {Theme.border()}; border-radius: {r}px;"
            f" padding: {padding}; font-family: 'Segoe UI'; font-size: 13px;"
            f" background-color: {Theme.input_bg()}; color: {Theme.text()};"
            f" selection-background-color: {ACCENT}; selection-color: #FFFFFF; }}"
            f" QLineEdit:hover {{ border-color: {Theme.border_strong()}; }}"
            f" QLineEdit:focus {{ border: 1.5px solid {ACCENT}; background-color: {foc}; }}"
            f" QLineEdit::placeholder {{ color: {Theme.text_muted()}; }}"
        )

    @staticmethod
    def search_input() -> str: return NEXAStyles._input_base("9px 14px")

    @staticmethod
    def input() -> str: return NEXAStyles._input_base("10px 14px")

    @staticmethod
    def text_edit() -> str:
        r   = NEXAStyles.INPUT_RADIUS
        foc = t(LIGHT_INPUT_FOCUS, DARK_INPUT_FOCUS)
        return (
            f"QTextEdit {{ background-color: {Theme.input_bg()}; color: {Theme.text()};"
            f" border: 1px solid {Theme.border()}; border-radius: {r}px; padding: 10px;"
            f" font-family: 'Segoe UI'; font-size: 13px;"
            f" selection-background-color: {ACCENT}; }}"
            f" QTextEdit:focus {{ border: 1.5px solid {ACCENT}; background-color: {foc}; }}"
        )

    # ── Sidebar ──────────────────────────────────────────────────────────────
    @staticmethod
    def sidebar_button(active: bool = False) -> str:
        tx  = ACCENT if active else Theme.text()
        bg  = Theme.active_bg() if active else "transparent"
        bar = f"border-left: 3px solid {ACCENT};" if active else "border-left: 3px solid transparent;"
        fw  = 600 if active else 400
        return (
            f"QPushButton {{ background-color: {bg}; color: {tx}; {bar}"
            f" border-top: none; border-right: none; border-bottom: none;"
            f" border-radius: 8px; padding: 9px 12px; text-align: left;"
            f" font-family: 'Segoe UI'; font-size: 13px; font-weight: {fw}; }}"
            f" QPushButton:hover {{ background-color: {Theme.hover_bg()}; }}"
            f" QPushButton:pressed {{ background-color: {Theme.active_bg()}; }}"
        )

    @staticmethod
    def sidebar_section_label() -> str:
        # Alineado con la columna de texto de los ítems (icono 20 + gap 12).
        return (
            f"QLabel#sidebarSectionLabel {{ color: {Theme.sidebar_text_secondary()};"
            f" font-family: 'Segoe UI'; font-size: 10px; font-weight: 600;"
            f" padding: 18px 8px 6px 59px; letter-spacing: 1.4px;"
            f" background: transparent; border: none; }}"
        )

    @staticmethod
    def sidebar_user_box() -> str:
        return (
            f"QFrame#sidebarUser {{ background-color: {Theme.sidebar_bg()};"
            f" border-top: 1px solid {Theme.sidebar_border()}; }}"
        )

    @staticmethod
    def logo_card() -> str:
        return (
            f"QFrame#logoCard {{ background-color: #FFFFFF;"
            f" border: 1px solid {Theme.logo_card_border()}; border-radius: 10px; }}"
        )

    @staticmethod
    def sidebar_user_card() -> str:
        return (
            f"QFrame#sidebarUserCard {{ background-color: {Theme.sidebar_card()};"
            f" border-radius: 10px; }}"
        )

    # ── Badges / KPIs / Tablas ───────────────────────────────────────────────
    @staticmethod
    def badge(text: str, color: str) -> str:
        bg = f"{color}1A"
        return (
            f"QLabel {{ background-color: {bg}; color: {color};"
            f" border: 1px solid {color}33; border-radius: 5px;"
            f" padding: 3px 9px; font-family: 'Segoe UI'; font-size: 11px; font-weight: 600; }}"
        )

    @staticmethod
    def kpi_card(color: str = ACCENT) -> str:
        r = NEXAStyles.CARD_RADIUS
        return (
            f"QFrame {{ background-color: {Theme.card()};"
            f" border: 1px solid {Theme.border()}; border-left: 3px solid {color};"
            f" border-radius: {r}px; }}"
        )

    @staticmethod
    def table() -> str:
        return (
            f"QTableWidget {{ border: none; font-family: 'Segoe UI'; font-size: 13px;"
            f" background-color: {Theme.card()}; color: {Theme.text()};"
            f" gridline-color: {Theme.border()}; selection-background-color: {ACCENT}22; }}"
            f" QTableWidget::item {{ padding: 10px 8px; border-bottom: 1px solid {Theme.border()}; }}"
            f" QTableWidget::item:selected {{ background-color: {ACCENT}1A; color: {Theme.text()}; }}"
            f" QHeaderView::section {{ background-color: {Theme.bg()};"
            f" color: {Theme.text_secondary()}; border: none;"
            f" border-bottom: 1px solid {Theme.border()}; padding: 10px 8px;"
            f" font-family: 'Segoe UI'; font-weight: 600; font-size: 11px; letter-spacing: 0.5px; }}"
        )

    @staticmethod
    def combo_box() -> str:
        r = NEXAStyles.INPUT_RADIUS
        return (
            f"QComboBox {{ background-color: {Theme.input_bg()}; color: {Theme.text()};"
            f" border: 1px solid {Theme.border()}; border-radius: {r}px;"
            f" padding: 8px 12px; font-family: 'Segoe UI'; font-size: 13px; min-width: 120px; }}"
            f" QComboBox:hover {{ border-color: {Theme.border_strong()}; }}"
            f" QComboBox:focus {{ border: 1.5px solid {ACCENT}; }}"
            f" QComboBox::drop-down {{ border: none; width: 24px; }}"
            f" QComboBox QAbstractItemView {{ background-color: {Theme.card()}; color: {Theme.text()};"
            f" border: 1px solid {Theme.border()}; selection-background-color: {ACCENT}22;"
            f" padding: 4px; outline: none; }}"
        )

    @staticmethod
    def tab(active: bool = False) -> str:
        c  = ACCENT if active else Theme.text_secondary()
        bb = ACCENT if active else "transparent"
        fw = 600 if active else 500
        return (
            f"QPushButton {{ background-color: transparent; color: {c}; border: none;"
            f" border-bottom: 2px solid {bb}; padding: 8px 18px;"
            f" font-family: 'Segoe UI'; font-size: 13px; font-weight: {fw}; }}"
            f" QPushButton:hover {{ color: {ACCENT}; }}"
        )

    @staticmethod
    def alert(kind: str) -> str:
        cmap = {"success": SUCCESS, "warning": WARNING, "error": ERROR, "info": INFO}
        bgm  = {"success": SUCCESS_BG, "warning": WARNING_BG, "error": ERROR_BG, "info": INFO_BG}
        c  = cmap.get(kind, INFO)
        bg = bgm.get(kind, INFO_BG)
        return (
            f"QFrame#alert {{ background-color: {bg}; border: 1px solid {c}40;"
            f" border-radius: 10px; padding: 10px 14px; }}"
            f" QLabel {{ color: {c}; background: transparent; border: none; }}"
        )

    @staticmethod
    def scroll_area() -> str:
        bs = Theme.border_strong()
        return (
            f"QScrollArea {{ border: none; background-color: transparent; }}"
            f" QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}"
            f" QScrollBar::handle:vertical {{ background: {bs}; border-radius: 4px; min-height: 32px; }}"
            f" QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}"
            f" QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
            f" QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}"
            f" QScrollBar::handle:horizontal {{ background: {bs}; border-radius: 4px; min-width: 32px; }}"
            f" QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}"
            f" QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}"
        )

    @staticmethod
    def divider() -> str:
        return f"background-color: {Theme.border()}; border: none;"


# ---------------------------------------------------------------------------
# Componentes compuestos reutilizables
# ---------------------------------------------------------------------------
class StatusBadge(QLabel):
    def __init__(self, status: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        label, color = PLUGIN_STATUS_BADGES.get(
            status, (status.capitalize(), Theme.text_muted())
        )
        self.setText(label)
        self.setStyleSheet(NEXAStyles.badge(label, color))
        self.setFixedHeight(22)


class HealthIndicator(QLabel):
    def __init__(self, status: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        color = STATUS_COLORS.get(status, Theme.text_muted())
        self.setText(f"\u25cf {status.capitalize()}")
        self.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent; border: none;"
        )


class KPIWidget(QFrame):
    """Tarjeta KPI con barra de color lateral."""

    def __init__(self, title: str, value: str = "0", icon: str = "",
                 color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.kpi_card(color))
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(18, 14, 18, 14)

        top = QHBoxLayout()
        if icon:
            ico = Icon(icon, 16)
            ico.set_color(color)
            top.addWidget(ico)
        top.addStretch()
        layout.addLayout(top)

        self._value = QLabel(value)
        self._value.setFont(get_font(26, bold=True))
        self._value.setStyleSheet(
            f"color: {Theme.text()}; background: transparent; border: none;"
        )
        layout.addWidget(self._value)

        self._title = QLabel(title)
        self._title.setFont(get_font(11))
        self._title.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        layout.addWidget(self._title)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class AppCard(QFrame):
    """Tarjeta de aplicación — jerarquía visual clara, hover, favorito y badge."""

    def __init__(self, plugin_id: str, name: str, description: str,
                 category: str = "", status: str = "oficial",
                 execution_count: int = 0, is_favorite: bool = False,
                 icon_name: str = "package", parent: QWidget | None = None,
                 on_click: Callable[[str], None] | None = None) -> None:
        super().__init__(parent)
        self.plugin_id = plugin_id
        self._on_click = on_click
        self._is_fav   = is_favorite
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.card_no_hover())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(190)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        # Fila 1: icono + botón favorito
        row1 = QHBoxLayout()
        row1.setSpacing(0)
        icon_bg = ACCENT_BG if not is_dark() else ACCENT_DARK_BG
        icon_frame = QFrame()
        icon_frame.setFixedSize(44, 44)
        icon_frame.setStyleSheet(
            f"background-color: {icon_bg}; border-radius: 11px; border: none;"
        )
        icon_lbl = Icon(icon_name, 22)
        icon_lbl.set_color(ACCENT)
        il = QVBoxLayout(icon_frame)
        il.setContentsMargins(0, 0, 0, 0)
        il.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(icon_frame)
        row1.addStretch()

        self._fav_btn = QPushButton()
        self._fav_btn.setFixedSize(30, 30)
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; border-radius: 15px; }}"
            f" QPushButton:hover {{ background-color: {Theme.hover_bg()}; }}"
        )
        self._fav_btn.clicked.connect(self._on_fav_click)
        self._update_fav_icon(is_favorite)
        row1.addWidget(self._fav_btn)
        lay.addLayout(row1)

        # Nombre
        name_lbl = QLabel(name)
        name_lbl.setFont(get_font(14, bold=True))
        name_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        name_lbl.setWordWrap(True)
        lay.addWidget(name_lbl)

        # Descripción
        desc_text = description[:120] + ("\u2026" if len(description) > 120 else "")
        desc_lbl = QLabel(desc_text)
        desc_lbl.setFont(get_font(11))
        desc_lbl.setStyleSheet(
            f"color: {Theme.text_secondary()}; background: transparent; border: none;"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setMinimumHeight(36)
        lay.addWidget(desc_lbl)

        lay.addStretch()

        # Footer: categoría + Botón Abrir
        row4 = QHBoxLayout()
        row4.setSpacing(6)
        if category:
            cat_lbl = QLabel(category.capitalize())
            cat_lbl.setFont(get_font(10))
            cat_lbl.setStyleSheet(
                f"color: {Theme.text_muted()}; background: transparent; border: none;"
            )
            row4.addWidget(cat_lbl)
        row4.addStretch()
        
        self._open_btn = QPushButton("Abrir")
        self._open_btn.setFont(get_font(10, bold=True))
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT}15;
                color: {ACCENT};
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT}30;
            }}
        """)
        self._open_btn.clicked.connect(lambda: self._on_click(self.plugin_id) if self._on_click else None)
        row4.addWidget(self._open_btn)
        
        lay.addLayout(row4)

    def _update_fav_icon(self, is_fav: bool) -> None:
        fav_ico = Icon("star", 16, ACCENT if is_fav else Theme.text_muted())
        self._fav_btn.setIcon(QIcon(fav_ico.get_pixmap()))
        self._fav_btn.setIconSize(fav_ico.size())

    def _on_fav_click(self) -> None:
        self._is_fav = not self._is_fav
        self._update_fav_icon(self._is_fav)

    def enterEvent(self, event) -> None:
        self.setStyleSheet(NEXAStyles.card_hover())
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setStyleSheet(NEXAStyles.card_no_hover())
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._on_click:
            self._on_click(self.plugin_id)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Paleta Qt coherente con el tema activo
# ---------------------------------------------------------------------------
def setup_app_palette(app: QApplication) -> None:
    """Aplica colores Qt Palette alineados con el tema NEXA activo."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,           QColor(Theme.bg()))
    p.setColor(QPalette.ColorRole.WindowText,       QColor(Theme.text()))
    p.setColor(QPalette.ColorRole.Base,             QColor(Theme.input_bg()))
    p.setColor(QPalette.ColorRole.AlternateBase,    QColor(Theme.hover_bg()))
    p.setColor(QPalette.ColorRole.Text,             QColor(Theme.text()))
    p.setColor(QPalette.ColorRole.BrightText,       QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.Button,           QColor(Theme.surface()))
    p.setColor(QPalette.ColorRole.ButtonText,       QColor(Theme.text()))
    p.setColor(QPalette.ColorRole.Highlight,        QColor(ACCENT))
    p.setColor(QPalette.ColorRole.HighlightedText,  QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.PlaceholderText,  QColor(Theme.text_muted()))
    p.setColor(QPalette.ColorRole.ToolTipBase,      QColor(Theme.surface()))
    p.setColor(QPalette.ColorRole.ToolTipText,      QColor(Theme.text()))
    p.setColor(QPalette.ColorRole.Link,             QColor(ACCENT))
    app.setPalette(p)




