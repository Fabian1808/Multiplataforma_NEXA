"""Reglas de validación de Excel de HHEE contra RAINBOW.

Cada regla es una función pura: (registro_excel, resultado, cfg) -> Hallazgo.
Un hallazgo OK significa que la regla pasó; OBSERVADO/ERROR significa que
hay una inconsistencia que el usuario debe revisar.
"""

from dataclasses import dataclass, field


@dataclass
class Hallazgo:
    fila: int
    persona: str
    campo: str
    estado: str
    valor_excel: object = None
    valor_sistema: object = None
    observacion: str = ""


TOLERANCIA = 0.01


def _igual(a, b, tol=TOLERANCIA):
    """Compara dos valores numéricos con tolerancia."""
    try:
        return abs(float(a or 0) - float(b or 0)) < tol
    except (TypeError, ValueError):
        return str(a).strip().upper() == str(b).strip().upper()


def _ok(fila, persona, campo, val_excel, val_sistema):
    return Hallazgo(fila, persona, campo, "OK", val_excel, val_sistema,
                    "Información validada correctamente.")


def _error(fila, persona, campo, val_excel, val_sistema, msg):
    return Hallazgo(fila, persona, campo, "ERROR", val_excel, val_sistema, msg)


def _obs(fila, persona, campo, val_excel, val_sistema, msg):
    return Hallazgo(fila, persona, campo, "OBSERVADO", val_excel, val_sistema, msg)


# ---------------------------------------------------------------------------
# 1. Persona existe en RAINBOW
# ---------------------------------------------------------------------------
def regla_persona_existe(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    if resultado.estado == "PENDIENTE":
        return _error(f, p, "Persona", p, None,
                      "La persona no fue encontrada en RAINBOW.")
    return _ok(f, p, "Persona", p, resultado.empleado_relatorio or p)


# ---------------------------------------------------------------------------
# 2. Fecha válida
# ---------------------------------------------------------------------------
def regla_fecha_valida(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    fecha = registro.get("fecha")
    if fecha is None:
        return _error(f, p, "Fecha", registro.get("fecha"), None,
                      "La fecha no es válida o está vacía.")
    return _ok(f, p, "Fecha", str(fecha), str(resultado.fecha))


# ---------------------------------------------------------------------------
# 3. Hora de inicio existe
# ---------------------------------------------------------------------------
def regla_hora_inicio(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    h = resultado.hora_entrada
    if h is None:
        return _error(f, p, "Hora de Inicio", None, None,
                      "Falta hora de inicio. No se encontró entrada en RAINBOW.")
    return _ok(f, p, "Hora de Inicio", str(h), str(h))


# ---------------------------------------------------------------------------
# 4. Hora final existe
# ---------------------------------------------------------------------------
def regla_hora_final(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    h = resultado.hora_salida
    if h is None:
        return _error(f, p, "Hora Final", None, None,
                      "Falta hora final. No se encontró salida en RAINBOW.")
    return _ok(f, p, "Hora Final", str(h), str(h))


# ---------------------------------------------------------------------------
# 5. Duración positiva
# ---------------------------------------------------------------------------
def regla_duracion_positiva(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    ht = resultado.horas_trabajadas
    if ht is not None and ht <= 0:
        return _error(f, p, "Duración", ht, ht,
                      "La duración debe ser mayor a cero.")
    if ht is None:
        return _error(f, p, "Duración", None, None,
                      "No se pudo calcular la duración.")
    return _ok(f, p, "Duración", round(ht, 2), round(ht, 2))


# ---------------------------------------------------------------------------
# 6. Horas trabajadas coinciden
# ---------------------------------------------------------------------------
def regla_horas_trabajadas(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    v_excel = registro.get("valores_excel", {}).get("hh_rev")
    v_sistema = resultado.hh_rev
    if v_excel is None or v_sistema is None:
        return _ok(f, p, "Horas Trabajadas", v_excel, v_sistema)
    if _igual(v_excel, v_sistema):
        return _ok(f, p, "Horas Trabajadas", v_excel, v_sistema)
    return _obs(f, p, "Horas Trabajadas", v_excel, v_sistema,
                "Las horas validadas no coinciden con las calculadas por el sistema "
                "(Excel: %.2f, Sistema: %.2f)." % (float(v_excel), float(v_sistema)))


# ---------------------------------------------------------------------------
# 7. Horas extras coinciden
# ---------------------------------------------------------------------------
def regla_horas_extras(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    he_excel = registro.get("valores_excel", {}).get("hexagesimal")
    he_sistema = resultado.hexagesimal
    if he_excel is None or he_sistema is None:
        return _ok(f, p, "Horas Extras", he_excel, he_sistema)
    if _igual(he_excel, he_sistema):
        return _ok(f, p, "Horas Extras", he_excel, he_sistema)
    return _error(f, p, "Horas Extras", he_excel, he_sistema,
                  "Las horas extras no coinciden (Excel: %.2f, Sistema: %.2f)."
                  % (float(he_excel), float(he_sistema)))


# ---------------------------------------------------------------------------
# 8. Tipo HHEE coincide
# ---------------------------------------------------------------------------
def regla_tipo_hhee(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    tipo_excel = str(registro.get("valores_excel", {}).get("tipo", "")).strip().upper()
    tipo_sistema = str(resultado.tipo_rev or "").strip().upper()
    if not tipo_excel or not tipo_sistema:
        return _ok(f, p, "Tipo HHEE", tipo_excel or None, tipo_sistema or None)
    if tipo_excel == tipo_sistema:
        return _ok(f, p, "Tipo HHEE", tipo_excel, tipo_sistema)
    return _error(f, p, "Tipo HHEE", tipo_excel, tipo_sistema,
                  "El tipo de HHEE no coincide (Excel: %s, Sistema: %s)."
                  % (tipo_excel, tipo_sistema))


# ---------------------------------------------------------------------------
# 9. Split correcto para SOBRETIEMPO (25%+35%, sin 100%)
# ---------------------------------------------------------------------------
def regla_split_sobretiempo(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    tipo = str(resultado.tipo_rev or "").upper()
    if "SOBRETIEMPO" not in tipo:
        return _ok(f, p, "Split SOBRETIEMPO", None, None)
    ve = registro.get("valores_excel", {})
    h25_e = float(ve.get("h25") or 0)
    h35_e = float(ve.get("h35") or 0)
    h100_e = float(ve.get("h100") or 0)
    h25_s = resultado.horas_25
    h35_s = resultado.horas_35
    h100_s = resultado.horas_100
    errores = []
    if not _igual(h25_e, h25_s):
        errores.append("25%%: debería ser %.2f y es %.2f" % (h25_s, h25_e))
    if not _igual(h35_e, h35_s):
        errores.append("35%%: debería ser %.2f y es %.2f" % (h35_s, h35_e))
    if h100_e > 0.01:
        errores.append("SOBRETIEMPO no debe tener horas al 100%%")
    if errores:
        return _error(f, p, "Split SOBRETIEMPO", "%.2f/%.2f/%.2f" % (h25_e, h35_e, h100_e),
                       "%.2f/%.2f/%.2f" % (h25_s, h35_s, h100_s),
                       "Distribución incorrecta: " + "; ".join(errores) + ".")
    return _ok(f, p, "Split SOBRETIEMPO", "%.2f/%.2f/%.2f" % (h25_e, h35_e, h100_e),
               "%.2f/%.2f/%.2f" % (h25_s, h35_s, h100_s))


# ---------------------------------------------------------------------------
# 10. Split correcto para ACTIVACION (100% solamente)
# ---------------------------------------------------------------------------
def regla_split_activacion(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    tipo = str(resultado.tipo_rev or "").upper()
    if "ACTIVACION" not in tipo:
        return _ok(f, p, "Split ACTIVACION", None, None)
    ve = registro.get("valores_excel", {})
    h25_e = float(ve.get("h25") or 0)
    h35_e = float(ve.get("h35") or 0)
    h100_e = float(ve.get("h100") or 0)
    h25_s = resultado.horas_25
    h35_s = resultado.horas_35
    h100_s = resultado.horas_100
    errores = []
    if h25_e > 0.01:
        errores.append("25%%: debería ser 0.00 y es %.2f" % h25_e)
    if h35_e > 0.01:
        errores.append("35%%: debería ser 0.00 y es %.2f" % h35_e)
    if not _igual(h100_e, h100_s):
        errores.append("100%%: debería ser %.2f y es %.2f" % (h100_s, h100_e))
    if errores:
        return _error(f, p, "Split ACTIVACION", "%.2f/%.2f/%.2f" % (h25_e, h35_e, h100_e),
                       "%.2f/%.2f/%.2f" % (h25_s, h35_s, h100_s),
                       "ACTIVACION debe ser al 100%%. " + "; ".join(errores) + ".")
    return _ok(f, p, "Split ACTIVACION", "%.2f/%.2f/%.2f" % (h25_e, h35_e, h100_e),
               "%.2f/%.2f/%.2f" % (h25_s, h35_s, h100_s))


# ---------------------------------------------------------------------------
# 11. Tarifa de especialidad correcta
# ---------------------------------------------------------------------------
def regla_tarifa_especialidad(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    esp = resultado.especialidad
    if not esp:
        return _ok(f, p, "Tarifa Especialidad", None, None)
    tabla = (_cfg or {}).get("_tabla_costos")
    if tabla is None:
        return _ok(f, p, "Tarifa Especialidad", esp, None)
    tarifa = tabla.lookup(esp)
    if tarifa is None:
        return _error(f, p, "Tarifa Especialidad", esp, None,
                      "No se encontró tarifa para la especialidad '%s'." % esp)
    return _ok(f, p, "Tarifa Especialidad", esp, tarifa.especialidad)


# ---------------------------------------------------------------------------
# 12. Valor HHEE correcto
# ---------------------------------------------------------------------------
def regla_valor_hhee(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    ve = registro.get("valores_excel", {})
    v_excel = float(ve.get("valor_hhee") or 0)
    v_sistema = float(resultado.valor_hhee or 0)
    if v_excel == 0 and v_sistema == 0:
        return _ok(f, p, "Valor HHEE", 0, 0)
    if v_excel == 0 and v_sistema > 0:
        return _error(f, p, "Valor HHEE", v_excel, v_sistema,
                      "El Excel no registra valor HHEE, pero el sistema calcula S/ %.2f."
                      % v_sistema)
    if _igual(v_excel, v_sistema):
        return _ok(f, p, "Valor HHEE", v_excel, v_sistema)
    return _error(f, p, "Valor HHEE", v_excel, v_sistema,
                  "El valor HHEE no coincide (Excel: S/ %.2f, Sistema: S/ %.2f)."
                  % (v_excel, v_sistema))


# ---------------------------------------------------------------------------
# 13. Transporte correcto
# ---------------------------------------------------------------------------
def regla_transporte(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    ve = registro.get("valores_excel", {})
    t_excel = float(ve.get("transporte_valor") or 0)
    t_sistema = float(resultado.transporte_valor or 0)
    cant_excel = int(float(ve.get("transporte_cant") or 0))
    cant_sistema = resultado.transporte_cant
    if t_excel == 0 and t_sistema == 0:
        return _ok(f, p, "Transporte", 0, 0)
    if cant_excel != 0 and cant_excel != cant_sistema:
        return _error(f, p, "Transporte", cant_excel, cant_sistema,
                      "La cantidad de personas no coincide (Excel: %d, Sistema: %d)."
                      % (cant_excel, cant_sistema))
    if _igual(t_excel, t_sistema):
        return _ok(f, p, "Transporte", t_excel, t_sistema)
    cfg_costos = (_cfg or {}).get("costos", {})
    tarifa = cfg_costos.get("transporte_por_persona", 90)
    return _error(f, p, "Transporte", t_excel, t_sistema,
                  "El costo de transporte por persona no corresponde "
                  "(Excel: S/ %.2f, Sistema: S/ %.2f). Tarifa esperada: S/ %s."
                  % (t_excel, t_sistema, tarifa))


# ---------------------------------------------------------------------------
# 14. Alimentación corresponde al turno
# ---------------------------------------------------------------------------
def regla_alimentacion(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    ve = registro.get("valores_excel", {})
    alim_excel = str(ve.get("alimentacion_tipo") or "").strip().upper()
    alim_sistema = str(resultado.alimentacion_tipo or "").strip().upper()
    if not alim_excel and not alim_sistema:
        return _ok(f, p, "Alimentación", None, None)
    if not alim_excel:
        return _ok(f, p, "Alimentación", None, alim_sistema)
    if alim_excel == alim_sistema:
        return _ok(f, p, "Alimentación", alim_excel, alim_sistema)
    return _obs(f, p, "Alimentación", alim_excel, alim_sistema,
                "El tipo de alimentación no coincide "
                "(Excel: %s, Sistema: %s)." % (alim_excel, alim_sistema))


# ---------------------------------------------------------------------------
# 15. Total correcto (HHEE + Transporte + Alimentación)
# ---------------------------------------------------------------------------
def regla_total(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    ve = registro.get("valores_excel", {})
    total_excel = float(ve.get("costo_total") or 0)
    total_sistema = float(resultado.costo_total or 0)
    if total_excel == 0 and total_sistema == 0:
        return _ok(f, p, "Costo Total", 0, 0)
    if _igual(total_excel, total_sistema):
        return _ok(f, p, "Costo Total", total_excel, total_sistema)
    return _error(f, p, "Costo Total", total_excel, total_sistema,
                  "El total no coincide (Excel: S/ %.2f, Sistema: S/ %.2f). "
                  "Diferencia: S/ %.2f."
                  % (total_excel, total_sistema, abs(total_excel - total_sistema)))


# ---------------------------------------------------------------------------
# 16. Campos obligatorios no vacíos
# ---------------------------------------------------------------------------
def regla_campos_obligatorios(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    campos = {
        "Fecha": registro.get("fecha"),
        "Turno": registro.get("turno"),
        "Persona": registro.get("empleado"),
    }
    faltantes = [k for k, v in campos.items() if not v or str(v).strip() == ""]
    if faltantes:
        return _error(f, p, "Campos Obligatorios", None, None,
                      "Faltan campos obligatorios: %s." % ", ".join(faltantes))
    return _ok(f, p, "Campos Obligatorios", "Completo", "Completo")


# ---------------------------------------------------------------------------
# 17. No duplicados
# ---------------------------------------------------------------------------
def regla_no_duplicados(registro, resultado, _cfg=None):
    f, p = registro["fila_excel"], registro["empleado"]
    duplicados = (_cfg or {}).get("_duplicados Detectados") or set()
    clave = (registro.get("empleado"), str(registro.get("fecha")),
             registro.get("turno"))
    if clave in duplicados:
        return _error(f, p, "Duplicados", str(clave), None,
                      "Registro duplicado: misma persona, fecha y turno.")
    return _ok(f, p, "Duplicados", "Sin duplicados", "Sin duplicados")


# ---------------------------------------------------------------------------
# Lista maestra de todas las reglas
# ---------------------------------------------------------------------------
REGLAS = [
    regla_persona_existe,
    regla_fecha_valida,
    regla_hora_inicio,
    regla_hora_final,
    regla_duracion_positiva,
    regla_horas_trabajadas,
    regla_horas_extras,
    regla_tipo_hhee,
    regla_split_sobretiempo,
    regla_split_activacion,
    regla_tarifa_especialidad,
    regla_valor_hhee,
    regla_transporte,
    regla_alimentacion,
    regla_total,
    regla_campos_obligatorios,
    regla_no_duplicados,
]


def ejecutar_reglas(registro, resultado, cfg=None):
    """Ejecuta todas las reglas y devuelve lista de Hallazgos."""
    return [regla(registro, resultado, cfg) for regla in REGLAS]


def estado_resumen(hallazgos):
    """Resumen: devuelve dict con conteos OK/OBSERVADO/ERROR."""
    ok = sum(1 for h in hallazgos if h.estado == "OK")
    obs = sum(1 for h in hallazgos if h.estado == "OBSERVADO")
    err = sum(1 for h in hallazgos if h.estado == "ERROR")
    return {"ok": ok, "observado": obs, "error": err, "total": len(hallazgos)}


def estado_fila(hallazgos):
    """Estado general de una fila: ERROR si hay error, OBSERVADO si hay obs, OK."""
    for h in hallazgos:
        if h.estado == "ERROR":
            return "ERROR"
    for h in hallazgos:
        if h.estado == "OBSERVADO":
            return "OBSERVADO"
    return "OK"


def observaciones_fila(hallazgos):
    """Concatena observaciones de una fila (solo NO-OK)."""
    partes = ["%s: %s" % (h.campo, h.observacion) for h in hallazgos
              if h.estado != "OK"]
    return " | ".join(partes) if partes else "Información validada correctamente."
