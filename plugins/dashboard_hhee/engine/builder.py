
import os
import json
import glob
import tempfile
import webbrowser
from collections import defaultdict

def build_dashboard(historicos_dir, anio, empresa_filtro=None):
    # Buscar todos los JSON de ese año
    patron = os.path.join(historicos_dir, str(anio), "*", "resumen_*.json")
    archivos = glob.glob(patron)
    
    if not archivos:
        raise ValueError(f"No hay datos historicos para el año {anio}")
        
    # Agrupar por periodo y obtener el más reciente
    periodos = defaultdict(list)
    for ruta in archivos:
        # ruta: historico/2026/01_ENERO_2026/resumen_20260829_161029.json
        periodo = os.path.basename(os.path.dirname(ruta))
        periodos[periodo].append(ruta)
        
    datos_graficos = []
    
    # Ordenar los periodos (asumiendo que empiezan con 01_ENERO_, 02_FEBRERO_, etc)
    for periodo in sorted(periodos.keys()):
        archivos_periodo = sorted(periodos[periodo])
        ultimo_json = archivos_periodo[-1] # El último generado
        
        with open(ultimo_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        empresa_json = data.get("config", {}).get("empresa_activa", "DESCONOCIDA")
        if empresa_filtro and empresa_filtro != "TODAS" and empresa_json != empresa_filtro:
            continue
            
        resumen = data.get("dashboard", {}).get("resumen", {})
        
        # Extraer mes del periodo (ej. 01_ENERO_2026 -> ENERO)
        partes = periodo.split("_")
        mes_nombre = partes[1] if len(partes) > 1 else periodo
        
        datos_graficos.append({
            "mes": mes_nombre,
            "empresa": empresa_json,
            "horas_extras": resumen.get("total_horas_extras", 0),
            "costo_total": resumen.get("total_costo", 0),
            "empleados": resumen.get("total_empleados", 0)
        })
        
    if not datos_graficos:
        raise ValueError("No se encontraron datos para los filtros seleccionados.")
        
    # Generar HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Dashboard Horas Extras - {empresa_filtro or "TODAS"} - {anio}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .col {{ flex: 1; min-width: 300px; }}
        h1, h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Dashboard Horas Extras - {empresa_filtro or "TODAS"} ({anio})</h1>
    
    <div class="row">
        <div class="card col">
            <h2>Horas Extras por Mes</h2>
            <canvas id="chartHoras"></canvas>
        </div>
        <div class="card col">
            <h2>Costo Total (S/) por Mes</h2>
            <canvas id="chartCosto"></canvas>
        </div>
    </div>
    
    <script>
        const datos = {json.dumps(datos_graficos)};
        
        const labels = datos.map(d => d.mes);
        const dataHoras = datos.map(d => d.horas_extras);
        const dataCostos = datos.map(d => d.costo_total);
        
        new Chart(document.getElementById("chartHoras"), {{
            type: "bar",
            data: {{
                labels: labels,
                datasets: [{{
                    label: "Horas Extras",
                    data: dataHoras,
                    backgroundColor: "rgba(54, 162, 235, 0.6)",
                    borderColor: "rgba(54, 162, 235, 1)",
                    borderWidth: 1
                }}]
            }},
            options: {{ responsive: true }}
        }});
        
        new Chart(document.getElementById("chartCosto"), {{
            type: "line",
            data: {{
                labels: labels,
                datasets: [{{
                    label: "Costo (S/)",
                    data: dataCostos,
                    backgroundColor: "rgba(255, 99, 132, 0.2)",
                    borderColor: "rgba(255, 99, 132, 1)",
                    borderWidth: 2,
                    fill: true
                }}]
            }},
            options: {{ responsive: true }}
        }});
    </script>
</body>
</html>"""

    out_path = os.path.join(tempfile.gettempdir(), f"dashboard_hhee_{os.getpid()}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return out_path

def abrir_dashboard(historicos_dir, anio, empresa):
    ruta = build_dashboard(historicos_dir, anio, empresa)
    webbrowser.open(f"file:///{ruta}")
    return ruta

