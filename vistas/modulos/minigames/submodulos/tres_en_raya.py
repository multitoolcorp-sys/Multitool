"""
Tres en Raya (Tic-Tac-Toe) — Submódulo MiniGames
Modo Jugador vs. IA y 2 Jugadores, con puntuación guardada (solo vs IA) y layout responsivo.
"""
import random
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QFrame, QComboBox, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from ..utils.score_manager import ScoreManager


class TabTresEnRaya(QWidget):
    VACIO = ""
    X = "X"
    O = "O"

    GANADORAS = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Filas
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columnas
        [0, 4, 8], [2, 4, 6],              # Diagonales
    ]

    def __init__(self, parent=None, colores=None, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        self.ruta_usuario = Path(ruta_usuario or ".")
        self.score_manager = ScoreManager(self.ruta_usuario)

        self.tablero = [self.VACIO] * 9
        self.turno_actual = self.X
        self.partida_activa = False
        self.modo = "ia"          # "ia" | "2j"
        self.dificultad = "dificil"  # "facil" | "dificil"
        self.marcador = {"X": 0, "O": 0, "Empate": 0}

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

        # Header y Puntuación
        top_hdr = QHBoxLayout()
        lbl_titulo = QLabel("✕ TRES EN RAYA ○")
        lbl_titulo.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        top_hdr.addWidget(lbl_titulo)
        top_hdr.addStretch()

        self.lbl_puntos = QLabel(f"🏆 Puntos: {self.score_manager.get_puntos('tres_en_raya')}")
        self.lbl_puntos.setStyleSheet(f"color: {self.colores['advertencia']}; font-weight: bold; font-size: 13px; background: rgba(251,191,36,0.1); padding: 4px 12px; border-radius: 12px; border: 1px solid rgba(251,191,36,0.2);")
        top_hdr.addWidget(self.lbl_puntos)
        main.addLayout(top_hdr)

        # Configuración
        cfg = QHBoxLayout()
        cfg.setSpacing(10)

        lbl_modo = QLabel("Modo:")
        lbl_modo.setStyleSheet("color: #AAA; font-size: 11px;")
        cfg.addWidget(lbl_modo)
        self.combo_modo = QComboBox()
        self.combo_modo.addItems(["🤖 Jugador vs. IA (Gana Puntos)", "👥 Jugador vs. Jugador"])
        self.combo_modo.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 6px; padding: 4px 8px; border: none;")
        self.combo_modo.currentIndexChanged.connect(self._cambiar_modo)
        cfg.addWidget(self.combo_modo)

        lbl_dif = QLabel("Dificultad:")
        lbl_dif.setStyleSheet("color: #AAA; font-size: 11px;")
        cfg.addWidget(lbl_dif)
        self.combo_dif = QComboBox()
        self.combo_dif.addItems(["😅 Fácil (+5 pts)", "🧠 Difícil (+10 pts)"])
        self.combo_dif.setCurrentIndex(1)
        self.combo_dif.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 6px; padding: 4px 8px; border: none;")
        self.combo_dif.currentIndexChanged.connect(self._cambiar_dificultad)
        cfg.addWidget(self.combo_dif)
        cfg.addStretch()
        main.addLayout(cfg)

        # Marcador
        marc = QHBoxLayout()
        marc.setSpacing(8)
        self.lbl_marc_x = self._crear_marcador("❌ X", "#EF4444")
        self.lbl_emp = self._crear_marcador("🤝 Empate", "#FBBF24")
        self.lbl_marc_o = self._crear_marcador("⭕ O", "#34D399")
        marc.addWidget(self.lbl_marc_x)
        marc.addWidget(self.lbl_emp)
        marc.addWidget(self.lbl_marc_o)
        main.addLayout(marc)

        # Estado del juego
        self.lbl_estado = QLabel("Presiona ▶ Nueva Partida para empezar")
        self.lbl_estado.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_estado.setStyleSheet(f"color: {self.colores['fg_principal']};")
        main.addWidget(self.lbl_estado)

        # Tablero 3x3 responsivo
        tablero_frame = QFrame()
        tablero_frame.setMaximumSize(320, 320)
        tablero_frame.setMinimumSize(240, 240)
        tablero_frame.setStyleSheet(f"""
            QFrame {{ background: {self.colores['bg_secundario']};
                border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); }}
        """)
        grid = QGridLayout(tablero_frame)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(6)

        self.btns = []
        for i in range(9):
            btn = QPushButton("")
            btn.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QPushButton().sizePolicy())
            btn.setMinimumSize(70, 70)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['bg_terciario']};
                    border-radius: 8px; border: none; color: white;
                }}
                QPushButton:hover:enabled {{ background: rgba(99,102,241,0.2); }}
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            btn.setEnabled(False)
            grid.addWidget(btn, i // 3, i % 3)
            self.btns.append(btn)

        cont = QHBoxLayout()
        cont.addStretch()
        cont.addWidget(tablero_frame)
        cont.addStretch()
        main.addLayout(cont)

        # Botón Nueva Partida
        self.btn_nueva = QPushButton("▶ Nueva Partida")
        self.btn_nueva.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_nueva.setFixedHeight(40)
        self.btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nueva.setStyleSheet(f"""
            QPushButton {{ background: {self.colores['acento']}; color: white; border-radius: 8px; border: none; }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_nueva.clicked.connect(self.nueva_partida)
        main.addWidget(self.btn_nueva)

        scroll.setWidget(content)
        root_lay.addWidget(scroll)

    def _crear_marcador(self, texto, color):
        frame = QFrame()
        frame.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 8px;")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 4, 10, 4)
        lbl_n = QLabel(texto)
        lbl_n.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; background: transparent;")
        lbl_n.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_v = QLabel("0")
        lbl_v.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_v.setStyleSheet("color: white; background: transparent;")
        lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_n)
        lay.addWidget(lbl_v)
        frame.lbl_valor = lbl_v
        return frame

    def _cambiar_modo(self, idx):
        self.modo = "ia" if idx == 0 else "2j"
        self.combo_dif.setEnabled(idx == 0)
        self.nueva_partida()

    def _cambiar_dificultad(self, idx):
        self.dificultad = "facil" if idx == 0 else "dificil"

    def nueva_partida(self):
        self.tablero = [self.VACIO] * 9
        self.turno_actual = self.X
        self.partida_activa = True
        for btn in self.btns:
            btn.setText("")
            btn.setEnabled(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.colores['bg_terciario']};
                    border-radius: 8px; border: none; color: white;
                }}
                QPushButton:hover:enabled {{ background: rgba(99,102,241,0.2); }}
            """)
        self._actualizar_estado()

    def _actualizar_estado(self):
        if self.modo == "ia":
            texto = f"Turno: {'Tú (❌ X)' if self.turno_actual == self.X else '🤖 IA (⭕ O)'}"
        else:
            texto = f"Turno: {'❌ Jugador X' if self.turno_actual == self.X else '⭕ Jugador O'}"
        self.lbl_estado.setText(texto)
        self.lbl_estado.setStyleSheet(f"color: {'#EF4444' if self.turno_actual == self.X else '#34D399'}; font-size: 13px; font-weight: bold;")

    def _on_click(self, idx):
        if not self.partida_activa or self.tablero[idx] != self.VACIO:
            return
        if self.modo == "ia" and self.turno_actual == self.O:
            return
        self._colocar(idx, self.turno_actual)
        ganador = self._verificar_ganador()
        if ganador is not None:
            self._finalizar(ganador)
            return
        self.turno_actual = self.O if self.turno_actual == self.X else self.X
        self._actualizar_estado()
        if self.modo == "ia" and self.turno_actual == self.O and self.partida_activa:
            QTimer.singleShot(350, self._turno_ia)

    def _colocar(self, idx, jugador):
        self.tablero[idx] = jugador
        btn = self.btns[idx]
        btn.setText("❌" if jugador == self.X else "⭕")
        color = "#EF4444" if jugador == self.X else "#34D399"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.15);
                border-radius: 8px; border: 2px solid {color}; color: white;
            }}
        """)
        btn.setEnabled(False)

    def _turno_ia(self):
        if not self.partida_activa:
            return
        if self.dificultad == "dificil":
            movimiento = self._minimax_mejor()
        else:
            movimiento = self._ia_facil()
        if movimiento is not None:
            self._colocar(movimiento, self.O)
            ganador = self._verificar_ganador()
            if ganador is not None:
                self._finalizar(ganador)
                return
            self.turno_actual = self.X
            self._actualizar_estado()

    def _ia_facil(self):
        libres = [i for i, v in enumerate(self.tablero) if v == self.VACIO]
        if not libres:
            return None
        if random.random() < 0.4:
            return self._minimax_mejor() if random.random() < 0.5 else random.choice(libres)
        return random.choice(libres)

    def _minimax_mejor(self):
        mejor_score = float("-inf")
        mejor_mov = None
        for i in range(9):
            if self.tablero[i] == self.VACIO:
                self.tablero[i] = self.O
                score = self._minimax(0, False, float("-inf"), float("inf"))
                self.tablero[i] = self.VACIO
                if score > mejor_score:
                    mejor_score = score
                    mejor_mov = i
        return mejor_mov

    def _minimax(self, profundidad, maximizando, alpha, beta):
        estado = self._verificar_ganador_logica()
        if estado is not None:
            return {"X": -10, "O": 10, "empate": 0}[estado] - profundidad if estado != "empate" else 0

        if maximizando:
            mejor = float("-inf")
            for i in range(9):
                if self.tablero[i] == self.VACIO:
                    self.tablero[i] = self.O
                    mejor = max(mejor, self._minimax(profundidad + 1, False, alpha, beta))
                    self.tablero[i] = self.VACIO
                    alpha = max(alpha, mejor)
                    if beta <= alpha:
                        break
            return mejor
        else:
            peor = float("inf")
            for i in range(9):
                if self.tablero[i] == self.VACIO:
                    self.tablero[i] = self.X
                    peor = min(peor, self._minimax(profundidad + 1, True, alpha, beta))
                    self.tablero[i] = self.VACIO
                    beta = min(beta, peor)
                    if beta <= alpha:
                        break
            return peor

    def _verificar_ganador_logica(self):
        for combo in self.GANADORAS:
            a, b, c = combo
            if self.tablero[a] and self.tablero[a] == self.tablero[b] == self.tablero[c]:
                return self.tablero[a]
        if self.VACIO not in self.tablero:
            return "empate"
        return None

    def _verificar_ganador(self):
        for combo in self.GANADORAS:
            a, b, c = combo
            if self.tablero[a] and self.tablero[a] == self.tablero[b] == self.tablero[c]:
                self._resaltar_ganadoras(combo)
                return self.tablero[a]
        if self.VACIO not in self.tablero:
            return "empate"
        return None

    def _resaltar_ganadoras(self, combo):
        for i in combo:
            self.btns[i].setStyleSheet(f"""
                QPushButton {{
                    background: rgba(99,102,241,0.35);
                    border-radius: 8px; border: 2px solid {self.colores['acento']}; color: white;
                }}
            """)

    def _finalizar(self, resultado):
        self.partida_activa = False
        for btn in self.btns:
            btn.setEnabled(False)

        if resultado == "empate":
            self.marcador["Empate"] += 1
            self.lbl_estado.setText("🤝 ¡EMPATE!")
            self.lbl_estado.setStyleSheet("color: #FBBF24; font-size: 15px; font-weight: bold;")
            self.lbl_emp.lbl_valor.setText(str(self.marcador["Empate"]))
        else:
            self.marcador[resultado] += 1
            if self.modo == "ia":
                if resultado == self.X:
                    pts = 10 if self.dificultad == "dificil" else 5
                    total = self.score_manager.sumar_puntos("tres_en_raya", pts)
                    self.lbl_puntos.setText(f"🏆 Puntos: {self.score_manager.get_puntos('tres_en_raya')}")
                    msg = f"🎉 ¡¡GANASTE!! (+{pts} PTS)"
                else:
                    msg = "🤖 IA Gana"
            else:
                msg = f"¡{'❌ X' if resultado == self.X else '⭕ O'} Gana! 🎉"
            self.lbl_estado.setText(msg)
            color = "#EF4444" if resultado == self.X else "#34D399"
            self.lbl_estado.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")
            if resultado == self.X:
                self.lbl_marc_x.lbl_valor.setText(str(self.marcador["X"]))
            else:
                self.lbl_marc_o.lbl_valor.setText(str(self.marcador["O"]))
