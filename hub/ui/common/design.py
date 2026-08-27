"""UI Common — NEXA Design System v3.0.

Sistema de diseño corporativo moderno (SaaS) con tema claro/oscuro.
Proporciona tokens de color, tipografía, espaciado y generadores de
estilos/componentes reutilizables para toda la plataforma.

Identidad NEXA:
  - Acento: naranja #FF5500 (usado con moderación, jerarquía de acento)
  - Neutros elegantes claro/oscuro
  - Tipografía: Segoe UI
  - Iconografía: familia de iconos lineales propios (QPainter), sin emojis.
"""

from __future__ import annotations

import json
import os
import math
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QRectF, QPointF, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import (
    QColor, QFont, QPalette, QIcon, QPixmap, QPainter, QPen, QBrush,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect, QSizeGrip,
)

# ---------------------------------------------------------------------------
# Cor / identidad
# ---------------------------------------------------------------------------
ACCENT = "#FF5500"
ACCENT_HOVER = "#E64A00"
ACCENT_PRESSED = "#CC4100"
ACCENT_LIGHT = "#FF7A33"
ACCENT_BG = "#FFF3EB"
ACCENT_TINT = "#FFE8D9"

# Estados semánticos
SUCCESS = "#16A34A"
SUCCESS_BG = "#E9F7EF"
WARNING = "#D97706"
WARNING_BG = "#FEF3E2"
ERROR = "#DC2626"
ERROR_BG = "#FDECEC"
INFO = "#2563EB"
INFO_BG = "#EAF1FE"

STATUS_COLORS = {"operational": SUCCESS, "warning": WARNING, "error": ERROR, "info": INFO}
PLUGIN_STATUS_BADGES = {
    "oficial": ("Oficial", SUCCESS),
    "comunidad": ("Comunidad", INFO),
    "beta": ("Beta", WARNING),
    "deprecada": ("Deprecada", ERROR),
}

# ---------------------------------------------------------------------------
# Paleta oscura (diseñado específicamente, no inversión de la clara)
# ---------------------------------------------------------------------------
DARK_BG = "#14141D"
DARK_SURFACE = "#1E1E2A"
DARK_CARD = "#23232F"
DARK_SIDEBAR = "#191923"
DARK_HEADER = "#1E1E2A"
DARK_BORDER = "#2E2E3C"
DARK_BORDER_STRONG = "#3A3A4A"
DARK_TEXT = "#EDEDF3"
DARK_TEXT_SECONDARY = "#B4B4C4"
DARK_TEXT_MUTED = "#7C7C8F"
DARK_INPUT = "#1A1A26"
DARK_HOVER = "#292938"
DARK_ACTIVE_BG = "#2E2E3C"

# ---------------------------------------------------------------------------
# Paleta clara
# ---------------------------------------------------------------------------
LIGHT_BG = "#F5F6F8"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_CARD = "#FFFFFF"
LIGHT_SIDEBAR = "#FCFCFD"
LIGHT_HEADER = "#FFFFFF"
LIGHT_BORDER = "#E6E7EB"
LIGHT_BORDER_STRONG = "#D4D6DC"
LIGHT_TEXT = "#1A1D24"
LIGHT_TEXT_SECONDARY = "#5B5F6B"
LIGHT_TEXT_MUTED = "#9A9EA9"
LIGHT_INPUT = "#FFFFFF"
LIGHT_HOVER = "#F2F3F6"
LIGHT_ACTIVE_BG = "#FFF2E9"

# ---------------------------------------------------------------------------
# Estado global del tema
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Tipografía y escala
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"


def get_font(size: int = 12, bold: bool = False, italic: bool = False, weight: int = -1) -> QFont:
    font = QFont(FONT_FAMILY, size)
    font.setBold(bold)
    font.setItalic(italic)
    if weight >= 0:
        font.setWeight(QFont.Weight(int(weight)))
    return font


# ---------------------------------------------------------------------------
# Iconos lineales (familia propia, consistentes, sin emojis)
# ---------------------------------------------------------------------------
class Icon(QLabel):
    """Icono lineal monocromo dibujado con QPainter.

    Proporciona una familia de iconos visualmente consistente.
    Uso: ico = Icon("home", 18); ico.set_color("#FF5500")
    """

    _PATHS: dict[str, list] = {
        "home": [("path", "M4 11 L12 4 L20 11"), ("path", "M6 11 v8 h12 v-8")],
        "grid": [
            ("rect", (3, 3, 7, 7)), ("rect", (14, 3, 7, 7)),
            ("rect", (3, 14, 7, 7)), ("rect", (14, 14, 7, 7)),
        ],
        "search": [("circle", (10, 10, 6)), ("path", "M15 15 L21 21")],
        "apps": [
            ("rect", (4, 4, 5, 5)), ("rect", (15, 4, 5, 5)),
            ("rect", (4, 15, 5, 5)), ("rect", (15, 15, 5, 5)),
        ],
        "file": [("path", "M6 3 H14 L18 7 V21 H6 Z"), ("path", "M14 3 v4 h4")],
        "list": [
            ("path", "M8 6 H20"), ("path", "M8 12 H20"), ("path", "M8 18 H20"),
            ("dot", (4, 6)), ("dot", (4, 12)), ("dot", (4, 18)),
        ],
        "book": [
            ("path", "M4 5 C4 3.9 4.9 3 6 3 H20 V21 H6 C4.9 21 4 20.1 4 19 Z"),
            ("path", "M4 19 C4 20.1 4.9 21 6 21 H20"),
        ],
        "wrench": [
            ("path",
             "M14.7 6.3a4.5 4.5 0 0 0-5.8 5.8L4 17l3 3 4.9-4.9a4.5 4.5 0 0 0 5.8-5.8L14 13l-3-3 3.7-3.7z"),
        ],
        "chart": [
            ("path", "M4 20 H20"), ("path", "M6 16 v-5"), ("path", "M12 16 v-9"), ("path", "M18 16 v-7"),
        ],
        "shield": [
            ("path", "M12 3 L20 6 v6 c0 5-3.5 8-8 9 C7.5 20 4 17 4 12 V6 Z"),
        ],
        "users": [
            ("circle", (12, 8, 3.2)), ("path", "M6 18 c0-3 2.7-5 6-5 s6 2 6 5"),
            ("path", "M4 16 c0-1.8 1-3.2 2.6-4"), ("path", "M20 16 c0-1.8-1-3.2-2.6-4"),
        ],
        "user": [
            ("circle", (12, 8, 3.5)), ("path", "M5 19 c0-3.5 3-6 7-6 s7 2.5 7 6"),
        ],
        "bell": [
            ("path", "M6 9 a6 6 0 0 1 12 0 c0 4 1.5 5.5 2 6 H4 c.5-.5 2-2 2-6"),
            ("path", "M10 19 a2 2 0 0 0 4 0"),
        ],
        "settings": [
            ("circle", (12, 12, 3)),
            ("path",
             "M12 3 v3 M12 18 v3 M3 12 h3 M18 12 h3 M5.6 5.6 l2.1 2.1 M16.3 16.3 l2.1 2.1 "
             "M18.4 5.6 l-2.1 2.1 M7.7 16.3 l-2.1 2.1"),
        ],
        "sun": [
            ("circle", (12, 12, 4)), ("path",
             "M12 2 v2 M12 20 v2 M2 12 h2 M20 12 h2 M4.9 4.9 L6.3 6.3 M17.7 17.7 l1.4 1.4 "
             "M19.1 4.9 l-1.4 1.4 M6.3 17.7 l-1.4 1.4"),
        ],
        "moon": [
            ("path", "M20 14 A8 8 0 1 1 10 4 a6 6 0 0 0 10 10"),
        ],
        "logout": [
            ("path", "M14 4 H5 a2 2 0 0 0-2 2 v12 a2 2 0 0 0 2 2 h9"),
            ("path", "M17 8 l4 4 -4 4"), ("path", "M21 12 H9"),
        ],
        "play": [
            ("poly", [(7, 5), (19, 12), (7, 19)]),
        ],
        "back": [("path", "M19 12 H5 M11 6 l-6 6 6 6")],
        "star": [
            ("poly", [
                (12, 3.5), (14.5, 8.5), (20, 9.2), (16, 13), (17, 18.5),
                (12, 16), (7, 18.5), (8, 13), (4, 9.2), (9.5, 8.5),
            ]),
        ],
        "folder": [
            ("path", "M3 7 a2 2 0 0 1 2-2 h4 l2 2 h8 a2 2 0 0 1 2 2 v8 a2 2 0 0 1-2 2 H5 a2 2 0 0 1-2-2 Z"),
        ],
        "check": [("path", "M4 12 L9 17 L20 6")],
        "close": [("path", "M6 6 L18 18 M18 6 L6 18")],
        "upload": [
            ("path", "M12 15 V4"), ("path", "M7 9 l5-5 5 5"), ("path", "M4 16 v3 a2 2 0 0 0 2 2 h12 a2 2 0 0 0 2-2 v-3"),
        ],
        "clock": [
            ("circle", (12, 12, 8)), ("path", "M12 8 v4 l3 2"),
        ],
        "activity": [
            ("path", "M3 12 h4 l3-7 4 14 3-7 h4"),
        ],
        "flag": [
            ("path", "M5 21 V4"), ("path", "M5 4 c3-2 6 2 9 0 s4 0 6 0 v8 c-2 0-4 2-6 0 s-3-2-6 0"),
        ],
        "refresh": [
            ("path", "M20 12 A8 8 0 1 1 18 6"), ("path", "M18 4 v4 h-4"),
        ],
        "plugin": [
            ("poly", [(12, 3), (20, 8), (20, 16), (12, 21), (4, 16), (4, 8)]),
        ],
        "cube": [
            ("path", "M12 3 L21 8 v8 L12 21 L3 16 V8 Z"), ("path", "M3 8 l9 5 9-5"), ("path", "M12 13 v8"),
        ],
        "filter": [
            ("path", "M3 5 H21 M6 12 H18 M10 19 H14"),
        ],
        "eye": [
            ("path", "M2 12 c3-5 7.5-7 10-7 s7 2 10 7 c-3 5-7.5 7-10 7 s-7-2-10-7"),
            ("circle", (12, 12, 3)),
        ],
        "eye_off": [
            ("path", "M3 3 L21 21"),
            ("path", "M9.9 5.1 A10 10 0 0 1 12 5 c2.5 0 7 2 10 7 a14 14 0 0 1-3.2 3.6"),
            ("path", "M6.2 6.8 A14 14 0 0 0 2 12 c3 5 7.5 7 10 7 a10 10 0 0 0 4-0.85"),
            ("path", "M9.9 9.9 a3 3 0 0 0 4.2 4.2"),
        ],
    }

    def __init__(self, name: str = "plugin", size: int = 16, color: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._icon_size = size
        self._color = color or (ACCENT if not is_dark() else ACCENT_LIGHT)
        self.setFixedSize(size + 4, size + 4)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._render()

    def set_color(self, color: str) -> None:
        self._color = color
        self._render()

    def set_icon(self, name: str) -> None:
        self._name = name
        self._render()

    def _render(self) -> None:
        size = self._icon_size
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self._color))
        pen.setWidthF(max(1.5, size / 11))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for shape in Icon._PATHS.get(self._name, []):
            kind = shape[0]
            if kind == "path":
                p.drawPath(self._parse_path(shape[1], size))
            elif kind == "circle":
                cx, cy, r = shape[1]
                p.drawEllipse(QPointF(cx * size / 24, cy * size / 24), r * size / 24, r * size / 24)
            elif kind == "rect":
                x, y, w, h = shape[1]
                p.drawRect(QRectF(x * size / 24, y * size / 24, w * size / 24, h * size / 24))
            elif kind == "dot":
                x, y = shape[1]
                p.setBrush(QBrush(self._color))
                p.drawEllipse(QPointF(x * size / 24, y * size / 24), 1.2 * size / 24, 1.2 * size / 24)
                p.setBrush(Qt.BrushStyle.NoBrush)
            elif kind == "poly":
                pts = [QPointF(x * size / 24, y * size / 24) for x, y in shape[1]]
                poly = QPolygonF(pts)
                p.setBrush(QBrush(QColor(self._color)))
                p.drawPolygon(poly)
                p.setBrush(Qt.BrushStyle.NoBrush)
        p.end()
        self.setPixmap(pm)
        self.setStyleSheet("background: transparent; border: none;")

    def _parse_path(self, d: str, size: int):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        cmd = None
        tokens = d.replace(",", " ").split()
        i = 0
        cx = cy = 0.0
        def _n(idx):
            return float(tokens[idx]) * size / 24.0
        guard = 0
        max_guard = len(tokens) * 4 + 8
        while i < len(tokens) and guard < max_guard:
            guard += 1
            tok = tokens[i]
            if tok and tok[0].isalpha():
                cmd = tok
                i += 1
                continue
            if cmd in ("M", "m"):
                x, y = _n(i), _n(i + 1)
                if cmd == "m":
                    x, y = cx + x, cy + y
                path.moveTo(x, y)
                cx, cy = x, y
                i += 2
                cmd = "L"
            elif cmd in ("L", "l"):
                x, y = _n(i), _n(i + 1)
                if cmd == "l":
                    x, y = cx + x, cy + y
                path.lineTo(x, y)
                cx, cy = x, y
                i += 2
            elif cmd in ("H", "h"):
                x = _n(i)
                if cmd == "h":
                    x = cx + x
                path.lineTo(x, cy)
                cx = x
                i += 1
            elif cmd in ("V", "v"):
                y = _n(i)
                if cmd == "v":
                    y = cy + y
                path.lineTo(cx, y)
                cy = y
                i += 1
            elif cmd == "Z":
                path.closeSubpath()
                i += 1
            else:
                i += 1
        return path


# ---------------------------------------------------------------------------
# Sombras suaves
# ---------------------------------------------------------------------------
def make_shadow(parent: QWidget, blur: int = 24, offset_y: int = 4, color: str = "#0000001F") -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(color))
    return shadow


def get_icon_char(char: str, color: str = "", size: int = 16) -> QLabel:
    """Compatibilidad con API anterior: raster de caracter.

    En lugar de un emoji arbitrario devolvemos un Icon neutral para que las
    vistas migradas sigan funcionando con la nueva familia de iconos.
    """
    try:
        icon = Icon("plugin", size, color)
        return icon
    except Exception:
        lbl = QLabel(char)
        lbl.setFont(get_font(size))
        lbl.setStyleSheet(f"color: {color or ACCENT}; background: transparent; border: none;")
        lbl.setFixedSize(size + 8, size + 8)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl


# ---------------------------------------------------------------------------
# Tokens semánticos de tema (Theme API estable)
# ---------------------------------------------------------------------------
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
    def info() -> str: return INFO
    @staticmethod
    def input_bg() -> str: return t(LIGHT_INPUT, DARK_INPUT)
    @staticmethod
    def hover_bg() -> str: return t(LIGHT_HOVER, DARK_HOVER)
    @staticmethod
    def active_bg() -> str: return t(LIGHT_ACTIVE_BG, DARK_ACTIVE_BG)
    @staticmethod
    def border_strong() -> str: return t(LIGHT_BORDER_STRONG, DARK_BORDER_STRONG)


# ---------------------------------------------------------------------------
# NEXAStyles — generadores de estilos de componentes
# ---------------------------------------------------------------------------
class NEXAStyles:
    SIDEBAR_WIDTH = 252
    HEADER_HEIGHT = 60
    CARD_BORDER_RADIUS = 12
    BUTTON_BORDER_RADIUS = 8
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 16
    SPACING_XL = 24
    SPACING_XXL = 32
    PADDING_CARD = 20

    # ----- Contenedores -----
    @staticmethod
    def sidebar() -> str:
        return f"""
            QWidget#sidebar {{
                background-color: {Theme.sidebar_bg()};
                border-right: 1px solid {Theme.border()};
            }}
        """

    @staticmethod
    def header() -> str:
        return f"""
            QFrame#header {{
                background-color: {Theme.header_bg()};
                border-bottom: 1px solid {Theme.border()};
            }}
        """

    @staticmethod
    def _card_base(hover: bool) -> str:
        radius = NEXAStyles.CARD_BORDER_RADIUS
        hover_rule = f"""QFrame#card:hover {{ border-color: {ACCENT}66; }}""" if hover else ""
        return f"""
            QFrame#card {{
                background-color: {Theme.card()};
                border: 1px solid {Theme.border()};
                border-radius: {radius}px;
            }}
            {hover_rule}
        """

    @staticmethod
    def card() -> str:
        return NEXAStyles._card_base(hover=True)

    @staticmethod
    def card_no_hover() -> str:
        return NEXAStyles._card_base(hover=False)

    # ----- Botones -----
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
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {ACCENT_PRESSED}; }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:disabled {{ background-color: {Theme.hover_bg()}; color: {Theme.text_muted()}; }}
        """

    @staticmethod
    def secondary_button() -> str:
        return f"""
            QPushButton {{
                background-color: {Theme.surface()};
                color: {Theme.text()};
                border: 1px solid {Theme.border_strong()};
                border-radius: {NEXAStyles.BUTTON_BORDER_RADIUS}px;
                padding: 9px 20px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; background-color: {ACCENT_BG if not is_dark() else DARK_HOVER}; }}
            QPushButton:pressed {{ background-color: {Theme.hover_bg()}; }}
            QPushButton:disabled {{ color: {Theme.text_muted()}; border-color: {Theme.border()}; }}
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
                font-weight: 500;
            }}
            QPushButton:hover {{ color: {ACCENT}; background-color: {Theme.hover_bg()}; }}
            QPushButton:pressed {{ background-color: {Theme.active_bg()}; }}
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
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #B91C1C; }}
            QPushButton:pressed {{ background-color: #991B1B; }}
        """

    # ----- Inputs -----
    @staticmethod
    def search_input() -> str:
        return f"""
            QLineEdit {{
                border: 1px solid {Theme.border()};
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 13px;
                background-color: {Theme.input_bg()};
                color: {Theme.text()};
                selection-background-color: {ACCENT};
                selection-color: #FFFFFF;
            }}
            QLineEdit:hover {{ border-color: {Theme.border_strong()}; }}
            QLineEdit:focus {{ border: 1px solid {ACCENT};
                background-color: {Theme.input_bg()}; }}
            QLineEdit::placeholder {{ color: {Theme.text_muted()}; }}
        """

    @staticmethod
    def input() -> str:
        return f"""
            QLineEdit {{
                border: 1px solid {Theme.border()};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                background-color: {Theme.input_bg()};
                color: {Theme.text()};
                selection-background-color: {ACCENT};
                selection-color: #FFFFFF;
            }}
            QLineEdit:hover {{ border-color: {Theme.border_strong()}; }}
            QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
            QLineEdit::placeholder {{ color: {Theme.text_muted()}; }}
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
                selection-background-color: {ACCENT};
            }}
            QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
        """

    # ----- Navegación (sidebar) -----
    @staticmethod
    def sidebar_button(active: bool = False) -> str:
        text_color = Theme.text() if not is_dark() else "#EDEDF3"
        bg = Theme.active_bg() if active else "transparent"
        accent = f"""border-left: 3px solid {ACCENT};""" if active else "border-left: 3px solid transparent;"
        hover = Theme.hover_bg()
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                {accent}
                border-top: none; border-right: none; border-bottom: none;
                border-radius: 8px;
                padding: 9px 12px;
                text-align: left;
                font-size: 13px;
                font-weight: {600 if active else 400};
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {Theme.active_bg()}; }}
        """

    @staticmethod
    def sidebar_section_label() -> str:
        return f"""
            QLabel {{
                color: {Theme.text_muted()};
                font-size: 10px;
                font-weight: 700;
                padding: 10px 12px 4px 12px;
                letter-spacing: 1.2px;
            }}
        """

    @staticmethod
    def sidebar_user_box() -> str:
        return f"""
            QFrame#sidebarUser {{
                background-color: {Theme.hover_bg()};
                border-radius: 10px;
            }}
        """

    # ----- Badges / KPIs / Tablas -----
    @staticmethod
    def badge(text: str, color: str) -> str:
        bg = f"{color}18"
        return f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """

    @staticmethod
    def kpi_card(color: str = ACCENT) -> str:
        return f"""
            QFrame {{
                background-color: {Theme.card()};
                border: 1px solid {Theme.border()};
                border-radius: 12px;
                padding: 18px;
            }}
        """

    @staticmethod
    def table() -> str:
        return f"""
            QTableWidget {{
                border: 1px solid {Theme.border()};
                border-radius: 10px;
                font-size: 12px;
                background-color: {Theme.card()};
                color: {Theme.text()};
                gridline-color: {Theme.border()};
                selection-background-color: {ACCENT}26;
            }}
            QTableWidget::item {{ padding: 8px; }}
            QTableWidget::item:selected {{ background-color: {ACCENT}1F; color: {Theme.text()}; }}
            QHeaderView::section {{
                background-color: {Theme.hover_bg()};
                color: {Theme.text_secondary()};
                border: none;
                border-bottom: 1px solid {Theme.border()};
                padding: 10px 8px;
                font-weight: 600;
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
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                min-width: 120px;
            }}
            QComboBox:hover {{ border-color: {Theme.border_strong()}; }}
            QComboBox:focus {{ border: 1px solid {ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background-color: {Theme.card()};
                color: {Theme.text()};
                border: 1px solid {Theme.border()};
                selection-background-color: {ACCENT}26;
                padding: 4px;
                outline: none;
            }}
        """

    @staticmethod
    def tab(active: bool = False) -> str:
        color = ACCENT if active else Theme.text_secondary()
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: none;
                border-bottom: 2px solid {ACCENT if active else "transparent"};
                padding: 8px 16px;
                font-size: 13px;
                font-weight: {600 if active else 500};
            }}
            QPushButton:hover {{ color: {ACCENT}; }}
        """

    @staticmethod
    def alert(kind: str) -> str:
        color_map = {"success": SUCCESS, "warning": WARNING, "error": ERROR, "info": INFO}
        bg_map = {"success": SUCCESS_BG, "warning": WARNING_BG, "error": ERROR_BG, "info": INFO_BG}
        color = color_map.get(kind, INFO)
        bg = bg_map.get(kind, INFO_BG)
        return f"""
            QFrame#alert {{
                background-color: {bg};
                border: 1px solid {color}40;
                border-radius: 10px;
                padding: 10px 14px;
            }}
            QLabel {{ color: {color}; background: transparent; border: none; }}
        """

    @staticmethod
    def scroll_area() -> str:
        return f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{
                background: transparent; width: 10px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.border_strong()}; border-radius: 5px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: transparent; height: 10px; margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {Theme.border_strong()}; border-radius: 5px; min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """


# ---------------------------------------------------------------------------
# Componentes compuestos
# ---------------------------------------------------------------------------
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
        self.setText(f"\u25cf {status.capitalize()}")
        self.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")


class KPIWidget(QFrame):
    def __init__(self, title: str, value: str = "0", icon: str = "",
                 color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.kpi_card(color))
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(18, 16, 18, 16)
        top = QHBoxLayout()
        if icon:
            ico = Icon("chart" if icon else "chart", 18, color)
            ico.set_color(color)
            top.addWidget(ico)
        top.addStretch()
        layout.addLayout(top)
        self._value = QLabel(value)
        self._value.setFont(get_font(28, weight=QFont.Weight.DemiBold))
        self._value.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
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
                 icon_name: str = "apps", parent: QWidget | None = None,
                 on_click: Callable[[str], None] | None = None) -> None:
        super().__init__(parent)
        self.plugin_id = plugin_id
        self._on_click = on_click
        self.setObjectName("card")
        self.setStyleSheet(NEXAStyles.card_no_hover())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        icon_frame = QFrame()
        icon_frame.setFixedSize(42, 42)
        icon_frame.setStyleSheet(f"background-color: {ACCENT_BG if not is_dark() else ACCENT + '1F'};"
                                 f"border-radius: 10px; border: none;")
        icon_lbl = Icon(icon_name, 20)
        icon_lbl.set_color(ACCENT)
        icon_l = QVBoxLayout(icon_frame)
        icon_l.setContentsMargins(0, 0, 0, 0)
        icon_l.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(icon_frame)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setFont(get_font(13, weight=QFont.Weight.DemiBold))
        name_lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        name_lbl.setWordWrap(True)
        info.addWidget(name_lbl)
        cat_lbl = QLabel(category.capitalize() if category else "")
        cat_lbl.setFont(get_font(10))
        cat_lbl.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
        info.addWidget(cat_lbl)
        top_row.addLayout(info, stretch=1)

        self._fav_btn = QPushButton()
        fav_icon = Icon("star", 16, ACCENT if is_favorite else Theme.text_muted())
        self._fav_btn.setLayout(QVBoxLayout())
        self._fav_btn.layout().setContentsMargins(0, 0, 0, 0)
        self._fav_btn.layout().addWidget(fav_icon, 0, Qt.AlignmentFlag.AlignCenter)
        self._fav_btn.setFixedSize(30, 30)
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn.setStyleSheet(
            f"background-color: {(ACCENT + '14') if is_favorite else 'transparent'};"
            f"border: none; border-radius: 6px;")
        top_row.addWidget(self._fav_btn)
        layout.addLayout(top_row)

        desc = QLabel(description[:110] + ("..." if len(description) > 110 else ""))
        desc.setFont(get_font(11))
        desc.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        desc.setWordWrap(True)
        desc.setMaximumHeight(34)
        layout.addWidget(desc)

        bottom = QHBoxLayout()
        badge_label, badge_color = PLUGIN_STATUS_BADGES.get(status, (status, Theme.text_muted()))
        badge = QLabel(badge_label)
        badge.setStyleSheet(NEXAStyles.badge(badge_label, badge_color))
        bottom.addWidget(badge)
        bottom.addStretch()
        if execution_count > 0:
            e_icon = Icon("play", 11, Theme.text_muted())
            exec_w = QWidget()
            el = QHBoxLayout(exec_w)
            el.setContentsMargins(0, 0, 0, 0)
            el.setSpacing(4)
            el.addWidget(e_icon)
            e_lbl = QLabel(str(execution_count))
            e_lbl.setFont(get_font(10))
            e_lbl.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent; border: none;")
            el.addWidget(e_lbl)
            bottom.addWidget(exec_w)
        layout.addLayout(bottom)

    def mousePressEvent(self, event) -> None:
        if self._on_click:
            self._on_click(self.plugin_id)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Paleta de la aplicación
# ---------------------------------------------------------------------------
def setup_app_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(Theme.bg()))
    palette.setColor(QPalette.WindowText, QColor(Theme.text()))
    palette.setColor(QPalette.Base, QColor(Theme.input_bg()))
    palette.setColor(QPalette.AlternateBase, QColor(Theme.hover_bg()))
    palette.setColor(QPalette.Text, QColor(Theme.text()))
    palette.setColor(QPalette.Button, QColor(Theme.surface()))
    palette.setColor(QPalette.ButtonText, QColor(Theme.text()))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.PlaceholderText, QColor(Theme.text_muted()))
    palette.setColor(QPalette.ToolTipBase, QColor(Theme.surface()))
    palette.setColor(QPalette.ToolTipText, QColor(Theme.text()))
    palette.setColor(QPalette.Link, QColor(ACCENT))
    app.setPalette(palette)


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------
def _text_primary() -> str: return Theme.text()
def _text_secondary() -> str: return Theme.text_secondary()
def _text_muted() -> str: return Theme.text_muted()
def _surface() -> str: return Theme.surface()
def _border() -> str: return Theme.border()

TEXT_PRIMARY = property(_text_primary) if False else Theme.text()
TEXT_SECONDARY = property(_text_secondary) if False else Theme.text_secondary()
TEXT_MUTED = property(_text_muted) if False else Theme.text_muted()
SURFACE = property(_surface) if False else Theme.surface()
BORDER = property(_border) if False else Theme.border()
DARK = DARK_SIDEBAR
SURFACE_VARIANT = DARK_SURFACE
