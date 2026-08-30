from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QComboBox)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor, QFont, QPainter
import pandas as pd
from pathlib import Path

try:
    from PySide6.QtCharts import QChart, QChartView, QLineSeries, QBarSeries, QBarSet, QPieSeries, QValueAxis, QBarCategoryAxis, QDateTimeAxis
except ImportError:
    pass

class NativeDashboard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard Ejecutivo - Asistencia Masiva")
        self.resize(1200, 800)
        self.df = self._load_data()
        
        # Filtros seleccionados
        self.sel_empresa = "TODAS"
        self.sel_mes = "TODOS"
        self.sel_anio = "TODOS"
        
        self._setup_main_ui()
        
    def _load_data(self):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        db_path = base_dir / "historico" / "asistencia" / "db.csv"
        if not db_path.exists():
            return pd.DataFrame()
        df = pd.read_csv(db_path)
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"])
            df["Mes"] = df["Fecha"].dt.month_name()
            df["Año"] = df["Fecha"].dt.year.astype(str)
        return df

    def _setup_main_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        title = QLabel("Dashboard Ejecutivo de Asistencia")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        self.main_layout.addWidget(title)
        
        if self.df.empty:
            self.main_layout.addWidget(QLabel("No hay datos procesados. Por favor procesa archivos primero."))
            return
            
        # --- FILTROS ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Empresa:"))
        self.cb_empresa = QComboBox()
        empresas = ["TODAS"] + sorted([str(e) for e in self.df["Empresa"].dropna().unique()])
        self.cb_empresa.addItems(empresas)
        self.cb_empresa.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.cb_empresa)
        
        filter_layout.addWidget(QLabel("Año:"))
        self.cb_anio = QComboBox()
        anios = ["TODOS"] + sorted([str(a) for a in self.df["Año"].dropna().unique()])
        self.cb_anio.addItems(anios)
        self.cb_anio.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.cb_anio)
        
        filter_layout.addWidget(QLabel("Mes:"))
        self.cb_mes = QComboBox()
        meses = ["TODOS"] + sorted([str(m) for m in self.df["Mes"].dropna().unique()])
        self.cb_mes.addItems(meses)
        self.cb_mes.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.cb_mes)
        
        filter_layout.addStretch()
        self.main_layout.addLayout(filter_layout)
        
        # CONTENEDOR DINAMICO
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0,0,0,0)
        self.main_layout.addWidget(self.content_widget)
        
        self._render_dashboard()
        
    def _on_filter_changed(self):
        self.sel_empresa = self.cb_empresa.currentText()
        self.sel_anio = self.cb_anio.currentText()
        self.sel_mes = self.cb_mes.currentText()
        self._render_dashboard()
        
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self._clear_layout(item.layout())

    def _render_dashboard(self):
        self._clear_layout(self.content_layout)
        
        # Filtrar DF
        df_filt = self.df.copy()
        if self.sel_empresa != "TODAS":
            df_filt = df_filt[df_filt["Empresa"] == self.sel_empresa]
        if self.sel_anio != "TODOS":
            df_filt = df_filt[df_filt["Año"] == self.sel_anio]
        if self.sel_mes != "TODOS":
            df_filt = df_filt[df_filt["Mes"] == self.sel_mes]
            
        if df_filt.empty:
            self.content_layout.addWidget(QLabel("No hay datos para los filtros seleccionados."))
            return
            
        # KPIs
        kpi_layout = QHBoxLayout()
        total_personal = df_filt["Empleado"].nunique()
        total_horas = df_filt["Horas Trabajadas Hexagesimales"].sum()
        promedio_horas = total_horas / total_personal if total_personal > 0 else 0
        dias_registrados = df_filt["Fecha"].nunique()
        
        kpis = [
            ("Total Personal", str(total_personal)),
            ("Horas Totales", f"{total_horas:,.1f}"),
            ("Productividad (Hrs/Pers)", f"{promedio_horas:,.1f}"),
            ("Días Registrados", str(dias_registrados))
        ]
        
        for k, v in kpis:
            card = QWidget()
            card.setStyleSheet("background-color: white; border-radius: 8px; border-left: 5px solid #FF5A00; padding: 10px;")
            card_layout = QVBoxLayout(card)
            l_val = QLabel(v)
            l_val.setStyleSheet("font-size: 28px; font-weight: bold; color: #1F2937;")
            l_lbl = QLabel(k)
            l_lbl.setStyleSheet("font-size: 13px; color: #6B7280; font-weight: bold;")
            card_layout.addWidget(l_val)
            card_layout.addWidget(l_lbl)
            kpi_layout.addWidget(card)
            
        self.content_layout.addLayout(kpi_layout)
        
        # Charts
        charts_layout = QHBoxLayout()
        try:
            # 1. Line Chart
            chart1 = QChart()
            chart1.setTitle("Evolución de Horas Trabajadas")
            series1 = QLineSeries()
            series1.setName("Horas Totales")
            series1.setColor(QColor("#FF5A00"))
            
            df_trend = df_filt.groupby("Fecha")["Horas Trabajadas Hexagesimales"].sum().reset_index()
            df_trend = df_trend.sort_values("Fecha")
            
            max_y = 0
            for _, row in df_trend.iterrows():
                dt = row["Fecha"]
                qdt = QDateTime(dt.year, dt.month, dt.day, 0, 0, 0)
                series1.append(qdt.toMSecsSinceEpoch(), row["Horas Trabajadas Hexagesimales"])
                if row["Horas Trabajadas Hexagesimales"] > max_y:
                    max_y = row["Horas Trabajadas Hexagesimales"]
                    
            chart1.addSeries(series1)
            
            # Eje X: Fecha
            axisX = QDateTimeAxis()
            axisX.setFormat("dd-MM-yyyy")
            axisX.setTitleText("Fecha")
            chart1.addAxis(axisX, Qt.AlignBottom)
            series1.attachAxis(axisX)
            
            # Eje Y: Horas
            axisY = QValueAxis()
            axisY.setTitleText("Horas Totales")
            axisY.setRange(0, max_y * 1.1)  # 10% padding
            chart1.addAxis(axisY, Qt.AlignLeft)
            series1.attachAxis(axisY)
            
            chart1.legend().hide()
            view1 = QChartView(chart1)
            view1.setRenderHint(QPainter.RenderHint.Antialiasing)
            charts_layout.addWidget(view1)
            
            # 2. Pie Chart
            chart2 = QChart()
            chart2.setTitle("Distribución por Empresa")
            series2 = QPieSeries()
            df_emp = df_filt.groupby("Empresa")["Horas Trabajadas Hexagesimales"].sum().reset_index()
            for _, row in df_emp.iterrows():
                slice_ = series2.append(str(row["Empresa"]), row["Horas Trabajadas Hexagesimales"])
                slice_.setLabelVisible(True)
                
            chart2.addSeries(series2)
            view2 = QChartView(chart2)
            view2.setRenderHint(QPainter.RenderHint.Antialiasing)
            charts_layout.addWidget(view2)
        except Exception as e:
            charts_layout.addWidget(QLabel(f"Gráficos no disponibles: {e}"))
            
        self.content_layout.addLayout(charts_layout)
        
        # Top 10
        top_lbl = QLabel("Top 10 Empleados con más horas")
        top_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.content_layout.addWidget(top_lbl)
        
        df_top = df_filt.groupby(["Empleado", "Empresa"])["Horas Trabajadas Hexagesimales"].sum().reset_index()
        df_top = df_top.sort_values("Horas Trabajadas Hexagesimales", ascending=False).head(10)
        
        table = QTableWidget(len(df_top), 3)
        table.setHorizontalHeaderLabels(["Empleado", "Empresa", "Horas Totales"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        for i, row in enumerate(df_top.itertuples()):
            table.setItem(i, 0, QTableWidgetItem(str(row.Empleado)))
            table.setItem(i, 1, QTableWidgetItem(str(row.Empresa)))
            h_item = QTableWidgetItem(f"{row._3:,.2f}")
            h_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 2, h_item)
            
        self.content_layout.addWidget(table)

def open_dashboard(parent):
    dlg = NativeDashboard(parent)
    dlg.exec()
