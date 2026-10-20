"""
Ajedrez (Chess) — Submódulo de MiniGames
Juego de Ajedrez clásico con piezas unicode, resaltado visual de jaque,
detección estricta de jaque mate y movimientos legales (sin red online).
Modos: Vs IA y 1v1 Local.
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

# Piezas Unicode
WHITE_PIECES = {"P": "♙", "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔"}
BLACK_PIECES = {"p": "♟", "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚"}

PIECE_VALUES = {
    "P": 10, "N": 30, "B": 35, "R": 50, "Q": 90, "K": 900,
    "p": -10, "n": -30, "b": -35, "r": -50, "q": -90, "k": -900
}


class TabAjedrez(QWidget):
    def __init__(self, parent=None, colores=None, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "advertencia": "#FBBF24"
        }
        self.ruta_usuario = Path(ruta_usuario or ".")
        self.score_manager = ScoreManager(self.ruta_usuario)

        self.tablero = self._tablero_inicial()
        self.turno = "W"  # "W" | "B"
        self.seleccionado = None  # (r, c)
        self.movimientos_posibles = []
        self.modo = "ia"   # "ia" | "2j"
        self.partida_activa = False

        self._build()

    def _tablero_inicial(self):
        return [
            ["r", "n", "b", "q", "k", "b", "n", "r"],
            ["p", "p", "p", "p", "p", "p", "p", "p"],
            ["", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", ""],
            ["P", "P", "P", "P", "P", "P", "P", "P"],
            ["R", "N", "B", "Q", "K", "B", "N", "R"],
        ]

    def _build(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        main = QVBoxLayout(content)
        main.setContentsMargins(15, 12, 15, 12)
        main.setSpacing(10)
        main.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header y Puntos
        top_hdr = QHBoxLayout()
        lbl_tit = QLabel("♟ AJEDREZ CLÁSICO 1v1")
        lbl_tit.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        top_hdr.addWidget(lbl_tit)
        top_hdr.addStretch()

        self.lbl_puntos = QLabel(f"🏆 Puntos: {self.score_manager.get_puntos('ajedrez')}")
        self.lbl_puntos.setStyleSheet(f"color: {self.colores['advertencia']}; font-weight: bold; font-size: 13px; background: rgba(251,191,36,0.1); padding: 4px 12px; border-radius: 12px; border: 1px solid rgba(251,191,36,0.2);")
        top_hdr.addWidget(self.lbl_puntos)
        main.addLayout(top_hdr)

        # Barra de Configuración
        cfg = QHBoxLayout()
        lbl_modo = QLabel("Modo de Juego:")
        lbl_modo.setStyleSheet("color: #AAB0B8; font-size: 11px; font-weight: bold;")
        cfg.addWidget(lbl_modo)

        self.combo_modo = QComboBox()
        self.combo_modo.addItems(["🤖 Jugador (Blancas) vs. IA (Negras)", "👥 2 Jugadores 1v1 Local"])
        self.combo_modo.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 6px; padding: 5px 10px; border: 1px solid rgba(255,255,255,0.1);")
        self.combo_modo.currentIndexChanged.connect(self._cambiar_modo)
        cfg.addWidget(self.combo_modo)

        btn_nueva = QPushButton("▶ Nueva Partida")
        btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        btn_nueva.clicked.connect(self.nueva_partida)
        cfg.addWidget(btn_nueva)

        cfg.addStretch()
        main.addLayout(cfg)

        # Estado del juego / Jaque banner
        self.lbl_estado = QLabel("Turno: Blancas (♔)")
        self.lbl_estado.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_estado.setStyleSheet("color: white; padding: 4px;")
        main.addWidget(self.lbl_estado)

        # Tablero 8x8 con coordenadas
        board_container = QFrame()
        board_container.setFixedSize(380, 380)
        board_container.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 10px; border: 2px solid rgba(255,255,255,0.08);")
        self.grid = QGridLayout(board_container)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(0)

        self.btns = {}
        for r in range(8):
            for c in range(8):
                btn = QPushButton("")
                btn.setFixedSize(45, 45)
                btn.setFont(QFont("Segoe UI Symbol", 22))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, row=r, col=c: self._on_square_click(row, col))
                self.grid.addWidget(btn, r, c)
                self.btns[(r, c)] = btn

        cont = QHBoxLayout()
        cont.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cont.addWidget(board_container)
        main.addLayout(cont)

        scroll.setWidget(content)
        root_lay.addWidget(scroll)

        self.nueva_partida()

    def _cambiar_modo(self, idx):
        self.modo = "ia" if idx == 0 else "2j"
        self.nueva_partida()

    def nueva_partida(self):
        self.tablero = self._tablero_inicial()
        self.turno = "W"
        self.seleccionado = None
        self.movimientos_posibles = []
        self.partida_activa = True
        self.lbl_estado.setText("Turno: Blancas (♔)")
        self.lbl_estado.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.dibujar_tablero()

    def _posicion_rey(self, color, board=None):
        t = board if board is not None else self.tablero
        king_piece = "K" if color == "W" else "k"
        for r in range(8):
            for c in range(8):
                if t[r][c] == king_piece:
                    return (r, c)
        return None

    def dibujar_tablero(self):
        rey_blanco_jaque = self._is_king_in_check("W")
        rey_negro_jaque = self._is_king_in_check("B")
        pos_rey_w = self._posicion_rey("W")
        pos_rey_b = self._posicion_rey("B")

        for r in range(8):
            for c in range(8):
                btn = self.btns[(r, c)]
                pieza = self.tablero[r][c]

                # Texto de pieza
                symbol = WHITE_PIECES.get(pieza, BLACK_PIECES.get(pieza, ""))
                btn.setText(symbol)

                # Color de fondo casilla
                es_clara = (r + c) % 2 == 0
                bg_color = "#E2D6B5" if es_clara else "#B88B4A"
                border_css = "border: none;"

                if (r, c) == self.seleccionado:
                    bg_color = "#6366F1"
                elif (r, c) in self.movimientos_posibles:
                    if self.tablero[r][c]:
                        bg_color = "#EF4444"
                        border_css = "border: 2px solid #FFFFFF;"
                    else:
                        bg_color = "#34D399"
                        border_css = "border: 2px solid #059669;"
                elif (r, c) == pos_rey_w and rey_blanco_jaque:
                    bg_color = "#DC2626"
                    border_css = "border: 3px solid #FDE047;"
                elif (r, c) == pos_rey_b and rey_negro_jaque:
                    bg_color = "#DC2626"
                    border_css = "border: 3px solid #FDE047;"

                fg_color = "#FFFFFF" if pieza.isupper() else "#111111"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {bg_color}; color: {fg_color};
                        {border_css} margin: 0;
                    }}
                """)

    def _on_square_click(self, r, c):
        if not self.partida_activa:
            return
        if self.modo == "ia" and self.turno == "B":
            return

        pieza = self.tablero[r][c]
        es_propia = (pieza.isupper() if self.turno == "W" else pieza.islower()) if pieza else False

        if self.seleccionado is None:
            if es_propia:
                self.seleccionado = (r, c)
                self.movimientos_posibles = self._generar_movimientos_legales(r, c)
                self.dibujar_tablero()
        else:
            if (r, c) in self.movimientos_posibles:
                sr, sc = self.seleccionado
                self._mover(sr, sc, r, c)
                self.seleccionado = None
                self.movimientos_posibles = []

                if self._verificar_fin_juego():
                    return

                self.turno = "B" if self.turno == "W" else "W"
                self._actualizar_estado_turno()
                self.dibujar_tablero()

                if self.modo == "ia" and self.turno == "B" and self.partida_activa:
                    QTimer.singleShot(400, self._turno_ia)
            elif es_propia:
                self.seleccionado = (r, c)
                self.movimientos_posibles = self._generar_movimientos_legales(r, c)
                self.dibujar_tablero()
            else:
                self.seleccionado = None
                self.movimientos_posibles = []
                self.dibujar_tablero()

    def _mover(self, r1, c1, r2, c2):
        pieza = self.tablero[r1][c1]
        self.tablero[r2][c2] = pieza
        self.tablero[r1][c1] = ""
        # Coronación de peón
        if pieza == "P" and r2 == 0:
            self.tablero[r2][c2] = "Q"
        elif pieza == "p" and r2 == 7:
            self.tablero[r2][c2] = "q"

    def _turno_ia(self):
        if not self.partida_activa:
            return
        movs = self._todos_movimientos_legales("B")
        if not movs:
            self._finalizar("W")
            return

        # IA evalúa jugadas y prioriza capturas / defender jaque
        movs.sort(key=lambda m: self._evaluar_movimiento(m[0], m[1], m[2], m[3]), reverse=True)
        r1, c1, r2, c2 = movs[0]
        self._mover(r1, c1, r2, c2)

        if self._verificar_fin_juego():
            return

        self.turno = "W"
        self._actualizar_estado_turno()
        self.dibujar_tablero()

    def _evaluar_movimiento(self, r1, c1, r2, c2):
        dest = self.tablero[r2][c2]
        val = abs(PIECE_VALUES.get(dest, 0)) * 12
        # Dar preferencia a ocupar el centro
        val += (3.5 - abs(3.5 - r2)) + (3.5 - abs(3.5 - c2))
        return val + random.uniform(0, 1.5)

    def _is_king_in_check(self, color, board=None):
        """Verifica de forma estricta si el rey de 'color' está bajo ataque en el tablero."""
        t = board if board is not None else self.tablero
        king_pos = self._posicion_rey(color, t)
        if not king_pos:
            return True

        opp_color = "B" if color == "W" else "W"
        kr, kc = king_pos

        for r in range(8):
            for c in range(8):
                p = t[r][c]
                if p and ((opp_color == "W" and p.isupper()) or (opp_color == "B" and p.islower())):
                    ptype = p.upper()
                    # 1. Peón
                    if ptype == "P":
                        dir_r = -1 if opp_color == "W" else 1
                        for dc in [-1, 1]:
                            if (r + dir_r, c + dc) == (kr, kc):
                                return True
                    # 2. Caballo
                    elif ptype == "N":
                        saltos = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
                        if any((r + dr, c + dc) == (kr, kc) for dr, dc in saltos):
                            return True
                    # 3. Torre, Alfil, Reina
                    elif ptype in ["R", "B", "Q"]:
                        dirs = []
                        if ptype in ["R", "Q"]: dirs += [(-1, 0), (1, 0), (0, -1), (0, 1)]
                        if ptype in ["B", "Q"]: dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                        for dr, dc in dirs:
                            step = 1
                            while 0 <= r + dr * step < 8 and 0 <= c + dc * step < 8:
                                dest = t[r + dr * step][c + dc * step]
                                if (r + dr * step, c + dc * step) == (kr, kc):
                                    return True
                                if dest:
                                    break
                                step += 1
                    # 4. Rey enemigo
                    elif ptype == "K":
                        if abs(r - kr) <= 1 and abs(c - kc) <= 1:
                            return True
        return False

    def _generar_movimientos_legales(self, r, c):
        """Genera únicamente los movimientos válidos que NO dejan al rey propio en jaque."""
        pieza = self.tablero[r][c]
        if not pieza:
            return []
        color = "W" if pieza.isupper() else "B"
        candidatos = self._generar_movimientos_pseudo(r, c)
        legales = []

        for r2, c2 in candidatos:
            # Simular movimiento en copia del tablero
            copia = [row[:] for row in self.tablero]
            copia[r2][c2] = copia[r][c]
            copia[r][c] = ""
            if not self._is_king_in_check(color, copia):
                legales.append((r2, c2))

        return legales

    def _todos_movimientos_legales(self, color):
        res = []
        for r in range(8):
            for c in range(8):
                p = self.tablero[r][c]
                if p and ((color == "W" and p.isupper()) or (color == "B" and p.islower())):
                    legales = self._generar_movimientos_legales(r, c)
                    for r2, c2 in legales:
                        res.append((r, c, r2, c2))
        return res

    def _has_legal_moves(self, color):
        return len(self._todos_movimientos_legales(color)) > 0

    def _actualizar_estado_turno(self):
        en_jaque = self._is_king_in_check(self.turno)
        simb = "Blancas (♔)" if self.turno == "W" else "Negras (♚)"
        if en_jaque:
            self.lbl_estado.setText(f"⚠️ ¡JAQUE! Turno: {simb}")
            self.lbl_estado.setStyleSheet("color: #FBBF24; font-weight: bold; font-size: 13px;")
        else:
            self.lbl_estado.setText(f"Turno: {simb}")
            self.lbl_estado.setStyleSheet("color: #FFFFFF; font-weight: bold;")

    def _verificar_fin_juego(self):
        siguiente = "B" if self.turno == "W" else "W"
        en_jaque = self._is_king_in_check(siguiente)
        tiene_movs = self._has_legal_moves(siguiente)

        if not tiene_movs:
            if en_jaque:
                self._finalizar(self.turno)  # El que acaba de mover dio Jaque Mate
            else:
                self.partida_activa = False
                self.lbl_estado.setText("🤝 TABLAS (Rey Ahogado)")
                self.lbl_estado.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: bold;")
            self.dibujar_tablero()
            return True
        return False

    def _finalizar(self, ganador):
        self.partida_activa = False
        if ganador == "W":
            if self.modo == "ia":
                self.score_manager.sumar_puntos("ajedrez", 10)
                self.lbl_puntos.setText(f"🏆 Puntos: {self.score_manager.get_puntos('ajedrez')}")
                msg = "🎉 ¡JAQUE MATE! GANASTE (+10 PTS)"
            else:
                msg = "🎉 ¡JAQUE MATE! Ganaron las Blancas (♔)"
            self.lbl_estado.setText(msg)
            self.lbl_estado.setStyleSheet("color: #34D399; font-size: 13px; font-weight: bold;")
        else:
            msg = "🤖 ¡JAQUE MATE! IA Gana la partida" if self.modo == "ia" else "🎉 ¡JAQUE MATE! Ganaron las Negras (♚)"
            self.lbl_estado.setText(msg)
            self.lbl_estado.setStyleSheet("color: #F87171; font-size: 13px; font-weight: bold;")

    # ── Generador de Movimientos Pseudo-Legales ─────────────────────────
    def _generar_movimientos_pseudo(self, r, c):
        p = self.tablero[r][c]
        if not p:
            return []
        movs = []
        color = "W" if p.isupper() else "B"
        ptype = p.upper()

        def add_if_valid(nr, nc):
            if 0 <= nr < 8 and 0 <= nc < 8:
                dest = self.tablero[nr][nc]
                if not dest:
                    movs.append((nr, nc))
                    return True
                elif (color == "W" and dest.islower()) or (color == "B" and dest.isupper()):
                    movs.append((nr, nc))
                    return False
                else:
                    return False
            return False

        if ptype == "P":
            dir_r = -1 if color == "W" else 1
            start_r = 6 if color == "W" else 1
            # Avance 1
            if 0 <= r + dir_r < 8 and not self.tablero[r + dir_r][c]:
                movs.append((r + dir_r, c))
                # Avance 2
                if r == start_r and not self.tablero[r + 2 * dir_r][c]:
                    movs.append((r + 2 * dir_r, c))
            # Capturas diagonales
            for dc in [-1, 1]:
                nc = c + dc
                nr = r + dir_r
                if 0 <= nr < 8 and 0 <= nc < 8:
                    dest = self.tablero[nr][nc]
                    if dest and ((color == "W" and dest.islower()) or (color == "B" and dest.isupper())):
                        movs.append((nr, nc))

        elif ptype == "N":
            saltos = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
            for dr, dc in saltos:
                add_if_valid(r + dr, c + dc)

        elif ptype in ["R", "B", "Q"]:
            dirs = []
            if ptype in ["R", "Q"]:
                dirs += [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if ptype in ["B", "Q"]:
                dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in dirs:
                step = 1
                while add_if_valid(r + dr * step, c + dc * step):
                    step += 1

        elif ptype == "K":
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr != 0 or dc != 0:
                        add_if_valid(r + dr, c + dc)

        return movs
