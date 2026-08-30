"""Funciones de agregación de resultados de conciliación.

Agrupa registros por empleado, turno, especialidad, día de semana,
y genera totales de horas y costos para dashboards.
"""

from collections import defaultdict


def _clave(valor):
    return str(valor or "").strip().upper()


def _he_horas(r):
    if r.horas_extras is None:
        return 0.0
    try:
        return float(r.horas_extras)
    except (TypeError, ValueError):
        return 0.0


def _costo(r, attr):
    v = getattr(r, attr, None)
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _safe_float(r, attr, default=0.0):
    v = getattr(r, attr, None)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _agregar_empleado(acum, r):
    acum["registros"] += 1
    acum["horas_extras"] += _he_horas(r)
    acum["horas_25"] += _safe_float(r, "horas_25")
    acum["horas_35"] += _safe_float(r, "horas_35")
    acum["horas_100"] += _safe_float(r, "horas_100")
    acum["valor_hhee"] += _safe_float(r, "valor_hhee")
    acum["transporte"] += _safe_float(r, "transporte_valor")
    acum["alimentacion"] += _safe_float(r, "alimentacion_valor")
    acum["costo_total"] += _safe_float(r, "costo_total")
    acum["monto_declarado"] += _safe_float(r, "monto_total")

    est = str(r.estado or "").strip().upper()
    acum["estados"][est] = acum["estados"].get(est, 0) + 1

    conf = str(r.confianza or "").strip().upper()
    acum["confianza"][conf] = acum["confianza"].get(conf, 0) + 1

    if r.fecha:
        acum["fechas"].add(str(r.fecha))

    if r.turno:
        turnos = acum["turnos"]
        turnos[r.turno] = turnos.get(r.turno, 0) + 1

    if _he_horas(r) > 0:
        acum["dias_con_he"] += 1
        he = _he_horas(r)
        if he > acum["he_max_dia"]:
            acum["he_max_dia"] = he


def _nuevo_acum():
    return {
        "registros": 0,
        "horas_extras": 0.0,
        "horas_25": 0.0,
        "horas_35": 0.0,
        "horas_100": 0.0,
        "valor_hhee": 0.0,
        "transporte": 0.0,
        "alimentacion": 0.0,
        "costo_total": 0.0,
        "monto_declarado": 0.0,
        "estados": {},
        "confianza": {},
        "fechas": set(),
        "turnos": {},
        "dias_con_he": 0,
        "he_max_dia": 0.0,
    }


def _serializar_acum(acum):
    return {
        "registros": acum["registros"],
        "horas_extras": round(acum["horas_extras"], 2),
        "horas_25": round(acum["horas_25"], 2),
        "horas_35": round(acum["horas_35"], 2),
        "horas_100": round(acum["horas_100"], 2),
        "valor_hhee": round(acum["valor_hhee"], 2),
        "transporte": round(acum["transporte"], 2),
        "alimentacion": round(acum["alimentacion"], 2),
        "costo_total": round(acum["costo_total"], 2),
        "monto_declarado": round(acum["monto_declarado"], 2),
        "estados": acum["estados"],
        "confianza": acum["confianza"],
        "dias_trabajados": len(acum["fechas"]),
        "dias_con_he": acum["dias_con_he"],
        "he_max_dia": round(acum["he_max_dia"], 2),
        "turno_principal": max(acum["turnos"], key=acum["turnos"].get) if acum["turnos"] else "",
    }


def _dia_semana_es(fecha):
    if fecha is None:
        return ""
    try:
        dias = {0: "LUNES", 1: "MARTES", 2: "MIERCOLES", 3: "JUEVES",
                4: "VIERNES", 5: "SABADO", 6: "DOMINGO"}
        if hasattr(fecha, "weekday"):
            return dias.get(fecha.weekday(), "")
        from datetime import datetime as _dt
        s = str(fecha).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return dias[_dt.strptime(s, fmt).weekday()]
            except (ValueError, AttributeError):
                continue
    except Exception:
        pass
    return ""


def agregar_por_empleado(resultados):
    """Agrupa por nombre de empleado (consolidado). Devuelve dict."""
    grupos = defaultdict(lambda: _nuevo_acum())
    for r in resultados:
        clave = _clave(r.empleado)
        if not clave:
            continue
        _agregar_empleado(grupos[clave], r)

    salida = {}
    for nombre, acum in grupos.items():
        datos = _serializar_acum(acum)
        datos["empleado"] = nombre
        salida[nombre] = datos
    return salida


def agregar_por_turno(resultados):
    """Agrupa por turno (T1/T2/T3). Devuelve dict."""
    grupos = defaultdict(lambda: _nuevo_acum())
    for r in resultados:
        clave = _clave(r.turno) or "SIN TURNO"
        _agregar_empleado(grupos[clave], r)
    return {k: _serializar_acum(v) for k, v in grupos.items()}


def agregar_por_especialidad(resultados):
    """Agrupa por especialidad. Devuelve dict."""
    grupos = defaultdict(lambda: _nuevo_acum())
    for r in resultados:
        clave = _clave(r.especialidad) or "SIN ESPECIALIDAD"
        _agregar_empleado(grupos[clave], r)
    return {k: _serializar_acum(v) for k, v in grupos.items()}


def agregar_por_dia_semana(resultados):
    """Agrupa por día de la semana. Devuelve dict."""
    grupos = defaultdict(lambda: _nuevo_acum())
    for r in resultados:
        dia = _dia_semana_es(r.fecha) or "DESCONOCIDO"
        _agregar_empleado(grupos[dia], r)
    return {k: _serializar_acum(v) for k, v in grupos.items()}


def agregar_por_estado(resultados):
    """Cuenta registros por estado. Devuelve dict."""
    conteo = defaultdict(lambda: {"registros": 0, "costo_total": 0.0, "monto_declarado": 0.0})
    for r in resultados:
        est = str(r.estado or "").strip().upper() or "SIN ESTADO"
        conteo[est]["registros"] += 1
        conteo[est]["costo_total"] += _safe_float(r, "costo_total")
        conteo[est]["monto_declarado"] += _safe_float(r, "monto_total")
    return {k: {"registros": v["registros"],
                "costo_total": round(v["costo_total"], 2),
                "monto_declarado": round(v["monto_declarado"], 2)}
            for k, v in conteo.items()}


def calcular_alertas(resultados, umbrales=None):
    """Detecta colaboradores con anomalías.

    Devuelve lista de dicts: {tipo, severidad, empleado, mensaje, valor}.
    """
    umbrales = umbrales or {}
    umbral_he = umbrales.get("horas_extras_max_mes", 40)
    umbral_costo_factor = umbrales.get("costo_anomalo_factor", 3.0)

    empleados = agregar_por_empleado(resultados)
    if not empleados:
        return []

    costos_totales = [v["costo_total"] for v in empleados.values() if v["costo_total"] > 0]
    promedio_costo = sum(costos_totales) / len(costos_totales) if costos_totales else 0

    alertas = []

    for nombre, datos in empleados.items():
        if datos["horas_extras"] > umbral_he:
            alertas.append({
                "tipo": "EXCESO_HE",
                "severidad": "ALTA",
                "empleado": nombre,
                "mensaje": "%s tiene %.1fh de HE este mes (limite: %dh)."
                           % (nombre, datos["horas_extras"], umbral_he),
                "valor": datos["horas_extras"],
            })

        if datos["costo_total"] > promedio_costo * umbral_costo_factor and promedio_costo > 0:
            alertas.append({
                "tipo": "COSTO_ANOMALO",
                "severidad": "ALTA",
                "empleado": nombre,
                "mensaje": "%s tiene un costo de S/ %.2f (promedio: S/ %.2f)."
                           % (nombre, datos["costo_total"], promedio_costo),
                "valor": datos["costo_total"],
            })

    sin_rainbow = sum(1 for r in resultados
                      if str(getattr(r, "validacion_rainbow", "") or "").upper() == "NO"
                      and _he_horas(r) > 0)
    if sin_rainbow > 0:
        alertas.append({
            "tipo": "SIN_EVIDENCIA",
            "severidad": "MEDIA",
            "empleado": "",
            "mensaje": "%d registro(s) con horas extras sin evidencia en RAINBOW." % sin_rainbow,
            "valor": sin_rainbow,
        })

    return sorted(alertas, key=lambda a: {"ALTA": 0, "MEDIA": 1, "BAJA": 2}.get(a["severidad"], 9))


def construir_dashboard(resultados):
    """Construye todos los datos del dashboard para el historial.

    Devuelve dict serializable a JSON.
    """
    por_empleado = agregar_por_empleado(resultados)
    ranking = sorted(por_empleado.values(), key=lambda x: x["costo_total"], reverse=True)

    return {
        "por_empleado": ranking[:50],
        "por_turno": agregar_por_turno(resultados),
        "por_especialidad": agregar_por_especialidad(resultados),
        "por_dia_semana": agregar_por_dia_semana(resultados),
        "por_estado": agregar_por_estado(resultados),
        "alertas": calcular_alertas(resultados),
        "resumen": {
            "total_empleados": len(por_empleado),
            "total_registros": len(resultados),
            "total_horas_extras": round(sum(d["horas_extras"] for d in por_empleado.values()), 2),
            "total_costo": round(sum(d["costo_total"] for d in por_empleado.values()), 2),
            "total_valor_hhee": round(sum(d["valor_hhee"] for d in por_empleado.values()), 2),
            "promedio_he_empleado": round(
                sum(d["horas_extras"] for d in por_empleado.values()) / len(por_empleado), 2
            ) if por_empleado else 0,
            "empleados_con_he": sum(1 for d in por_empleado.values() if d["horas_extras"] > 0),
        },
    }
