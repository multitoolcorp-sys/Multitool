"""
Damas (Checkers) — Submódulo de MiniGames
Juego de Damas con captura de fichas, coronación de damas, IA, modo 2 jugadores y sistema de puntos (PvsAI).
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

# Fichas Unicode: "r"=Roja, "b"=Blanca, "R"=Dama Roja, "B"=Dama Blanca
SYMBOLS = {"r": "🔴", "R": "👑", "b": "⚪", "B": "👑", "": ""}


class TabDamas(QWidget):
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
        self.turno = "r"  # "r" (Rojas / Jugador) | "b" (Blancas / IA)
        self.seleccionado = None
        self.movimientos_posibles = {}  # dict (r, c) -> lista de (r2, c2, captura_pos)
        self.modo = "ia"
        self.partida_activa = False

        self._build()

    def _tablero_inicial(self):
        t = [["" for _ in range(8)] for _ in range(8)]
        # Fichas Blancas (b) en filas 0, 1, 2 en casillas oscuras
        for r in range(3):
            for c in range(8):
                if (r + c) % 2 == 1:
                    t[r][c] = "b"
        # Fichas Rojas (r) en filas 5, 6, 7 en casillas oscuras
        for r in range(5, 8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    t[r][c] = "r"
        return t

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
        main.setSpacing(10)
        main.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header y Puntos
        top_hdr = QHBoxLayout()
        lbl_tit = QLabel("🔴 DAMAS INTERNACIONALES ⚪")
        lbl_tit.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        top_hdr.addWidget(lbl_tit)
        top_hdr.addStretch()

        self.lbl_puntos = QLabel(f"🏆 Puntos: {self.score_manager.get_puntos('damas')}")
        self.lbl_puntos.setStyleSheet(f"color: {self.colores['advertencia']}; font-weight: bold; font-size: 13px; background: rgba(251,191,36,0.1); padding: 4px 12px; border-radius: 12px; border: 1px solid rgba(251,191,36,0.2);")
        top_hdr.addWidget(self.lbl_puntos)
        main.addLayout(top_hdr)

        # Configuración
        cfg = QHBoxLayout()
        lbl_modo = QLabel("Modo:")
        lbl_modo.setStyleSheet("color: #AAA; font-size: 11px;")
        cfg.addWidget(lbl_modo)
        self.combo_modo = QComboBox()
        self.combo_modo.addItems(["🤖 Jugador (Rojas) vs. IA (Blancas)", "👥 2 Jugadores Local", "📡 1v1 Red Local LAN Socket"])
        self.combo_modo.setStyleSheet(f"background: {self.colores['bg_secundario']}; color: white; border-radius: 6px; padding: 4px 8px; border: none;")
        self.combo_modo.currentIndexChanged.connect(self._cambiar_modo)
        cfg.addWidget(self.combo_modo)

        btn_nueva = QPushButton("▶ Nueva Partida")
        btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nueva.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        btn_nueva.clicked.connect(self.nueva_partida)
        cfg.addWidget(btn_nueva)

        from ..utils.game_socket_manager import GameSocketManager
        self.socket_mgr = GameSocketManager(usuario="Jugador Damas")
        self.socket_mgr.configurar_callbacks(self._on_lan_move_received, self._on_lan_status)

        cfg.addStretch()
        main.addLayout(cfg)

        # Estado
        self.lbl_estado = QLabel("Presiona ▶ Nueva Partida para jugar")
        self.lbl_estado.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_estado.setStyleSheet("color: white;")
        main.addWidget(self.lbl_estado)

        # Tablero 8x8
        board_frame = QFrame()
        board_frame.setFixedSize(360, 360)
        board_frame.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);")
        self.grid = QGridLayout(board_frame)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(0)

        self.btns = {}
        for r in range(8):
            for c in range(8):
                btn = QPushButton("")
                btn.setFixedSize(43, 43)
                btn.setFont(QFont("Segoe UI Emoji", 18))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, row=r, col=c: self._on_square_click(row, col))
                self.grid.addWidget(btn, r, c)
                self.btns[(r, c)] = btn

        cont = QHBoxLayout()
        cont.addStretch()
        cont.addWidget(board_frame)
        cont.addStretch()
        main.addLayout(cont)

        scroll.setWidget(content)
        root_lay.addWidget(scroll)

        self.nueva_partida()

    def _cambiar_modo(self, idx):
        self.modo = "ia" if idx == 0 else "2j"
        self.nueva_partida()

    def nueva_partida(self):
        self.tablero = self._tablero_inicial()
        self.turno = "r"
        self.seleccionado = None
        self.movimientos_posibles = {}
        self.partida_activa = True
        self.lbl_estado.setText("Turno: Rojas (🔴)")
        self.lbl_estado.setStyleSheet("color: #EF4444; font-weight: bold;")
        self.dibujar_tablero()

    def dibujar_tablero(self):
        destinos_validos = [m[0] for m in self.movimientos_posibles.get(self.seleccionado, [])] if self.seleccionado else []
        for r in range(8):
            for c in range(8):
                btn = self.btns[(r, c)]
                ficha = self.tablero[r][c]
                btn.setText(SYMBOLS.get(ficha, ""))

                es_oscura = (r + c) % 2 == 1
                bg_color = "#3A2E39" if es_oscura else "#DDB88C"
                fg_color = "#FFFFFF"

                if ficha == "r":
                    fg_color = "#EF4444"
                elif ficha == "R":
                    fg_color = "#EF4444"  # Corona Roja
                elif ficha == "b":
                    fg_color = "#FFFFFF"
                elif ficha == "B":
                    fg_color = "#38BDF8"  # Corona Blanca (Celeste brillante para distinguir la IA)

                if (r, c) == self.seleccionado:
                    bg_color = "#6366F1"
                elif (r, c) in destinos_validos:
                    bg_color = "#34D399"

                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {bg_color}; color: {fg_color}; border: none; margin: 0; font-size: 22px; font-weight: bold;
                    }}
                """)

    def _on_square_click(self, r, c):
        if not self.partida_activa:
            return
        if self.modo == "ia" and self.turno == "b":
            return

        ficha = self.tablero[r][c]
        es_propia = ficha.lower() == self.turno if ficha else False

        if self.seleccionado is None:
            if es_propia:
                movs = self._obtener_movimientos_ficha(r, c)
                if movs:
                    self.seleccionado = (r, c)
                    self.movimientos_posibles = {(r, c): movs}
                    self.dibujar_tablero()
        else:
            opciones = self.movimientos_posibles.get(self.seleccionado, [])
            target = next((m for m in opciones if (m[0], m[1]) == (r, c)), None)

            if target:
                sr, sc = self.seleccionado
                dr, dc, cap = target
                self._mover(sr, sc, dr, dc, cap)

                if self._verificar_fin_juego():
                    return

                # Si fue una captura, verificar si hay comida seguida con la misma ficha
                if cap:
                    mas_capturas = [m for m in self._obtener_movimientos_ficha(dr, dc) if m[2] is not None]
                    if mas_capturas:
                        self.seleccionado = (dr, dc)
                        self.movimientos_posibles = {(dr, dc): mas_capturas}
                        self.lbl_estado.setText(f"🔥 ¡COMIDA SEGUIDA! Volver a comer con ({'Rojas 🔴' if self.turno == 'r' else 'Blancas ⚪'})")
                        self.lbl_estado.setStyleSheet("color: #FBBF24; font-weight: bold;")
                        self.dibujar_tablero()
                        return

                self.seleccionado = None
                self.movimientos_posibles = {}
                self.turno = "b" if self.turno == "r" else "r"
                self.lbl_estado.setText(f"Turno: {'Rojas (🔴)' if self.turno == 'r' else 'Blancas (⚪)'}")
                self.lbl_estado.setStyleSheet(f"color: {'#EF4444' if self.turno == 'r' else '#FFFFFF'}; font-weight: bold;")
                self.dibujar_tablero()

                if self.modo == "ia" and self.turno == "b" and self.partida_activa:
                    QTimer.singleShot(400, self._turno_ia)
            elif es_propia:
                movs = self._obtener_movimientos_ficha(r, c)
                if movs:
                    self.seleccionado = (r, c)
                    self.movimientos_posibles = {(r, c): movs}
                    self.dibujar_tablero()
                else:
                    self.seleccionado = None
                    self.movimientos_posibles = {}
                    self.dibujar_tablero()
            else:
                self.seleccionado = None
                self.movimientos_posibles = {}
                self.dibujar_tablero()

    def _mover(self, r1, c1, r2, c2, captura_pos=None):
        ficha = self.tablero[r1][c1]
        self.tablero[r2][c2] = ficha
        self.tablero[r1][c1] = ""
        if captura_pos:
            cr, cc = captura_pos
            self.tablero[cr][cc] = ""

        # Coronación a Dama (Reina)
        if ficha == "r" and r2 == 0:
            self.tablero[r2][c2] = "R"
        elif ficha == "b" and r2 == 7:
            self.tablero[r2][c2] = "B"

    def _turno_ia(self):
        if not self.partida_activa:
            return
        todos = self._todos_movimientos("b")
        if not todos:
            self._finalizar("r")
            return

        capturas = [m for m in todos if m[4] is not None]
        mov_elegido = random.choice(capturas) if capturas else random.choice(todos)

        r1, c1, r2, c2, cap = mov_elegido
        self._mover(r1, c1, r2, c2, cap)

        if self._verificar_fin_juego():
            return

        # Comidas seguidas para la IA
        if cap:
            mas_cap = [m for m in self._obtener_movimientos_ficha(r2, c2) if m[2] is not None]
            if mas_cap:
                QTimer.singleShot(300, lambda: self._mover_ia_seguido(r2, c2, mas_cap))
                return

        self.turno = "r"
        self.lbl_estado.setText("Turno: Rojas (🔴)")
        self.lbl_estado.setStyleSheet("color: #EF4444; font-weight: bold;")
        self.dibujar_tablero()

    def _mover_ia_seguido(self, r1, c1, capturas_disponibles):
        mov = random.choice(capturas_disponibles)
        r2, c2, cap = mov
        self._mover(r1, c1, r2, c2, cap)
        if self._verificar_fin_juego():
            return
        mas_cap = [m for m in self._obtener_movimientos_ficha(r2, c2) if m[2] is not None]
        if mas_cap:
            QTimer.singleShot(300, lambda: self._mover_ia_seguido(r2, c2, mas_cap))
            return
        self.turno = "r"
        self.lbl_estado.setText("Turno: Rojas (🔴)")
        self.lbl_estado.setStyleSheet("color: #EF4444; font-weight: bold;")
        self.dibujar_tablero()

    def _verificar_fin_juego(self):
        rojas = sum(1 for fila in self.tablero for f in fila if f.lower() == "r")
        blancas = sum(1 for fila in self.tablero for f in fila if f.lower() == "b")
        if rojas == 0:
            self._finalizar("b")
            return True
        if blancas == 0:
            self._finalizar("r")
            return True
        return False

    def _finalizar(self, ganador):
        self.partida_activa = False
        if ganador == "r":
            if self.modo == "ia":
                self.score_manager.sumar_puntos("damas", 10)
                self.lbl_puntos.setText(f"🏆 Puntos: {self.score_manager.get_puntos('damas')}")
                msg = "🎉 ¡GANASTE CONTRA LA IA! (+10 PTS)"
            else:
                msg = "🎉 ¡Ganaron las Rojas (🔴)!"
            self.lbl_estado.setText(msg)
            self.lbl_estado.setStyleSheet("color: #34D399; font-size: 13px; font-weight: bold;")
        else:
            msg = "🤖 IA Gana la partida" if self.modo == "ia" else "🎉 ¡Ganaron las Blancas (⚪)!"
            self.lbl_estado.setText(msg)
            self.lbl_estado.setStyleSheet("color: #F87171; font-size: 13px; font-weight: bold;")

    # ── Reglas de Movimiento Damas (Internacionales) ─────────────────────
    def _todos_movimientos(self, color):
        res = []
        for r in range(8):
            for c in range(8):
                if self.tablero[r][c].lower() == color:
                    movs = self._obtener_movimientos_ficha(r, c)
                    for dr, dc, cap in movs:
                        res.append((r, c, dr, dc, cap))
        return res

    def _obtener_movimientos_ficha(self, r, c):
        ficha = self.tablero[r][c]
        if not ficha:
            return []
        color = ficha.lower()
        es_dama = ficha.isupper()
        movs = []

        dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)] if es_dama else ([(-1, -1), (-1, 1)] if color == "r" else [(1, -1), (1, 1)])

        if not es_dama:
            # Peón normal: Solo se desplaza o captura HACIA ADELANTE (sin comer hacia atrás)
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    dest = self.tablero[nr][nc]
                    if not dest:
                        movs.append((nr, nc, None))
                    elif dest and dest.lower() != color:
                        nnr, nnc = nr + dr, nc + dc
                        if 0 <= nnr < 8 and 0 <= nnc < 8 and not self.tablero[nnr][nnc]:
                            movs.append((nnr, nnc, (nr, nc)))
        else:
            # Dama Voladora (Regla Internacional: se mueve X casillas libres en diagonal y come a distancia)
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                step = 1
                enemigo_hallado = None
                while True:
                    nr, nc = r + dr * step, c + dc * step
                    if not (0 <= nr < 8 and 0 <= nc < 8):
                        break
                    dest = self.tablero[nr][nc]
                    if not dest:
                        if enemigo_hallado is None:
                            movs.append((nr, nc, None))
                        else:
                            movs.append((nr, nc, enemigo_hallado))
                    elif dest.lower() != color and enemigo_hallado is None:
                        enemigo_hallado = (nr, nc)
                    else:
                        break
                    step += 1

        return movs

    def _on_lan_move_received(self, data):
        payload = data.get("payload", {})
        orig = payload.get("orig")
        dest = payload.get("dest")
        capt = payload.get("capt")
        if orig and dest:
            r1, c1 = orig
            r2, c2 = dest
            self.tablero[r2][c2] = self.tablero[r1][c1]
            self.tablero[r1][c1] = ""
            if capt:
                cr, cc = capt
                self.tablero[cr][cc] = ""
            self.turno = "b" if self.turno == "r" else "r"
            self._render_tablero()

    def _on_lan_status(self, msg):
        self.lbl_estado.setText(msg)
