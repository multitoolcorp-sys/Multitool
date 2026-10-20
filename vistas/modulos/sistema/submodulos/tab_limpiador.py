import os
import shutil
import platform
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QFrame, QProgressBar, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath

class DonutChart(QWidget):
    """Gráfico circular personalizado tipo Donut dibujado con QPainter"""
    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {
            "acento": "#6366F1", "exito": "#34D399", "error": "#F87171",
            "bg_secundario": "#1E1E2E", "fg_secundario": "#AAB0B8"
        }
        self.setMinimumSize(220, 220)
        self.data = {}  # Formato: {"Categoría": (bytes, color_hex)}

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h) - 50
        x = (w - size) // 2
        y = (h - size) // 2

        total = sum(val[0] for val in self.data.values())

        if total == 0:
            # Círculo vacío decorativo
            painter.setPen(QPen(QColor(255, 255, 255, 15), 18))
            painter.drawEllipse(x + 9, y + 9, size - 18, size - 18)
            
            font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
            painter.setFont(QFont(font_family, 10, QFont.Weight.Bold))
            painter.setPen(QColor(self.colores.get("fg_secundario", "#AAB0B8")))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sin archivos\npor limpiar")
            return

        start_angle = 90 * 16  # Qt mide en 1/16 de grado, iniciar arriba (90°)
        
        for name, (val, color_hex) in self.data.items():
            if val <= 0: continue
            span_angle = -int((val / total) * 360 * 16)
            
            pen = QPen(QColor(color_hex), 18)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            
            painter.drawArc(x + 9, y + 9, size - 18, size - 18, start_angle, span_angle)
            start_angle += span_angle

        # Leyenda central
        font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        painter.setFont(QFont(font_family, 8, QFont.Weight.Bold))
        painter.setPen(QColor(self.colores.get("fg_secundario", "#AAB0B8")))
        painter.drawText(x, y + size//2 - 15, size, 20, Qt.AlignmentFlag.AlignCenter, "RECUPERABLE")

        total_str = self._format_size(total)
        painter.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(x, y + size//2 + 5, size, 25, Qt.AlignmentFlag.AlignCenter, total_str)

    def _format_size(self, b):
        if b == 0: return "0 B"
        for u in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} PB"


class DiskScannerThread(QThread):
    """Hilo asíncrono para escanear directorios y obtener tamaños"""
    finished = pyqtSignal(dict)

    def __init__(self, categories):
        super().__init__()
        self.categories = categories

    def run(self):
        results = {}
        
        # 1. Temporales de Sistema
        if "temp" in self.categories:
            temp_path = os.environ.get("TEMP") or os.environ.get("TMP")
            results["temp"] = self._get_folder_size(temp_path)
        else:
            results["temp"] = 0

        # 2. Caché de Navegadores
        if "cache" in self.categories:
            results["cache"] = self._get_browser_cache_size()
        else:
            results["cache"] = 0

        # 3. Papelera de Reciclaje
        if "recycle" in self.categories:
            results["recycle"] = self._get_recycle_bin_size()
        else:
            results["recycle"] = 0

        self.finished.emit(results)

    def _get_folder_size(self, path):
        if not path or not os.path.exists(path):
            return 0
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except:
                        pass
        except:
            pass
        return total

    def _get_browser_cache_size(self):
        total = 0
        paths = []
        if platform.system() == "Windows":
            paths.append(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache"))
            paths.append(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"))
        elif platform.system() == "Darwin":
            paths.append(os.path.expanduser("~/Library/Caches/Google/Chrome/Default/Cache"))
        else:
            paths.append(os.path.expanduser("~/.cache/google-chrome/Default/Cache"))

        for p in paths:
            total += self._get_folder_size(p)
        return total

    def _get_recycle_bin_size(self):
        if platform.system() == "Windows":
            try:
                cmd = "Get-ChildItem -Path 'C:\\$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum"
                out = subprocess.check_output(["powershell", "-Command", cmd], text=True)
                for line in out.splitlines():
                    if "Sum" in line and ":" in line:
                        val = line.split(":")[1].strip()
                        if val.isdigit():
                            return int(val)
            except:
                pass
        return 0


class DiskCleanerThread(QThread):
    """Hilo asíncrono para eliminar archivos y liberar espacio"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, categories):
        super().__init__()
        self.categories = categories

    def run(self):
        deleted = 0

        # 1. Temporales
        if "temp" in self.categories:
            self.progress.emit("Limpiando temporales del sistema...")
            temp_path = os.environ.get("TEMP") or os.environ.get("TMP")
            deleted += self._clean_folder(temp_path)

        # 2. Caché de Navegador
        if "cache" in self.categories:
            self.progress.emit("Limpiando caché de navegadores...")
            paths = []
            if platform.system() == "Windows":
                paths.append(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache"))
                paths.append(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"))
            elif platform.system() == "Darwin":
                paths.append(os.path.expanduser("~/Library/Caches/Google/Chrome/Default/Cache"))
            else:
                paths.append(os.path.expanduser("~/.cache/google-chrome/Default/Cache"))

            for p in paths:
                deleted += self._clean_folder(p)

        # 3. Papelera
        if "recycle" in self.categories:
            self.progress.emit("Vaciando papelera de reciclaje...")
            deleted += self._clean_recycle_bin()

        self.finished.emit(deleted)

    def _clean_folder(self, path):
        if not path or not os.path.exists(path): return 0
        total_deleted = 0
        for item in os.listdir(path):
            ip = os.path.join(path, item)
            try:
                if os.path.isdir(ip):
                    sz = self._get_folder_size(ip)
                    shutil.rmtree(ip)
                    total_deleted += sz
                else:
                    sz = os.path.getsize(ip)
                    os.remove(ip)
                    total_deleted += sz
            except:
                pass
        return total_deleted

    def _get_folder_size(self, path):
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    total += os.path.getsize(fp)
        except: pass
        return total

    def _clean_recycle_bin(self):
        if platform.system() == "Windows":
            try:
                # Medir tamaño
                cmd_size = "Get-ChildItem -Path 'C:\\$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum"
                out = subprocess.check_output(["powershell", "-Command", cmd_size], text=True)
                before = 0
                for line in out.splitlines():
                    if "Sum" in line and ":" in line:
                        val = line.split(":")[1].strip()
                        if val.isdigit(): before = int(val)
                
                # Ejecutar comando vaciar
                subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"], capture_output=True)
                return before
            except: pass
        return 0


class TabLimpiador(QWidget):
    """Pestaña de Analizador y Limpiador de Disco"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks

        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.setStyleSheet("color: white;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ── Columna Izquierda: Opciones y Control ──
        left_card = QFrame()
        left_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        left_lay = QVBoxLayout(left_card)
        left_lay.setContentsMargins(20, 20, 20, 20)
        left_lay.setSpacing(15)

        lbl_opt_title = QLabel("SELECCIÓN DE LIMPIEZA")
        lbl_opt_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_opt_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        left_lay.addWidget(lbl_opt_title)

        # Checkboxes
        check_style = """
            QCheckBox { spacing: 10px; font-size: 13px; border: none; background: transparent; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.15); }
            QCheckBox::indicator:unchecked { background-color: #2D2D3D; }
            QCheckBox::indicator:checked { background-color: #6366F1; image: none; border-color: #6366F1; }
        """
        self.cb_temp = QCheckBox("Archivos Temporales del Sistema")
        self.cb_temp.setChecked(True)
        self.cb_temp.setStyleSheet(check_style)
        left_lay.addWidget(self.cb_temp)

        self.cb_cache = QCheckBox("Caché de Navegadores (Chrome / Edge)")
        self.cb_cache.setChecked(True)
        self.cb_cache.setStyleSheet(check_style)
        left_lay.addWidget(self.cb_cache)

        self.cb_recycle = QCheckBox("Papelera de Reciclaje (Windows)")
        self.cb_recycle.setChecked(True)
        self.cb_recycle.setStyleSheet(check_style)
        left_lay.addWidget(self.cb_recycle)

        left_lay.addSpacing(15)

        # Botón Analizar
        self.btn_analizar = QPushButton("🔍  INICIAR ANÁLISIS")
        self.btn_analizar.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_analizar.setFixedHeight(45)
        self.btn_analizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analizar.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; border-color: {self.colores['acento']}; }}
        """)
        self.btn_analizar.clicked.connect(self.iniciar_analisis)
        left_lay.addWidget(self.btn_analizar)

        # Botón Limpiar
        self.btn_limpiar = QPushButton("🧹  LIMPIAR ESPACIO SELECCIONADO")
        self.btn_limpiar.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_limpiar.setFixedHeight(45)
        self.btn_limpiar.setEnabled(False)
        self.btn_limpiar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_limpiar.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(52, 211, 153, 0.1);
                color: #A7F3D0; border-radius: 8px; border: 1px solid rgba(52, 211, 153, 0.2);
            }}
            QPushButton:hover:enabled {{ background-color: {self.colores['exito']}; color: white; border-color: {self.colores['exito']}; }}
            QPushButton:disabled {{ background-color: rgba(255,255,255,0.02); color: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.02); }}
        """)
        self.btn_limpiar.clicked.connect(self.iniciar_limpieza)
        left_lay.addWidget(self.btn_limpiar)

        left_lay.addStretch()

        # Progreso
        self.lbl_status = QLabel("Listo para analizar.")
        self.lbl_status.setFont(QFont(self.font_family, 9))
        self.lbl_status.setStyleSheet("color: rgba(255,255,255,0.6); border: none; background: transparent;")
        left_lay.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background-color: rgba(255,255,255,0.05); border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background-color: {self.colores['acento']}; border-radius: 3px; }}
        """)
        left_lay.addWidget(self.progress)

        layout.addWidget(left_card, 1)

        # ── Columna Derecha: Gráfico Donut ──
        right_card = QFrame()
        right_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        right_lay = QVBoxLayout(right_card)
        right_lay.setContentsMargins(20, 20, 20, 20)
        right_lay.setSpacing(15)

        lbl_graph_title = QLabel("DISTRIBUCIÓN DEL ESPACIO")
        lbl_graph_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_graph_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        right_lay.addWidget(lbl_graph_title)

        self.donut_chart = DonutChart(self, self.colores)
        right_lay.addWidget(self.donut_chart, 1)

        # Leyenda de categorías
        self.lbl_details = QLabel("")
        self.lbl_details.setFont(QFont(self.font_family, 9))
        self.lbl_details.setStyleSheet("color: rgba(255,255,255,0.85); border: none; background: transparent;")
        self.lbl_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_lay.addWidget(self.lbl_details)

        layout.addWidget(right_card, 1)

    def iniciar_analisis(self):
        self.btn_analizar.setEnabled(False)
        self.btn_limpiar.setEnabled(False)
        self.lbl_status.setText("Analizando espacio en disco...")
        self.progress.setRange(0, 0) # Efecto indeterminado

        categories = []
        if self.cb_temp.isChecked(): categories.append("temp")
        if self.cb_cache.isChecked(): categories.append("cache")
        if self.cb_recycle.isChecked(): categories.append("recycle")

        self.scanner = DiskScannerThread(categories)
        self.scanner.finished.connect(self.finalizar_analisis)
        self.scanner.start()

    def finalizar_analisis(self, results):
        self.btn_analizar.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.lbl_status.setText("Análisis finalizado.")

        # Actualizar Donut
        chart_data = {
            "Temporales": (results["temp"], "#6366F1"),
            "Caché": (results["cache"], "#34D399"),
            "Papelera": (results["recycle"], "#F87171")
        }
        self.donut_chart.set_data(chart_data)

        # Actualizar leyenda detallada
        total = sum(results.values())
        if total > 0:
            details = []
            for k, (v, color) in chart_data.items():
                if v > 0:
                    details.append(f"<span style='color:{color};'>●</span> {k}: {self.donut_chart._format_size(v)}")
            self.lbl_details.setText("  •  ".join(details))
            self.btn_limpiar.setEnabled(True)
        else:
            self.lbl_details.setText("No hay archivos para limpiar en las categorías seleccionadas.")
            self.btn_limpiar.setEnabled(False)

    def iniciar_limpieza(self):
        categories = []
        if self.cb_temp.isChecked(): categories.append("temp")
        if self.cb_cache.isChecked(): categories.append("cache")
        if self.cb_recycle.isChecked(): categories.append("recycle")

        if not categories: return

        confirm_msg = QMessageBox(self)
        confirm_msg.setIcon(QMessageBox.Icon.Question)
        confirm_msg.setWindowTitle("Confirmar Limpieza")
        confirm_msg.setText("¿Estás seguro de que deseas eliminar permanentemente los archivos seleccionados?")
        confirm_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {self.colores['bg_secundario']}; }}
            QLabel {{ color: white; }}
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 15px;
                min-width: 70px;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; }}
        """)
        confirm = confirm_msg.exec()
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.btn_analizar.setEnabled(False)
        self.btn_limpiar.setEnabled(False)
        self.progress.setRange(0, 0)

        self.cleaner = DiskCleanerThread(categories)
        self.cleaner.progress.connect(self.lbl_status.setText)
        self.cleaner.finished.connect(self.finalizar_limpieza)
        self.cleaner.start()

    def finalizar_limpieza(self, deleted_bytes):
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.btn_analizar.setEnabled(True)
        self.lbl_status.setText("Limpieza completada.")
        
        size_str = self.donut_chart._format_size(deleted_bytes)
        info_msg = QMessageBox(self)
        info_msg.setIcon(QMessageBox.Icon.Information)
        info_msg.setWindowTitle("Limpieza Completada")
        info_msg.setText(f"Se han liberado con éxito {size_str} de espacio en disco.")
        info_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        info_msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {self.colores['bg_secundario']}; }}
            QLabel {{ color: white; }}
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 15px;
                min-width: 70px;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento']}; }}
        """)
        info_msg.exec()

        # Resetear gráfico
        self.donut_chart.set_data({})
        self.lbl_details.setText("")
