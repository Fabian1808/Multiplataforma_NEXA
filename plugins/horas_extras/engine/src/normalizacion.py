"""Funciones de normalización de datos.

Aplicables a nombres, fechas y horas de ambas fuentes (consolidado y relatorio).
La normalización es la primera capa del matching de empleados.
"""

import datetime
import functools
import re
import unicodedata


@functools.lru_cache(maxsize=200000)
def normalizar_nombre_cached(texto):
    """Memoizada: en relatorios anuales el mismo nombre aparece decenas de
    miles de veces y la normalizacion es identica cada vez."""
    return normalizar_nombre(texto)


def normalizar_nombre(texto):
    """Normaliza un nombre para comparación.

    - mayúsculas
    - elimina tildes y diacríticos (NFD)
    - elimina caracteres especiales
    - colapsa espacios y quita espacios al inicio/final
    """
    if texto is None:
        return ""
    s = str(texto)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokens(nombre_normalizado):
    """Devuelve el conjunto de tokens de un nombre normalizado."""
    return set(nombre_normalizado.split()) if nombre_normalizado else set()


def normalizar_fecha(valor, patrones=("%d/%m/%Y",)):
    """Convierte fecha (datetime o texto) a datetime.date.

    Acepta datetime.datetime, datetime.date y texto en los patrones dados.
    """
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    s = str(valor).strip()
    for patron in patrones:
        try:
            return datetime.datetime.strptime(s, patron).date()
        except ValueError:
            continue
    raise ValueError("Fecha no parseable: %r" % valor)


def normalizar_hora(valor):
    """Convierte hora (datetime.time o texto) a datetime.time.

    Acepta time, datetime, y texto 'HH:MM[:SS]'. RAINBOW trunca el último
    dígito de los segundos (19:16:2 = 19:16:20) — regla confirmada con el
    llenado manual: pad-DERECHA; si el resultado excede 59 s (:9 -> :90),
    se usa pad-izquierda (:9 -> :09), la única interpretación plausible.
    """
    if isinstance(valor, datetime.time):
        return valor
    if isinstance(valor, datetime.datetime):
        return valor.time()
    s = str(valor).strip()
    partes = s.split(":")
    if 2 <= len(partes) <= 3 and all(p.isdigit() for p in partes):
        try:
            h = int(partes[0])
            m = int(partes[1])
            seg = int(partes[2]) if len(partes) == 3 else 0
            if len(partes) == 3 and len(partes[2]) == 1:
                seg = int(partes[2] + "0")
                if seg > 59:
                    seg = int("0" + partes[2])
        except ValueError:
            return None
        if 0 <= h <= 23 and 0 <= m <= 59 and 0 <= seg <= 59:
            return datetime.time(h, m, seg)
        return None
    raise ValueError("Hora no parseable: %r" % valor)