"""GUI widget de HORAS EXTRAS MASIVA para el Hub (embebido).

Flujo de usuario: Cargar Rainbow / Personal (Relatorio) / Tarifas
-> Calcular -> Revisar KPIs y TOPs -> Exportar Excel (detalle).
Sigue la paleta NEXA (claro/oscuro automático vía Theme).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
    QFrame, QHeaderView, QProgressBar,
)

from hub.ui.common.design import (
    ACCENT, ERROR, WARNING, SUCCESS, Theme, NEXAStyles, KPIWidget, get_font,
)

# ruta al motor
ENGINE_SRC = Path(__file__).resolve().parent.parent / "engine" / "src"
if str(ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(ENGINE_SRC))


class _CalculoThread(QThread):
    finalizado = Signal(bool, str)

    def __init__(self, cfg, fuentes, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.fuentes = fuentes

    def run(self):
        try:
            import config as cmod
            import motor as mmod
            self.cfg = cmod.cargar_config(self.cfg)
            self.resultado = mmod.ejecutar(self.fuentes, self.cfg)
            self.finalizado.emit(True, "")
        except Exception as exc:  # noqa
            import traceback
            self.finalizado.emit(False, str(exc) + "\n" + traceback.format_exc())


class _ExportarThread(QThread):
    """Llama a exportacion en un hilo para no congelar la UI con datos grandes."""

    finalizado = Signal(bool, str)

    def __init__(self, resultado, cfg, ruta, parent=None):
        super().__init__(parent)
        self.resultado = resultado
        self.cfg = cfg
        self.ruta = ruta

    def run(self):
        try:
            import exportacion
            exportacion.exportar(self.resultado, self.ruta, self.cfg or {})
            self.finalizado.emit(True, self.ruta)
        except Exception as exc:  # noqa
            import traceback
            self.finalizado.emit(False, str(exc) + "\n" + traceback.format_exc())


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
        self._setup_ui()

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        titulo = QLabel("Horas Extras Masiva")
        titulo.setFont(get_font(20, bold=True))
        titulo.setStyleSheet(f"color: {Theme.text()}; background: transparent;")
        root.addWidget(titulo)

        desc = QLabel(
            "Procesa marcaciones RAINBOW contra el maestro de personal (RELATORIO) "
            "y el tarifario (TARIFAS) para calcular horas extras valorizadas en soles, "
            "con matching tarifario por niveles de confianza, auditoría y trazabilidad."
        )
        desc.setWordWrap(True)
        desc.setFont(get_font(12))
        desc.setStyleSheet(f"color: {Theme.text_secondary()}; background: transparent;")
        root.addWidget(desc)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("QTabWidget::pane{border:none;}")
        self._tabs.addTab(self._build_tab_proceso(), "Proceso")
        self._tabs.addTab(self._build_tab_detalle(), "Detalle")
        root.addWidget(self._tabs, 1)

        self._progreso = QProgressBar()
        self._progreso.hide()
        root.addWidget(self._progreso)

        self._status = QLabel("Listo. Seleccione los archivos y presione Calcular.")
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

        # Nota: TARIFAS, ÁREAS y GERENCIA ya vienen embebidos en el motor,
        # no hace falta que el usuario los suba.
        nota = self._label(
            "TARIFAS, ÁREAS y GERENCIA están integrados en el módulo (no requiere subirlos).",
            11)
        nota.setStyleSheet(f"color: {Theme.text_muted()}; background: transparent;")
        card_lay.addWidget(nota)

        lay.addWidget(card)

        # ---- botón calcular
        btn_row = QHBoxLayout()
        self.btn_calcular = QPushButton("Calcular Horas Extras Masiva")
        self.btn_calcular.setStyleSheet(NEXAStyles.primary_button())
        self.btn_calcular.setMinimumHeight(42)
        self.btn_calcular.clicked.connect(self._ejecutar)
        btn_row.addWidget(self.btn_calcular)
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
            if n == 1:
                edit.setText(Path(rutas[0]).name)
            else:
                edit.setText("%d archivos RAINBOW seleccionados" % n)
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo", "", "Excel (*.xlsx *.XLSX)")
        if not ruta:
            return
        self._fuentes[key] = ruta
        edit, _btn = self._file_rows[key]
        edit.setText(Path(ruta).name)

    def _ejecutar(self):
        requeridos = {
            "rainbow": "RAINBOW",
            "relatorio": "RELATORIO",
        }
        for key, nombre in requeridos.items():
            if not self._fuentes.get(key):
                QMessageBox.warning(self, "Faltan datos",
                                    f"Seleccione el archivo {nombre}.")
                return
        self.btn_calcular.setEnabled(False)
        self._progreso.setRange(0, 0)
        self._progreso.show()
        self._status.setText("Calculando…")

        import config as cmod
        import motor as mmod
        fuentes = mmod.Fuentes(
            rainbow=self._fuentes["rainbow"],
            relatorio=self._fuentes["relatorio"],
            tarifas=self._fuentes["tarifas"],
            areas=self._fuentes["areas"],
            gerencia=self._fuentes["gerencia"],
        )
        # evitar bloquear UI con th especial; se ejecuta en hilo
        self._worker = _CalculoThread(self._cfg, fuentes, self)
        self._worker.finalizado.connect(self._on_calculo)
        self._worker.start()

    def _on_calculo(self, ok, msg):
        self._progreso.hide()
        self.btn_calcular.setEnabled(True)
        if not ok:
            self._status.setText("Error en el cálculo.")
            QMessageBox.critical(self, "Error", "Ocurrió un error:\n" + msg)
            return
        self._resultado = getattr(self._worker, "resultado", None)
        self._cfg = getattr(self._worker, "cfg", None)
        self._render_kpis()
        self._render_tops()
        self._cargar_tabla_detalle()
        self.btn_exportar.setEnabled(True)
        self.btn_exportar_proceso.setEnabled(True)
        self.btn_detalle_todos.setText("Mostrar todos" if self._resultado.estados.get("ERROR", 0) else "Solo OK")
        self._status.setText(
            f"Proceso completado: {self._resultado.totales['jornadas']} jornadas, "
            f"{self._resultado.horas_extra_total} h de HH.EE., "
            f"{self._resultado.monto_total} de monto total.")
        QMessageBox.information(self, "Éxito",
                                "Cálculo completado con éxito.")

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
        import dashboard
        an = dashboard.Analisis(self._resultado)
        self._llenar_top(self._top_trabajadores, an.top("trabajador"))
        self._llenar_top(self._top_cargos, an.top("cargo"))

    def _llenar_top(self, tabla, datos):
        tabla.setRowCount(0)
        for i, (nombre, v) in enumerate(datos):
            tabla.insertRow(i)
            texto = nombre
            if len(str(texto)) > 34:
                texto = str(texto)[:31] + "…"
            tabla.setItem(i, 0, QTableWidgetItem(str(texto)))
            tabla.setItem(i, 1, QTableWidgetItem(str(v["horas"])))
            tabla.setItem(i, 2, QTableWidgetItem(str(v["monto"])))

    def _cargar_tabla_detalle(self):
        if not self._resultado:
            return
        solo_ok = self.btn_detalle_todos.isChecked()
        filas = self._resultado.filas
        if solo_ok:
            filas = [f for f in filas if f["estado"] == "OK"]
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

    def _exportar(self):
        if not self._resultado:
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar reporte", "Horas_Extras_Masiva.xlsx", "Excel (*.xlsx)")
        if not ruta:
            return
        # Deshabilitar botones y bloquear la tabla mientras se escribe el Excel
        for btn in (getattr(self, "btn_exportar", None),
                    getattr(self, "btn_exportar_proceso", None),
                    getattr(self, "btn_calcular", None)):
            if btn is not None:
                btn.setEnabled(False)
        self._status.setText("Generando Excel…")
        self._progreso.setRange(0, 0)
        self._progreso.show()
        self._worker_exp = _ExportarThread(self._resultado, self._cfg, ruta, self)
        self._worker_exp.finalizado.connect(self._on_exportado)
        self._worker_exp.start()

    def _on_exportado(self, ok, msg):
        self._progreso.hide()
        self.btn_calcular.setEnabled(True)
        self.btn_exportar.setEnabled(self._resultado is not None)
        self.btn_exportar_proceso.setEnabled(self._resultado is not None)
        if ok:
            self._status.setText("Reporte exportado correctamente.")
            QMessageBox.information(self, "Éxito",
                                    f"Reporte exportado en:\n{msg}")
        else:
            self._status.setText("Error al exportar.")
            QMessageBox.critical(self, "Error",
                                 "No se pudo exportar:\n%s" % msg)


def create_widget(parent: QWidget | None = None) -> QWidget:
    return HorasExtrasMasivaWidget(parent)
