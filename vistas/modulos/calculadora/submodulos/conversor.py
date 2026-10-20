import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QMessageBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..utils.conversor_logic import ConversorLogic

class TabCalculadoraConversor(QWidget):
    """Interfaz dinámica para conversión de múltiples unidades de medida"""
    def __init__(self, parent, colores, agregar_al_historial_callback):
        super().__init__(parent)
        self.colores = colores
        self.agregar_al_historial = agregar_al_historial_callback
        
        # Fuente adaptable
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"
        self.mono_font = "Consolas" if platform.system() == "Windows" else "Monospace"
        
        self.inicializar_ui()

    def inicializar_ui(self):
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(10, 10, 10, 10)
        self.layout_principal.setSpacing(8)
        
        # --- SELECCIÓN DE CATEGORÍA ---
        cat_card = QFrame()
        cat_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        cat_lay = QVBoxLayout(cat_card)
        cat_lay.setContentsMargins(12, 8, 12, 8)
        
        lbl_tipo = QLabel("CATEGORÍA DE CONVERSIÓN")
        lbl_tipo.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_tipo.setStyleSheet(f"color: {self.colores['acento']}; border: none; ")
        cat_lay.addWidget(lbl_tipo)
        
        self.tipos = [
            "Longitud", "Masa", "Volumen", "Temperatura", "Área", "Tiempo", "Velocidad", "Datos",
            "Divisas", "Bases Numéricas", "Formatos de Color"
        ]
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(self.tipos)
        self.combo_tipo.setFont(QFont(self.font_family, 9))
        self.combo_tipo.setMinimumHeight(32)
        self.combo_tipo.setStyleSheet(self._get_combo_style())
        self.combo_tipo.currentTextChanged.connect(self.actualizar_unidades)
        cat_lay.addWidget(self.combo_tipo)
        
        self.layout_principal.addWidget(cat_card)
        
        # --- PANEL DE ACCIÓN ---
        action_card = QFrame()
        action_card.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        action_lay = QVBoxLayout(action_card)
        action_lay.setContentsMargins(12, 8, 12, 8)
        action_lay.setSpacing(8)
        
        # Valor de entrada
        val_lay = QVBoxLayout()
        lbl_val = QLabel("CANTIDAD A CONVERTIR")
        lbl_val.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        val_lay.addWidget(lbl_val)
        
        self.txt_valor = QLineEdit()
        self.txt_valor.setPlaceholderText("Introduce un valor numérico...")
        self.txt_valor.setFont(QFont(self.mono_font, 10))
        self.txt_valor.setMinimumHeight(32)
        self.txt_valor.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 8px;
                padding-left: 15px;
            }}
            QLineEdit:focus {{ border: 1px solid {self.colores['acento']}; }}
        """)
        self.txt_valor.returnPressed.connect(self.realizar_conversion)
        val_lay.addWidget(self.txt_valor)
        action_lay.addLayout(val_lay)
        
        # Selectores Origen/Destino
        select_lay = QHBoxLayout()
        select_lay.setSpacing(10)
        
        def crear_panel_unidad(titulo):
            v = QVBoxLayout()
            l = QLabel(titulo)
            l.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
            v.addWidget(l)
            c = QComboBox()
            c.setMinimumHeight(32)
            c.setStyleSheet(self._get_combo_style())
            v.addWidget(c)
            return v, c

        v_de, self.combo_origen = crear_panel_unidad("DESDE")
        v_a, self.combo_destino = crear_panel_unidad("HACIA")
        
        select_lay.addLayout(v_de, 1)
        select_lay.addLayout(v_a, 1)
        action_lay.addLayout(select_lay)
        
        # Botón Convertir
        self.btn_convertir = QPushButton("🚀 PROCESAR CONVERSIÓN")
        self.btn_convertir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convertir.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_convertir.setMinimumHeight(34)
        self.btn_convertir.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colores['acento']};
                color: white; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background-color: {self.colores['acento_hover']}; }}
        """)
        self.btn_convertir.clicked.connect(self.realizar_conversion)
        action_lay.addWidget(self.btn_convertir)
        
        self.layout_principal.addWidget(action_card)
        
        # --- RESULTADO PREMIUM ---
        self.res_card = QFrame()
        self.res_card.setMinimumHeight(50)
        self.res_card.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 12px; border: 1px solid {self.colores['exito']}33;")
        res_lay = QVBoxLayout(self.res_card)
        
        self.lbl_resultado = QLabel("El resultado aparecerá aquí")
        self.lbl_resultado.setFont(QFont(self.mono_font, 10, QFont.Weight.Bold))
        self.lbl_resultado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado.setStyleSheet(f"color: {self.colores['exito']}; border: none;")
        res_lay.addWidget(self.lbl_resultado)
        
        self.layout_principal.addWidget(self.res_card)
        self.layout_principal.addStretch()
        
        # Carga inicial
        self.actualizar_unidades(self.tipos[0])

    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background-color: {self.colores['bg_terciario']};
                color: white; border: none; border-radius: 8px;
                padding-left: 12px; 
            }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid white; }}
            QComboBox QAbstractItemView {{
                background-color: {self.colores['bg_secundario']};
                color: white; selection-background-color: {self.colores['acento']};
                border: 1px solid rgba(255,255,255,0.1);
                outline: none; padding: 5px;
            }}
        """

    def actualizar_unidades(self, tipo):
        u = []
        if tipo == "Longitud": u = ["Kilómetro", "Metro", "Centímetro", "Milímetro", "Milla", "Yarda", "Pie", "Pulgada"]
        elif tipo == "Masa": u = ["Tonelada", "Kilogramo", "Gramo", "Miligramo", "Libra", "Onza"]
        elif tipo == "Volumen": u = ["Metro cúbico", "Litro", "Mililitro", "Galón", "Cuarto", "Pinta", "Onza líquida"]
        elif tipo == "Temperatura": u = ["Celsius", "Fahrenheit", "Kelvin"]
        elif tipo == "Área": u = ["Kilómetro cuadrado", "Metro cuadrado", "Centímetro cuadrado", "Milla cuadrada", "Acre", "Pie cuadrado"]
        elif tipo == "Tiempo": u = ["Año", "Mes", "Semana", "Día", "Hora", "Minuto", "Segundo", "Milisegundo"]
        elif tipo == "Velocidad": u = ["Kilómetro por hora", "Metro por segundo", "Milla por hora", "Pie por segundo", "Nudo"]
        elif tipo == "Datos": u = ["Byte", "Kilobyte", "Megabyte", "Gigabyte", "Terabyte", "Petabyte"]
        elif tipo == "Divisas": u = [
            "Dólar Estadounidense (USD)", "Euro (EUR)", "Libra Esterlina (GBP)", "Yen Japonés (JPY)", 
            "Boliviano (BOB)", "Peso Mexicano (MXN)", "Peso Argentino (ARS)", "Real Brasileño (BRL)", 
            "Peso Chileno (CLP)", "Sol Peruano (PEN)", "Peso Colombiano (COP)"
        ]
        elif tipo == "Bases Numéricas": u = ["Decimal (Base 10)", "Binario (Base 2)", "Octal (Base 8)", "Hexadecimal (Base 16)"]
        elif tipo == "Formatos de Color": u = ["HEX (#RRGGBB)", "RGB (R, G, B)", "HSL (H, S%, L%)", "CMYK (C%, M%, Y%, K%)"]
        
        self.combo_origen.clear()
        self.combo_origen.addItems(u)
        self.combo_destino.clear()
        self.combo_destino.addItems(u)
        
        if len(u) > 1: self.combo_destino.setCurrentIndex(1)

    def realizar_conversion(self):
        try:
            val_str = self.txt_valor.text().strip()
            if not val_str: 
                QMessageBox.warning(self, "Valor Requerido", "Por favor ingresa la cantidad que deseas convertir.")
                return
                
            tipo = self.combo_tipo.currentText()
            origen = self.combo_origen.currentText()
            destino = self.combo_destino.currentText()
            
            # Obtener cache_dir del parent
            cache_dir = None
            try:
                p1 = self.parent()
                if p1:
                    p2 = p1.parent()
                    if p2:
                        cache_dir = getattr(p2, "ruta_usuario", None)
            except:
                pass
                
            res = ConversorLogic.convertir(val_str, tipo, origen, destino, cache_dir)
            
            if isinstance(res, (float, int)):
                res_str = f"{res:.8g}"
            else:
                res_str = str(res)
                
            txt = f"{val_str} {origen} ➔ {res_str} {destino}"
            
            self.lbl_resultado.setText(txt)
            self.agregar_al_historial(tipo, txt)
            
        except ValueError as ve:
            QMessageBox.critical(self, "Entrada Inválida", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error de Conversión", f"Ocurrió un problema procesando los datos: {e}")

