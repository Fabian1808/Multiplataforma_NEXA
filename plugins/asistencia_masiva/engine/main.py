import sys
import os
import csv
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

def procesar_masivo(rutas):
    base_dir = Path(__file__).parent.parent.parent
    horas_extras_src = base_dir / "horas_extras" / "engine" / "src"
    if str(horas_extras_src) not in sys.path:
        sys.path.insert(0, str(horas_extras_src))
        
    try:
        import lectura
        import config as cfg_mod
    except ImportError:
        raise RuntimeError("No se pudo cargar el modulo de lectura de horas_extras.")
        
    cfg = {
        "lectura": cfg_mod._DEFAULT["lectura"]
    }
    
    avisos = []
    marcaciones, _ = lectura.leer_relatorio(rutas, cfg, avisos)
    
    if not marcaciones:
        raise ValueError("No se encontraron marcaciones en los archivos proporcionados.")
        
    # Filtrar solo Permitidos
    marcaciones = [m for m in marcaciones if m.get("situacion", "") == "Permitido"]
    
    # Agrupar por empleado
    from collections import defaultdict
    emp_punches = defaultdict(list)
    
    for m in marcaciones:
        emp = m.get("empleado")
        fecha = m.get("fecha")
        hora = m.get("hora")
        empresa = m.get("empresa_raw", "") or m.get("empresa", "")
        tipo = m.get("tipo_acceso", "").lower()
        
        if emp and fecha and hora:
            dt = datetime.combine(fecha, hora)
            emp_punches[emp].append({
                "dt": dt,
                "empresa": empresa,
                "tipo": tipo
            })
            
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asistencia Masiva"
    
    headers = ["Empresa", "Empleado", "Fecha Inicio", "Hora Inicio", "Fecha Fin", "Hora Fin", "Horas Trabajadas", "Horas Trabajadas Hexagesimales"]
    ws.append(headers)
    
    def _fmt_hms(segundos):
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = int(segundos % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
        
    csv_data = []
    
    for emp, punches in emp_punches.items():
        # Ordenar cronologicamente
        punches.sort(key=lambda x: x["dt"])
        
        last_in = None
        
        # Algoritmo de emparejamiento inteligente
        for p in punches:
            # Identificar si es entrada o salida basado en el texto
            is_in = "entrada" in p["tipo"]
            is_out = "salida" in p["tipo"]
            
            # Si el tipo no esta claro, usamos heuristica de tiempo
            if not is_in and not is_out:
                if last_in is None:
                    is_in = True
                else:
                    # Si han pasado mas de 14 horas desde el ultimo punch, asumimos que olvido salir
                    # y este es un nuevo ingreso.
                    if (p["dt"] - last_in["dt"]).total_seconds() > 14 * 3600:
                        is_in = True
                        last_in = None
                    else:
                        is_out = True
            
            if is_in:
                # Si ya habia una entrada, se sobrescribe (olvido marcar salida)
                last_in = p
            elif is_out:
                if last_in is not None:
                    # Match encontrado!
                    dt_inicio = last_in["dt"]
                    dt_fin = p["dt"]
                    
                    segundos = (dt_fin - dt_inicio).total_seconds()
                    
                    # Filtro de sanidad: si es mas de 24 horas, probablemente es error de marcacion
                    if 0 < segundos < 24 * 3600:
                        empresa = last_in["empresa"] or p["empresa"]
                        hexa = round(segundos / 3600.0, 2)
                        
                        row = [
                            empresa,
                            emp,
                            dt_inicio.strftime("%Y-%m-%d"),
                            dt_inicio.strftime("%H:%M:%S"),
                            dt_fin.strftime("%Y-%m-%d"),
                            dt_fin.strftime("%H:%M:%S"),
                            _fmt_hms(segundos),
                            hexa
                        ]
                        ws.append(row)
                        
                        # Para el CSV de dashboard (lo asociamos a la fecha de inicio del turno)
                        csv_data.append([
                            empresa,
                            emp,
                            dt_inicio.strftime("%Y-%m-%d"),
                            dt_inicio.strftime("%H:%M:%S"),
                            dt_fin.strftime("%H:%M:%S"),
                            _fmt_hms(segundos),
                            hexa
                        ])
                    last_in = None
                
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = (max_length + 2)
        
    out_path = os.path.join(tempfile.gettempdir(), f"Asistencia_Masiva_{os.getpid()}.xlsx")
    wb.save(out_path)
    
    historico_dir = base_dir.parent.parent / "historico" / "asistencia"
    historico_dir.mkdir(parents=True, exist_ok=True)
    db_path = historico_dir / "db.csv"
    
    # El dashboard lee "Fecha", "Horas Trabajadas Hexagesimales", "Empresa", "Empleado"
    # Asi que guardamos con headers compatibles para el dashboard nativo
    dash_headers = ["Empresa", "Empleado", "Fecha", "Hora Inicio", "Hora Fin", "Horas Trabajadas", "Horas Trabajadas Hexagesimales"]
    with open(db_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(dash_headers)
        writer.writerows(csv_data)
        
    return out_path
