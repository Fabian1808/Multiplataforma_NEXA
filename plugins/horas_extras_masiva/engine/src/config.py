"""Configuración centralizada de HORAS EXTRAS MASIVA.

Toda columna, regla de turno, jornada, horas extras, matching de empleados
y matching tarifario vive aquí (y puede sobrescribirse con un config.json
externo). Nada de columnas/tarifas hardcodeadas en el código.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path


DEFAULT_CONFIG: dict = {
    "moneda": "S/",
    "decimales": 2,
    # ------------------------------------------------------------------
    # INGESTA — RAINBOW (marcaciones entrada/salida)
    # ------------------------------------------------------------------
    "rainbow": {
        "hoja": None,  # None = primera hoja con datos
        "fila_encabezado": 1,
        "col_tipo": "Tipo",
        "col_empresa": "Empresa Tercero",
        "col_ruc": "RUC",
        "col_num_personal": "Num Personal",
        "col_fotocheck": "Fotocheck",
        "col_empleado": "Empleado",
        "col_dni": "DNI",
        "col_fecha": "Fecha",
        "col_hora": "Hora",
        "col_tipo_acceso": "Tipo Acceso",
        "col_situacion": "Situación",
        "permitido_si": "Permitido",
        # palabras que hacen match de entrada/salida cuando Tipo Acceso no es literal
        "txt_entrada": ("entrada", "ingreso"),
        "txt_salida": ("salida",),
    },
    # ------------------------------------------------------------------
    # INGESTA — RELATORIO (maestro de personal). Columna -> índice/alias.
    # ------------------------------------------------------------------
    "relatorio": {
        "hoja": None,  # None = detectar hoja con la columna Empleado / primera con datos
        "fila_encabezado": 1,
        "columnas": {
            "empresa": "Empresa",
            "unidad": "Unidad",
            "codigo_grupo": "Codigo del Grupo",
            "grupo_empresa": "Grupo Empresa",
            "codigo_empresa": "Codigo Empresa",
            "empresa_terceros": "Empresa Terceros",
            "ruc": "RUC",
            "nombre_comercial": "Nombre Comercial",
            "grupo_terceros": "Grupo Terceros",
            "empleado": "Empleado",
            "fotocheck": "Fotocheck",
            "fecha_admision": "Fecha de Admisión",
            "fecha_despido": "Fecha de Despido",
            "motivo_despido": "Motivo Despido",
            "fecha_inactividad": "Fecha Inactividad",
            "motivo_inactividad": "Motivo Inactividad",
            "inicio_actividad": "Inicio Actividad",
            "fin_actividad": "Fin Actividad",
            "dni": "DNI",
            "extranjero": "Extranjero",
            "sexo": "Sexo",
            "fecha_nacimiento": "Fecha Nacimiento",
            "cargo": "Cargo",
            "seccion": "Sección",
            "matricula_ext": "Matrícula Ext",
            "fecha_inclusion": "Fecha Inclusión",
            "hora_inclusion": "Hora Inclusión",
            "contrato": "Contrato",
            "unidad_trabajo": "Unidad de Trabajo",
            "perfil_contrato": "Perfil Contrato",
            "tipo_sangre": "Tipo de Sangre",
        },
    },
    # ------------------------------------------------------------------
    # INGESTA — TARIFAS
    # ------------------------------------------------------------------
    "tarifas": {
        "hoja": None,
        "fila_encabezado": 1,
        "col_id": "ID",
        "col_title": "Title",
        "col_empresa": "Empresa",
        "col_objeto": "Objeto del contrato",
        "col_ruc": "RUC",
        "col_cargo": "Descripcion Cargo",
        "col_25": "25%",
        "col_35": "35%",
        "col_100": "100%",
        "col_tipo_item": "Tipo de Item",
    },
    # ------------------------------------------------------------------
    # INGESTA — ÁREAS y GERENCIA (enriquecimiento opcional)
    # ------------------------------------------------------------------
    "areas": {
        "hoja": None,
        "fila_encabezado": 1,
        "col_titulo": "Título",
        "col_id": "Id",
        "col_id_gerencia": "Id_Gerencia",
    },
    "gerencia": {
        "hoja": None,
        "fila_encabezado": 1,
        "col_titulo": "Título",
        "col_id": "Id",
    },
    # ------------------------------------------------------------------
    # NORMALIZACIÓN
    # ------------------------------------------------------------------
    "normalizacion": {
        "mayusculas": True,
        "quitar_tildes": True,
        "quitar_caracteres_especiales": True,
        "ordenar_tokens": False,
    },
    # ------------------------------------------------------------------
    # CONCILIACIÓN RAINBOW ↔ PERSONAL
    # ------------------------------------------------------------------
    "conciliacion": {
        # orden de preferencia de identificadores
        "claves": ["dni", "fotocheck", "num_personal"],
        "usar_nombre_normalizado": True,
        "matching": {
            "umbral_exacta": 100.0,
            "umbral_difusa_min": 82.0,
            "margen_ambiguo": 2.0,
            "candidatos_max": 5,
            "alias": {
                "activo": True,
                "edicion_max": 1,
                "len_min_substring": 4,
                "piso_cobertura_alias": 60,
            },
        },
    },
    # ------------------------------------------------------------------
    # TURNOS y JORNADA
    # ------------------------------------------------------------------
    "jornada": {
        "descuento_comida_horas": 1.0,   # T1
        # Hueco entre salida y la siguiente entrada para considerarlos la MISMA
        # jornada (ej. pausa de almuerzo). 0 = no fusionar (cada tramo es jornada).
        "max_pausa_fusion_horas": 3.0,
        "min_duracion_jornada_horas": 2.0,
    },
    "turnos": {
        "T1": {
            "jornada_horas": 10.0,
            "entrada": {"min": "04:00", "max": "12:00"},
            "salida": {"min": "11:00", "max": "23:59"},
            "descuento_comida_horas": 1.0,
            "hora_limite_sin_comida": 6.0,
            "duracion_max_horas": 15.0,
        },
        "T2": {
            "jornada_horas": 12.0,
            "cruza_medianoche": True,
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
            "duracion_max_horas": 17.0,
        },
        "T3": {
            "jornada_horas": 8.0,
            "entrada": {"min": "12:00", "max": "15:00"},
            "salida": {"min": "18:00", "max": "23:59"},
            "duracion_max_horas": 12.0,
        },
    },
    # ------------------------------------------------------------------
    # HORAS EXTRAS — vigencia de tarifas por tipo
    # Interpretación parametrizable de 25% / 35% / 100%.
    # 'tipo_hora' -> columna del tarifario que debe usarse.
    # "horas_limite_25": primeras N h de sobretiempo van a 25%, resto a 35%.
    # ------------------------------------------------------------------
    "horas_extras": {
        "tipos_hora": {
            "25%": {"columna": "25%", "pct": 0.25},
            "35%": {"columna": "35%", "pct": 0.35},
            "100%": {"columna": "100%", "pct": 1.00},
        },
        # Clasificación de jornadas → tipos de hora
        "clasificacion": {
            "SOBRETIEMPO": {
                "min_horas_extras": 0.0,
                "horas_limite_25": 2.0,   # primeras 2h -> 25%, exceso -> 35%
                "tipo_25": "25%",
                "tipo_35": "35%",
            },
            "ACTIVACION": {
                "min_horas_extras": 7.0,  # jornada >= 7h -> activación al 100%
                "tipo_100": "100%",
            },
        },
    },
    # ------------------------------------------------------------------
    # MATCHING TARIFARIO — niveles de confianza
    # ------------------------------------------------------------------
    "matching_tarifas": {
        "claves": ("ruc", "empresa", "cargo"),
        "niveles": {
            "ALTA": {"ruc": True, "empresa": True, "cargo": True},
            "MEDIA": {"empresa": True, "cargo": True, "contrato": True},
            "BAJA": {"cargo": True},
        },
        "requiere_objeto": False,  # True si Objeto del contrato es obligatorio para match ALTA
    },
    # ------------------------------------------------------------------
    # VALIDACIÓN / ESTADOS
    # ------------------------------------------------------------------
    "validacion": {
        "estados": ["OK", "ADVERTENCIA", "REVISAR", "ERROR"],
        "horas_anomalas_max": 24.0,
        "considerar_inactivo": True,
    },
    # ------------------------------------------------------------------
    # EXPORTACIÓN
    # ------------------------------------------------------------------
    "exportacion": {
        "hojas": ["DETALLE"],
        "encabezado_color": "#FF5503",
        "encabezado_fuente": "FFFFFF",
    },
}


def _merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def cargar_config(ruta: str | os.PathLike | None = None) -> dict:
    """Carga config.json externo fusionado sobre los valores por defecto."""
    cfg = deepcopy(DEFAULT_CONFIG)
    if ruta and os.path.exists(str(ruta)):
        with open(str(ruta), encoding="utf-8") as fh:
            cfg = _merge(cfg, json.load(fh))
    return cfg


def guardar_config(cfg: dict, ruta: str | os.PathLike) -> None:
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(str(ruta), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def escribir_config_ejemplo(destino: str | os.PathLike) -> None:
    guardar_config(deepcopy(DEFAULT_CONFIG), destino)
