import os
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeView, QHBoxLayout, 
    QLineEdit, QPushButton, QLabel, QFrame, QComboBox, QMessageBox, QProgressDialog
)
from PyQt6.QtGui import QFileSystemModel, QFont
from PyQt6.QtCore import Qt, QStorageInfo, QTimer

from ..utils.operation_worker import FileOperationWorker

class TabCommander(QWidget):
    """Submódulo estilo Total Commander con doble panel y transferencia segura"""
    def __init__(self, parent, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.font_family = "Segoe UI" if os.name == 'nt' else "Inter"
        
        # Modelos independientes para cada panel
        self.model_izq = QFileSystemModel()
        self.model_izq.setRootPath("")
        
        self.model_der = QFileSystemModel()
        self.model_der.setRootPath("")
        
        self.inicializar_ui()
        
        # Timer para detección en caliente de unidades sin lag
        self.timer_unidades = QTimer(self)
        self.timer_unidades.timeout.connect(self.refrescar_unidades)
        self.timer_unidades.start(10000)
        
    def inicializar_ui(self):
        self.setStyleSheet(f"""
            QWidget {{ color: {self.colores['fg_principal']}; }}
            QToolTip {{
                background-color: {self.colores['bg_secundario']};
                color: white;
                border: 1px solid {self.colores['acento']};
                padding: 6px 10px;
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # CONTENEDOR PRINCIPAL CON BOTONES CENTRALES
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(8)

        splitter = QSplitter()
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: rgba(255,255,255,0.06);
                width: 1px;
                margin: 8px 0;
            }}
        """)

        # Panel Izquierdo
        self.panel_izq, self.combo_izq, self.tree_izq, self.path_izq = self.crear_panel(self.model_izq, os.path.expanduser("~"))
        # Panel Derecho
        self.panel_der, self.combo_der, self.tree_der, self.path_der = self.crear_panel(self.model_der, os.path.abspath(os.sep))

        # BOTONES ACCIÓN CENTRALES (columna central estrecha)
        mid_frame = QFrame()
        mid_frame.setFixedWidth(46)
        mid_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        mid_actions = QVBoxLayout(mid_frame)
        mid_actions.setSpacing(8)
        mid_actions.setContentsMargins(4, 15, 4, 15)
        mid_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_action_style = f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: rgba(255,255,255,0.9);
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            QPushButton:hover {{
                background: {self.colores['acento']};
                border-color: {self.colores['acento']};
                color: white;
            }}
            QPushButton:pressed {{ background: {self.colores['acento_hover']}; }}
        """

        self.btn_copy_to_der = QPushButton("→")
        self.btn_copy_to_der.setToolTip("Copiar selección → derecha")
        self.btn_copy_to_der.setFixedSize(34, 34)
        self.btn_copy_to_der.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_to_der.setStyleSheet(btn_action_style)
        self.btn_copy_to_der.clicked.connect(lambda: self.ejecutar_transferencia("izq", "der", "copiar"))

        self.btn_copy_to_izq = QPushButton("←")
        self.btn_copy_to_izq.setToolTip("Copiar selección ← izquierda")
        self.btn_copy_to_izq.setFixedSize(34, 34)
        self.btn_copy_to_izq.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_to_izq.setStyleSheet(btn_action_style)
        self.btn_copy_to_izq.clicked.connect(lambda: self.ejecutar_transferencia("der", "izq", "copiar"))

        self.btn_move_to_der = QPushButton("⇒")
        self.btn_move_to_der.setToolTip("Mover selección → derecha")
        self.btn_move_to_der.setFixedSize(34, 34)
        self.btn_move_to_der.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_move_to_der.setStyleSheet(btn_action_style)
        self.btn_move_to_der.clicked.connect(lambda: self.ejecutar_transferencia("izq", "der", "cortar"))

        mid_actions.addStretch()
        mid_actions.addWidget(self.btn_copy_to_der)
        mid_actions.addWidget(self.btn_copy_to_izq)
        mid_actions.addSpacing(8)
        mid_actions.addWidget(self.btn_move_to_der)
        mid_actions.addStretch()

        splitter.addWidget(self.panel_izq)
        splitter.addWidget(self.panel_der)

        main_h_layout.addWidget(splitter, 1)
        main_h_layout.addWidget(mid_frame)

        layout.addLayout(main_h_layout)
        self.refrescar_unidades()

    def ejecutar_transferencia(self, origen_key, destino_key, accion):
        """Lógica de transferencia segura entre paneles"""
        tree_orig = self.tree_izq if origen_key == "izq" else self.tree_der
        model_orig = self.model_izq if origen_key == "izq" else self.model_der
        path_dest = self.path_der if destino_key == "der" else self.path_izq
        
        idx = tree_orig.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Selección", "Por favor seleccione un archivo o carpeta del panel de origen.")
            return
            
        src_path = model_orig.filePath(idx)
        dest_dir = path_dest.text()
        dest_path = os.path.join(dest_dir, os.path.basename(src_path))
        
        if os.path.exists(dest_path):
            res = QMessageBox.warning(self, "Sobrescribir", f"El destino ya existe:\n{dest_path}\n¿Desea sobrescribirlo?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.No: return

        # Diálogo de progreso
        self.prog_dialog = QProgressDialog(f"Transfiriendo a {dest_dir}...", "Cancelar", 0, 100, self)
        self.prog_dialog.setWindowTitle("Procesando Archivos")
        self.prog_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.prog_dialog.setStyleSheet(f"background: {self.colores['bg_principal']}; color: white;")
        self.prog_dialog.setValue(0)

        # Iniciar Worker
        self.worker = FileOperationWorker(src_path, dest_path, accion)
        self.worker.progress.connect(lambda p, m: (self.prog_dialog.setValue(p), self.prog_dialog.setLabelText(m)))
        self.worker.finished.connect(self._finalizar_transferencia)
        self.prog_dialog.canceled.connect(self.worker.terminate)
        self.worker.start()

    def _finalizar_transferencia(self, exito, mensaje):
        self.prog_dialog.setValue(100)
        if exito:
            # Forzar refresco de modelos reasignando el rootPath
            self.model_izq.setRootPath(self.model_izq.rootPath())
            self.model_der.setRootPath(self.model_der.rootPath())
        else:
            QMessageBox.critical(self, "Error", mensaje)

    def crear_panel(self, model, ruta_inicial):
        w = QFrame()
        w.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(8)

        # Header de navegación
        nav_header = QVBoxLayout()
        nav_header.setSpacing(6)

        # Fila 1: Selector de Unidad
        drive_row = QHBoxLayout()
        lbl_drive = QLabel("Unidad:")
        lbl_drive.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_drive.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        combo_drive = QComboBox()
        combo_drive.setFixedHeight(32)
        combo_drive.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_terciario']};
                color: white;
                padding: 4px 10px;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.06);
                font-size: 9pt;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {self.colores['bg_terciario']};
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                selection-background-color: {self.colores['acento']}44;
            }}
        """)
        drive_row.addWidget(lbl_drive)
        drive_row.addWidget(combo_drive, 1)
        nav_header.addLayout(drive_row)

        # Fila 2: Ruta y subir nivel
        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        q_path = QLineEdit(ruta_inicial)
        q_path.setFixedHeight(32)
        q_path.setStyleSheet(f"""
            QLineEdit {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['fg_principal']};
                padding: 0px 10px;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.06);
                font-size: 9pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores['acento']};
                background: {self.colores['bg_principal']};
            }}
        """)
        btn_up = QPushButton("↑")
        btn_up.setFixedSize(32, 32)
        btn_up.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_up.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                color: rgba(255,255,255,0.7);
                border: 1px solid rgba(255,255,255,0.06);
            }}
            QPushButton:hover {{
                background: {self.colores['acento']};
                color: white;
            }}
        """)
        path_row.addWidget(q_path)
        path_row.addWidget(btn_up)
        nav_header.addLayout(path_row)

        l.addLayout(nav_header)

        # Árbol de archivos
        tree = QTreeView()
        tree.setModel(model)
        tree.setRootIndex(model.index(ruta_inicial))
        tree.setSortingEnabled(True)
        tree.setAnimated(True)
        tree.setIndentation(18)
        tree.setHeaderHidden(False)
        tree.setColumnWidth(0, 250)
        tree.setColumnHidden(1, True)
        tree.setColumnHidden(2, True)
        tree.setColumnHidden(3, True)
        tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        tree.setStyleSheet(f"""
            QTreeView {{
                background: transparent;
                border: none;
                outline: none;
                font-size: 9pt;
            }}
            QTreeView::item {{
                padding: 5px 4px;
                border-radius: 4px;
            }}
            QTreeView::item:hover {{
                background: rgba(255,255,255,0.06);
            }}
            QTreeView::item:selected {{
                background: {self.colores['acento']}33;
                color: white;
                border-left: 2px solid {self.colores['acento']};
            }}
            QHeaderView::section {{
                background: {self.colores['bg_terciario']};
                color: {self.colores['fg_secundario']};
                padding: 6px 10px;
                border: none;
                font-size: 8px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.15);
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        l.addWidget(tree)
        
        # Conexiones mejoradas para modo árbol
        def on_selection_changed(selected, deselected):
            indexes = selected.indexes()
            if indexes: q_path.setText(model.filePath(indexes[0]))
                
        def go_up():
            curr = q_path.text()
            p = os.path.dirname(curr)
            if p and p != curr:
                q_path.setText(p)
                tree.setCurrentIndex(model.index(p))
                tree.scrollTo(model.index(p))
                
        def on_enter_path():
            p = q_path.text()
            if os.path.exists(p):
                idx = model.index(p)
                tree.setCurrentIndex(idx)
                tree.scrollTo(idx)
                tree.expand(idx)
                
        def on_drive_changed(index):
            drive_path = combo_drive.itemData(index)
            if drive_path:
                model.setRootPath(drive_path)
                tree.setRootIndex(model.index(drive_path))
                q_path.setText(drive_path)

        tree.selectionModel().selectionChanged.connect(on_selection_changed)
        btn_up.clicked.connect(go_up)
        q_path.returnPressed.connect(on_enter_path)
        combo_drive.currentIndexChanged.connect(on_drive_changed)
        
        return w, combo_drive, tree, q_path

    def refrescar_unidades(self):
        """Detección en caliente ultra-rápida de unidades locales y extraíbles (sin lag)"""
        try:
            from ..utils.drive_detector import obtener_unidades_rapidas
            unidades = obtener_unidades_rapidas()
            actuales = [(texto, ruta) for texto, ruta, _ in unidades]
        except Exception as e:
            print(f"Error al obtener unidades en Commander: {e}")
            actuales = []
        
        if actuales == getattr(self, "_ultimas_unidades_cmd", None):
            return
        self._ultimas_unidades_cmd = actuales

        def actualizar_combo(combo):
            prev_path = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            for text, path in actuales:
                combo.addItem(text, path)
            combo.blockSignals(False)
            
            idx = combo.findData(prev_path)
            if idx != -1: combo.setCurrentIndex(idx)

        actualizar_combo(self.combo_izq)
        actualizar_combo(self.combo_der)
