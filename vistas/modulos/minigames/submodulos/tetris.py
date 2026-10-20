import random
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QPen

from ..utils.score_manager import ScoreManager

TETROMINOES = {
    'I': {'shape': [[1, 1, 1, 1]], 'color': '#00F0FF'},
    'J': {'shape': [[1, 0, 0], [1, 1, 1]], 'color': '#0000FF'},
    'L': {'shape': [[0, 0, 1], [1, 1, 1]], 'color': '#FF8000'},
    'O': {'shape': [[1, 1], [1, 1]], 'color': '#FFFF00'},
    'S': {'shape': [[0, 1, 1], [1, 1, 0]], 'color': '#00FF00'},
    'T': {'shape': [[0, 1, 0], [1, 1, 1]], 'color': '#A000F0'},
    'Z': {'shape': [[1, 1, 0], [0, 1, 1]], 'color': '#FF0000'}
}

class TetrisCanvas(QWidget):
    """Lienzo de dibujo discreto para la cuadrícula 10x20 de Tetris sin rastros de color"""
    def __init__(self, parent):
        super().__init__(parent)
        self.grid = [[0]*10 for _ in range(20)]
        self.cur_piece = None
        self.cur_pos = [0, 0]
        self.cur_color = "#6366F1"
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(240, 480)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        painter.fillRect(rect, QColor("#121218"))

        cw = rect.width() / 10.0
        ch = rect.height() / 20.0

        # 1. Dibujar bloques fijados en el tablero
        for r in range(20):
            for c in range(10):
                x1 = int(c * cw)
                y1 = int(r * ch)
                w1 = int((c + 1) * cw) - x1
                h1 = int((r + 1) * ch) - y1

                val = self.grid[r][c]
                if val:
                    painter.setBrush(QBrush(QColor(val)))
                    painter.setPen(QPen(QColor("#000000"), 1))
                    painter.drawRect(x1, y1, w1, h1)
                else:
                    painter.setPen(QPen(QColor("rgba(255,255,255,0.05)"), 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(x1, y1, w1, h1)

        # 2. Dibujar pieza activa en descenso
        if self.cur_piece:
            r0, c0 = self.cur_pos
            for r, row in enumerate(self.cur_piece):
                for c, val in enumerate(row):
                    if val:
                        pr, pc = r0 + r, c0 + c
                        if 0 <= pr < 20 and 0 <= pc < 10:
                            x1 = int(pc * cw)
                            y1 = int(pr * ch)
                            w1 = int((pc + 1) * cw) - x1
                            h1 = int((pr + 1) * ch) - y1

                            painter.setBrush(QBrush(QColor(self.cur_color)))
                            painter.setPen(QPen(QColor("#FFFFFF"), 1))
                            painter.drawRect(x1, y1, w1, h1)


class TabTetris(QWidget):
    """Submódulo Tetris Arcade Mítico nativo en PyQt6 con registro en extras_scores.json"""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.score = 0
        self.lines = 0
        self.level = 1
        self.running = False

        self.inicializar_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._game_tick)

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Canvas Tetris
        self.canvas = TetrisCanvas(self)
        layout.addWidget(self.canvas, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        # Panel Estadísticas
        panel = QFrame()
        panel.setFixedWidth(220)
        panel.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 15px;")
        p_lay = QVBoxLayout(panel)
        p_lay.setSpacing(12)

        lbl_tit = QLabel("🧱 TETRIS ARCADE")
        lbl_tit.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento};")
        p_lay.addWidget(lbl_tit)

        self.lbl_score = QLabel("Score: 0")
        self.lbl_score.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        p_lay.addWidget(self.lbl_score)

        self.lbl_lines = QLabel("Líneas: 0")
        self.lbl_lines.setFont(QFont(self.font_family, 10))
        p_lay.addWidget(self.lbl_lines)

        self.lbl_level = QLabel("Nivel: 1")
        self.lbl_level.setFont(QFont(self.font_family, 10))
        p_lay.addWidget(self.lbl_level)

        self.btn_start = QPushButton("▶ INICIAR / REINICIAR")
        self.btn_start.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet(f"background: {exito}; color: white; border-radius: 6px; padding: 10px; border: none;")
        self.btn_start.clicked.connect(self._start_game)
        p_lay.addWidget(self.btn_start)

        lbl_ctrl = QLabel("Controles:\n← / → : Mover\n↑ / W : Rotar pieza\n↓ / S : Caída rápida\nEspacio : Caída instantánea")
        lbl_ctrl.setFont(QFont(self.font_family, 8))
        lbl_ctrl.setStyleSheet("color: rgba(255,255,255,0.5);")
        p_lay.addWidget(lbl_ctrl)

        p_lay.addStretch()
        layout.addWidget(panel)

    def _start_game(self):
        self.canvas.grid = [[0]*10 for _ in range(20)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.running = True
        self._update_stats()
        self._spawn_piece()
        self.timer.start(450)
        self.canvas.setFocus()

    def _spawn_piece(self):
        key = random.choice(list(TETROMINOES.keys()))
        spec = TETROMINOES[key]
        self.canvas.cur_piece = [list(row) for row in spec['shape']]
        self.canvas.cur_color = spec['color']
        self.canvas.cur_pos = [0, 4]

        if not self._valid_move(self.canvas.cur_piece, self.canvas.cur_pos):
            self.running = False
            self.timer.stop()
            self.btn_start.setText("▶ GAME OVER - REINICIAR")
            self._guardar_game_over()

    def _valid_move(self, piece, pos):
        r0, c0 = pos
        for r, row in enumerate(piece):
            for c, val in enumerate(row):
                if val:
                    pr, pc = r0 + r, c0 + c
                    if pr < 0:
                        if pc < 0 or pc >= 10: return False
                        continue
                    if pr >= 20 or pc < 0 or pc >= 10: return False
                    if self.canvas.grid[pr][pc]: return False
        return True

    def _game_tick(self):
        if not self.running: return
        r, c = self.canvas.cur_pos
        if self._valid_move(self.canvas.cur_piece, [r + 1, c]):
            self.canvas.cur_pos[0] += 1
        else:
            self._lock_piece()
            self._clear_lines()
            self._spawn_piece()
        self.canvas.update()

    def _lock_piece(self):
        if not self.canvas.cur_piece: return
        r0, c0 = self.canvas.cur_pos
        for r, row in enumerate(self.canvas.cur_piece):
            for c, val in enumerate(row):
                if val:
                    pr, pc = r0 + r, c0 + c
                    if 0 <= pr < 20 and 0 <= pc < 10:
                        self.canvas.grid[pr][pc] = self.canvas.cur_color
        self.canvas.cur_piece = None

    def _clear_lines(self):
        new_grid = [row for row in self.canvas.grid if any(val == 0 for val in row)]
        cleared = 20 - len(new_grid)
        if cleared > 0:
            for _ in range(cleared):
                new_grid.insert(0, [0]*10)
            self.canvas.grid = new_grid
            self.lines += cleared
            pts_mult = {1: 10, 2: 25, 3: 50, 4: 100}
            pts_ganados = pts_mult.get(cleared, cleared * 20)
            self.score += cleared * 100 * self.level
            self.level = 1 + self.lines // 10
            self.timer.setInterval(max(80, 450 - (self.level - 1)*35))
            self._update_stats()
            try:
                ScoreManager(self.ruta_usuario).sumar_puntos("tetris", pts_ganados)
            except Exception: pass

    def _guardar_game_over(self):
        try:
            sm = ScoreManager(self.ruta_usuario)
            if self.score > 0:
                sm.sumar_puntos("tetris", max(5, self.score // 100))
                sm.actualizar_highscore("tetris", self.score)
        except Exception: pass

    def _update_stats(self):
        self.lbl_score.setText(f"Score: {self.score}")
        self.lbl_lines.setText(f"Líneas: {self.lines}")
        self.lbl_level.setText(f"Nivel: {self.level}")

    def keyPressEvent(self, event):
        if not self.running or not self.canvas.cur_piece: return
        key = event.key()
        r, c = self.canvas.cur_pos

        if key in [Qt.Key.Key_Left, Qt.Key.Key_A]:
            if self._valid_move(self.canvas.cur_piece, [r, c - 1]):
                self.canvas.cur_pos[1] -= 1
        elif key in [Qt.Key.Key_Right, Qt.Key.Key_D]:
            if self._valid_move(self.canvas.cur_piece, [r, c + 1]):
                self.canvas.cur_pos[1] += 1
        elif key in [Qt.Key.Key_Down, Qt.Key.Key_S]:
            if self._valid_move(self.canvas.cur_piece, [r + 1, c]):
                self.canvas.cur_pos[0] += 1
        elif key in [Qt.Key.Key_Up, Qt.Key.Key_W]:
            rotated = [list(row) for row in zip(*self.canvas.cur_piece[::-1])]
            if self._valid_move(rotated, [r, c]):
                self.canvas.cur_piece = rotated
        elif key == Qt.Key.Key_Space:
            while self._valid_move(self.canvas.cur_piece, [r + 1, c]):
                r += 1
            self.canvas.cur_pos[0] = r
            self._lock_piece()
            self._clear_lines()
            self._spawn_piece()

        self.canvas.update()

    def actualizar_tema(self, colores):
        self.colores = colores
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

    def cleanup(self):
        if self.running:
            self.running = False
            self.timer.stop()
            self._guardar_game_over()
