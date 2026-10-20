import random
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..utils.score_manager import ScoreManager

PALABRAS_DEFAULT = [
    "PYTHON PROGRAMACION", "INTELIGENCIA ARTIFICIAL", "TECLADO MECANICO",
    "SUPER MARIO BROS", "MINECRAFT SURVIVAL", "DESARROLLO DE SOFTWARE"
]

HANGMAN_STAGES = [
    """
       +---+
       |   |
           |
           |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
           |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
       |   |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|   |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
      /    |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
      / \\  |
           |
    =========
    """
]

class TabAhorcado(QWidget):
    """Submódulo Juego del Ahorcado con palabra personalizada, sin teclado virtual y horca arriba"""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.palabra_secreta = ""
        self.letras_usadas = set()
        self.intentos_fallidos = 0
        self.max_fallos = 6

        self.inicializar_ui()
        self.nuevo_juego()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        lbl_tit = QLabel("🔤 JUEGO DEL AHORCADO")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        hdr.addWidget(lbl_tit)

        hdr.addStretch()

        btn_new = QPushButton("🔄 Nueva Palabra Aleatoria")
        btn_new.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setStyleSheet(f"background: {exito}; color: white; border-radius: 6px; padding: 6px 14px; border: none;")
        btn_new.clicked.connect(self.nuevo_juego)
        hdr.addWidget(btn_new)

        layout.addLayout(hdr)

        # Barra de palabra personalizada
        word_box = QFrame()
        word_box.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 10px 15px;")
        w_lay = QHBoxLayout(word_box)
        w_lay.addWidget(QLabel("✍️ Definir palabra/frase propia:", font=QFont(self.font_family, 9, QFont.Weight.Bold)))
        
        self.txt_custom_word = QLineEdit()
        self.txt_custom_word.setPlaceholderText("Escribe la palabra secreta (ej. SUPER MARIO BROS)...")
        self.txt_custom_word.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_custom_word.setFont(QFont(self.font_family, 9))
        self.txt_custom_word.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px;")
        self.txt_custom_word.returnPressed.connect(self._fijar_palabra_custom)
        w_lay.addWidget(self.txt_custom_word, 1)

        btn_set = QPushButton("🔒 Fijar Palabra")
        btn_set.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_set.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        btn_set.clicked.connect(self._fijar_palabra_custom)
        w_lay.addWidget(btn_set)

        layout.addWidget(word_box)

        # Horca ARRIBA
        self.lbl_horca = QLabel(HANGMAN_STAGES[0])
        self.lbl_horca.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.lbl_horca.setStyleSheet("color: #F87171;")
        self.lbl_horca.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_horca)

        # Palabra Oculta centrada abajo
        self.lbl_palabra = QLabel("_ _ _ _ _")
        self.lbl_palabra.setFont(QFont("Consolas", 24, QFont.Weight.Bold))
        self.lbl_palabra.setStyleSheet(f"color: {acento}; letter-spacing: 4px;")
        self.lbl_palabra.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_palabra)

        # Input de prueba
        input_box = QFrame()
        input_box.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 10px 15px;")
        i_lay = QHBoxLayout(input_box)
        i_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        i_lay.addWidget(QLabel("🎯 Escribe letra o palabra:", font=QFont(self.font_family, 10, QFont.Weight.Bold)))
        
        self.txt_guess = QLineEdit()
        self.txt_guess.setFixedWidth(180)
        self.txt_guess.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.txt_guess.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_guess.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px;")
        self.txt_guess.returnPressed.connect(self._probar_input)
        i_lay.addWidget(self.txt_guess)

        btn_guess = QPushButton("🎯 Probar")
        btn_guess.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_guess.setStyleSheet(f"background: {exito}; color: white; border-radius: 6px; padding: 6px 16px; border: none;")
        btn_guess.clicked.connect(self._probar_input)
        i_lay.addWidget(btn_guess)

        layout.addWidget(input_box)

        self.lbl_info = QLabel("Fallos: 0 / 6")
        self.lbl_info.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_info.setStyleSheet("color: rgba(255,255,255,0.7);")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_info)

    def nuevo_juego(self):
        self.letras_usadas.clear()
        self.intentos_fallidos = 0
        self.palabra_secreta = random.choice(PALABRAS_DEFAULT).upper()
        self.txt_custom_word.clear()

        self.lbl_horca.setText(HANGMAN_STAGES[0])
        self.lbl_info.setText(f"Fallos: 0 / {self.max_fallos}")
        self._render_palabra()

    def _fijar_palabra_custom(self):
        txt = self.txt_custom_word.text().strip().upper()
        if not txt: return
        self.palabra_secreta = txt
        self.letras_usadas.clear()
        self.intentos_fallidos = 0

        self.lbl_horca.setText(HANGMAN_STAGES[0])
        self.lbl_info.setText(f"¡Palabra personalizada fijada! Fallos: 0 / {self.max_fallos}")
        self._render_palabra()
        QMessageBox.information(self, "Palabra Fijada", "🔒 Tu palabra/frase personalizada ha sido registrada en secreto.")

    def _probar_input(self):
        txt = self.txt_guess.text().strip().upper()
        self.txt_guess.clear()
        if not txt: return

        if len(txt) == 1:
            self._probar_letra(txt)
        else:
            if txt == self.palabra_secreta:
                for c in self.palabra_secreta: self.letras_usadas.add(c)
                self._render_palabra()
                self._comprobar_estado()
            else:
                self.intentos_fallidos += 1
                self.lbl_horca.setText(HANGMAN_STAGES[min(self.intentos_fallidos, 6)])
                self.lbl_info.setText(f"❌ La palabra '{txt}' no es correcta. Fallos: {self.intentos_fallidos} / {self.max_fallos}")
                self._comprobar_estado()

    def _probar_letra(self, letra):
        if letra in self.letras_usadas: return
        self.letras_usadas.add(letra)

        if letra not in self.palabra_secreta:
            self.intentos_fallidos += 1
            self.lbl_horca.setText(HANGMAN_STAGES[min(self.intentos_fallidos, 6)])

        self.lbl_info.setText(f"Fallos: {self.intentos_fallidos} / {self.max_fallos}")
        self._render_palabra()
        self._comprobar_estado()

    def _render_palabra(self):
        display_list = []
        for char in self.palabra_secreta:
            if char == " ":
                display_list.append("  ")
            elif char in self.letras_usadas:
                display_list.append(char)
            else:
                display_list.append("_")
        self.lbl_palabra.setText(" ".join(display_list))

    def _comprobar_estado(self):
        if all(c == " " or c in self.letras_usadas for c in self.palabra_secreta):
            QMessageBox.information(self, "¡Victoria!", f"🎉 ¡Felicidades! Has adivinado la palabra secreta:\n{self.palabra_secreta}")
            try: ScoreManager(self.ruta_usuario).sumar_puntos("ahorcado", 10)
            except Exception: pass
            self.nuevo_juego()
        elif self.intentos_fallidos >= self.max_fallos:
            QMessageBox.critical(self, "Ahorcado", f"💀 ¡Has sido ahorcado! La palabra era:\n{self.palabra_secreta}")
            self.nuevo_juego()
