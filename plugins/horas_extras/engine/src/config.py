"""Carga y validación de la configuración externa del sistema.

La configuración vive en config/config.json (no en el código), para que
un futuro responsable pueda ajustar parámetros sin tocar el código.
"""

import json
import os
from copy import deepcopy

_DEFAULT = {
    "modo_prueba": True,
    "version_sistema": "1.0.0",
    "actualizacion": {
        "url": "",
        "verificar_al_inicio": True,
        "permitir_http": False,
        "timeout_seg": 10,
    },
    "rutas": {
        "input_consolidado": "CONSOLIDADO - ENERO RevFinal (1).xlsx",
        "input_relatorio": [],
        "output_dir": "data/output",
        "historicos_dir": "historico",
        "logs_dir": "logs",
    },
    "lectura": {
        "hoja_consolidado": "4 BDHHEE",
        "tabla_consolidado": "Tabla3",
        "col_fecha": "Fecha",
        "col_turno": "Turno",
        "col_empleado": "Apellidos y Nombres",
        "col_hora_inicio": "Hora de Inicio",
        "col_hora_fin": "Hora Fin",
        "col_validacion": "VALIDACION RAINBOW",
        "col_tipo_hhee": "TIPO DE HHEE",
        "col_hora_inicio_obj": "HORA INICIO",
        "col_hora_fin_obj": "HORA FINAL",
        "col_comentarios": "Comentarios",
        "col_numcontrol": "# Control",
        "col_monto_total": "Total HHEE + Transp. + Aliment (S/)",
        "col_horas_declaradas": "H-H",
        "col_hh_rev": "H-H REV",
        "col_tipo_rev": "TIPO",
        "col_duracion_txt": "HORA INICIO - HORA FINAL",
        "col_sin_almuerzo": "Cantidad de horas - 1 de almuerzo",
        "col_hexagesimal": "Hexagesimal",
        "col_especialidad": "ESPECIALIDAD",
        "col_npersonas": "N° personas",
        "col_hh_correo": "H-H CORREO",
        "col_tipo_hhee_excel": "TIPO DE HHEE",
        "hoja_costos": "Costos At. Emerg",
        "hoja_relatorio": "Sheet1",
        "col_rel_empleado": "Empleado",
        "col_rel_fecha": "Fecha",
        "col_rel_hora": "Hora",
        "col_rel_tipo_acceso": "Tipo Acceso",
        "col_rel_situacion": "Situación",
        "col_rel_tipo": "Tipo",
        "col_rel_dni": "DNI",
        "col_rel_empresa": "Empresa Tercero",
        "solo_tipo": "Tercero",
    },
    "jornada": {
        "descuento_comida_horas": 1.0,
    },
    "normalizacion": {
        "mayusculas": True,
        "quitar_tildes": True,
        "quitar_caracteres_especiales": True,
        "ordenar_tokens": False,
    },
    "matching": {
        "umbral_exacta": 100.0,
        "umbral_difusa_min": 82.0,
        "margen_ambiguo": 2.0,
        "usar_rapidfuzz": False,
        "candidatos_max": 5,
        "alias": {
            "activo": True,
            "edicion_max": 1,
            "len_min_substring": 4,
            "piso_cobertura_alias": 60,
        },
    },
    "turnos": {
        "T1": {
            "entrada": {"min": "04:00", "max": "12:00"},
            "salida": {"min": "11:00", "max": "23:59"},
        },
        "T2": {
            "entrada_dia_d": {"min": "17:00", "max": "23:59"},
            "entrada_dia_dmas1": {"min": "00:00", "max": "06:00"},
            "salida_dia_dmas1": {"min": "00:00", "max": "13:00"},
            "salida_mismo_dia": {"min": "22:00", "max": "23:59"},
            "ventana_busqueda_horas": 19,
            "rango_duracion_horas": [6, 16],
            "rango_duracion_madrugada_horas": [0.5, 8],
            "madrugada_horas": {"min": "04:00", "max": "08:00"},
            "pausa_nueva_jornada_min": 60,
            "puntaje_minimo": 55,
        },
        "T3": {
            "entrada": {"min": "12:00", "max": "15:00"},
            "salida": {"min": "18:00", "max": "23:59"},
        },
    },
    "marcaciones": {
        "incluir_denegados": True,
        "dedupe_segundos": 60,
        "dedupe_estrategia": "entrada_primera_salida_ultima",
    },
    "comentarios": {
        "mas12_activo": True,
        "mas12_umbral_horas": 12.0,
        "texto_mas12": "Mostrar evidencia de gerente general por motivo de pasar +12 horas.",
        "sin_marcacion": "NO HAY EVIDENCIA DE ENTRADA NI SALIDA EN RAINBOW",
        "sin_salida": "NO HAY EVIDENCIA DE SALIDA EN RAINBOW",
        "sin_entrada": "NO HAY EVIDENCIA DE ENTRADA EN RAINBOW",
    },
    "confianza": {
        "minima_aceptable": "MEDIA",
        "dedupe_segundos_usados_a": "MEDIA",
        "difusa_score_min_alta": 95.0,
    },
    "duplicados": {"detectar_ambiguos": True},
    "productividad": {
        "tiempo_manual_por_registro_min": 5,
        "tiempo_revision_excepcion_min": 10,
        "costo_hora_hombre": 0.0,
    },
    "impacto": {"moneda": "S/"},
    "salida": {
        "nombre_archivo": "CONSOLIDADO_COMPLETADO.xlsx",
        "modificar_celdas": ["HORA INICIO", "HORA FINAL", "Comentarios",
                             "Hora de Inicio", "Hora Fin", "VALIDACION RAINBOW",
                             "TIPO DE HHEE"],
        "validacion_rainbow": {"si": "SI", "no": "NO"},
        "sobrescribir": False,
        "metodo_escritura": "openpyxl",
    },
    "clasificacion_hhee": {
        "sobretiempo_max_horas": 3.0,
        "activacion_min_horas": 7.0,
        "activacion_max_horas": 12.0,
        "sobretiempo": "Sobretiempo",
        "activacion": "Activación",
        "revisar": "Revisar en Rainbow",
        "turno_nominal_horas": 9.6,
        "sobretiempo_col": "SOBRETIEMPO",
        "activacion_col": "ACTIVACION",
        "revisar_col": "REVISAR EN RAINBOW",
    },
    "conciliacion": {
        "estrategia": "ventana_turno",
        "fin_madrugada": "08:00",
    },
    "costos": {
        "transporte_por_persona": 90,
        "alimentacion_franjas": {
            "T1": {"limite_bajo": 1.5, "limite_medio": 10.0,
                   "valor_bajo": 8, "valor_medio": 13, "valor_alto": 19},
            "T2": {"valor_bajo": 0, "valor_medio": 0, "valor_alto": 0},
            "T3": {"valor_bajo": 13, "valor_medio": 13, "valor_alto": 13},
        },
        "alimentacion_unitario": 13.42,
    },
}


def _merge(base, override):
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def cargar_config(ruta=None):
    """Carga config.json fusionado sobre los valores por defecto y resuelve
    la empresa activa en `turnos` (estructura que usa el motor)."""
    cfg = deepcopy(_DEFAULT)
    if ruta and os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as fh:
            cfg = _merge(cfg, json.load(fh))
    return _resolver_empresa(cfg)


def aplicar_empresa(cfg, nombre):
    """Cambia la empresa activa y vuelve a resolver turnos/empresa_info."""
    cfg["empresa_activa"] = nombre
    return _resolver_empresa(cfg)


def _resolver_empresa(cfg):
    """Resuelve la empresa activa en la estructura de turnos del motor.

    - Si `empresas` está definida: valida la empresa activa y deriva sus
      turnos (nominal -> ventanas) con `empresas.derivar_turno`.
    - Si no: usa los `turnos` del archivo/config por defecto como empresa
      "GENERICA" (compatibilidad con configs históricas).
    """
    empresas = cfg.get("empresas")
    if empresas is None:
        for t, tcfg in cfg["turnos"].items():
            if "cruza_medianoche" not in tcfg:
                tcfg["cruza_medianoche"] = "entrada_dia_d" in tcfg or t == "T2"
        cfg["empresa_info"] = {
            "nombre": "GENERICA",
            "sobretiempo_maximo": None,
            "descuento_comida_horas": cfg.get("jornada", {}).get("descuento_comida_horas", 1.0),
            "turnos_configurados": cfg["turnos"],
        }
        cfg["empresas_disponibles"] = ["GENERICA"]
        return cfg

    if not isinstance(empresas, dict) or not empresas:
        raise ValueError("La seccion 'empresas' de la configuracion esta vacia o es invalida.")

    from empresas import derivar_turno, validar_empresa

    nombre = cfg.get("empresa_activa")
    if not nombre:
        raise ValueError("La configuracion define 'empresas' pero falta 'empresa_activa'. "
                         "Disponibles: %s" % ", ".join(sorted(empresas)))
    if nombre not in empresas:
        raise ValueError("La empresa activa '%s' no esta en la configuracion. Disponibles: %s"
                         % (nombre, ", ".join(sorted(empresas))))

    for emp, ecfg in empresas.items():
        validar_empresa(emp, ecfg)

    ecfg = empresas[nombre]
    tol = ecfg.get("tolerancia") or {}
    tol_ent = tol.get("entrada", 20)
    tol_sal = tol.get("salida", 60)
    turnos = {t: derivar_turno(tcfg, tol_ent, tol_sal) for t, tcfg in ecfg["turnos"].items()}

    cfg["turnos"] = turnos
    cfg["empresa_info"] = {
        "nombre": nombre,
        "sobretiempo_maximo": ecfg.get("sobretiempo_maximo"),
        "descuento_comida_horas": ecfg.get(
            "descuento_comida_horas",
            cfg.get("jornada", {}).get("descuento_comida_horas", 1.0)),
        "turnos_configurados": ecfg["turnos"],
        "tolerancia": tol,
    }
    cfg["empresas_disponibles"] = sorted(empresas)
    return cfg


def hora_a_minutos(texto):
    """Convierte 'HH:MM' o 'HH:MM:SS' a minutos desde media noche.

    Lanza ValueError con mensaje claro si el valor no es parseable (en
    lugar de fallar con IndexError como ocurría con '17' o '17:').
    """
    if isinstance(texto, (int, float)):
        raise ValueError("Hora invalida: %r (se esperaba 'HH:MM')." % texto)
    s = str(texto).strip()
    partes = s.split(":")
    if not (2 <= len(partes) <= 3) or not all(p.isdigit() for p in partes):
        raise ValueError("Hora invalida: %r (se esperaba 'HH:MM' o 'HH:MM:SS')." % s)
    h, m = int(partes[0]), int(partes[1])
    if h > 23 or m > 59:
        raise ValueError("Hora fuera de rango: %r." % s)
    return h * 60 + m