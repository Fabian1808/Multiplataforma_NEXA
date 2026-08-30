from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFileDialog, QListWidget, QMessageBox, QDialog)
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from pathlib import Path
import sys
import shutil
import os

class Worker(QThread):
    finished = Signal(bool, str)
    
    def __init__(self, relatorios, engine_path):
        super().__init__()
        self.relatorios = relatorios
        self.engine_path = engine_path
        
    def run(self):
        try:
            from plugins.asistencia_masiva.engine import main as engine_main
            output_file = engine_main.procesar_masivo(self.relatorios)
            self.finished.emit(True, output_file)
        except Exception as e:
            import traceback
            self.finished.emit(False, str(e) + "\n" + traceback.format_exc())

class PluginWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._relatorios = []
        self._last_excel = None
        self._setup_ui()
        self._engine_path = Path(__file__).parent
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        lbl = QLabel("Reporte Masivo de Asistencia (Rainbow)")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(lbl)
        
        desc = QLabel("Genera un Excel con el consolidado de horas de todo el personal usando los reportes de Rainbow, y alimenta el Dashboard BI.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        btn_add = QPushButton("1. Añadir archivos Rainbow (.xlsx)")
        btn_add.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        btn_add.clicked.connect(self._add_files)
        layout.addWidget(btn_add)
        
        self.list_files = QListWidget()
        self.list_files.setMaximumHeight(100)
        layout.addWidget(self.list_files)
        
        btn_clear = QPushButton("Limpiar lista")
        btn_clear.clicked.connect(self._clear_files)
        layout.addWidget(btn_clear)
        
        # Action Buttons
        self.btn_process = QPushButton("2. Procesar Data")
        self.btn_process.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_process.clicked.connect(self._process)
        layout.addWidget(self.btn_process)
        
        row_actions = QHBoxLayout()
        
        self.btn_download = QPushButton("Descargar Excel")
        self.btn_download.setStyleSheet("background-color: #107C41; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_download.clicked.connect(self._download_excel)
        self.btn_download.setEnabled(False)
        row_actions.addWidget(self.btn_download)
        
        self.btn_bi = QPushButton("Visualizar Dashboard (Nativo)")
        self.btn_bi.setStyleSheet("background-color: #FF5A00; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_bi.clicked.connect(self._open_dashboard)
        row_actions.addWidget(self.btn_bi)
        
        layout.addLayout(row_actions)
        
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        layout.addStretch()
        
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar archivos de Rainbow", "", "Excel (*.xlsx)")
        if files:
            for f in files:
                if f not in self._relatorios:
                    self._relatorios.append(f)
                    self.list_files.addItem(Path(f).name)
                    
    def _clear_files(self):
        self._relatorios.clear()
        self.list_files.clear()
        self.btn_download.setEnabled(False)
        self._last_excel = None
        self.lbl_status.setText("")
        
    def _process(self):
        if not self._relatorios:
            QMessageBox.warning(self, "Aviso", "Añada al menos un archivo Rainbow.")
            return
            
        self.btn_process.setEnabled(False)
        self.btn_download.setEnabled(False)
        self.lbl_status.setText("Procesando archivos y actualizando base de datos BI... Por favor espere.")
        
        self.worker = Worker(self._relatorios, self._engine_path)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
        
    def _on_finished(self, success, result):
        self.btn_process.setEnabled(True)
        if success:
            self._last_excel = result
            self.btn_download.setEnabled(True)
            self.lbl_status.setText("¡Proceso completado! Data lista para descargar o visualizar en BI.")
            QMessageBox.information(self, "Éxito", "El procesamiento finalizó correctamente.\nLa base de datos del Dashboard BI ha sido actualizada.")
        else:
            self.lbl_status.setText("Error en el proceso.")
            QMessageBox.critical(self, "Error", f"Ocurrió un error al procesar:\n{result}")
            
    def _download_excel(self):
        if not self._last_excel or not os.path.exists(self._last_excel):
            QMessageBox.warning(self, "Aviso", "No hay un archivo Excel generado. Procese primero.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte Masivo", "Reporte_Masivo_Asistencia.xlsx", "Excel (*.xlsx)")
        if save_path:
            try:
                shutil.copy2(self._last_excel, save_path)
                QMessageBox.information(self, "Éxito", f"Archivo guardado exitosamente en:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo:\n{e}")

    def _open_dashboard(self):
        try:
            from plugins.asistencia_masiva.engine.native_dashboard import open_dashboard
            open_dashboard(self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el Dashboard Nativo:\n{e}")

def create_widget(parent=None):
    return PluginWidget()
