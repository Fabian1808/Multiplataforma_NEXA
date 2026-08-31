"""Capa 5 — VALIDACIÓN y ESTADOS de cada registro calculado.

Asigna uno de: OK / ADVERTENCIA / REVISAR / ERROR según reglas
parametrizables (solo el mínimo que el prompt exige; las tarifas no
encontradas NO eliminan el registro, solo lo marcan para revisión).
"""

from __future__ import annotations

from decimal import Decimal


ESTADOS = ["OK", "ADVERTENCIA", "REVISAR", "ERROR"]


def validar_fila(fila, cfg) -> str:
    """Devuelve el estado de una fila de DETALLE ya valorizada."""
    vcfg = cfg.get("validacion") or {}
    max_anom = Decimal(str(vcfg.get("horas_anomalas_max", 24.0)))

    estado = "OK"
    # Horas extras muy altas -> ADVERTENCIA
    extra = Decimal(str(fila.get("horas_extras") or 0))
    if extra > max_anom:
        estado = "ADVERTENCIA"
    # Sin tarifa o ambigua -> REVISAR
    if fila.get("estado") in ("REVISAR", "ERROR"):
        estado = fila["estado"]
    # Sin conciliar / sin cargo ya marca REVISAR desde tarifario
    return estado


def resumen_estados(filas) -> dict:
    conteo = {e: 0 for e in ESTADOS}
    for f in filas:
        conteo[f.get("estado", "OK")] = conteo.get(f.get("estado", "OK"), 0) + 1
    return conteo


def aplicar_estados(filas, cfg):
    """Sobrescribe/consolida estados finales y calcula totales."""
    for f in filas:
        f["estado"] = validar_fila(f, cfg)
    return filas
