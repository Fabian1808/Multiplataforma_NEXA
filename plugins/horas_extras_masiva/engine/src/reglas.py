"""Capa 3 — REGLAS de turno, jornada y horas extras.

Agrupa las marcaciones de cada empleado por ventana de jornada, detecta el
turno (T1/T2/T3) por el rango horario, calcula:
  - horas trabajadas (con descuento de comida/madrugada según turno)
  - jornada contratada del turno
  - horas extras del día (tiempo trabajado - jornada)
Todo es parametrizable en config (NUNCA hardcodeado).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import ingesta as ing
import utiles as u


@dataclass
class TramoMalformado:
    """Día de un empleado que no se pudo descomponer en entrada/salida."""
    fecha: date
    empleado: str
    motivo: str


@dataclass
class Jornada:
    empleado: ing.Empleado
    fecha: date
    turno: str = ""
    inicio: datetime | None = None
    fin: datetime | None = None
    horas_trabajadas: Decimal = Decimal("0")
    jornada: Decimal = Decimal("0")
    horas_extras: Decimal = Decimal("0")
    notas: list[str] = field(default_factory=list)

    @property
    def horas_extras_positivas(self) -> Decimal:
        return self.horas_extras if self.horas_extras > 0 else Decimal("0")


def _hora_str(t: time | None) -> str | None:
    if not t:
        return None
    return "%02d:%02d" % (t.hour, t.minute)


def _en_rango(t: time, rmin: str, rmax: str) -> bool:
    if not t or not rmin or not rmax:
        return True
    hm = "%02d:%02d" % (t.hour, t.minute)
    return rmin <= hm <= rmax


def _dec(h) -> Decimal:
    return Decimal(str(h))


def horas_en_rango(inicio: time, fin: time, rmin: str, rmax: str) -> Decimal:
    """Horas (decimal) del tramo [inicio, fin] que caen dentro de [rmin, rmax]."""
    if not inicio or not fin:
        return Decimal("0")
    a = u.hora_a_decimal(inicio)
    b = u.hora_a_decimal(fin)
    ra = u.hora_a_decimal(time.fromisoformat(rmin)) if rmin else Decimal("0")
    rb = u.hora_a_decimal(time.fromisoformat(rmax)) if rmax else Decimal("23.999")
    # recortar
    lo = max(a, ra)
    hi = min(b, rb)
    if hi <= lo:
        return Decimal("0")
    return (hi - lo).quantize(Decimal("0.0001"))


def detectar_turno(inicio: datetime | None, fin: datetime | None,
                   cfg) -> str:
    """Detecta T1/T2/T3 por el rango horario de la jornada.

    T1 (diurno): entrada 04:00-12:00, salida 11:00-23:59, 10h.
    T2 (noche): cruza medianoche, entrada 17:00-23:59 / 00:00-06:00, 12h.
    T3 (tarde): entrada 12:00-15:00, salida 18:00-23:59, 8h.
    """
    turnos = cfg.get("turnos") or {}
    if not inicio or not fin:
        return ""
    entrada = inicio.time()
    salida = fin.time()
    # margen de 1h para detectar turno
    # T2 (noche) primero: salida en madrugada (00:00-13:00) o entrada en tarde-noche
    t2 = turnos.get("T2") or {}
    entrada_ok = _en_rango(entrada, t2.get("entrada_dia_d", {}).get("min", "17:00"),
                           t2.get("entrada_dia_d", {}).get("max", "23:59")) or \
                 _en_rango(entrada, t2.get("entrada_dia_dmas1", {}).get("min", "00:00"),
                           t2.get("entrada_dia_dmas1", {}).get("max", "06:00"))
    salida_ok = _en_rango(salida, t2.get("salida_dia_dmas1", {}).get("min", "00:00"),
                          t2.get("salida_dia_dmas1", {}).get("max", "13:00"))
    if entrada_ok and salida_ok:
        return "T2"
    t1 = turnos.get("T1") or {}
    if _en_rango(entrada, t1.get("entrada", {}).get("min", "04:00"),
                 t1.get("entrada", {}).get("max", "12:00")) and \
       _en_rango(salida, t1.get("salida", {}).get("min", "11:00"),
                 t1.get("salida", {}).get("max", "23:59")):
        return "T1"
    t3 = turnos.get("T3") or {}
    if _en_rango(entrada, t3.get("entrada", {}).get("min", "12:00"),
                 t3.get("entrada", {}).get("max", "15:00")) and \
       _en_rango(salida, t3.get("salida", {}).get("min", "18:00"),
                 t3.get("salida", {}).get("max", "23:59")):
        return "T3"
    return ""


def _descuento_comida(turno: str, horas_trab: Decimal, cfg) -> Decimal:
    """Descuento de comida según turno y horas trabajadas."""
    turnos = cfg.get("turnos") or {}
    t = turnos.get(turno) or {}
    if t.get("descuento_comida_horas") is None:
        return Decimal("0")
    desc = _dec(t["descuento_comida_horas"])
    limite = t.get("hora_limite_sin_comida")
    if limite is not None and horas_trab <= _dec(limite):
        return Decimal("0")
    return desc


def calcular_jornadas_masivo(conciliados, cfg, avisos=None) -> list[Jornada]:
    """Arma las jornadas de cada empleado fusionando tramos entrada<->salida.

    Algoritmo:
    1) Tramo: cada Entrada abre y su Salida cierra (aut�mata). Entradas
       consecutivas conservan solo la primera; salida sin entrada = malformado.
    2) Fusión: tramos consecutivos del mismo trabajador se fusionan cuando el
       hueco entre la salida de uno y la entrada del siguiente es una pausa
       corta (`jornada.max_pausa_fusion_horas`), t�pica de almuerzo. La jornada
       resultante va de la entrada del primero a la salida del �ltimo, con un
       solo descuento de comida.
    3) Validaci�n de duraci�n por turno (evita turnos absurdos de 22h).
    """
    avisos = [] if avisos is None else avisos
    jcfg = cfg.get("jornada") or {}
    max_pausa = _dec(jcfg.get("max_pausa_fusion_horas", 3.0))
    malformados: list[TramoMalformado] = []
    jornadas: list[Jornada] = []
    clave2emp = {}
    concil_por_emp: dict[str, list] = {}
    for rc in conciliados:
        if not rc.conciliado:
            continue
        e = rc.empleado
        clave = (e.empleado, e.dni or e.fotocheck)
        clave2emp[clave] = e
        concil_por_emp.setdefault(clave, []).append(rc)

    for clave, regs in concil_por_emp.items():
        regs.sort(key=lambda r: (r.marcacion.fecha, r.marcacion.hora))
        e = clave2emp[clave]
        tramos = _construir_tramos(regs, e, malformados)
        tramos = _fusionar_tramos(tramos, max_pausa)
        for inicio_dt, fin_dt in tramos:
            duracion = u.diff_datetime(inicio_dt, fin_dt)
            if duracion <= 0:
                malformados.append(TramoMalformado(inicio_dt.date(), e.empleado,
                                                   "Rango an�malo"))
                continue
            min_dur = _dec(jcfg.get("min_duracion_jornada_horas", 2.0))
            if duracion < min_dur:
                continue
            j = _armar_jornada_dt(e, inicio_dt, fin_dt, cfg)
            if j is None:
                malformados.append(TramoMalformado(inicio_dt.date(), e.empleado,
                                                   "Duraci�n o turno an�malo"))
                continue
            jornadas.append(j)

    return jornadas, malformados


def _construir_tramos(regs, e, malformados):
    """Devuelve lista de (datetime_inicio, datetime_fin) con el aut�mata."""
    tramos = []
    abierta = None
    for rc in regs:
        mar = rc.marcacion
        if mar.es_entrada:
            abierta = mar  # entradas consecutivas: conserva la primera/última apertura
        else:
            if abierta is None:
                malformados.append(TramoMalformado(mar.fecha, e.empleado,
                                                   "Salida sin entrada previa"))
                continue
            inicio = datetime.combine(abierta.fecha, abierta.hora)
            fin = datetime.combine(mar.fecha, mar.hora)
            if fin <= inicio:
                fin = fin + timedelta(days=1)
            if fin > inicio:
                tramos.append([inicio, fin])
            abierta = None
    if abierta is not None:
        malformados.append(TramoMalformado(abierta.fecha, e.empleado,
                                           "Entrada sin salida posterior"))
    return tramos


def _fusionar_tramos(tramos, max_pausa):
    """Fusiona tramos adyacentes separados por una pausa <= max_pausa (almuerzo)."""
    if len(tramos) < 2:
        return tramos
    fusionados = [list(tramos[0])]
    for tramo in tramos[1:]:
        prev = fusionados[-1]
        gap = u.diff_datetime(prev[1], tramo[0])
        if 0 <= gap <= max_pausa:
            # misma jornada: extender el fin al tramo actual
            prev[1] = tramo[1]
        else:
            fusionados.append(list(tramo))
    return [tuple(t) for t in fusionados]


def _armar_jornada_dt(e, inicio: datetime, fin: datetime, cfg) -> Jornada | None:
    horas_trab = u.diff_datetime(inicio, fin)
    if horas_trab <= 0:
        return None
    turno = detectar_turno(inicio, fin, cfg)
    if not turno:
        turno = "T1"
    t = (cfg.get("turnos") or {}).get(turno) or {}
    max_h = t.get("duracion_max_horas")
    if max_h is not None and horas_trab > _dec(max_h):
        return None
    jornada_h = _dec(t.get("jornada_horas", 10))
    desc_comida = _descuento_comida(turno, horas_trab, cfg)
    ht = horas_trab - desc_comida
    extras = ht - jornada_h
    j = Jornada(
        empleado=e,
        fecha=inicio.date(),
        turno=turno,
        inicio=inicio,
        fin=fin,
        horas_trabajadas=ht.quantize(Decimal("0.0001")),
        jornada=jornada_h.quantize(Decimal("0.0001")),
        horas_extras=extras.quantize(Decimal("0.0001")),
    )
    if desc_comida > 0:
        j.notas.append("Descuento comida %.2fh" % desc_comida)
    return j


def _armar_jornada_simple(e, entrada: ing.Marcacion, salida: ing.Marcacion,
                          cfg) -> Jornada | None:
    """Compatibilidad: arma una jornada directamente desde dos marcaciones."""
    inicio = datetime.combine(entrada.fecha, entrada.hora)
    fin = datetime.combine(salida.fecha, salida.hora)
    if fin <= inicio:
        fin = fin + timedelta(days=1)
        if fin <= inicio:
            return None
    return _armar_jornada_dt(e, inicio, fin, cfg)
