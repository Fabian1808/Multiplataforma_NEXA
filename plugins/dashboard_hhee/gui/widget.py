
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QComboBox, QMessageBox)

class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        lbl = QLabel("Dashboard Interactivo de Horas Extras")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(lbl)
        
        desc = QLabel("Genera una vista gráfica del histórico de validaciones, visualizando horas extras y costos agrupados por mes.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Filtros
        h_layout = QHBoxLayout()
        
        self.combo_anio = QComboBox()
        self.combo_anio.addItems(["2025", "2026", "2027"])
        self.combo_anio.setCurrentText("2026")
        
        self.combo_empresa = QComboBox()
        self.combo_empresa.addItems(["TODAS", "EMSUNIR", "CONFIPETROL", "CJM"])
        
        h_layout.addWidget(QLabel("Año:"))
        h_layout.addWidget(self.combo_anio)
        h_layout.addWidget(QLabel("Empresa:"))
        h_layout.addWidget(self.combo_empresa)
        h_layout.addStretch()
        
        layout.addLayout(h_layout)
        
        self.btn_generar = QPushButton("Generar y Abrir Dashboard")
        self.btn_generar.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 10px;")
        self.btn_generar.clicked.connect(self._generar)
        layout.addWidget(self.btn_generar)
        
        layout.addStretch()
        
    def _generar(self):
        anio = self.combo_anio.currentText()
        empresa = self.combo_empresa.currentText()
        
        import json
        appdata = Path(os.environ.get("APPDATA", "")) / "NEXA" / "ProductivityHub"
        config_path = appdata / "plugins" / "horas_extras" / "config" / "config.json"
        
        historicos_dir = "historico"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    historicos_dir = cfg.get("rutas", {}).get("historicos_dir", "historico")
            except Exception:
                pass
                
        base_dir = Path.cwd()
        if not os.path.isabs(historicos_dir):
            if (base_dir / "data" / historicos_dir).exists():
                hist_path = base_dir / "data" / historicos_dir
            else:
                hist_path = base_dir / historicos_dir
        else:
            hist_path = Path(historicos_dir)
            
        if not hist_path.exists():
            QMessageBox.warning(self, "Error", f"No se encontró la carpeta de históricos en:\n{hist_path}")
            return
            
        engine_src = str(Path(__file__).parent.parent / "engine")
        if engine_src not in sys.path:
            sys.path.insert(0, engine_src)
            
        try:
            import builder
            builder.abrir_dashboard(str(hist_path), anio, empresa)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el dashboard:\n{e}")

def get_widget():
    return DashboardWidget()



def create_widget(parent=None):
    return PluginWidget()

