import os
import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel, QFrame, QMessageBox, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class ChartStudio(QWidget):
    """Estudio de generación de gráficos estadísticos basados en la selección de la tabla"""
    def __init__(self, parent_table, colores):
        super().__init__()
        self.parent_table = parent_table
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.inicializar_ui()

    def inicializar_ui(self):
        self.setStyleSheet(f"background-color: {self.colores['bg_secundario']}; color: white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Título
        lbl_title = QLabel("📊 ESTUDIO DE GRÁFICOS")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']}; border: none; background: transparent;")
        layout.addWidget(lbl_title)

        # Controles
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet("background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;")
        ctrl_lay = QVBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(10, 10, 10, 10)
        ctrl_lay.setSpacing(8)

        lbl_type = QLabel("TIPO DE GRÁFICO:")
        lbl_type.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_type.setStyleSheet("color: rgba(255,255,255,0.6); border: none;")
        ctrl_lay.addWidget(lbl_type)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["Líneas", "Barras", "Dispersión (Scatter)", "Tarta (Pie)"])
        self.combo_type.setFont(QFont(self.font_family, 9))
        self.combo_type.setFixedHeight(30)
        self.combo_type.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 6px; padding-left: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
                border: 1px solid rgba(255,255,255,0.1);
            }}
        """)
        ctrl_lay.addWidget(self.combo_type)

        # Botón Generar
        self.btn_generate = QPushButton("📈 GENERAR GRÁFICO")
        self.btn_generate.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_generate.setFixedHeight(34)
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white; border-radius: 6px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores.get('acento_hover', '#4F46E5')}; }}
        """)
        self.btn_generate.clicked.connect(self.generar_grafico)
        ctrl_lay.addWidget(self.btn_generate)

        layout.addWidget(ctrl_card)

        # Lienzo (Lugar del gráfico)
        self.graph_container = QVBoxLayout()
        self.graph_container.setSpacing(0)
        
        if not MATPLOTLIB_AVAILABLE:
            lbl_error = QLabel("Matplotlib no está disponible.\nEjecuta 'pip install matplotlib' para habilitar esta función.")
            lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_error.setStyleSheet("color: #F87171; border: 1px dashed #F87171; padding: 20px; border-radius: 8px;")
            lbl_error.setWordWrap(True)
            self.graph_container.addWidget(lbl_error)
            self.canvas = None
        else:
            self.fig, self.ax = plt.subplots(figsize=(4, 3))
            self.canvas = FigureCanvas(self.fig)
            self.fig.patch.set_facecolor(self.colores["bg_secundario"])
            self.graph_container.addWidget(self.canvas)
            self._config_ax()

        layout.addLayout(self.graph_container, 1)

        # Botones de exportación
        if MATPLOTLIB_AVAILABLE:
            h_export = QHBoxLayout()
            h_export.setSpacing(10)

            btn_copy = QPushButton("📋 Copiar")
            btn_copy.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn_copy.setFixedHeight(32)
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; border-radius: 6px; border: none;")
            btn_copy.clicked.connect(self.copiar_grafico)
            h_export.addWidget(btn_copy, 1)

            btn_save = QPushButton("💾 Guardar")
            btn_save.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn_save.setFixedHeight(32)
            btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_save.setStyleSheet(f"background-color: {self.colores['bg_terciario']}; color: white; border-radius: 6px; border: none;")
            btn_save.clicked.connect(self.guardar_grafico)
            h_export.addWidget(btn_save, 1)

            layout.addLayout(h_export)

    def _config_ax(self):
        if not MATPLOTLIB_AVAILABLE: return
        self.ax.set_facecolor(self.colores["bg_principal"])
        self.ax.tick_params(colors=self.colores["fg_secundario"], labelsize=8)
        self.ax.grid(True, color="white", alpha=0.04, linestyle=":", linewidth=0.5)
        for spine in ["top", "right"]:
            self.ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            self.ax.spines[spine].set_color((1, 1, 1, 0.1))

    def generar_grafico(self):
        if not MATPLOTLIB_AVAILABLE:
            QMessageBox.warning(self, "Matplotlib", "La librería Matplotlib no está instalada.")
            return

        ranges = self.parent_table.selectedRanges()
        if not ranges:
            QMessageBox.warning(self, "Selección vacía", "Selecciona primero un rango de celdas en la hoja.")
            return

        r = ranges[0]
        top, bottom = r.topRow(), r.bottomRow()
        left, right = r.leftColumn(), r.rightColumn()

        # Extraer datos de la selección
        x_data = []
        y_data_series = [] # Lista de listas para múltiples columnas de datos

        num_cols = right - left + 1
        num_rows = bottom - top + 1

        if num_rows < 1 or num_cols < 1:
            return

        # Intentar parsear las celdas
        try:
            for row in range(top, bottom + 1):
                # Eje X
                x_item = self.parent_table.item(row, left)
                x_val = x_item.text().strip() if x_item else f"Fila {row+1}"
                x_data.append(x_val)

                # Ejes Y
                for col_idx in range(1, num_cols):
                    col = left + col_idx
                    if len(y_data_series) < col_idx:
                        y_data_series.append([])
                    
                    y_item = self.parent_table.item(row, col)
                    y_str = y_item.text().strip() if y_item else "0"
                    try:
                        y_val = float(y_str.replace(',', '.'))
                    except ValueError:
                        y_val = 0.0
                    y_data_series[col_idx-1].append(y_val)
        except Exception as e:
            QMessageBox.critical(self, "Error de Datos", f"No se pudieron leer los datos seleccionados: {e}")
            return

        # Si sólo se seleccionó una sola columna, mapear filas como X y valores de la columna como Y
        if num_cols == 1:
            y_data_series = [[]]
            x_data = []
            for idx, row in enumerate(range(top, bottom + 1)):
                x_data.append(f"F{row+1}")
                y_item = self.parent_table.item(row, left)
                y_str = y_item.text().strip() if y_item else "0"
                try:
                    y_val = float(y_str.replace(',', '.'))
                except ValueError:
                    y_val = 0.0
                y_data_series[0].append(y_val)

        # Graficar
        self.ax.clear()
        self._config_ax()

        chart_type = self.combo_type.currentText()
        palette = [self.colores["acento"], self.colores["exito"], self.colores["advertencia"], self.colores["error"], "#F43F5E", "#10B981", "#3B82F6"]

        import numpy as np
        x_indices = np.arange(len(x_data))

        try:
            if "Líneas" in chart_type:
                for idx, y_data in enumerate(y_data_series):
                    color = palette[idx % len(palette)]
                    self.ax.plot(x_indices, y_data, marker='o', markersize=4, color=color, linewidth=2, label=f"Serie {idx+1}")
                    if len(x_indices) > 0:
                        self.ax.fill_between(x_indices, y_data, color=color, alpha=0.1)
                self.ax.set_xticks(x_indices)
                self.ax.set_xticklabels(x_data, rotation=15, ha='right')
                self.ax.legend(frameon=False, labelcolor="white", fontsize=8)

            elif "Barras" in chart_type:
                width = 0.8 / len(y_data_series)
                for idx, y_data in enumerate(y_data_series):
                    color = palette[idx % len(palette)]
                    self.ax.bar(x_indices + idx * width - (width * (len(y_data_series)-1)/2), y_data, width, color=color, label=f"Serie {idx+1}")
                self.ax.set_xticks(x_indices)
                self.ax.set_xticklabels(x_data, rotation=15, ha='right')
                self.ax.legend(frameon=False, labelcolor="white", fontsize=8)

            elif "Dispersión" in chart_type:
                for idx, y_data in enumerate(y_data_series):
                    color = palette[idx % len(palette)]
                    self.ax.scatter(x_indices, y_data, color=color, s=50, alpha=0.8, label=f"Serie {idx+1}")
                self.ax.set_xticks(x_indices)
                self.ax.set_xticklabels(x_data, rotation=15, ha='right')
                self.ax.legend(frameon=False, labelcolor="white", fontsize=8)

            elif "Tarta" in chart_type:
                # Usar la primera serie de datos Y
                y_data = y_data_series[0]
                # Filtrar valores negativos de la tarta
                y_data_clean = [max(v, 0.0) for v in y_data]
                if sum(y_data_clean) == 0:
                    y_data_clean = [1.0] * len(y_data_clean)
                
                self.ax.pie(
                    y_data_clean, labels=x_data, colors=palette,
                    autopct='%1.1f%%', textprops={'color': 'white', 'fontsize': 8},
                    wedgeprops={'edgecolor': self.colores["bg_principal"], 'linewidth': 1, 'antialiased': True}
                )

            try:
                self.fig.tight_layout()
            except:
                pass
            self.canvas.draw()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Matplotlib Error")
            msg.setText(f"Ocurrió un error al renderizar el gráfico:\n\n{e}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setStyleSheet(f"""
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
            msg.exec()

    def copiar_grafico(self):
        if not MATPLOTLIB_AVAILABLE or self.canvas is None: return
        pixmap = self.canvas.grab()
        QApplication.clipboard().setPixmap(pixmap)
        QMessageBox.information(self, "Estudio de Gráficos", "El gráfico ha sido copiado al portapapeles como imagen.")

    def guardar_grafico(self):
        if not MATPLOTLIB_AVAILABLE or self.canvas is None: return
        from PyQt6.QtWidgets import QFileDialog
        path, ok = QFileDialog.getSaveFileName(self, "Guardar Gráfico", "grafico.png", "PNG Imagen (*.png)")
        if ok and path:
            try:
                self.fig.savefig(path, facecolor=self.fig.get_facecolor(), edgecolor='none', dpi=200)
                QMessageBox.information(self, "Estudio de Gráficos", f"Gráfico guardado con éxito en:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar la imagen: {e}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background-color: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white;")
