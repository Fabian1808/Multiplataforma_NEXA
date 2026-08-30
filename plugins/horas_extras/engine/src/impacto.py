"""Cálculo de productividad e impacto económico.

Productividad: tiempo manual vs automatizado, horas-hombre ahorradas,
% de reducción y % de automatización.

Impacto económico: monto declarado, validado, observado, pendiente y
ahorro (potencial y confirmado). El ahorro confirmado solo se marca
tras la validación del negocio.
"""

ESTADOS_SIN_SUSTENTO = {"SIN MARCACIÓN", "SIN ENTRADA", "SIN SALIDA", "OBSERVADO"}
ESTADOS_PENDIENTES = {"PENDIENTE", "AMBIGUO", "REVISIÓN MANUAL", "ERROR"}


def calcular_productividad(resultados, cfg, tiempo_ejecucion_segundos=0.0):
    """Calcula las métricas de productividad del período."""
    total = len(resultados)
    manual_min = total * cfg["productividad"]["tiempo_manual_por_registro_min"]

    excepciones = sum(1 for r in resultados if r.estado != "VALIDADO")
    ejecucion_min = tiempo_ejecucion_segundos / 60.0
    automatizado_min = ejecucion_min + excepciones * cfg["productividad"]["tiempo_revision_excepcion_min"]

    ahorrados_min = max(0.0, manual_min - automatizado_min)
    reduccion_pct = (ahorrados_min / manual_min * 100) if manual_min else 0.0

    validados = sum(1 for r in resultados if r.estado == "VALIDADO")
    automatizacion_pct = (validados / total * 100) if total else 0.0

    costo_hh = cfg["productividad"]["costo_hora_hombre"]
    ahorro_monetario = ahorrados_min / 60.0 * costo_hh if costo_hh else None

    return {
        "registros_procesados": total,
        "registros_validados": validados,
        "excepciones": excepciones,
        "tiempo_manual_min": round(manual_min, 2),
        "tiempo_ejecucion_seg": round(tiempo_ejecucion_segundos, 2),
        "tiempo_automatizado_min": round(automatizado_min, 2),
        "horas_hombre_ahorradas_min": round(ahorrados_min, 2),
        "horas_hombre_ahorradas": round(ahorrados_min / 60.0, 4),
        "reduccion_pct": round(reduccion_pct, 2),
        "automatizacion_pct": round(automatizacion_pct, 2),
        "ahorro_monetario_hh": ahorro_monetario,
    }


def calcular_impacto(resultados):
    """Calcula las magnitudes económicas del período."""
    monto_declarado = round(sum(r.monto_total for r in resultados), 2)
    monto_validado = round(sum(r.monto_total for r in resultados if r.estado == "VALIDADO"), 2)
    monto_observado = round(sum(r.monto_total for r in resultados if r.estado in ESTADOS_SIN_SUSTENTO), 2)
    monto_pendiente = round(sum(r.monto_total for r in resultados if r.estado in ESTADOS_PENDIENTES), 2)

    ahorro_potencial = monto_observado

    excedentes = 0.0
    for r in resultados:
        if r.estado == "VALIDADO" and r.monto_total and r.costo_total:
            diff = round(float(r.monto_total) - float(r.costo_total), 2)
            if diff > 0:
                excedentes += diff
    ahorro_confirmado = round(excedentes, 2)

    reduccion_pct = (monto_observado / monto_declarado * 100) if monto_declarado else 0.0

    return {
        "monto_declarado": monto_declarado,
        "monto_validado": monto_validado,
        "monto_observado": monto_observado,
        "monto_pendiente": monto_pendiente,
        "ahorro_potencial": ahorro_potencial,
        "ahorro_confirmado": ahorro_confirmado,
        "reduccion_pct": round(reduccion_pct, 2),
    }