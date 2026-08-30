"""Generación de gráficos y KPIs para el dashboard de HHEE.

Usa matplotlib para generar imágenes PNG que se muestran en la GUI
o se exportan a PDF/Excel.
"""

import io
import os
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


COLORES = {
    "acento": "#FF5500",
    "verde": "#27AE60",
    "amarillo": "#F39C12",
    "rojo": "#E74C3C",
    "azul": "#3498DB",
    "gris": "#95A5A6",
    "morado": "#9B59B6",
    "turquesa": "#1ABC9C",
}

ESTADO_COLORES = {
    "VALIDADO": "#27AE60",
    "OBSERVADO": "#F39C12",
    "PENDIENTE": "#E74C3C",
    "AMBIGUO": "#E74C3C",
    "SIN MARCACIÓN": "#E74C3C",
    "SIN MARCACION": "#E74C3C",
    "SIN ENTRADA": "#E74C3C",
    "SIN SALIDA": "#E74C3C",
    "REVISIÓN MANUAL": "#9B59B6",
    "REVISION MANUAL": "#9B59B6",
    "ERROR": "#7F8C8D",
}

TARIFA_COLORES = {
    "25%": "#3498DB",
    "35%": "#F39C12",
    "100%": "#E74C3C",
}


def _fig_a_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                facecolor="#FFFFFF", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def grafico_barras_estado(por_estado):
    """Bar chart: registros por estado."""
    if not HAS_MATPLOTLIB:
        return None
    estados = list(por_estado.keys())
    registros = [por_estado[e]["registros"] for e in estados]
    colores = [ESTADO_COLORES.get(e, "#95A5A6") for e in estados]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    barras = ax.barh(estados, registros, color=colores, height=0.6, edgecolor="white")
    ax.set_xlabel("Registros", fontsize=10)
    ax.set_title("Distribución por Estado", fontsize=12, fontweight="bold", pad=12)
    ax.invert_yaxis()
    for barra, val in zip(barras, registros):
        ax.text(barra.get_width() + 0.5, barra.get_y() + barra.get_height() / 2,
                str(val), va="center", fontsize=9, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_a_bytes(fig)


def grafico_torta_costos(total_25, total_35, total_100):
    """Pie chart: distribución de costos por tarifa."""
    if not HAS_MATPLOTLIB:
        return None
    valores = [total_25, total_35, total_100]
    etiquetas = ["25%% (S/%.0f)" % total_25, "35%% (S/%.0f)" % total_35, "100%% (S/%.0f)" % total_100]
    colores = [TARIFA_COLORES["25%"], TARIFA_COLORES["35%"], TARIFA_COLORES["100%"]]
    explode = (0.02, 0.02, 0.02)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    total = sum(valores)
    if total > 0:
        wedges, texts, autotexts = ax.pie(
            valores, labels=etiquetas, colors=colores, explode=explode,
            autopct=lambda p: "%.1f%%" % p if p > 1 else "",
            startangle=90, textprops={"fontsize": 9})
        for at in autotexts:
            at.set_fontweight("bold")
    ax.set_title("Distribución de Costos por Tarifa", fontsize=11, fontweight="bold", pad=10)
    fig.tight_layout()
    return _fig_a_bytes(fig)


def grafico_barras_top_empleados(datos_empleados, top_n=10):
    """Horizontal bar chart: top N empleados por costo total."""
    if not HAS_MATPLOTLIB or not datos_empleados:
        return None
    ranking = sorted(datos_empleados, key=lambda x: x["costo_total"], reverse=True)[:top_n]
    nombres = [d["empleado"][:20] for d in ranking]
    costos = [d["costo_total"] for d in ranking]

    fig, ax = plt.subplots(figsize=(8, max(3, top_n * 0.4)))
    colores = [COLORES["acento"] if i == 0 else COLORES["azul"] for i in range(len(ranking))]
    barras = ax.barh(nombres[::-1], costos[::-1], color=colores[::-1], height=0.6, edgecolor="white")
    ax.set_xlabel("Costo Total (S/)", fontsize=10)
    ax.set_title("Top %d Colaboradores por Costo HHEE" % top_n, fontsize=11, fontweight="bold", pad=12)
    for barra, val in zip(barras, costos[::-1]):
        ax.text(barra.get_width() + max(costos) * 0.01, barra.get_y() + barra.get_height() / 2,
                "S/ %.0f" % val, va="center", fontsize=8, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: "S/ %.0f" % x))
    fig.tight_layout()
    return _fig_a_bytes(fig)


def grafico_barras_top_horas(datos_empleados, top_n=10):
    """Horizontal bar chart: top N empleados por horas extras."""
    if not HAS_MATPLOTLIB or not datos_empleados:
        return None
    ranking = sorted(datos_empleados, key=lambda x: x["horas_extras"], reverse=True)[:top_n]
    nombres = [d["empleado"][:20] for d in ranking]
    horas = [d["horas_extras"] for d in ranking]

    fig, ax = plt.subplots(figsize=(7, max(3, top_n * 0.4)))
    colores = [COLORES["rojo"] if h > 40 else COLORES["amarillo"] if h > 25 else COLORES["verde"]
               for h in horas]
    barras = ax.barh(nombres[::-1], horas[::-1], color=colores[::-1], height=0.6, edgecolor="white")
    ax.set_xlabel("Horas Extras", fontsize=10)
    ax.set_title("Top %d Colaboradores por Horas Extras" % top_n, fontsize=11, fontweight="bold", pad=12)
    for barra, val in zip(barras, horas[::-1]):
        ax.text(barra.get_width() + max(horas) * 0.01, barra.get_y() + barra.get_height() / 2,
                "%.1fh" % val, va="center", fontsize=8, fontweight="bold")
    ax.axvline(x=40, color=COLORES["rojo"], linestyle="--", alpha=0.5, label="Umbral 40h")
    ax.legend(fontsize=8, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_a_bytes(fig)


def grafico_barras_por_turno(por_turno):
    """Grouped bar chart: horas y costos por turno."""
    if not HAS_MATPLOTLIB or not por_turno:
        return None
    turnos = sorted(por_turno.keys())
    horas = [por_turno[t]["horas_extras"] for t in turnos]
    costos = [por_turno[t]["costo_total"] for t in turnos]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.5))

    colores_h = [COLORES["azul"], COLORES["amarillo"], COLORES["rojo"]][:len(turnos)]
    ax1.bar(turnos, horas, color=colores_h, edgecolor="white", width=0.5)
    ax1.set_title("Horas Extras por Turno", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Horas", fontsize=9)
    for i, v in enumerate(horas):
        ax1.text(i, v + max(horas) * 0.02, "%.1f" % v, ha="center", fontsize=9, fontweight="bold")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax2.bar(turnos, costos, color=colores_h, edgecolor="white", width=0.5)
    ax2.set_title("Costo Total por Turno", fontsize=10, fontweight="bold")
    ax2.set_ylabel("S/", fontsize=9)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: "S/ %.0f" % x))
    for i, v in enumerate(costos):
        ax2.text(i, v + max(costos) * 0.02, "S/ %.0f" % v, ha="center", fontsize=8, fontweight="bold")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.tight_layout()
    return _fig_a_bytes(fig)


def grafico_barras_especialidad(por_esp, top_n=8):
    """Bar chart: costos por especialidad."""
    if not HAS_MATPLOTLIB or not por_esp:
        return None
    ranking = sorted(por_esp.items(), key=lambda x: x[1]["costo_total"], reverse=True)[:top_n]
    nombres = [k[:18] for k, v in ranking]
    costos = [v["costo_total"] for k, v in ranking]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(nombres, costos, color=COLORES["turquesa"], edgecolor="white", width=0.6)
    ax.set_ylabel("Costo Total (S/)", fontsize=10)
    ax.set_title("Costos por Especialidad", fontsize=11, fontweight="bold", pad=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: "S/ %.0f" % x))
    for i, v in enumerate(costos):
        ax.text(i, v + max(costos) * 0.02, "S/ %.0f" % v, ha="center", fontsize=8, fontweight="bold",
                rotation=45)
    plt.xticks(rotation=30, ha="right", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_a_bytes(fig)


def grafico_semaforo(validados, observados, pendientes):
    """Donut chart semáforo: salud general."""
    if not HAS_MATPLOTLIB:
        return None
    total = validados + observados + pendientes
    if total == 0:
        return None

    sizes = [validados, observados, pendientes]
    labels = ["VALIDADOS (%d)" % validados, "OBSERVADOS (%d)" % observados, "PENDIENTES (%d)" % pendientes]
    colores = [COLORES["verde"], COLORES["amarillo"], COLORES["rojo"]]
    non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colores) if s > 0]

    if not non_zero:
        return None

    fig, ax = plt.subplots(figsize=(4, 3.5))
    sizes_nz = [x[0] for x in non_zero]
    labels_nz = [x[1] for x in non_zero]
    colores_nz = [x[2] for x in non_zero]

    wedges, texts, autotexts = ax.pie(
        sizes_nz, labels=labels_nz, colors=colores_nz,
        autopct=lambda p: "%.0f%%" % p if p > 2 else "",
        startangle=90, pctdistance=0.75,
        textprops={"fontsize": 9})
    for at in autotexts:
        at.set_fontweight("bold")
        at.set_fontsize(9)

    centre_circle = plt.Circle((0, 0), 0.5, fc="white")
    ax.add_artist(centre_circle)
    ax.text(0, 0, "%d%%" % (validados / total * 100) if total else "0",
            ha="center", va="center", fontsize=16, fontweight="bold", color=COLORES["verde"])
    ax.set_title("Salud General", fontsize=11, fontweight="bold", pad=8)
    fig.tight_layout()
    return _fig_a_bytes(fig)


def generar_todos_los_graficos(dashboard_data):
    """Genera todos los gráficos y devuelve dict nombre->bytes_io."""
    graficos = {}
    res = dashboard_data.get("resumen", {})
    por_emp = dashboard_data.get("por_empleado", [])
    por_turno = dashboard_data.get("por_turno", {})
    por_esp = dashboard_data.get("por_especialidad", {})
    por_estado = dashboard_data.get("por_estado", {})

    total_25 = sum(d.get("horas_25", 0) * d.get("valor_hhee", 0) /
                   max(d.get("horas_extras", 1), 0.01) for d in por_emp) if por_emp else 0
    total_35 = sum(d.get("horas_35", 0) * d.get("valor_hhee", 0) /
                   max(d.get("horas_extras", 1), 0.01) for d in por_emp) if por_emp else 0
    total_100 = sum(d.get("horas_100", 0) * d.get("valor_hhee", 0) /
                    max(d.get("horas_extras", 1), 0.01) for d in por_emp) if por_emp else 0

    g = grafico_semaforo(
        por_estado.get("VALIDADO", {}).get("registros", 0),
        sum(v.get("registros", 0) for k, v in por_estado.items() if k != "VALIDADO"),
        0)
    if g:
        graficos["semaforo"] = g

    g = grafico_barras_estado(por_estado)
    if g:
        graficos["estados"] = g

    g = grafico_torta_costos(total_25, total_35, total_100)
    if g:
        graficos["costos_tarifa"] = g

    g = grafico_barras_top_empleados(por_emp, 10)
    if g:
        graficos["top_costos"] = g

    g = grafico_barras_top_horas(por_emp, 10)
    if g:
        graficos["top_horas"] = g

    g = grafico_barras_por_turno(por_turno)
    if g:
        graficos["por_turno"] = g

    g = grafico_barras_especialidad(por_esp)
    if g:
        graficos["por_especialidad"] = g

    return graficos


def imagen_desde_bytes(buf, max_width=800):
    """Convierte bytes de PNG a PhotoImage para tkinter."""
    if not HAS_PIL or buf is None:
        return None
    try:
        img = Image.open(buf)
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def guardar_graficos(dashboard_data, carpeta):
    """Guarda todos los gráficos como PNG en la carpeta."""
    os.makedirs(carpeta, exist_ok=True)
    graficos = generar_todos_los_graficos(dashboard_data)
    rutas = {}
    for nombre, buf in graficos.items():
        ruta = os.path.join(carpeta, "grafico_%s.png" % nombre)
        with open(ruta, "wb") as f:
            f.write(buf.read())
        buf.seek(0)
        rutas[nombre] = ruta
    return rutas
