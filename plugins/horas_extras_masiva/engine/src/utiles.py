"""Normalización y utilidades de HORAS EXTRAS MASIVA.

Fechas, horas, nombres, cadenas y valores monetarios. El dinero se maneja
con decimal.Decimal para evitar errores de floating point.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP


# ---------------------------------------------------------------------------
# Normalización de texto
# ---------------------------------------------------------------------------
def quitar_tildes(texto: str) -> str:
    s = str(texto or "")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


HEX_ACCENTED = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")


def normalizar_texto(texto, cfg=None) -> str:
    s = str(texto or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokens(nombre: str):
    return [t for t in nombre.replace("-", " ").replace(".", " ").split() if t]


def normalizar_nombre(nombre, cfg=None) -> str:
    """Normaliza un nombre: sin tildes, a mayúsculas, tokens ordenados si aplica."""
    cfg = cfg or {}
    norm = cfg.get("normalizacion") or {}
    s = quitar_tildes(str(nombre or "")).upper()
    s = re.sub(r"[^A-Z0-9ÑÁÉÍÓÚ ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if norm.get("ordenar_tokens", False):
        s = " ".join(sorted(s.split()))
    return s


def normalizar_nombre_cached(nombre, cfg=None, cache=None):
    if cache is None:
        return normalizar_nombre(nombre, cfg)
    key = str(nombre)
    if key in cache:
        return cache[key]
    val = normalizar_nombre(nombre, cfg)
    cache[key] = val
    return val


def limpiar_codigo(texto) -> str:
    """Extrae solo el código numérico si el nombre trae '000000002 - ALBERT'."""
    s = str(texto or "").strip()
    m = re.match(r"^(\d+)\s*-", s)
    if m:
        return m.group(1)
    return s


def limpiar_ruc(texto) -> str:
    s = str(texto or "").strip()
    s = re.sub(r"\D", "", s)
    return s


def normalizar_dni(texto) -> str:
    s = str(texto or "").strip()
    return re.sub(r"\D", "", s) or ""


# ---------------------------------------------------------------------------
# Fechas y horas
# ---------------------------------------------------------------------------
_FORMATOS_FECHA = [
    "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y",
    "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y %H:%M:%S",
]


def _parse_fecha_serie(valor) -> date | None:
    # Excel serial datetime
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        try:
            dt = datetime(1899, 12, 30) + timedelta(days=float(valor))
            return dt.date()
        except (ValueError, OverflowError):
            return None
    return None


def normalizar_fecha(valor) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        d = _parse_fecha_serie(valor)
        if d:
            return d
    s = str(valor).strip()
    s = s.split(" ")[0]
    res = None
    for fmt in _FORMATOS_FECHA:
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue
    # dd/mm/yyyy con barras invertidas o puntos
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            if y < 100:
                y += 2000 if y < 70 else 1900
            return date(y, mo, d)
        except ValueError:
            return None
    return res


def normalizar_hora(valor) -> time | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.time()
    if isinstance(valor, time):
        return valor
    if isinstance(valor, (int, float)):
        # Excel serial time (fracción de día) o segundos
        f = float(valor) % 1.0
        seg = int(round(f * 86400))
        return time(seg // 3600, (seg % 3600) // 60, seg % 60)
    s = str(valor).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    se = int(m.group(3) or 0)
    if 0 <= h <= 23 and 0 <= mi <= 59 and 0 <= se <= 59:
        return time(h, mi, se)
    return None


# ---------------------------------------------------------------------------
# Horas (Decimal para cálculos)
# ---------------------------------------------------------------------------
def hora_a_decimal(t: time | None) -> Decimal:
    if t is None:
        return Decimal("0")
    return (Decimal(t.hour) + Decimal(t.minute) / 60 + Decimal(t.second) / 3600).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP)


def decimal_a_hms(dec) -> str:
    d = Decimal(str(dec))
    total = int(d * 3600)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return "%02d:%02d:%02d" % (h, m, s)


def diff_horas(t_inicio, t_fin, cruza_medianoche=False) -> Decimal:
    """Diferencia en horas decimales entre dos horas, con opción de cruce de medianoche."""
    a = hora_a_decimal(t_inicio)
    b = hora_a_decimal(t_fin)
    if cruza_medianoche and b < a:
        b += Decimal(24)
    return (b - a).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def diff_datetime(dt1: datetime, dt2: datetime) -> Decimal:
    seg = (dt2 - dt1).total_seconds()
    return (Decimal(str(round(seg / 3600.0, 6)))).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Dinero (Decimal exacto)
# ---------------------------------------------------------------------------
def d(v) -> Decimal:
    """Convierte cualquier valor a Decimal sin errores de punto flotante."""
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def moneda(v, cfg=None) -> str:
    cfg = cfg or {}
    simbolo = cfg.get("moneda", "S/")
    dec = cfg.get("decimales", 2)
    monto = d(v).quantize(Decimal("0." + "0" * dec) if dec else Decimal("1"),
                          rounding=ROUND_HALF_UP)
    neg = monto < 0
    s = format(abs(monto), ",.%df" % dec)
    return ("-%s %s" if neg else "%s %s") % (simbolo, s)


def monto_decimal(v) -> Decimal:
    return d(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
