"""UI Common — NEXA Design System v4.0.

Sistema de diseño corporativo de nivel premium.
Modo oscuro: superficies con elevación real (Material You-like).
Modo claro: moderno y profesional inspirado en Apple HIG.

Identidad NEXA:
  Acento principal : #FF5503  (naranja)
  Gris corporativo : #3B3B3B
  Tipografía        : Segoe UI
  Iconografía       : vectores propios (QPainter), sin emojis.
"""

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

# ---------------------------------------------------------------------------
# IDENTIDAD NEXA
# ---------------------------------------------------------------------------
ACCENT         = "#FF5503"
ACCENT_HOVER   = "#E64C02"
ACCENT_PRESSED = "#CC4402"
ACCENT_LIGHT   = "#FF7B36"
ACCENT_BG      = "#FFF4ED"
ACCENT_TINT    = "#FFEAE0"
ACCENT_DARK_BG = "#FF550322"

# Estados semánticos
SUCCESS    = "#16A34A"
SUCCESS_BG = "#DCFCE7"
WARNING    = "#D97706"
WARNING_BG = "#FEF3C7"
ERROR      = "#DC2626"
ERROR_BG   = "#FEE2E2"
INFO       = "#2563EB"
INFO_BG    = "#DBEAFE"

STATUS_COLORS = {"operational": SUCCESS, "warning": WARNING, "error": ERROR, "info": INFO}
PLUGIN_STATUS_BADGES = {
    "oficial":   ("Oficial",    SUCCESS),
    "comunidad": ("Comunidad",  INFO),
    "beta":      ("Beta",       WARNING),
    "deprecada": ("Deprecada",  ERROR),
}

# ---------------------------------------------------------------------------
# MODO OSCURO — superficies con elevación real
#  dp0  #121214  fondo base
#  dp1  #1C1C1F  sidebar / nav
#  dp2  #202024  header
#  dp4  #28282C  cards
#  dp8  #2E2E34  cards hover / dialogs
# ---------------------------------------------------------------------------
DARK_BG            = "#111111"
DARK_SURFACE       = "#1C1C1F"
DARK_SURFACE_2     = "#202024"
DARK_CARD          = "#28282C"
DARK_CARD_ELEVATED = "#2E2E34"
DARK_SIDEBAR       = "#171717"
DARK_HEADER        = "#202024"
DARK_BORDER        = "#38383E"
DARK_BORDER_STRONG = "#4A4A52"
DARK_TEXT          = "#F2F2F7"
DARK_TEXT_SECONDARY = "#9A9AA8"
DARK_TEXT_MUTED    = "#5E5E6A"
DARK_INPUT         = "#1C1C1F"
DARK_INPUT_FOCUS   = "#28282C"
DARK_HOVER         = "#2E2E34"
DARK_ACTIVE_BG     = "#FF550318"
DARK_SECTION_LABEL = "#5E5E6A"

# ---------------------------------------------------------------------------
# Sidebar — paleta profesional dedicada (claro/oscuro)
#   Claro: fondo #FFFFFF, activo #FF5503, hover #FFF1EB, seleccionado #FFF3ED
#   Oscuro: fondo #171717, activo #FF6A2A, hover #292929, seleccionado #2A1A14
# ---------------------------------------------------------------------------
LIGHT_SIDEBAR_TEXT      = "#1F1F1F"
DARK_SIDEBAR_TEXT       = "#F5F5F5"
LIGHT_SIDEBAR_TEXT_2    = "#6B7280"
DARK_SIDEBAR_TEXT_2     = "#A3A3A3"
LIGHT_SIDEBAR_ICON      = "#3B3B3B"
DARK_SIDEBAR_ICON       = "#D4D4D4"
LIGHT_SIDEBAR_HOVER     = "#FFF1EB"
DARK_SIDEBAR_HOVER      = "#292929"
LIGHT_SIDEBAR_ACTIVE_BG = "#FFF3ED"
DARK_SIDEBAR_ACTIVE_BG  = "#2A1A14"
LIGHT_SIDEBAR_BORDER    = "#E5E7EB"
DARK_SIDEBAR_BORDER     = "#2D2D2D"
LIGHT_SIDEBAR_ACTIVE    = "#FF5503"
DARK_SIDEBAR_ACTIVE     = "#FF6A2A"
# Relleno neutro ligero de tarjetas/paneles internos del sidebar.
LIGHT_SIDEBAR_CARD      = "#F7F8FA"
DARK_SIDEBAR_CARD       = "#1E1E1E"
# Borde de la tarjeta del logo (blanca en ambos modos): en oscuro un gris medio.
LIGHT_LOGO_CARD_BORDER  = "#E5E7EB"
DARK_LOGO_CARD_BORDER   = "#3A3A3A"

# ---------------------------------------------------------------------------
# MODO CLARO — moderno y limpio con estructura visual clara
# ---------------------------------------------------------------------------
LIGHT_BG             = "#F5F5F7"
LIGHT_SURFACE        = "#FFFFFF"
LIGHT_CARD           = "#FFFFFF"
LIGHT_CARD_ELEVATED  = "#F9F9FB"
LIGHT_SIDEBAR        = "#FFFFFF"
LIGHT_HEADER         = "#FFFFFF"
LIGHT_BORDER         = "#E5E5EA"
LIGHT_BORDER_STRONG  = "#C7C7CC"
LIGHT_TEXT           = "#1C1C1E"
LIGHT_TEXT_SECONDARY = "#636366"
LIGHT_TEXT_MUTED     = "#AEAEB2"
LIGHT_INPUT          = "#F5F5F7"
LIGHT_INPUT_FOCUS    = "#FFFFFF"
LIGHT_HOVER          = "#F0F0F3"
LIGHT_ACTIVE_BG      = "#FFF2EC"
LIGHT_SECTION_LABEL  = "#AEAEB2"

# ---------------------------------------------------------------------------
# Estado global del tema
# ---------------------------------------------------------------------------
_APPDATA    = os.environ.get("APPDATA", str(Path.home()))
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
    """Devuelve el token correcto según el tema activo en el momento de la llamada."""
    return dark if is_dark() else light


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


# ---------------------------------------------------------------------------
# Iconos lineales — familia propia, sin emojis
#  Variantes "outline" basadas en la convención Lucide (grid 24x24, stroke 2).
# ---------------------------------------------------------------------------
_SVG_TOKEN_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


def _arc_cubics(ax, ay, rx, ry, rot_deg, large_arc, sweep, bx, by):
    """Convierte un arco elíptico SVG a segmentos cúbicos de Bézier.

    Recibe coordenadas de inicio (ax, ay), radios rx/ry, rotación en grados,
    flags large-arc/sweep y fin (bx, by). Devuelve lista de tuplas
    ((c1x, c1y), (c2x, c2y), (x, y)).
    """
    if ax == bx and ay == by:
        return []
    phi = math.radians(rot_deg)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    dx = (ax - bx) / 2.0
    dy = (ay - by) / 2.0
    tx = cos_p * dx + sin_p * dy
    ty = -sin_p * dx + cos_p * dy
    rx, ry = abs(rx), abs(ry)
    rat = tx * tx / (rx * rx) if rx else 0.0
    rat += ty * ty / (ry * ry) if ry else 0.0
    if rat > 1.0:
        s = math.sqrt(rat)
        rx *= s
        ry *= s
    den = rx * rx * ty * ty + ry * ry * tx * tx
    if den:
        num = rx * rx * ry * ry - rx * rx * ty * ty - ry * ry * tx * tx
        rad = math.sqrt(max(num, 0.0) / den)
        if large_arc == sweep:
            rad = -rad
    else:
        rad = 0.0
    ccx = rad * rx * ty / ry if ry else 0.0
    ccy = -rad * ry * tx / rx if rx else 0.0
    cx = cos_p * ccx - sin_p * ccy + (ax + bx) / 2.0
    cy = sin_p * ccx + cos_p * ccy + (ay + by) / 2.0

    def _ang(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        nm = math.hypot(ux, uy) * math.hypot(vx, vy)
        if nm == 0:
            return 0.0
        a = math.acos(max(-1.0, min(1.0, dot / nm)))
        return -a if ux * vy - uy * vx < 0 else a

    u1x, u1y = (tx - ccx) / rx if rx else 0.0, (ty - ccy) / ry if ry else 0.0
    u2x, u2y = (-tx - ccx) / rx if rx else 0.0, (-ty - ccy) / ry if ry else 0.0
    theta1 = _ang(1.0, 0.0, u1x, u1y)
    dtheta = _ang(u1x, u1y, u2x, u2y)
    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    def _pt(theta):
        return (
            cx + rx * math.cos(theta) * cos_p - ry * math.sin(theta) * sin_p,
            cy + rx * math.cos(theta) * sin_p + ry * math.sin(theta) * cos_p,
        )

    def _tan(theta):
        return (
            -(rx * math.sin(theta)) * cos_p - (ry * math.cos(theta)) * sin_p,
            -(rx * math.sin(theta)) * sin_p + (ry * math.cos(theta)) * cos_p,
        )

    nsegs = max(1, int(math.ceil(abs(dtheta) / (math.pi / 2.0))))
    dseg = dtheta / nsegs
    t0, out = theta1, []
    for _ in range(nsegs):
        t1 = t0 + dseg
        a = 4.0 / 3.0 * math.tan(dseg / 4.0)
        x1, y1 = _pt(t0)
        x2, y2 = _pt(t1)
        dx1, dy1 = _tan(t0)
        dx2, dy2 = _tan(t1)
        out.append(((x1 + a * dx1, y1 + a * dy1),
                    (x2 - a * dx2, y2 - a * dy2),
                    (x2, y2)))
        t0 = t1
    return out
class Icon(QLabel):
    """Icono lineal monocromo dibujado con QPainter.

    Uso:
        ico = Icon("home", 18)
        ico.set_color("#FF5503")
        pm  = ico.get_pixmap()   # siempre disponible
    """

    _PATHS: dict[str, list] = {
        "home":     [
            ("path", "M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"),
            ("path", "M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"),
        ],
        "grid":     [
            ("rect", (3, 3, 7, 7)), ("rect", (14, 3, 7, 7)),
            ("rect", (3, 14, 7, 7)), ("rect", (14, 14, 7, 7)),
        ],
        "search":   [("circle", (11, 11, 8)), ("path", "m21 21-4.34-4.34")],
        "apps":     [
            ("rect", (4, 4, 5, 5)), ("rect", (15, 4, 5, 5)),
            ("rect", (4, 15, 5, 5)), ("rect", (15, 15, 5, 5)),
        ],
        "house":    [
            ("path", "M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"),
            ("path", "M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"),
        ],
        "layout-grid": [
            ("rect", (3, 3, 7, 7)), ("rect", (14, 3, 7, 7)),
            ("rect", (14, 14, 7, 7)), ("rect", (3, 14, 7, 7)),
        ],
        "app-window": [
            ("rect", (2, 4, 20, 16)),
            ("path", "M10 4v4"), ("path", "M2 8h20"), ("path", "M6 4v4"),
        ],
        "lightbulb": [
            ("path", "M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"),
            ("path", "M9 18h6"), ("path", "M10 22h4"),
        ],
        "clipboard-list": [
            ("rect", (8, 2, 8, 4)),
            ("path", "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"),
            ("path", "M12 11h4"), ("path", "M12 16h4"),
            ("dot", (8, 11)), ("dot", (8, 16)),
        ],
        "triangle-alert": [
            ("path", "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"),
            ("path", "M12 9v4"), ("dot", (12, 17)),
        ],
        "book-open": [
            ("path", "M12 5v16"),
            ("path", "M20.001 19A2 2 0 0 0 22 17V5a2 2 0 0 0-1.999-2L16 3.002A5 5 0 0 0 12 5a5 5 0 0 0-4-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 1.999 2H8a5 5 0 0 1 4 2 5 5 0 0 1 4-2z"),
        ],
        "users-round": [
            ("path", "M18 21a8 8 0 0 0-16 0"),
            ("circle", (10, 8, 5)),
            ("path", "M22 20c0-3.37-2-6.5-4-8a5 5 0 0 0-.45-8.3"),
        ],
        "chart":    [
            ("path", "M4 20 H20"), ("path", "M6 16 v-5"),
            ("path", "M12 16 v-9"), ("path", "M18 16 v-7"),
        ],
        "chart-column": [
            ("path", "M3 3v16a2 2 0 0 0 2 2h16"),
            ("path", "M18 17V9"), ("path", "M13 17V5"), ("path", "M8 17v-3"),
        ],
        "shield":   [("path", "M12 3 L20 6 v6 c0 5-3.5 8-8 9 C7.5 20 4 17 4 12 V6 Z")],
        "shield-check": [
            ("path", "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"),
            ("path", "m9 12 2 2 4-4"),
        ],
        "user-cog": [
            ("path", "M10 15H6a4 4 0 0 0-4 4v2"),
            ("circle", (9, 7, 4)),
            ("circle", (18, 15, 3)),
            ("path", "m14.305 16.53.923-.382"),
            ("path", "m15.228 13.852-.923-.383"),
            ("path", "m16.852 12.228-.383-.923"),
            ("path", "m16.852 17.772-.383.924"),
            ("path", "m19.148 12.228.383-.923"),
            ("path", "m19.53 18.696-.382-.924"),
            ("path", "m20.772 13.852.924-.383"),
            ("path", "m20.772 16.148.924.383"),
        ],
        "file":     [("path", "M6 3 H14 L18 7 V21 H6 Z"), ("path", "M14 3 v4 h4")],
        "list":     [
            ("path", "M8 6 H20"), ("path", "M8 12 H20"), ("path", "M8 18 H20"),
            ("dot", (4, 6)), ("dot", (4, 12)), ("dot", (4, 18)),
        ],
        "book":     [
            ("path", "M4 5 C4 3.9 4.9 3 6 3 H20 V21 H6 C4.9 21 4 20.1 4 19 Z"),
            ("path", "M4 19 C4 20.1 4.9 21 6 21 H20"),
        ],
        "wrench":   [
            ("path", "M14.7 6.3a4.5 4.5 0 0 0-5.8 5.8L4 17l3 3 4.9-4.9a4.5 4.5 0 0 0 5.8-5.8L14 13l-3-3 3.7-3.7z"),
        ],
        "chart":    [
            ("path", "M4 20 H20"), ("path", "M6 16 v-5"),
            ("path", "M12 16 v-9"), ("path", "M18 16 v-7"),
        ],
        "shield":   [("path", "M12 3 L20 6 v6 c0 5-3.5 8-8 9 C7.5 20 4 17 4 12 V6 Z")],
        "users":    [
            ("circle", (12, 8, 3.2)), ("path", "M6 18 c0-3 2.7-5 6-5 s6 2 6 5"),
            ("path", "M4 16 c0-1.8 1-3.2 2.6-4"), ("path", "M20 16 c0-1.8-1-3.2-2.6-4"),
        ],
        "user":     [("circle", (12, 8, 3.5)), ("path", "M5 19 c0-3.5 3-6 7-6 s7 2.5 7 6")],
        "bell":     [
            ("path", "M6 9 a6 6 0 0 1 12 0 c0 4 1.5 5.5 2 6 H4 c.5-.5 2-2 2-6"),
            ("path", "M10 19 a2 2 0 0 0 4 0"),
        ],
        "settings": [
            ("circle", (12, 12, 3)),
            ("path", "M12 3 v3 M12 18 v3 M3 12 h3 M18 12 h3 "
                     "M5.6 5.6 l2.1 2.1 M16.3 16.3 l2.1 2.1 "
                     "M18.4 5.6 l-2.1 2.1 M7.7 16.3 l-2.1 2.1"),
        ],
        "sun":      [
            ("circle", (12, 12, 4)),
            ("path", "M12 2v2 M12 20v2 M2 12h2 M20 12h2 "
                     "m-17.07-7.07 1.41 1.41 m15.32 15.32 1.41 1.41 m-2.66-16.66 "
                     "1.41 1.41 M6.34 17.66l-1.41 1.41"),
        ],
        "moon":     [("path", "M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401")],
        "panel-left": [
            ("path", "M7 3 H19 a2 2 0 0 1 2 2 v14 a2 2 0 0 1-2 2 H7 Z"),
            ("path", "M7 3 v18"),
        ],
        "logout":   [
            ("path", "M14 4 H5 a2 2 0 0 0-2 2 v12 a2 2 0 0 0 2 2 h9"),
            ("path", "M17 8 l4 4 -4 4"), ("path", "M21 12 H9"),
        ],
        "play":     [("poly", [(7, 5), (19, 12), (7, 19)])],
        "back":     [("path", "M19 12 H5 M11 6 l-6 6 6 6")],
        "star":     [
            ("poly", [
                (12, 3.5), (14.5, 8.5), (20, 9.2), (16, 13), (17, 18.5),
                (12, 16),  (7, 18.5),   (8, 13),   (4, 9.2), (9.5, 8.5),
            ]),
        ],
        "folder":   [
            ("path", "M3 7 a2 2 0 0 1 2-2 h4 l2 2 h8 a2 2 0 0 1 2 2 v8 a2 2 0 0 1-2 2 H5 a2 2 0 0 1-2-2 Z"),
        ],
        "check":    [("path", "M4 12 L9 17 L20 6")],
        "close":    [("path", "M6 6 L18 18 M18 6 L6 18")],
        "upload":   [
            ("path", "M12 15 V4"), ("path", "M7 9 l5-5 5 5"),
            ("path", "M4 16 v3 a2 2 0 0 0 2 2 h12 a2 2 0 0 0 2-2 v-3"),
        ],
        "clock":    [("circle", (12, 12, 8)), ("path", "M12 8 v4 l3 2")],
        "activity": [("path", "M3 12 h4 l3-7 4 14 3-7 h4")],
        "flag":     [
            ("path", "M5 21 V4"),
            ("path", "M5 4 c3-2 6 2 9 0 s4 0 6 0 v8 c-2 0-4 2-6 0 s-3-2-6 0"),
        ],
        "refresh":  [("path", "M20 12 A8 8 0 1 1 18 6"), ("path", "M18 4 v4 h-4")],
        "plugin":   [("poly", [(12, 3), (20, 8), (20, 16), (12, 21), (4, 16), (4, 8)])],
        "cube":     [
            ("path", "M12 3 L21 8 v8 L12 21 L3 16 V8 Z"),
            ("path", "M3 8 l9 5 9-5"), ("path", "M12 13 v8"),
        ],
        "filter":   [("path", "M3 5 H21 M6 12 H18 M10 19 H14")],
        "eye":      [
            ("path", "M2 12 c3-5 7.5-7 10-7 s7 2 10 7 c-3 5-7.5 7-10 7 s-7-2-10-7"),
            ("circle", (12, 12, 3)),
        ],
        "eye_off":  [
            ("path", "M3 3 L21 21"),
            ("path", "M9.9 5.1 A10 10 0 0 1 12 5 c2.5 0 7 2 10 7 a14 14 0 0 1-3.2 3.6"),
            ("path", "M6.2 6.8 A14 14 0 0 0 2 12 c3 5 7.5 7 10 7 a10 10 0 0 0 4-0.85"),
            ("path", "M9.9 9.9 a3 3 0 0 0 4.2 4.2"),
        ],
        "info":     [("circle", (12, 12, 9)), ("path", "M12 8 v1"), ("path", "M12 11 v5")],
        "alert-triangle": [
            ("path", "M10.3 3.8 L2 20 h20 L13.7 3.8 a2 2 0 0 0-3.4 0 Z"),
            ("path", "M12 9 v4"), ("path", "M12 17 v1"),
        ],
        "trending-up": [("path", "M3 17 l5-5 4 4 9-9"), ("path", "M14 7 h6 v6")],
        "zap":      [("path", "M13 2 L5 13 h8 l-2 9 8-11 h-8 Z")],
        "package":  [
            ("path", "M21 16 V8 a2 2 0 0 0-1-1.7 l-7-4 a2 2 0 0 0-2 0 l-7 4 "
                     "A2 2 0 0 0 3 8 v8 a2 2 0 0 0 1 1.7 l7 4 a2 2 0 0 0 2 0 l7-4 "
                     "A2 2 0 0 0 21 16 Z"),
            ("path", "M3.3 7 L12 12 L20.7 7"), ("path", "M12 22 V12"),
        ],
        "link":     [
            ("path", "M10 13 a5 5 0 0 0 7.5 0.5 l3-3 a5 5 0 0 0-7-7 l-1.7 1.7"),
            ("path", "M14 11 a5 5 0 0 0-7.5-0.5 l-3 3 a5 5 0 0 0 7 7 l1.7-1.7"),
        ],
        "more-vertical": [("dot", (12, 5)), ("dot", (12, 12)), ("dot", (12, 19))],
    }

    def __init__(self, name: str = "plugin", size: int = 16, color: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name      = name
        self._icon_size = size
        self._color     = color or ACCENT
        self.setFixedSize(size + 4, size + 4)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._render()

    def set_color(self, color: str) -> None:
        self._color = color
        self._render()

    def set_icon(self, name: str) -> None:
        self._name = name
        self._render()

    def get_pixmap(self) -> QPixmap:
        """Renderiza y devuelve el QPixmap del icono."""
        return self._build_pixmap()

    def _render(self) -> None:
        self.setPixmap(self._build_pixmap())
        self.setStyleSheet("background: transparent; border: none;")

    def _build_pixmap(self) -> QPixmap:
        size = self._icon_size
        pm   = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self._color))
        pen.setWidthF(min(2.0, max(1.8, size / 12)))
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
                s = size / 24
                p.drawEllipse(QPointF(cx * s, cy * s), r * s, r * s)
            elif kind == "rect":
                x, y, w, h = shape[1]
                s = size / 24
                p.drawRect(QRectF(x * s, y * s, w * s, h * s))
            elif kind == "dot":
                x, y = shape[1]
                s = size / 24
                p.setBrush(QBrush(QColor(self._color)))
                p.drawEllipse(QPointF(x * s, y * s), 1.5 * s, 1.5 * s)
                p.setBrush(Qt.BrushStyle.NoBrush)
            elif kind == "poly":
                s   = size / 24
                pts = [QPointF(x * s, y * s) for x, y in shape[1]]
                p.setBrush(QBrush(QColor(self._color)))
                p.drawPolygon(QPolygonF(pts))
                p.setBrush(Qt.BrushStyle.NoBrush)
        p.end()
        return pm

    def _parse_path(self, d: str, size: int):
        """Convierte una ruta SVG (datos de iconos outline tipo Lucide) a QPainterPath.

        Soporta comandos absolutos y relativos: M L H V C S Q T A Z, con la
        repetición implícita de coordenadas de SVG. Coordenadas en grid 24x24.
        """
        from PySide6.QtGui import QPainterPath

        s      = size / 24.0
        path   = QPainterPath()
        tokens: list = []
        for m in _SVG_TOKEN_RE.finditer(d):
            tokens.append(m.group(1) if m.group(1) else float(m.group(2)))

        i = 0
        cmd: str | None = None
        cx = cy = 0.0
        sx = sy = 0.0
        ctrl: tuple[float, float] | None = None

        def num() -> float:
            return float(tokens[i])

        # Evita bucles infinitos ante datos mal formados.
        guard = 0
        max_guard = len(tokens) * 8 + 16
        while i < len(tokens) and guard < max_guard:
            guard += 1
            tok = tokens[i]
            if isinstance(tok, str):
                cmd = tok
                i += 1
                if cmd in "Zz":
                    path.closeSubpath()
                    cx, cy = sx, sy
                    ctrl = None
                continue

            if cmd is None:
                break
            if cmd in "Zz":  # número después de cerrar subruta: se ignora
                i += 1
                continue

            if cmd in "Mm":
                x, y = num() * s, num() * s
                if cmd == "m":
                    x += cx
                    y += cy
                path.moveTo(x, y)
                cx, cy, sx, sy = x, y, x, y
                cmd = "l" if cmd == "m" else "L"
                ctrl = None
                i += 2
            elif cmd in "Ll":
                x, y = num() * s, num() * s
                if cmd == "l":
                    x += cx
                    y += cy
                path.lineTo(x, y)
                cx, cy = x, y
                ctrl = None
                i += 2
            elif cmd in "Hh":
                x = num() * s
                if cmd == "h":
                    x += cx
                path.lineTo(x, cy)
                cx = x
                ctrl = None
                i += 1
            elif cmd in "Vv":
                y = num() * s
                if cmd == "v":
                    y += cy
                path.lineTo(cx, y)
                cy = y
                ctrl = None
                i += 1
            elif cmd in "Cc":
                x1, y1 = num() * s, num() * s
                x2, y2 = num() * s, num() * s
                x, y   = num() * s, num() * s
                if cmd == "c":
                    x1, y1 = cx + x1, cy + y1
                    x2, y2 = cx + x2, cy + y2
                    x, y   = cx + x, cy + y
                path.cubicTo(x1, y1, x2, y2, x, y)
                ctrl = (x2, y2)
                cx, cy = x, y
                i += 6
            elif cmd in "Ss":
                if ctrl is not None:
                    x1, y1 = 2 * cx - ctrl[0], 2 * cy - ctrl[1]
                else:
                    x1, y1 = cx, cy
                x2, y2 = num() * s, num() * s
                x, y   = num() * s, num() * s
                if cmd == "s":
                    x2, y2 = cx + x2, cy + y2
                    x, y   = cx + x, cy + y
                path.cubicTo(x1, y1, x2, y2, x, y)
                ctrl = (x2, y2)
                cx, cy = x, y
                i += 4
            elif cmd in "Qq":
                qx, qy = num() * s, num() * s
                x, y   = num() * s, num() * s
                if cmd == "q":
                    qx, qy = cx + qx, cy + qy
                    x, y   = cx + x, cy + y
                path.quadTo(qx, qy, x, y)
                ctrl = (qx, qy)
                cx, cy = x, y
                i += 4
            elif cmd in "Tt":
                if ctrl is not None:
                    qx, qy = 2 * cx - ctrl[0], 2 * cy - ctrl[1]
                else:
                    qx, qy = cx, cy
                x, y = num() * s, num() * s
                if cmd == "t":
                    x, y = cx + x, cy + y
                path.quadTo(qx, qy, x, y)
                ctrl = (qx, qy)
                cx, cy = x, y
                i += 2
            elif cmd in "Aa":
                rx, ry = num() * s, num() * s
                rot    = num()
                laf    = int(num())
                sf     = int(num())
                x, y   = num() * s, num() * s
                if cmd == "a":
                    x, y = cx + x, cy + y
                for c1, c2, end in _arc_cubics(cx, cy, rx, ry, rot, laf, sf, x, y):
                    path.cubicTo(c1[0], c1[1], c2[0], c2[1], end[0], end[1])
                cx, cy = x, y
                ctrl = None
                i += 7
            else:
                i += 1
        return path


# ---------------------------------------------------------------------------
# Sombras
# ---------------------------------------------------------------------------
def make_shadow(parent: QWidget, blur: int = 20, offset_y: int = 2,
                color: str = "#00000018") -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(color))
    return shadow


def get_icon_char(char: str = "", color: str = "", size: int = 16) -> QLabel:
    """Alias de compatibilidad con código anterior."""
    try:
        return Icon("plugin", size, color)
    except Exception:
        lbl = QLabel(char)
        lbl.setFont(get_font(size))
        lbl.setStyleSheet(f"color: {color or ACCENT}; background: transparent; border: none;")
        lbl.setFixedSize(size + 8, size + 8)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl


# ---------------------------------------------------------------------------
# Tokens semánticos de tema — API estable
# ---------------------------------------------------------------------------
class Theme:
    """Devuelve siempre el token del tema activo en el momento de la llamada."""

    @staticmethod
    def bg()             -> str: return t(LIGHT_BG,             DARK_BG)
    @staticmethod
    def surface()        -> str: return t(LIGHT_SURFACE,        DARK_SURFACE)
    @staticmethod
    def card()           -> str: return t(LIGHT_CARD,           DARK_CARD)
    @staticmethod
    def card_elevated()  -> str: return t(LIGHT_CARD_ELEVATED,  DARK_CARD_ELEVATED)
    @staticmethod
    def sidebar_bg()     -> str: return t(LIGHT_SIDEBAR,        DARK_SIDEBAR)
    @staticmethod
    def header_bg()      -> str: return t(LIGHT_HEADER,         DARK_HEADER)
    @staticmethod
    def border()         -> str: return t(LIGHT_BORDER,         DARK_BORDER)
    @staticmethod
    def border_strong()  -> str: return t(LIGHT_BORDER_STRONG,  DARK_BORDER_STRONG)
    @staticmethod
    def text()           -> str: return t(LIGHT_TEXT,           DARK_TEXT)
    @staticmethod
    def text_secondary() -> str: return t(LIGHT_TEXT_SECONDARY, DARK_TEXT_SECONDARY)
    @staticmethod
    def text_muted()     -> str: return t(LIGHT_TEXT_MUTED,     DARK_TEXT_MUTED)
    @staticmethod
    def accent()         -> str: return ACCENT
    @staticmethod
    def accent_hover()   -> str: return ACCENT_HOVER
    @staticmethod
    def success()        -> str: return SUCCESS
    @staticmethod
    def warning()        -> str: return WARNING
    @staticmethod
    def error()          -> str: return ERROR
    @staticmethod
    def info()           -> str: return INFO
    @staticmethod
    def input_bg()       -> str: return t(LIGHT_INPUT,          DARK_INPUT)
    @staticmethod
    def hover_bg()       -> str: return t(LIGHT_HOVER,          DARK_HOVER)
    @staticmethod
    def active_bg()      -> str: return t(LIGHT_ACTIVE_BG,      DARK_ACTIVE_BG)
    @staticmethod
    def section_label()  -> str: return t(LIGHT_SECTION_LABEL,  DARK_SECTION_LABEL)

    # ── Sidebar ────────────────────────────────────────────────────────────
    @staticmethod
    def sidebar_text()           -> str: return t(LIGHT_SIDEBAR_TEXT,      DARK_SIDEBAR_TEXT)
    @staticmethod
    def sidebar_text_secondary() -> str: return t(LIGHT_SIDEBAR_TEXT_2,    DARK_SIDEBAR_TEXT_2)
    @staticmethod
    def sidebar_icon()           -> str: return t(LIGHT_SIDEBAR_ICON,      DARK_SIDEBAR_ICON)
    @staticmethod
    def sidebar_hover()          -> str: return t(LIGHT_SIDEBAR_HOVER,     DARK_SIDEBAR_HOVER)
    @staticmethod
    def sidebar_active_bg()      -> str: return t(LIGHT_SIDEBAR_ACTIVE_BG, DARK_SIDEBAR_ACTIVE_BG)
    @staticmethod
    def sidebar_border()         -> str: return t(LIGHT_SIDEBAR_BORDER,    DARK_SIDEBAR_BORDER)
    @staticmethod
    def sidebar_active()         -> str: return t(LIGHT_SIDEBAR_ACTIVE,    DARK_SIDEBAR_ACTIVE)
    @staticmethod
    def logo_card_border()       -> str: return t(LIGHT_LOGO_CARD_BORDER,  DARK_LOGO_CARD_BORDER)
    @staticmethod
    def sidebar_card()           -> str: return t(LIGHT_SIDEBAR_CARD,      DARK_SIDEBAR_CARD)


# ---------------------------------------------------------------------------
# NEXAStyles — generadores de estilos QSS
# ---------------------------------------------------------------------------
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

        # Footer: categoría + badge estado
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
        badge = StatusBadge(status)
        row4.addWidget(badge)
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


# ---------------------------------------------------------------------------
# Aliases de compatibilidad con código existente
# ---------------------------------------------------------------------------
def _text_primary()   -> str: return Theme.text()
def _text_secondary() -> str: return Theme.text_secondary()
def _text_muted()     -> str: return Theme.text_muted()
def _surface()        -> str: return Theme.surface()
def _border()         -> str: return Theme.border()

TEXT_PRIMARY    = Theme.text()
TEXT_SECONDARY  = Theme.text_secondary()
TEXT_MUTED      = Theme.text_muted()
SURFACE         = Theme.surface()
BORDER          = Theme.border()
DARK            = DARK_SIDEBAR
SURFACE_VARIANT = DARK_SURFACE

