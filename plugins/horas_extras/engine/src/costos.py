"""Cálculo de costos de horas extras por especialidad.

Lee la tabla de tarifas de la hoja "Costos At. Emerg" del consolidado
y calcula: valor HHEE (25%/35%/100%), transporte y alimentación.

Las tarifas son costos por hora (S//h), NO sueldos.
"""

import re


class TarifaEspecialidad:
    __slots__ = ("especialidad", "costo_25", "costo_35", "costo_100")

    def __init__(self, especialidad, costo_25, costo_35, costo_100):
        self.especialidad = especialidad
        self.costo_25 = float(costo_25)
        self.costo_35 = float(costo_35)
        self.costo_100 = float(costo_100)


class TablaCostos:
    """Tabla de tarifas de HHEE por especialidad."""

    def __init__(self):
        self._tabla = []
        self._indice = {}

    def agregar(self, tarifa):
        self._tabla.append(tarifa)
        clave = _normalizar_especialidad(tarifa.especialidad)
        self._indice[clave] = tarifa

    def lookup(self, especialidad):
        if not especialidad:
            return None
        clave = _normalizar_especialidad(especialidad)
        if clave in self._indice:
            return self._indice[clave]
        # Búsqueda por contenido: "SOLDADOR 3G" en "Soldador 3G - Plumilla"
        for k, v in self._indice.items():
            if clave in k or k in clave:
                return v
        return None

    def especialidades(self):
        return [t.especialidad for t in self._tabla]

    def __len__(self):
        return len(self._tabla)


def _normalizar_especialidad(texto):
    """Normaliza nombre de especialidad para comparación case-insensitive."""
    s = str(texto or "").strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s


def cargar_tabla_costos(wb):
    """Lee la hoja 'Costos At. Emerg' de un workbook y devuelve TablaCostos.

    Busca la sección de costos de HHEE (filas con especialidad + tarifas
    25%/35%/100%). Las columnas Q=especialidad, R=costo_25, S=costo_35,
    T=costo_100 en la zona de.lookup (Q44:T55 aprox.).
    """
    tabla = TablaCostos()
    nombre_hoja = None
    for candidato in ("Costos At. Emerg", "Costos At.Emerg", "Costos"):
        if candidato in wb.sheetnames:
            nombre_hoja = candidato
            break
    if nombre_hoja is None:
        return tabla

    ws = wb[nombre_hoja]
    # Buscar la fila de encabezados de la tabla de lookup:
    # Q=especialidad, R=costo_25, S=costo_35, T=costo_100
    encabezado_fila = None
    for fila in range(1, 70):
        c_q = ws.cell(row=fila, column=17).value  # Q
        c_r = ws.cell(row=fila, column=18).value  # R
        if c_q and c_r:
            c_q_str = str(c_q).strip().upper()
            c_r_str = str(c_r).strip()
            # El encabezado típico tiene "MECANICO" en Q y un número en R
            # Detectamos la primera fila de datos válida
            try:
                float(c_r_str)
                # Si Q parece nombre de especialidad y R es número, es datos
                if c_q_str and not c_q_str.startswith("ITEM"):
                    encabezado_fila = fila
                    break
            except (ValueError, TypeError):
                continue

    if encabezado_fila is None:
        # Estrategia alternativa: buscar filas con patrón de datos
        for fila in range(40, 70):
            c_q = ws.cell(row=fila, column=17).value  # Q
            c_r = ws.cell(row=fila, column=18).value  # R
            c_s = ws.cell(row=fila, column=19).value  # S
            c_t = ws.cell(row=fila, column=20).value  # T
            if c_q and all(v is not None for v in (c_r, c_s, c_t)):
                try:
                    float(c_r)
                    float(c_s)
                    float(c_t)
                    encabezado_fila = fila
                    break
                except (ValueError, TypeError):
                    continue

    if encabezado_fila is None:
        return tabla

    for fila in range(encabezado_fila, encabezado_fila + 30):
        c_q = ws.cell(row=fila, column=17).value  # Q: especialidad
        c_r = ws.cell(row=fila, column=18).value  # R: costo 25%
        c_s = ws.cell(row=fila, column=19).value  # S: costo 35%
        c_t = ws.cell(row=fila, column=20).value  # T: costo 100%
        if not c_q:
            continue
        try:
            r, s, t = float(c_r or 0), float(c_s or 0), float(c_t or 0)
        except (ValueError, TypeError):
            continue
        if r > 0 or s > 0 or t > 0:
            tabla.agregar(TarifaEspecialidad(str(c_q).strip(), r, s, t))

    return tabla


def split_porcentajes(horas_extras, tipo, hexagesimal=None):
    """Divide las horas entre 25%, 35% y 100% según el tipo de HHEE.

    SOBRETIEMPO: primeras 2h al 25%, excedente al 35%.
    ACTIVACION: todo al 100% (usa hexagesimal = jornada neta).

    Devuelve dict {h25, h35, h100}.
    """
    tipo_upper = str(tipo or "").strip().upper()
    if "ACTIVACION" in tipo_upper:
        h = max(0.0, float(hexagesimal or 0))
        return {"h25": 0.0, "h35": 0.0, "h100": round(h, 4)}

    h = max(0.0, float(horas_extras or 0))
    h25 = round(min(h, 2.0), 4)
    h35 = round(max(h - 2.0, 0.0), 4)
    return {"h25": h25, "h35": h35, "h100": 0.0}


def calcular_valor_hhee(h25, h35, h100, tarifa):
    """Calcula el valor monetario de las horas extras.

    Devuelve dict {valor_25, valor_35, valor_100, valor_total}.
    """
    if tarifa is None:
        return {"valor_25": 0.0, "valor_35": 0.0, "valor_100": 0.0,
                "valor_total": 0.0}
    v25 = round(h25 * tarifa.costo_25, 2)
    v35 = round(h35 * tarifa.costo_35, 2)
    v100 = round(h100 * tarifa.costo_100, 2)
    return {"valor_25": v25, "valor_35": v35, "valor_100": v100,
            "valor_total": round(v25 + v35 + v100, 2)}


def calcular_transporte(cantidad_personas, cfg):
    """Calcula el costo unitario de transporte por trabajador.

    Regla real del Excel: un valor fijo por persona (S/ 90). El total se
    obtiene multiplicando la cantidad de personas por el valor unitario.

    Devuelve dict {cantidad, tarifa, valor}: 'valor' es el unitario por
    persona (para comparar con la columna 'Movilidad' del Excel). El total
    se calcula en el llamador como cantidad * valor.
    """
    costos_cfg = (cfg or {}).get("costos") or {}
    pu = float(costos_cfg.get("transporte_por_persona", 90))
    cant = max(0, int(float(cantidad_personas or 0)))
    if cant <= 0:
        return {"cantidad": 0, "tarifa": 0.0, "valor": 0.0}
    return {"cantidad": cant, "tarifa": pu, "valor": round(pu, 2)}


def _leer_franjas(turno, costos_cfg):
    """Devuelve la config de franjas de alimentacion para un turno."""
    franjas = (costos_cfg.get("alimentacion_franjas") or {}).get(turno)
    if isinstance(franjas, dict):
        return franjas
    return None


def calcular_alimentacion(turno, cfg, horas=0.0):
    """Calcula el costo de alimentación según turno y horas trabajadas.

    Regla real del Excel (por franjas de horas, según turno):
      - T1: <=limite_bajo -> valor_bajo; <=limite_medio -> valor_medio;
            >limite_medio -> valor_alto.
      - T2: sin alimentación (0).
      - T3: si hay horas -> valor_medio (13); sin horas -> 0.
    Sin horas trabajadas (o horas <= 0) nunca se cobra alimentación.

    Devuelve dict {tipo, valor}.
    """
    costos_cfg = (cfg or {}).get("costos") or {}
    turno_upper = str(turno or "").strip().upper()
    horas = float(horas or 0)

    if horas <= 0:
        return {"tipo": "SIN ALIMENTACION", "valor": 0.0}

    fr = _leer_franjas(turno_upper, costos_cfg)
    if fr is None:
        # Turno desconocido -> sin alimentacion
        return {"tipo": "SIN ALIMENTACION", "valor": 0.0}

    lb = float(fr.get("limite_bajo", 1.5))
    lm = float(fr.get("limite_medio", 10.0))
    vb = float(fr.get("valor_bajo", 0))
    vm = float(fr.get("valor_medio", 13))
    va = float(fr.get("valor_alto", 19))

    if horas <= lb:
        valor = vb
        tipo = "SNACK"
    elif horas <= lm:
        valor = vm
        tipo = "ALMUERZO"
    else:
        valor = va
        tipo = "ALMUERZO COMPLETO"

    if valor <= 0:
        return {"tipo": "SIN ALIMENTACION", "valor": 0.0}
    return {"tipo": tipo, "valor": valor}
