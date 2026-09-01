"""GUI widget de HORAS EXTRAS MASIVA para el Hub (embebido).

Flujo de usuario: Cargar Rainbow / Personal (Relatorio) / Tarifas
-> Calcular -> Revisar KPIs y TOPs -> Exportar Excel (detalle).
Sigue la paleta NEXA (claro/oscuro automático vía Theme).

Robustez y concurrencia:
- El cálculo pesado y la exportación corren en QThread y NUNCA tocan widgets;
  sólo emiten señales hacia el hilo principal.
- El widget expone refresh_style() para re-aplicar el tema en sitio, de modo que
  el contenedor (AppViewer) NO necesita destruir este widget al cambiar de tema.
- Los threads se detienen y esperan correctamente antes de destruir el widget
  (evita el fatal "QThread: Destroyed while thread is still running").
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QMargins
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
    QFrame, QHeaderView, QProgressBar, QScrollArea, QGridLayout,
)
from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries, QHorizontalBarSeries, QBarSet,
    QBarCategoryAxis, QValueAxis, QPieSeries, QPieSlice,
)

from hub.ui.common.design import (
    ACCENT, INFO, SUCCESS, WARNING, ERROR, Theme, NEXAStyles, KPIWidget, get_font,
)

logger = logging.getLogger("horas_extras_masiva")

# ruta al motor
ENGINE_SRC = Path(__file__).resolve().parent.parent / "engine" / "src"
if str(ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(ENGINE_SRC))
GUI_DIR = Path(__file__).resolve().parent
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

# Registro global de hilos de trabajo activos para esperarlos al cerrar la app
# (evita el abort "QThread: Destroyed while thread is still running").
from thread_registry import registrar_thread as _registrar_thread  # noqa: E402
from thread_registry import desregistrar_thread as _desregistrar_thread  # noqa: E402


class _CalculoThread(QThread):
    """Ejecuta el motor completo en segundo plano con informe de progreso.

    Emite: progreso(porcentaje, etapa, procesados, total)
           finalizado(ok, errores)
    El UI se actualiza SOLO desde el hilo principal (slot conectado).
    """

    progreso = Signal(int, str, int, int)
    finalizado = Signal(bool, str)

    def __init__(self, cfg, fuentes, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.fuentes = fuentes
        self.resultado = None
        self._cfg_r = None
        self._t0 = time.perf_counter()

    def run(self):
        try:
            import config as cmod
            import motor as mmod
            self._cfg_r = cmod.cargar_config(self.cfg)
            self.progreso.emit(0, "Leyendo archivos", 0, 0)
            self.resultado = mmod.ejecutar(
                self.fuentes, self._cfg_r,
                on_etapa=lambda nombre, pct: self.progreso.emit(pct, nombre, 0, 0))
            self.progreso.emit(100, "Completado", 0, 0)
            self.finalizado.emit(True, "")
        except Exception as exc:  # noqa
            import traceback
            logger.exception("Error en cálculo de horas extras")
            self.finalizado.emit(False, str(exc) + "\n" + traceback.format_exc())

    @property
    def duracion(self) -> float:
        return time.perf_counter() - self._t0


class _ExportarThread(QThread):
    """Llama a exportacion en un hilo para no congelar la UI con datos grandes."""

    finalizado = Signal(bool, str)

    def __init__(self, resultado, cfg, ruta, parent=None):
        super().__init__(parent)
        self.resultado = resultado
        self.cfg = cfg
        self.ruta = ruta
        self._t0 = time.perf_counter()

    def run(self):
        try:
            import exportacion
            exportacion.exportar(self.resultado, self.ruta, self.cfg or {})
            self.finalizado.emit(True, self.ruta)
        except Exception as exc:  # noqa
            import traceback
            logger.exception("Error al exportar")
            self.finalizado.emit(False, str(exc) + "\n" + traceback.format_exc())

    @property
    def duracion(self) -> float:
        return time.perf_counter() - self._t0


class HorasExtrasMasivaWidget(QWidget):
    """Widget embebido que expone create_widget() para el PluginRegistry."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._fuentes = {
            "rainbow": None, "relatorio": None, "tarifas": None,
            "areas": None, "gerencia": None,
        }
        self._resultado = None
        self._cfg = None
        self._analisis_cache = None
        self._worker = None          # _CalculoThread vigente
        self._worker_exp = None      # _ExportarThread vigente
        self._ocupado = False
        self._estrategia_cancelar = False
        self._tiempo_inicio = time.perf_counter()
        self._setup_ui()

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        titulo = QLabel("Horas Extras Masiva")
        titulo.setFont(get_font(20, bold=True))
        titulo.setObjectName("hemTitulo")
        titulo.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
        root.addWidget(titulo)

        desc = QLabel(
            "Procesa marcaciones RAINBOW contra el maestro de personal (RELATORIO) "
            "y el tarifario (TARIFAS) para calcular horas extras valorizadas en soles, "
            "con matching tarifario por niveles de confianza, auditoría y trazabilidad."
        )
        desc.setObjectName("hemDesc")
        desc.setWordWrap(True)
        desc.setFont(get_font(12))
        desc.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent;")
        root.addWidget(desc)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("QTabWidget::pane{border:none;}")
        self._tabs.addTab(self._build_tab_proceso(), "Proceso")
        self._tabs.addTab(self._build_tab_dashboard(), "Dashboard")
        self._tabs.addTab(self._build_tab_detalle(), "Detalle")
        root.addWidget(self._tabs, 1)

        self._progreso = QProgressBar()
        self._progreso.setRange(0, 100)
        self._progreso.setValue(0)
        self._progreso.hide()
        root.addWidget(self._progreso)

        self._status = QLabel("Listo. Seleccione los archivos y presione Calcular.")
        self._status.setObjectName("hemStatus")
        self._status.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent;")
        root.addWidget(self._status)

    def _build_tab_proceso(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(14)

        # ---- área de archivos
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(NEXAStyles.card_no_hover())
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 16)
        card_lay.setSpacing(10)
        card_lay.addWidget(self._label("Archivos fuente", 13, bold=True))

        self._file_rows = {}
        for key, nombre, requerido in [
            ("rainbow", "RAINBOW (marcaciones — puede ser varios archivos)", True),
            ("relatorio", "RELATORIO (maestro personal)", True),
        ]:
            fila = QHBoxLayout()
            req = " *" if requerido else " (opcional)"
            lbl = QLabel(nombre + req)
            lbl.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
            lbl.setMinimumWidth(240)
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setPlaceholderText("Seleccionar archivo(s)...")
            edit.setStyleSheet(NEXAStyles.input())
            btn = QPushButton("Examinar")
            btn.setStyleSheet(NEXAStyles.secondary_button())
            btn.clicked.connect(lambda _, k=key: self._seleccionar(k))
            fila.addWidget(lbl)
            fila.addWidget(edit, 1)
            fila.addWidget(btn)
            card_lay.addLayout(fila)
            self._file_rows[key] = (edit, btn)

        nota = self._label(
            "TARIFAS, ÁREAS y GERENCIA están integrados en el módulo (no requiere subirlos).",
            11)
        nota.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent;")
        card_lay.addWidget(nota)

        lay.addWidget(card)

        # ---- botones: calcular / cancelar / exportar
        btn_row = QHBoxLayout()
        self.btn_calcular = QPushButton("Calcular Horas Extras Masiva")
        self.btn_calcular.setStyleSheet(NEXAStyles.primary_button())
        self.btn_calcular.setMinimumHeight(42)
        self.btn_calcular.clicked.connect(self._ejecutar)
        btn_row.addWidget(self.btn_calcular)

        self.btn_cancelar = QPushButton("Cancelar proceso")
        self.btn_cancelar.setStyleSheet(NEXAStyles.danger_button())
        self.btn_cancelar.setMinimumHeight(42)
        self.btn_cancelar.setEnabled(False)
        self.btn_cancelar.clicked.connect(self._cancelar)
        btn_row.addWidget(self.btn_cancelar)

        self.btn_exportar_proceso = QPushButton("Descargar Excel")
        self.btn_exportar_proceso.setStyleSheet(NEXAStyles.secondary_button())
        self.btn_exportar_proceso.setMinimumHeight(42)
        self.btn_exportar_proceso.setEnabled(False)
        self.btn_exportar_proceso.clicked.connect(self._exportar)
        btn_row.addWidget(self.btn_exportar_proceso)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # ---- KPIs
        self._kpi_row = QHBoxLayout()
        self._kpis = {}
        for key in ("marcaciones", "jornadas", "conciliados", "horas", "monto", "errores"):
            kpi = KPIWidget("—", "0")
            kpi.setMinimumHeight(96)
            self._kpis[key] = kpi
            self._kpi_row.addWidget(kpi)
        lay.addLayout(self._kpi_row)

        # ---- TOP trabajadores y cargos
        tops = QHBoxLayout()
        self._top_trabajadores = self._tabla_top(["Trabajador", "HH.EE. (h)", "Monto (S/)"])
        self._top_cargos = self._tabla_top(["Cargo", "HH.EE. (h)", "Monto (S/)"])
        tops.addWidget(self._env_card("TOP trabajadores por monto", self._top_trabajadores))
        tops.addWidget(self._env_card("TOP cargos por monto", self._top_cargos))
        lay.addLayout(tops)
        lay.addStretch()
        return tab

    def _build_tab_dashboard(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        head = QHBoxLayout()
        self._dash_titulo = self._label(
            "Ejecute 'Calcular Horas Extras Masiva' para visualizar el dashboard.", 12)
        head.addWidget(self._dash_titulo)
        head.addStretch()
        lay.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background: transparent;}")

        cont = QWidget()
        grid = QGridLayout(cont)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)

        self._chart_top_trab = self._chart_view()
        self._chart_tipo = self._chart_view()
        self._chart_turno = self._chart_view()
        self._chart_empresa = self._chart_view()

        grid.addWidget(self._env_card("TOP 10 trabajadores por monto (S/)", self._chart_top_trab), 0, 0)
        grid.addWidget(self._env_card("Distribución por tipo de hora (h)", self._chart_tipo), 0, 1)
        grid.addWidget(self._env_card("Distribución por turno (h)", self._chart_turno), 1, 0)
        grid.addWidget(self._env_card("Distribución por empresa (monto S/)", self._chart_empresa), 1, 1)

        scroll.setWidget(cont)
        lay.addWidget(scroll, 1)
        self._dash_grid = grid
        return tab

    def _chart_view(self) -> QChartView:
        chart = QChart()
        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)
        chart.setMargins(QMargins(0, 0, 0, 0))
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setMinimumHeight(300)
        return view

    def _style_chart(self, chart: QChart, texto: str):
        chart.setTitle(texto)
        tf = QFont("Segoe UI", 12)
        tf.setBold(True)
        chart.setTitleFont(tf)
        chart.setTitleBrush(QColor(Theme.text()))
        chart.legend().setVisible(True)
        chart.legend().setLabelColor(QColor(Theme.text_secondary()))
        chart.legend().setFont(QFont("Segoe UI", 10))
        return chart

    # ---- constructores de gráficos ------------------------------------
    def _grafico_barras_h(self, labels, valores, color):
        chart = QChart()
        self._style_chart(chart, "")
        chart.legend().setVisible(False)
        series = QHorizontalBarSeries()
        set_b = QBarSet("")
        set_b.setColor(QColor(color))
        ordered = list(reversed(list(zip(labels, valores))))
        cat = []
        for lbl, _v in ordered:
            set_b.append(float(_v))
            cat.append(str(lbl))
        series.append(set_b)
        chart.addSeries(series)
        ax_y = QBarCategoryAxis()
        ax_y.append(cat)
        ax_y.setLabelsFont(QFont("Segoe UI", 9))
        ax_y.setLabelsColor(QColor(Theme.text_secondary()))
        chart.addAxis(ax_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(ax_y)
        ax_x = QValueAxis()
        ax_x.setLabelsFont(QFont("Segoe UI", 9))
        ax_x.setLabelsColor(QColor(Theme.text_secondary()))
        ax_x.setLabelFormat("%.0f")
        chart.addAxis(ax_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(ax_x)
        return chart

    def _grafico_barras_v(self, labels, valores, color, sufijo=""):
        chart = QChart()
        self._style_chart(chart, "")
        chart.legend().setVisible(False)
        series = QBarSeries()
        set_b = QBarSet("")
        set_b.setColor(QColor(color))
        cat = []
        for lbl, v in zip(labels, valores):
            set_b.append(float(v))
            cat.append(str(lbl))
        series.append(set_b)
        chart.addSeries(series)
        ax_x = QBarCategoryAxis()
        ax_x.append(cat)
        ax_x.setLabelsFont(QFont("Segoe UI", 9))
        ax_x.setLabelsColor(QColor(Theme.text_secondary()))
        chart.addAxis(ax_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(ax_x)
        ax_y = QValueAxis()
        ax_y.setLabelsFont(QFont("Segoe UI", 9))
        ax_y.setLabelsColor(QColor(Theme.text_secondary()))
        ax_y.setLabelFormat("%.0f" + sufijo)
        chart.addAxis(ax_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(ax_y)
        return chart

    def _grafico_torta(self, labels, valores):
        chart = QChart()
        self._style_chart(chart, "")
        serie = QPieSeries()
        serie.setHoleSize(0.35)
        serie.setPieSize(0.72)
        serie.setLabelsVisible(True)
        serie.setLabelsPosition(QPieSlice.LabelPosition.LabelOutside)
        paleta = [ACCENT, INFO, SUCCESS, WARNING, ERROR,
                  "#7C3AED", "#0EA5E9", "#DB2777", "#059669", "#D97706"]
        for i, (lbl, v) in enumerate(zip(labels, valores)):
            sl = serie.append(f"{lbl} ({v:g})", float(v))
            sl.setColor(QColor(paleta[i % len(paleta)]))
            sl.setLabelVisible(True)
            sl.setLabelColor(QColor(Theme.text_secondary()))
        chart.addSeries(serie)
        chart.legend().setVisible(False)
        return chart

    def _build_tab_detalle(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(10)

        barra = QHBoxLayout()
        self.btn_exportar = QPushButton("Exportar Excel")
        self.btn_exportar.setStyleSheet(NEXAStyles.primary_button())
        self.btn_exportar.setEnabled(False)
        self.btn_exportar.clicked.connect(self._exportar)
        barra.addWidget(self.btn_exportar)

        self.btn_detalle_todos = QPushButton("Solo OK")
        self.btn_detalle_todos.setStyleSheet(NEXAStyles.ghost_button())
        self.btn_detalle_todos.setCheckable(True)
        self.btn_detalle_todos.clicked.connect(self._cargar_tabla_detalle)
        barra.addWidget(self.btn_detalle_todos)
        barra.addStretch()
        lay.addLayout(barra)

        self._tabla_detalle = QTableWidget(0, 18)
        self._tabla_detalle.setHorizontalHeaderLabels([
            "Fecha", "Empleado", "DNI", "Cargo", "Empresa", "RUC", "Turno",
            "Entrada", "Salida", "H. Trab", "Jornada", "Horas Extras",
            "Tipo Hora", "Tarifa", "Monto (S/)", "Nivel Tarifa", "Estado",
        ])
        self._tabla_detalle.verticalHeader().setVisible(False)
        self._tabla_detalle.setStyleSheet(NEXAStyles.table())
        self._tabla_detalle.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla_detalle.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self._tabla_detalle)
        return tab

    # ---- helpers de UI
    def _label(self, texto, size=12, bold=False):
        l = QLabel(texto)
        l.setFont(get_font(size, bold=bold))
        l.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
        return l

    def _env_card(self, titulo, widget):
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(NEXAStyles.card_no_hover())
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.addWidget(self._label(titulo, 12, bold=True))
        v.addWidget(widget)
        return card

    def _tabla_top(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setStyleSheet(NEXAStyles.table())
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setMinimumHeight(180)
        return t

    # ------------------------------------------------------------------ theme (re-aplicar en sitio, no destruir)
    def refresh_style(self) -> None:
        """Re-aplica el tema activo sin destruir widgets ni hilos."""
        from hub.ui.common.design import setup_app_palette  # ya importado
        for oid in ("hemTitulo",):
            w = self.findChild(QLabel, oid)
            if w is not None:
                w.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
        for oid in ("hemDesc", "hemStatus"):
            w = self.findChild(QLabel, oid)
            if w is not None:
                w.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent;")
        self._tabs.setStyleSheet("QTabWidget::pane{border:none;}")
        # KPIs se refrescan con Theme activo
        for kpi in self._kpis.values():
            self._estilizar_kpi(kpi)

    def _estilizar_kpi(self, kpi: KPIWidget) -> None:
        kpi._value.setStyleSheet(f"color: {Theme.text()}; background: transparent; border: none;")
        kpi._title.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent; border: none;")
        kpi.setStyleSheet(NEXAStyles.kpi_card(ACCENT))

    # ------------------------------------------------------------------ actions
    def _seleccionar(self, key):
        if key == "rainbow":
            rutas, _ = QFileDialog.getOpenFileNames(
                self, "Seleccionar archivos RAINBOW", "", "Excel (*.xlsx *.XLSX)")
            if not rutas:
                return
            self._fuentes[key] = list(rutas)
            edit, _btn = self._file_rows[key]
            n = len(rutas)
            edit.setText(Path(rutas[0]).name if n == 1 else f"{n} archivos RAINBOW seleccionados")
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo", "", "Excel (*.xlsx *.XLSX)")
        if not ruta:
            return
        self._fuentes[key] = ruta
        edit, _btn = self._file_rows[key]
        edit.setText(Path(ruta).name)

    def _verificar_archivos(self) -> None:
        for key, nombre in (("rainbow", "RAINBOW"), ("relatorio", "RELATORIO")):
            if not self._fuentes.get(key):
                raise ValueError(f"Seleccione el archivo {nombre}.")

    def _ejecutar(self):
        if self._ocupado:
            self._status.setText("Ya hay un proceso en curso.")
            return
        # validar archivos con mensajes amigables (FASE 8)
        try:
            self._verificar_archivos()
        except ValueError as e:
            QMessageBox.warning(self, "Faltan datos", str(e))
            return
        self._iniciar_proceso()

    def _iniciar_proceso(self):
        self._ocupado = True
        self._estrategia_cancelar = False
        self._tiempo_inicio = time.perf_counter()
        self.btn_calcular.setEnabled(False)
        self.btn_calcular.setText("Procesando…")
        self.btn_cancelar.setEnabled(True)
        self.btn_exportar.setEnabled(False)
        self.btn_exportar_proceso.setEnabled(False)
        self._progreso.setRange(0, 100)
        self._progreso.setValue(0)
        self._progreso.show()
        self._status.setText("Preparando registros…")

        import config as cmod
        import motor as mmod
        fuentes = mmod.Fuentes(
            rainbow=self._fuentes["rainbow"],
            relatorio=self._fuentes["relatorio"],
            tarifas=self._fuentes["tarifas"],
            areas=self._fuentes["areas"],
            gerencia=self._fuentes["gerencia"],
        )
        # (Re)crear worker; el anterior ya terminó porque _ocupado se libera al final.
        self._worker = _CalculoThread(self._cfg, fuentes, self)
        self._worker.progreso.connect(self._on_progreso)
        self._worker.finalizado.connect(self._on_calculo)
        self._worker.finished.connect(lambda w=self._worker: self._on_thread_finished(w))
        _registrar_thread(self._worker)
        self._worker.start()

    def _on_progreso(self, pct, etapa, procesados, total):
        self._progreso.setValue(pct)
        extra = f" · {procesados:,}" if procesados else ""
        self._status.setText(f"{etapa}{extra} · {pct}%")

    def _on_thread_finished(self, worker):
        # Limpiar el worker para liberar memoria (FASE 4). El slot se llama en
        # el hilo principal (señal finished de QThread).
        _desregistrar_thread(worker)
        self._worker = None

    def _cancelar(self):
        """Cancelación segura: se espera a que el worker termine por su cuenta
        (el motor no se interrumpe a mitad por diseño; se marca y se ignora el
        resultado). La UI vuelve a estado inicial."""
        self._estrategia_cancelar = True
        self.btn_cancelar.setEnabled(False)
        self._status.setText("Cancelando… se esperará a que finalice la operación en curso.")
        # No destruimos el QThread vivo: esperamos su finish normal.

    def _on_calculo(self, ok, msg):
        self._ocupado = False
        self._progreso.hide()
        self.btn_calcular.setEnabled(True)
        self.btn_calcular.setText("Calcular Horas Extras Masiva")
        self.btn_cancelar.setEnabled(False)
        t = time.perf_counter() - self._tiempo_inicio
        if not ok:
            self._status.setText("Error en el cálculo.")
            QMessageBox.critical(self, "Error", "Ocurrió un error:\n" + msg)
            return
        if self._estrategia_cancelar:
            self._status.setText("Proceso cancelado.")
            return
        self._resultado = getattr(self._worker, "resultado", None)
        self._cfg = getattr(self._worker, "_cfg_r", None)
        self._analisis_cache = None
        self._render_kpis()
        self._render_tops()
        self._render_dashboard()
        self._cargar_tabla_detalle()
        self.btn_exportar.setEnabled(True)
        self.btn_exportar_proceso.setEnabled(True)
        self.btn_detalle_todos.setText(
            "Mostrar todos" if self._resultado.estados.get("ERROR", 0) else "Solo OK")
        self._status.setText(
            f"✓ Cálculo completado en {t:.2f}s: "
            f"{self._resultado.totales['jornadas']} jornadas, "
            f"{self._resultado.horas_extra_total} h de HH.EE., "
            f"{self._resultado.monto_total} de monto total.")
        logger.info("Cálculo completado en %.2fs: jornadas=%d HE=%s monto=%s",
                    t, self._resultado.totales['jornadas'],
                    self._resultado.horas_extra_total, self._resultado.monto_total)
        QMessageBox.information(self, "Éxito", "Cálculo completado con éxito.")

    def _analisis(self):
        if self._analisis_cache is None and self._resultado is not None:
            import dashboard
            self._analisis_cache = dashboard.Analisis(self._resultado)
        return self._analisis_cache

    def _render_kpis(self):
        r = self._resultado
        errores = r.estados.get("ERROR", 0) + r.estados.get("REVISAR", 0)
        self._kpis["marcaciones"].set_value(str(r.totales["marcaciones"]))
        self._kpis["marcaciones"]._title.setText("Marcaciones RAINBOW")
        self._kpis["jornadas"].set_value(str(r.totales["jornadas"]))
        self._kpis["jornadas"]._title.setText("Jornadas")
        self._kpis["conciliados"].set_value(str(r.totales["conciliados"]))
        self._kpis["conciliados"]._title.setText("Conciliados")
        self._kpis["horas"].set_value(str(r.horas_extra_total))
        self._kpis["horas"]._title.setText("Horas Extras (h)")
        self._kpis["monto"].set_value(str(r.monto_total))
        self._kpis["monto"]._title.setText("Monto total (S/)")
        self._kpis["errores"].set_value(str(errores))
        self._kpis["errores"]._title.setText("Errores / Revisar")
        self._kpis["errores"]._value.setStyleSheet(
            f"color: {'#DC2626' if errores else SUCCESS}; background: transparent;")

    def _render_tops(self):
        an = self._analisis()
        if an is None:
            return
        self._llenar_top(self._top_trabajadores, an.top("trabajador"))
        self._llenar_top(self._top_cargos, an.top("cargo"))

    def _llenar_top(self, tabla, datos):
        tabla.setRowCount(0)
        for i, (nombre, v) in enumerate(datos):
            tabla.insertRow(i)
            texto = str(nombre)
            if len(texto) > 34:
                texto = texto[:31] + "…"
            tabla.setItem(i, 0, QTableWidgetItem(texto))
            tabla.setItem(i, 1, QTableWidgetItem(str(v["horas"])))
            tabla.setItem(i, 2, QTableWidgetItem(str(v["monto"])))

    def _render_dashboard(self):
        an = self._analisis()
        if an is None:
            return
        top_trab = an.top("trabajador")
        chart = self._grafico_barras_h(
            [t[0] for t in top_trab][:10], [float(t[1]["monto"]) for t in top_trab][:10], ACCENT)
        chart.setTitle("TOP 10 trabajadores por monto (S/)")
        self._chart_top_trab.setChart(chart)

        por_tipo = an.por_tipo
        labels_t = [str(k) for k in por_tipo.keys()]
        vals_t = [float(v["horas"]) for v in por_tipo.values()]
        self._chart_tipo.setChart(self._grafico_torta(labels_t, vals_t) if labels_t else QChart())

        por_turno = an.por_turno
        self._chart_turno.setChart(self._grafico_barras_v(
            [str(k) for k in por_turno.keys()],
            [float(v["horas"]) for v in por_turno.values()], INFO))

        top_emp = an.top("empresa")
        self._chart_empresa.setChart(self._grafico_barras_v(
            [str(e[0]) for e in top_emp][:10],
            [float(e[1]["monto"]) for e in top_emp][:10], SUCCESS))

        self._dash_titulo.setText(
            f"Dashboard — {an.kpis['n_detalle']} registros, "
            f"{an.kpis['horas_totales']} h de HH.EE., "
            f"S/ {an.kpis['monto_total']} de monto total.")

    _MAX_FILAS_TABLA = 5000

    def _cargar_tabla_detalle(self):
        if not self._resultado:
            return
        solo_ok = self.btn_detalle_todos.isChecked()
        filas = self._resultado.filas
        if solo_ok:
            filas = [f for f in filas if f["estado"] == "OK"]
        total = len(filas)
        # FASE 4 (memoria): QTableWidget no virtualiza; materializar 62k filas x
        # 17 columnas (~1M QTableWidgetItem) dispara la memoria de la UI y el
        # render. Se muestran como mucho _MAX_FILAS_TABLA; el Excel exportado y
        # el Dashboard siguen reflejando el total completo.
        if total > self._MAX_FILAS_TABLA:
            filas = filas[:self._MAX_FILAS_TABLA]
        self._tabla_detalle.setRowCount(0)
        self._tabla_detalle.setRowCount(len(filas))
        for i, f in enumerate(filas):
            vals = [
                f["fecha"].strftime("%d/%m/%Y"), f["empleado"], f["dni"],
                f["cargo"], f["empresa"], f["ruc"], f["turno"], f["inicio"],
                f["fin"], f["horas_trabajadas"], f["jornada"], f["horas_extras"],
                f["tipo_hora"], f["tarifa"], f["monto"], f["nivel_tarifa"], f["estado"],
            ]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                self._tabla_detalle.setItem(i, j, item)
        if total > self._MAX_FILAS_TABLA:
            self._status.setText(
                self._status.text() + f"  · Detalle: mostrando {len(filas):,} de {total:,} filas (el Excel exporta el total).")

    def _exportar(self):
        if not self._resultado:
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar reporte", "Horas_Extras_Masiva.xlsx", "Excel (*.xlsx)")
        if not ruta:
            return
        # si hay cálculo en curso, no exportar a la vez (evita presión y confusión)
        if self._ocupado:
            return
        self._ocupado = True
        for btn in (getattr(self, "btn_exportar", None),
                    getattr(self, "btn_exportar_proceso", None),
                    getattr(self, "btn_calcular", None)):
            if btn is not None:
                btn.setEnabled(False)
        self._status.setText("Generando Excel…")
        self._progreso.setRange(0, 0)
        self._progreso.show()
        self._tiempo_inicio = time.perf_counter()
        self._worker_exp = _ExportarThread(self._resultado, self._cfg, ruta, self)
        self._worker_exp.finalizado.connect(self._on_exportado)
        self._worker_exp.finished.connect(lambda w=self._worker_exp: self._on_exp_finished(w))
        _registrar_thread(self._worker_exp)
        self._worker_exp.start()

    def _on_exp_finished(self, worker):
        _desregistrar_thread(worker)
        self._worker_exp = None

    def _on_exportado(self, ok, msg):
        self._ocupado = False
        self._progreso.hide()
        t = time.perf_counter() - self._tiempo_inicio
        self.btn_calcular.setEnabled(True)
        self.btn_exportar.setEnabled(self._resultado is not None)
        self.btn_exportar_proceso.setEnabled(self._resultado is not None)
        if ok:
            self._status.setText(f"Reporte exportado correctamente en {t:.2f}s.")
            QMessageBox.information(self, "Éxito", f"Reporte exportado en:\n{msg}")
        else:
            self._status.setText("Error al exportar.")
            QMessageBox.critical(self, "Error", "No se pudo exportar:\n%s" % msg)

    # ------------------------------------------------------------------ teardown seguro
    def shutdown(self) -> None:
        """Espera a que terminen los threads activos antes de destruir el widget."""
        for w in (self._worker, self._worker_exp):
            if w is not None and w.isRunning():
                logger.info("Esperando finalización de worker antes de destruir widget…")
                w.wait(8000)

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)


def create_widget(parent: QWidget | None = None) -> QWidget:
    return HorasExtrasMasivaWidget(parent)
