"""Módulo 2: Validación de Excel de HHEE contra RAINBOW.

Orquesta la lectura del Excel recibido, la reconciliación contra RAINBOW,
y la comparación de valores usando las reglas de negocio.
"""

import datetime
import os
import sys
import traceback

from conciliacion import conciliar, indexar_marcaciones
from config import cargar_config, aplicar_empresa
from costos import cargar_tabla_costos as _cargar_tabla_costos
from lectura import (
    cargar_tabla_costos, leer_consolidado, leer_relatorio,
    leer_columnas_validacion,
)
from matching import construir_indice
from reglas import (
    ejecutar_reglas, estado_fila, estado_resumen, observaciones_fila,
)
from validacion import validar_respuesta


def validar_excel(ruta_excel, cfg):
    """Orquesta la validación completa de un Excel contra RAINBOW.

    Devuelve dict con:
        registros: list[dict] - registros leídos del Excel
        resultados: list[ResultadoConciliacion] - cálculos del sistema
        hallazgos_por_fila: dict[fila_excel, list[Hallazgo]]
        resumen: dict - conteos OK/OBSERVADO/ERROR
        avisos: list[str]
        tiempo: float - segundos de ejecución
    """
    import time
    inicio = time.time()
    avisos = []

    # Abrir el consolidado UNA sola vez y reutilizarlo en la lectura de
    # registros, columnas de validación y tabla de costos (evita abrir el
    # archivo 3 veces). Se cierra en cada ruta de retorno.
    libro = None
    try:
        import openpyxl as _ox
        libro = _ox.load_workbook(ruta_excel, data_only=True)
    except Exception:
        libro = None

    # 1. Leer Excel - incluye columnas de costos para comparación
    try:
        registros = leer_consolidado(ruta_excel, cfg, avisos, wb=libro)
    except Exception as exc:
        if libro is not None:
            try:
                libro.close()
            except Exception:
                pass
        return {
            "registros": [], "resultados": [], "hallazgos_por_fila": {},
            "resumen": {"ok": 0, "observado": 0, "error": 0, "total": 0},
            "avisos": ["Error leyendo Excel: %s" % str(exc)],
            "tiempo": 0, "error": str(exc),
        }

    # 2. Agregar columnas de validación al registro
    leer_columnas_validacion(ruta_excel, registros, cfg, wb=libro)

    # 3. Leer RAINBOW
    rutas_rainbow = cfg["rutas"].get("input_relatorio", [])
    if not rutas_rainbow:
        if libro is not None:
            try:
                libro.close()
            except Exception:
                pass
        return {
            "registros": registros, "resultados": [],
            "hallazgos_por_fila": {},
            "resumen": {"ok": 0, "observado": 0, "error": len(registros),
                        "total": len(registros)},
            "avisos": ["No hay archivos RAINBOW cargados para validar."],
            "tiempo": time.time() - inicio,
        }

    try:
        marcaciones, avisos_rel = leer_relatorio(rutas_rainbow, cfg, avisos)
    except Exception as exc:
        if libro is not None:
            try:
                libro.close()
            except Exception:
                pass
        return {
            "registros": registros, "resultados": [],
            "hallazgos_por_fila": {},
            "resumen": {"ok": 0, "observado": 0, "error": len(registros),
                        "total": len(registros)},
            "avisos": ["Error leyendo RAINBOW: %s" % str(exc)],
            "tiempo": time.time() - inicio,
        }

    # 4. Filtrar por empresa activa
    from main import _filtrar_marcas_por_empresa
    marcaciones = _filtrar_marcas_por_empresa(marcaciones, cfg, avisos)

    # 5. Construir índices
    identidades = construir_indice(marcaciones)
    indice_marcas = indexar_marcaciones(
        marcaciones, cfg["marcaciones"]["incluir_denegados"],
        dedupe_segundos=cfg["marcaciones"].get("dedupe_segundos", 60),
        dedupe_estrategia=cfg["marcaciones"].get(
            "dedupe_estrategia", "entrada_primera_salida_ultima"))
    cfg["_match_cache"] = {}

    # 6. Cargar tabla de costos
    tabla_costos = cargar_tabla_costos(ruta_excel, wb=libro)
    cfg["_tabla_costos"] = tabla_costos

    # 7. Para cada registro: conciliar + validar + reglas
    resultados = []
    hallazgos_por_fila = {}
    duplicados = set()

    for reg in registros:
        try:
            res = conciliar(reg, marcaciones, indice_marcas, identidades, cfg)
            res = validar_respuesta(res, cfg)
        except Exception:
            from conciliacion import ResultadoConciliacion
            res = ResultadoConciliacion(reg)
            res.estado = "ERROR"
            res.confianza = "BAJA"
            res.observacion = ["Error en conciliación: %s"
                               % traceback.format_exc()]

        resultados.append(res)

        # Detectar duplicados
        clave_dup = (reg.get("empleado"), str(reg.get("fecha")),
                     reg.get("turno"))
        if clave_dup in duplicados:
            cfg.setdefault("_duplicados Detectados", set()).add(clave_dup)
        duplicados.add(clave_dup)

        # Ejecutar reglas de validación
        try:
            hallazgos = ejecutar_reglas(reg, res, cfg)
        except Exception:
            from reglas import Hallazgo
            hallazgos = [Hallazgo(
                reg["fila_excel"], reg["empleado"], "SISTEMA", "ERROR",
                observacion="Error ejecutando reglas: %s"
                % traceback.format_exc())]

        hallazgos_por_fila[reg["fila_excel"]] = hallazgos

    # 8. Resumen
    todos = [h for hs in hallazgos_por_fila.values() for h in hs]
    resumen = estado_resumen(todos)
    resumen["total_registros"] = len(registros)

    tiempo = time.time() - inicio

    if libro is not None:
        try:
            libro.close()
        except Exception:
            pass

    return {
        "registros": registros,
        "resultados": resultados,
        "hallazgos_por_fila": hallazgos_por_fila,
        "resumen": resumen,
        "avisos": avisos,
        "tiempo": tiempo,
    }


def validar_excel_para_gui(ruta_excel, cfg_ruta, empresa=None):
    """Punto de entrada para la GUI. Carga config, ejecuta y captura errores.

    Devuelve (texto_salida, exito).
    """
    try:
        cfg = cargar_config(cfg_ruta)
        if empresa:
            cfg = aplicar_empresa(cfg, empresa)

        resultado = validar_excel(ruta_excel, cfg)

        lineas = []
        lineas.append("=" * 60)
        lineas.append("VALIDACION DE EXCEL DE HHEE")
        lineas.append("=" * 60)
        lineas.append("Archivo: %s" % os.path.basename(ruta_excel))
        lineas.append("Registros: %d" % resultado["resumen"].get("total_registros", 0))
        lineas.append("")

        r = resultado["resumen"]
        lineas.append("RESULTADO:  OK=%d  OBSERVADO=%d  ERROR=%d" % (
            r["ok"], r["observado"], r["error"]))
        lineas.append("")

        if resultado["avisos"]:
            lineas.append("AVISOS:")
            for av in resultado["avisos"]:
                lineas.append("  - %s" % av)
            lineas.append("")

        lineas.append("Tiempo: %.1f segundos" % resultado["tiempo"])

        if resultado.get("error"):
            lineas.append("")
            lineas.append("ERROR FATAL: %s" % resultado["error"])

        return "\n".join(lineas), True

    except Exception:
        return "Error en validación:\n%s" % traceback.format_exc(), False
