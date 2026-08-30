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

