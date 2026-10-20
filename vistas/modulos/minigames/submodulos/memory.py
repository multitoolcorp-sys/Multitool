"""
Memory / Parejas — Submódulo de MiniGames
Juego de memoria de parejas de cartas/emojis con sistema de puntos y récords.
"""
import random
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from ..utils.score_manager import ScoreManager

EMOJIS = ["🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍒", "🥝", "🥑"]


class MemoryCard(QPushButton):
    def __init__(self, idx, emoji, parent=None):
        super().__init__("❓", parent)
        self.idx = idx
        self.emoji = emoji
        self.volteada = False
        self.emparejada = False
        self.setFixedSize(65, 65)
        self.setFont(QFont("Segoe UI", 22))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: #2D2D3D; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); color: white;
            }
            QPushButton:hover { background: rgba(99,102,241,0.2); }
        """)

    def mostrar(self):
        self.volteada = True
        self.setText(self.emoji)
        self.setStyleSheet("""
            QPushButton {
                background: #1E1E2E; border-radius: 8px; border: 2px solid #6366F1; color: white;
            }
        """)

    def ocultar(self):
        self.volteada = False
        self.setText("❓")
        self.setStyleSheet("""
            QPushButton {
                background: #2D2D3D; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); color: white;
            }
            QPushButton:hover { background: rgba(99,102,241,0.2); }
        """)

    def marcar_pareja(self):
        self.emparejada = True
        self.setEnabled(False)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(52,211,153,0.2); border-radius: 8px; border: 2px solid #34D399; color: white;
            }
        """)


class MemoryGUI(QWidget):
    def __init__(self, parent=None, colores=None, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "advertencia": "#FBBF24"
        }
        self.ruta_usuario = Path(ruta_usuario or ".")
        self.score_manager = ScoreManager(self.ruta_usuario)

        self.movimientos = 0
        self.parejas_encontradas = 0
        self.primera_carta = None
        self.segunda_carta = None
        self.bloqueado = False
        self.num_parejas = 8
        self._build()

    def _build(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        main = QVBoxLayout(content)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(12)
        main.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header y Puntos
        top_hdr = QHBoxLayout()
        lbl_tit = QLabel("🎴 JUEGO DE MEMORIA (PAREJAS)")
        lbl_tit.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        top_hdr.addWidget(lbl_tit)
        top_hdr.addStretch()

        self.lbl_puntos = QLabel(f"🏆 Puntos: {self.score_manager.get_puntos('memory')}")
        self.lbl_puntos.setStyleSheet(f"color: {self.colores['advertencia']}; font-weight: bold; font-size: 13px; background: rgba(251,191,36,0.1); padding: 4px 12px; border-radius: 12px; border: 1px solid rgba(251,191,36,0.2);")
        top_hdr.addWidget(self.lbl_puntos)
        main.addLayout(top_hdr)

        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        self.lbl_movs = QLabel("Movimientos: 0")
        self.lbl_movs.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        hdr.addWidget(self.lbl_movs)

        self.lbl_parejas = QLabel("Parejas: 0 / 8")
        self.lbl_parejas.setStyleSheet(f"color: {self.colores['exito']}; font-weight: bold; font-size: 12px;")
        hdr.addWidget(self.lbl_parejas)
        hdr.addStretch()

        btn_reiniciar = QPushButton("🔄 Reiniciar")
        btn_reiniciar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reiniciar.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        btn_reiniciar.clicked.connect(self.reiniciar)
        hdr.addWidget(btn_reiniciar)
        main.addLayout(hdr)

        self.grid_frame = QFrame()
        self.grid_frame.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06);")
        self.grid_lay = QGridLayout(self.grid_frame)
        self.grid_lay.setContentsMargins(12, 12, 12, 12)
        self.grid_lay.setSpacing(8)

        cont = QHBoxLayout()
        cont.addStretch()
        cont.addWidget(self.grid_frame)
        cont.addStretch()
        main.addLayout(cont)

        self.lbl_estado = QLabel("¡Encuentra todas las parejas!")
        self.lbl_estado.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_estado.setStyleSheet(f"color: {self.colores['fg_secundario']};")
        main.addWidget(self.lbl_estado)

        scroll.setWidget(content)
        root_lay.addWidget(scroll)

        self.reiniciar()

    def reiniciar(self):
        while self.grid_lay.count() > 0:
            item = self.grid_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.movimientos = 0
        self.parejas_encontradas = 0
        self.primera_carta = None
        self.segunda_carta = None
        self.bloqueado = False
        self.lbl_movs.setText("Movimientos: 0")
        self.lbl_parejas.setText(f"Parejas: 0 / {self.num_parejas}")
        self.lbl_estado.setText("¡Encuentra todas las parejas!")
        self.lbl_estado.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-weight: bold;")

        cartas_emojis = random.sample(EMOJIS, self.num_parejas) * 2
        random.shuffle(cartas_emojis)

        self.cartas = []
        for i, emoji in enumerate(cartas_emojis):
            card = MemoryCard(i, emoji, self)
            card.clicked.connect(lambda checked, c=card: self._on_card_click(c))
            self.cartas.append(card)
            self.grid_lay.addWidget(card, i // 4, i % 4)

    def _on_card_click(self, card):
        if self.bloqueado or card.volteada or card.emparejada:
            return

        card.mostrar()

        if self.primera_carta is None:
            self.primera_carta = card
        else:
            self.segunda_carta = card
            self.movimientos += 1
            self.lbl_movs.setText(f"Movimientos: {self.movimientos}")

            if self.primera_carta.emoji == self.segunda_carta.emoji:
                self.primera_carta.marcar_pareja()
                self.segunda_carta.marcar_pareja()
                self.parejas_encontradas += 1
                self.lbl_parejas.setText(f"Parejas: {self.parejas_encontradas} / {self.num_parejas}")
                self.primera_carta = None
                self.segunda_carta = None

                if self.parejas_encontradas == self.num_parejas:
                    pts = 10 if self.movimientos <= 12 else (7 if self.movimientos <= 16 else 5)
                    self.score_manager.sumar_puntos("memory", pts)
                    self.lbl_puntos.setText(f"🏆 Puntos: {self.score_manager.get_puntos('memory')}")
                    self.lbl_estado.setText(f"🎉 ¡GANASTE en {self.movimientos} movs! (+{pts} pts)")
                    self.lbl_estado.setStyleSheet("color: #34D399; font-size: 14px; font-weight: bold;")
            else:
                self.bloqueado = True
                QTimer.singleShot(800, self._ocultar_pareja)

    def _ocultar_pareja(self):
        if self.primera_carta and self.segunda_carta:
            self.primera_carta.ocultar()
            self.segunda_carta.ocultar()
        self.primera_carta = None
        self.segunda_carta = None
        self.bloqueado = False
