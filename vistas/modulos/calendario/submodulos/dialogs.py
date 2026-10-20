import platform
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget, 
    QLineEdit, QTextEdit, QComboBox, QApplication, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class DetailDialog(QDialog):
    """Diálogo premium para visualizar eventos de un día específico"""
    def __init__(self, parent, fecha, recs, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.fecha = fecha
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.setWindowTitle(f"Agenda - {fecha.strftime('%d/%m/%Y')}")
        self.setMinimumSize(420, 500)
        self.setStyleSheet(f"background-color: {colores['bg_principal']}; color: white;")
        
        self.inicializar_ui(recs)

    def inicializar_ui(self, recs):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # --- CABECERA ---
        header_card = QFrame()
        header_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        header_lay = QVBoxLayout(header_card)
        header_lay.setContentsMargins(15, 10, 15, 10)
        
        lbl_f = QLabel(self.fecha.strftime("%A, %d de %B").upper())
        lbl_f.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_f.setStyleSheet(f"color: {self.colores['acento']}; ")
        lbl_f.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_lay.addWidget(lbl_f)
        layout.addWidget(header_card)
        
        # --- LISTA DE EVENTOS ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        v_cont = QVBoxLayout(container)
        v_cont.setContentsMargins(0, 0, 0, 0)
        v_cont.setSpacing(10)
        
        if not recs:
            lbl_nada = QLabel("No hay eventos programados\npara este día.")
            lbl_nada.setFont(QFont(self.font_family, 9))
            lbl_nada.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_nada.setStyleSheet(f"color: {self.colores['fg_secundario']}; padding: 40px;")
            v_cont.addWidget(lbl_nada)
        else:
            for r in recs:
                card = QFrame()
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {self.colores['bg_secundario']}; 
                        border-radius: 8px; 
                        border: 1px solid rgba(255,255,255,0.03);
                    }}
                    QFrame:hover {{
                        background-color: rgba(255, 255, 255, 0.04);
                        border: 1px solid {self.colores['acento']}33;
                    }}
                """)
                c_lay = QHBoxLayout(card)
                c_lay.setContentsMargins(12, 10, 12, 10)
                c_lay.setSpacing(12)
                
                # Barra lateral indicativa
                cat_color = self.callbacks["get_cat_color"](r.get("categoria", "General"))
                bar = QFrame()
                bar.setFixedWidth(4)
                bar.setStyleSheet(f"background-color: {cat_color}; border-radius: 2px;")
                c_lay.addWidget(bar)
                
                # Información
                txt_lay = QVBoxLayout()
                txt_lay.setSpacing(2)
                lbl_h_t = QLabel(f"{r.get('hora', '00:00')} — {r['titulo']}")
                lbl_h_t.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
                txt_lay.addWidget(lbl_h_t)
                
                if r.get("descripcion"):
                    lbl_d = QLabel(r["descripcion"])
                    lbl_d.setFont(QFont(self.font_family, 8))
                    lbl_d.setStyleSheet(f"color: {self.colores['fg_secundario']};")
                    lbl_d.setWordWrap(True)
                    txt_lay.addWidget(lbl_d)
                c_lay.addLayout(txt_lay, 1)
                
                # Acciones
                act_lay = QHBoxLayout()
                act_lay.setSpacing(6)
                
                btn_edit = QPushButton("✎")
                btn_edit.setToolTip("Editar evento")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet(f"""
                    QPushButton {{
                        color: {self.colores['acento']}; 
                        border: none; 
                        font-size: 14px; 
                        background: transparent;
                        border-radius: 14px;
                        width: 28px;
                        height: 28px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.06);
                    }}
                """)
                btn_edit.clicked.connect(lambda ch, obj=r: self.editar_evento(obj))
                
                btn_del = QPushButton("✕")
                btn_del.setToolTip("Eliminar evento")
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet(f"""
                    QPushButton {{
                        color: {self.colores['error']}; 
                        border: none; 
                        font-size: 14px; 
                        background: transparent;
                        border-radius: 14px;
                        width: 28px;
                        height: 28px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.06);
                    }}
                """)
                btn_del.clicked.connect(lambda ch, rid=r["id"]: self.callbacks["eliminar"](self.fecha, rid, self))
                
                act_lay.addWidget(btn_edit)
                act_lay.addWidget(btn_del)
                c_lay.addLayout(act_lay)
                
                v_cont.addWidget(card)
        
        v_cont.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        
        # --- BOTÓN AÑADIR ---
        self.btn_add = QPushButton("+ NUEVO RECORDATORIO")
        self.btn_add.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.btn_add.setMinimumHeight(38)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        self.btn_add.clicked.connect(self.abrir_form_nuevo)
        layout.addWidget(self.btn_add)

    def abrir_form_nuevo(self):
        self.accept()
        self.callbacks["añadir_recordatorio"](self.fecha)

    def editar_evento(self, r_obj):
        self.accept()
        self.callbacks["ventana_formulario"]("Editar", self.fecha, r_obj)

class FormDialog(QDialog):
    """Diálogo premium para creación y edición de eventos"""
    def __init__(self, parent, modo, fecha, r_obj, colores, callbacks):
        super().__init__(parent)
        self.colores = colores
        self.callbacks = callbacks
        self.fecha = fecha
        self.r_id = r_obj["id"] if r_obj else None
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        
        self.setWindowTitle(f"{modo} Recordatorio")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"background-color: {colores['bg_principal']}; color: white;")
        
        self.inicializar_ui(modo, r_obj)

    def inicializar_ui(self, modo, r_obj):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        
        lbl_head = QLabel(f"{modo.upper()} EVENTO")
        lbl_head.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_head.setStyleSheet(f"color: {self.colores['acento']}; ")
        lbl_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_head)
        
        # Campos de Formulario
        layout.addWidget(self._crear_label("FECHA SELECCIONADA"))
        lbl_f = QLabel(self.fecha.strftime("%d / %m / %Y"))
        lbl_f.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_f.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 8px; padding: 10px; color: white;")
        layout.addWidget(lbl_f)
        
        layout.addWidget(self._crear_label("TÍTULO DEL RECORDATORIO"))
        self.txt_titulo = QLineEdit(r_obj["titulo"] if r_obj else "")
        self.txt_titulo.setPlaceholderText("Ej: Reunión de equipo, Cumpleaños...")
        self.txt_titulo.setMinimumHeight(38)
        self.txt_titulo.setStyleSheet(self._get_field_style())
        layout.addWidget(self.txt_titulo)
        
        row_params = QHBoxLayout()
        v_hora = QVBoxLayout()
        v_hora.addWidget(self._crear_label("HORA (HH:MM)"))
        self.txt_hora = QLineEdit(r_obj.get("hora", "12:00") if r_obj else "12:00")
        self.txt_hora.setMinimumHeight(38)
        self.txt_hora.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_hora.setStyleSheet(self._get_field_style())
        v_hora.addWidget(self.txt_hora)
        row_params.addLayout(v_hora)
        
        v_cat = QVBoxLayout()
        v_cat.addWidget(self._crear_label("CATEGORÍA"))
        self.combo_cat = QComboBox()
        self.combo_cat.addItems(["General", "Trabajo", "Personal", "Importante", "Otro"])
        if r_obj: self.combo_cat.setCurrentText(r_obj.get("categoria", "General"))
        self.combo_cat.setMinimumHeight(38)
        self.combo_cat.setStyleSheet(self._get_combo_style())
        v_cat.addWidget(self.combo_cat)
        row_params.addLayout(v_cat)
        layout.addLayout(row_params)
        
        layout.addWidget(self._crear_label("DESCRIPCIÓN (OPCIONAL)"))
        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("Añade más detalles sobre el evento...")
        if r_obj: self.txt_desc.setText(r_obj.get("descripcion", ""))
        self.txt_desc.setStyleSheet(self._get_field_style())
        self.txt_desc.setFixedHeight(80)
        layout.addWidget(self.txt_desc)
        
        # Checkbox Anual
        self.chk_anual = QCheckBox(" Repetir este evento cada año")
        self.chk_anual.setFont(QFont(self.font_family, 8))
        self.chk_anual.setStyleSheet(f"""
            QCheckBox {{ color: {self.colores['fg_secundario']}; margin-top: 5px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {self.colores['fg_secundario']}; }}
            QCheckBox::indicator:checked {{ background-color: {self.colores['acento']}; border: 1px solid {self.colores['acento']}; }}
        """)
        if r_obj and r_obj.get("anual", False):
            self.chk_anual.setChecked(True)
        layout.addWidget(self.chk_anual)

        # Checkbox Alarma Sonora / Aviso
        self.chk_alarma = QCheckBox(" 🔔 Activar alarma sonora / aviso de notificación")
        self.chk_alarma.setFont(QFont(self.font_family, 8))
        self.chk_alarma.setStyleSheet(self.chk_anual.styleSheet())
        self.chk_alarma.setChecked(r_obj.get("alarma", True) if r_obj else True)
        layout.addWidget(self.chk_alarma)
        
        # Botones de Acción
        btns_lay = QHBoxLayout()
        btns_lay.setSpacing(12)
        
        btn_cancel = QPushButton("CANCELAR")
        btn_cancel.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_cancel.setMinimumHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['bg_terciario']};
                color: white; border-radius: 8px; border: none; padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {self.colores['bg_secundario']}; border: 1px solid rgba(255,255,255,0.1); }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btns_lay.addWidget(btn_cancel)
        
        btn_save = QPushButton("GUARDAR CAMBIOS")
        btn_save.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_save.setMinimumHeight(38)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['exito']};
                color: white; border-radius: 8px; border: none; padding: 0 25px;
            }}
            QPushButton:hover {{ background-color: #279e72; }}
        """)
        btn_save.clicked.connect(self.validar_y_guardar)
        btns_lay.addWidget(btn_save)
        
        layout.addLayout(btns_lay)

    def _crear_label(self, texto):
        lbl = QLabel(texto)
        lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {self.colores['fg_secundario']}; ")
        return lbl

    def _get_field_style(self):
        return f"""
            QWidget {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255, 255, 255, 0.1); 
                border-radius: 8px; padding: 8px;
            }}
            QWidget:focus {{ border: 1px solid {self.colores['acento']}; }}
        """

    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: 1px solid rgba(255, 255, 255, 0.1); 
                border-radius: 8px; padding-left: 8px;
            }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
        """

    def validar_y_guardar(self):
        f_str = self.fecha.strftime("%Y-%m-%d")
        t = self.txt_titulo.text().strip()
        h = self.txt_hora.text().strip()
        c = self.combo_cat.currentText()
        d = self.txt_desc.toPlainText().strip()
        anual = self.chk_anual.isChecked()
        alarma = self.chk_alarma.isChecked()
        
        if not t:
            self.txt_titulo.setFocus()
            self.txt_titulo.setStyleSheet(self.txt_titulo.styleSheet() + f"border-color: {self.colores['error']};")
            return
            
        self.callbacks["guardar"](f_str, t, d, self.r_id, c, h, self, anual, alarma)

class GoToDateDialog(QDialog):
    """Diálogo para saltar rápidamente a una fecha (Año, Mes, Día opcional)"""
    def __init__(self, parent, colores, on_go_callback):
        super().__init__(parent)
        self.colores = colores
        self.on_go = on_go_callback
        self.setWindowTitle("Ir a fecha...")
        self.setFixedWidth(280)
        self.setStyleSheet(f"background-color: {colores['bg_principal']}; color: white;")
        
        import datetime
        hoy = datetime.date.today()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        
        lbl = QLabel("SELECCIONA LA FECHA")
        lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {colores['acento']};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        # Grid para inputs
        grid = QHBoxLayout()
        grid.setSpacing(8)
        
        def create_spin(min_v, max_v, curr, hint):
            from PyQt6.QtWidgets import QSpinBox
            s = QSpinBox()
            s.setRange(min_v, max_v)
            s.setValue(curr)
            s.setMinimumHeight(32)
            s.setStyleSheet(f"""
                QSpinBox {{
                    background: {colores['bg_terciario']}; 
                    color: white; 
                    border-radius: 6px; 
                    padding: 4px 8px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }}
                QSpinBox:focus {{
                    border: 1px solid {colores['acento']};
                }}
            """)
            v_lay = QVBoxLayout()
            v_lay.setSpacing(3)
            lbl_hint = QLabel(hint)
            lbl_hint.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lbl_hint.setStyleSheet(f"color: {colores['fg_secundario']};")
            v_lay.addWidget(lbl_hint)
            v_lay.addWidget(s)
            return s, v_lay

        self.spin_dia, lay_dia = create_spin(0, 31, 0, "Día (opc)")
        self.spin_mes, lay_mes = create_spin(1, 12, hoy.month, "Mes")
        self.spin_año, lay_año = create_spin(1900, 2100, hoy.year, "Año")
        
        grid.addLayout(lay_año)
        grid.addLayout(lay_mes)
        grid.addLayout(lay_dia)
        layout.addLayout(grid)
        
        btn_go = QPushButton("IR A LA FECHA ➔")
        btn_go.setMinimumHeight(36)
        btn_go.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        btn_go.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_go.setStyleSheet(f"""
            QPushButton {{
                background: {colores['acento']}; 
                color: white; 
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {colores['acento_hover']};
            }}
        """)
        btn_go.clicked.connect(self.confirmar)
        layout.addWidget(btn_go)
        
    def confirmar(self):
        d = self.spin_dia.value()
        m = self.spin_mes.value()
        a = self.spin_año.value()
        self.on_go(a, m, d if d > 0 else None)
        self.accept()
