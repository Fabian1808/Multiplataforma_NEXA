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

from .theme import ACCENT

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
        # --- Iconos mejorados / nuevos ---
        "monitor": [
            ("rect", (2, 3, 20, 14)),
            ("path", "M8 21h8"), ("path", "M12 17v4"),
        ],
        "file-text": [
            ("path", "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"),
            ("path", "M14 2v4a2 2 0 0 0 2 2h4"),
            ("path", "M10 9H8"), ("path", "M16 13H8"), ("path", "M16 17H8"),
        ],
        "alert-circle": [
            ("circle", (12, 12, 10)),
            ("path", "M12 8v4"), ("dot", (12, 16)),
        ],
        "bar-chart": [
            ("path", "M12 20V10"), ("path", "M18 20V4"), ("path", "M6 20v-4"),
        ],
        "shield-lock": [
            ("path", "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"),
            ("rect", (10, 11, 4, 5)),
            ("path", "M12 11v-2a2 2 0 1 1 4 0v2"),
        ],
        "globe": [
            ("circle", (12, 12, 10)),
            ("path", "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"),
            ("path", "M2 12h20"),
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
        "menu":           [("path", "M3 6 H21"), ("path", "M3 12 H21"), ("path", "M3 18 H21")],
        "chevron-right":  [("path", "M9 6 L15 12 L9 18")],
        "chevron-left":   [("path", "M15 6 L9 12 L15 18")],
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



# ---------------------------------------------------------------------------
# SvgIcon — carga SVGs personalizados desde assets/icons/
# ---------------------------------------------------------------------------
import sys as _sys

def _get_assets_icons_dir() -> Path:
    """Devuelve la ruta correcta a assets/icons/ tanto en modo .bat como en .exe."""
    if getattr(_sys, "frozen", False):
        # Modo .exe (PyInstaller): los assets están en sys._MEIPASS/assets/icons
        return Path(_sys._MEIPASS) / "assets" / "icons"
    else:
        # Modo .bat (código fuente): subir 3 niveles desde hub/ui/common/icons.py
        return Path(__file__).resolve().parents[3] / "assets" / "icons"

_ASSETS_ICONS_DIR = _get_assets_icons_dir()


class SvgIcon(QLabel):
    """Icono cargado desde un archivo SVG en assets/icons/.

    Uso:
        ico = SvgIcon("Inicio", 20)
        ico.set_color("#FF5503")   # recolorea el SVG en memoria

    Si el archivo no existe, cae al Icon vectorial equivalente.
    """

    # Mapeo: nombre lógico -> nombre de archivo (sin extensión, case-insensitive)
    _FILE_MAP: dict[str, str] = {
        "inicio":        "Inicio",
        "catalogo":      "catalogo",
        "buscar":        "buscar",
        "propuestas":    "propuestas",
        "solicitudes":   "Solicitudes",
        "incidencias":   "incidencias",
        "comunidad":     "Comunidad",
        "reportes":      "Reportes",
        "auditoria":     "Auditoria",
        "usuarios":      "Gestion_de_usuarios",
        "sun":           "claro",
        "moon":          "oscuro",
    }
    
    _FALLBACK_MAP: dict[str, str] = {
        "inicio":        "house",
        "catalogo":      "grid",
        "buscar":        "search",
        "propuestas":    "lightbulb",
        "solicitudes":   "file-text",
        "incidencias":   "alert-circle",
        "comunidad":     "users-round",
        "reportes":      "bar-chart",
        "auditoria":     "shield-lock",
        "usuarios":      "user-cog",
        "sun":           "sun",
        "moon":          "moon",
    }

    def __init__(self, name: str = "plugin", size: int = 20, color: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name      = name.lower()
        self._icon_size = size
        self._color     = color or ACCENT
        self.setFixedSize(size + 4, size + 4)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent; border: none;")
        self._render()

    def set_color(self, color: str) -> None:
        self._color = color
        self._render()

    def set_icon(self, name: str) -> None:
        self._name = name.lower()
        self._render()

    def get_pixmap(self) -> QPixmap:
        return self._build_pixmap()

    def _render(self) -> None:
        self.setPixmap(self._build_pixmap())

    def _build_pixmap(self) -> QPixmap:
        file_name = self._FILE_MAP.get(self._name)
        if file_name:
            svg_path = _ASSETS_ICONS_DIR / f"{file_name}.svg"
            if svg_path.exists():
                return self._render_svg(svg_path)
        # Fallback: ícono vectorial integrado
        fallback_name = self._FALLBACK_MAP.get(self._name, self._name)
        try:
            return Icon(fallback_name, self._icon_size, self._color).get_pixmap()
        except Exception:
            pm = QPixmap(self._icon_size, self._icon_size)
            pm.fill(Qt.GlobalColor.transparent)
            return pm

    def _render_svg(self, svg_path: Path) -> QPixmap:
        """Renderiza el SVG recoloreando todos los strokes/fills al color activo."""
        try:
            from PySide6.QtSvg import QSvgRenderer
            import re as _re
            svg_text = svg_path.read_text(encoding="utf-8", errors="replace")
            # Recolorar: reemplazar fill y stroke con el color activo
            svg_text = _re.sub(r'fill\s*=\s*"(?!none)[^"]*"', f'fill="{self._color}"', svg_text)
            svg_text = _re.sub(r'stroke\s*=\s*"(?!none)[^"]*"', f'stroke="{self._color}"', svg_text)
            svg_text = _re.sub(r'fill\s*:\s*(?!none)[^;}"]+', f'fill:{self._color}', svg_text)
            svg_text = _re.sub(r'stroke\s*:\s*(?!none)[^;}"]+', f'stroke:{self._color}', svg_text)
            renderer = QSvgRenderer()
            renderer.load(svg_text.encode("utf-8"))
            size = self._icon_size
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter)
            painter.end()
            return pm
        except Exception:
            # Si QSvg no está disponible, usar ícono vectorial integrado
            fallback_name = self._FALLBACK_MAP.get(self._name, self._name)
            try:
                return Icon(fallback_name, self._icon_size, self._color).get_pixmap()
            except Exception:
                pm = QPixmap(self._icon_size, self._icon_size)
                pm.fill(Qt.GlobalColor.transparent)
                return pm


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
