import sys
import random
import time
import math
import json
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QHBoxLayout, QFrame, QSizePolicy, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QSize, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush

class SnakeGame(QWidget):
    """Componente de lienzo para el juego Snake con estilo retro-neon premium y tamaño dinámico."""
    score_changed = pyqtSignal(int)
    game_over_signal = pyqtSignal()
    game_state_changed = pyqtSignal(bool)

    def __init__(self, colores, ruta_usuario=None):
        super().__init__()
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario or ".")
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.grid_size = 20
        self.cell_size = 20  # Se recalcula en paintEvent
        
        self.dificultad = "Fácil"
        self.walls = set()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        
        # Temporizador visual para la animación de pulsación de comida
        self.visual_timer = QTimer(self)
        self.visual_timer.timeout.connect(self.update)
        self.visual_timer.start(33) # ~30 fps
        
        self.reset_game()

    def reset_game(self):
        # Muros según dificultad
        self.walls = set()
        if self.dificultad == "Normal":
            self.walls = {QPoint(5, 5), QPoint(5, 14), QPoint(14, 5), QPoint(14, 14)}
        elif self.dificultad == "Difícil":
            self.walls = {
                QPoint(5, 5), QPoint(5, 6), QPoint(5, 7),
                QPoint(14, 12), QPoint(14, 13), QPoint(14, 14),
                QPoint(5, 14), QPoint(6, 14), QPoint(7, 14),
                QPoint(12, 5), QPoint(13, 5), QPoint(14, 5)
            }
            
        self.snake = [QPoint(10, 10), QPoint(10, 11), QPoint(10, 12)]
        self.direction = Qt.Key.Key_Up
        self.food = self._generate_food()
        self.score = 0
        self.is_running = False
        self.is_game_over = False
        self.timer.stop()
        self.score_changed.emit(0)
        self.update()

    def start_game(self):
        if not self.is_running:
            self.is_running = True
            self.is_game_over = False
            
            # Velocidad fija según dificultad
            interval = 180 if self.dificultad == "Fácil" else (130 if self.dificultad == "Normal" else 80)
            self.timer.start(interval)
            self.game_state_changed.emit(True)
            self.update()

    def _generate_food(self):
        while True:
            p = QPoint(random.randint(0, self.grid_size-1), random.randint(0, self.grid_size-1))
            if p not in self.snake and p not in self.walls:
                return p

    def keyPressEvent(self, event):
        key = event.key()
        if key in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]:
            # Evitar giro de 180 grados
            if key == Qt.Key.Key_Up and self.direction == Qt.Key.Key_Down: return
            if key == Qt.Key.Key_Down and self.direction == Qt.Key.Key_Up: return
            if key == Qt.Key.Key_Left and self.direction == Qt.Key.Key_Right: return
            if key == Qt.Key.Key_Right and self.direction == Qt.Key.Key_Left: return
            self.direction = key
        elif key == Qt.Key.Key_Space:
            if self.is_running:
                self.timer.stop()
                self.is_running = False
                self.game_state_changed.emit(False)
            elif not self.is_game_over:
                interval = 180 if self.dificultad == "Fácil" else (130 if self.dificultad == "Normal" else 80)
                self.timer.start(interval)
                self.is_running = True
                self.game_state_changed.emit(True)
            self.update()
        elif key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            if self.is_game_over:
                self.reset_game()
                self.start_game()
            elif self.is_running:
                self.timer.stop()
                self.is_running = False
                self.game_state_changed.emit(False)
            else:
                self.start_game()
            self.update()
        elif key == Qt.Key.Key_R:
            self.reset_game()
            self.update()

    def update_game(self):
        head = self.snake[0]
        new_head = QPoint(head.x(), head.y())
        
        if self.direction == Qt.Key.Key_Up: new_head.setY(head.y() - 1)
        elif self.direction == Qt.Key.Key_Down: new_head.setY(head.y() + 1)
        elif self.direction == Qt.Key.Key_Left: new_head.setX(head.x() - 1)
        elif self.direction == Qt.Key.Key_Right: new_head.setX(head.x() + 1)
        
        # Colisiones (Bordes, Cuerpo o Muros)
        if (new_head.x() < 0 or new_head.x() >= self.grid_size or 
            new_head.y() < 0 or new_head.y() >= self.grid_size or 
            new_head in self.snake or
            new_head in self.walls):
            self.is_game_over = True
            self.is_running = False
            self.timer.stop()
            self.save_score_to_history()
            self.game_over_signal.emit()
            self.game_state_changed.emit(False)
            self.update()
            return
            
        self.snake.insert(0, new_head)
        
        # Comer
        if new_head == self.food:
            self.score += 1
            self.score_changed.emit(self.score)
            self.food = self._generate_food()
            # Mantener la velocidad constante según nivel
            interval = 180 if self.dificultad == "Fácil" else (130 if self.dificultad == "Normal" else 80)
            self.timer.start(interval)
        else:
            self.snake.pop()
            
        self.update()

    def save_score_to_history(self):
        try:
            if self.score > 0:
                pts = min(10, self.score)
                from ..utils.score_manager import ScoreManager
                ScoreManager(self.ruta_usuario).sumar_puntos("snake", pts)

            path_scores = self.ruta_usuario / "extras_scores.json"
            scores = {}
            if path_scores.exists():
                with open(path_scores, "r", encoding="utf-8") as f:
                    scores = json.load(f)
            
            # Guardar récord de dificultad activa
            diff_key = "snake_highscore_" + ("facil" if self.dificultad == "Fácil" else ("normal" if self.dificultad == "Normal" else "dificil"))
            old_high = scores.get(diff_key, 0)
            if self.score > old_high:
                scores[diff_key] = self.score
            
            # Registrar en historial de Snake
            history = scores.get("snake_history", [])
            ahora = time.strftime("%d/%m %H:%M")
            history.insert(0, {
                "date": ahora,
                "score": self.score,
                "difficulty": self.dificultad
            })
            scores["snake_history"] = history[:30]
            
            with open(path_scores, "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=4)
        except Exception as e:
            print("Error al guardar puntuación de Snake:", e)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fondo
        qp.fillRect(self.rect(), QColor("#111116"))
        
        # Calcular cell_size y márgenes de centrado dinámicamente con un margen de seguridad
        margin = 16
        width = self.width() - margin * 2
        height = self.height() - margin * 2
        grid_pixels = min(width, height)
        self.cell_size = max(10, grid_pixels // self.grid_size)
        offset_x = margin + (width - self.cell_size * self.grid_size) // 2
        offset_y = margin + (height - self.cell_size * self.grid_size) // 2
        
        board_rect = QRect(offset_x, offset_y, self.cell_size * self.grid_size, self.cell_size * self.grid_size)
        
        # Dibujar borde neón indicador de pared (límite de juego)
        qp.setBrush(Qt.BrushStyle.NoBrush)
        glow_color = QColor(self.colores['acento'])
        glow_color.setAlpha(40)
        qp.setPen(QPen(glow_color, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        qp.drawRect(board_rect)
        qp.setPen(QPen(QColor(self.colores['acento']), 2, Qt.PenStyle.SolidLine))
        qp.drawRect(board_rect)
        
        # Rejilla de puntos (Dot grid) elegante
        qp.setPen(Qt.PenStyle.NoPen)
        qp.setBrush(QBrush(QColor(255, 255, 255, 12)))
        for x in range(self.grid_size + 1):
            for y in range(self.grid_size + 1):
                qp.drawEllipse(offset_x + x * self.cell_size - 1, offset_y + y * self.cell_size - 1, 2, 2)
        
        # Dibujar muros (neón rojo / gris oscuro)
        for wall in self.walls:
            wx = offset_x + wall.x() * self.cell_size
            wy = offset_y + wall.y() * self.cell_size
            
            # Glow rojo
            glow_color = QColor(255, 59, 48, 30)
            qp.setBrush(QBrush(glow_color))
            qp.setPen(Qt.PenStyle.NoPen)
            qp.drawRoundedRect(QRect(wx - 2, wy - 2, self.cell_size + 4, self.cell_size + 4), 6, 6)
            
            # Bloque físico
            qp.setBrush(QBrush(QColor("#2d2d3d")))
            qp.setPen(QPen(QColor("#ff3b30"), 1.5))
            qp.drawRoundedRect(QRect(wx + 1, wy + 1, self.cell_size - 2, self.cell_size - 2), 5, 5)
            
            # Detalle en X interno
            qp.setPen(QPen(QColor(255, 59, 48, 80), 1))
            qp.drawLine(wx + 4, wy + 4, wx + self.cell_size - 4, wy + self.cell_size - 4)
            qp.drawLine(wx + self.cell_size - 4, wy + 4, wx + 4, wy + self.cell_size - 4)

        # Comida pulsante radial
        t = time.time()
        pulse = (math.sin(t * 7) + 1.0) / 2.0  # 0 a 1
        cx = offset_x + self.food.x() * self.cell_size + self.cell_size / 2
        cy = offset_y + self.food.y() * self.cell_size + self.cell_size / 2
        base_r = (self.cell_size // 2) - 2
        
        # Anillo exterior
        outer_r = base_r + pulse * 6
        qp.setBrush(Qt.BrushStyle.NoBrush)
        qp.setPen(QPen(QColor(255, 59, 48, int(60 * (1 - pulse))), 2))
        qp.drawEllipse(QPointF(cx, cy), outer_r, outer_r)
        
        # Anillo intermedio
        middle_r = base_r + pulse * 3
        qp.setPen(QPen(QColor(255, 59, 48, int(130 * (1 - pulse * 0.5))), 1.5))
        qp.drawEllipse(QPointF(cx, cy), middle_r, middle_r)
        
        # Núcleo
        qp.setBrush(QBrush(QColor("#ff3b30")))
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawEllipse(QPointF(cx, cy), base_r - 1, base_r - 1)
        
        # Serpiente
        for i, p in enumerate(self.snake):
            is_head = (i == 0)
            color_hex = self.colores['acento'] if is_head else self.colores['acento_hover']
            base_color = QColor(color_hex)
            
            # Glow neón exterior
            glow_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 35)
            qp.setBrush(QBrush(glow_color))
            qp.setPen(Qt.PenStyle.NoPen)
            glow_rect = QRect(offset_x + p.x() * self.cell_size - 2, offset_y + p.y() * self.cell_size - 2, self.cell_size + 4, self.cell_size + 4)
            qp.drawRoundedRect(glow_rect, 6, 6)
            
            # Cuerpo principal
            qp.setBrush(QBrush(base_color))
            border_color = base_color.lighter(115)
            qp.setPen(QPen(border_color, 1))
            rect = QRect(offset_x + p.x() * self.cell_size, offset_y + p.y() * self.cell_size, self.cell_size, self.cell_size)
            qp.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 5, 5)
            
            # Ojos de la serpiente
            if is_head:
                qp.setBrush(QBrush(QColor("white")))
                qp.setPen(Qt.PenStyle.NoPen)
                eye_r = max(1.5, self.cell_size / 10)
                ecx = offset_x + p.x() * self.cell_size + self.cell_size / 2
                ecy = offset_y + p.y() * self.cell_size + self.cell_size / 2
                
                if self.direction in [Qt.Key.Key_Up, Qt.Key.Key_Down]:
                    qp.drawEllipse(QPointF(ecx - self.cell_size/5, ecy), eye_r, eye_r)
                    qp.drawEllipse(QPointF(ecx + self.cell_size/5, ecy), eye_r, eye_r)
                else:
                    qp.drawEllipse(QPointF(ecx, ecy - self.cell_size/5), eye_r, eye_r)
                    qp.drawEllipse(QPointF(ecx, ecy + self.cell_size/5), eye_r, eye_r)

        # Región lógica de colisión (el tablero visible)
        board_rect = QRect(offset_x, offset_y, self.cell_size * self.grid_size, self.cell_size * self.grid_size)

        # Pantalla de inicio
        if not self.is_running and not self.is_game_over:
            qp.fillRect(board_rect, QColor(10, 10, 15, 140))
            card_rect = board_rect.adjusted(40, 60, -40, -60)
            qp.setBrush(QBrush(QColor(30, 30, 46, 220)))
            qp.setPen(QPen(QColor(self.colores['acento']), 1.5))
            qp.drawRoundedRect(card_rect, 16, 16)
            
            qp.setPen(QColor("white"))
            qp.setFont(QFont("Outfit", 22, QFont.Weight.Bold))
            qp.drawText(card_rect.adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "SNAKE GAME")
            
            qp.setPen(QColor(self.colores['fg_secundario']))
            qp.setFont(QFont("Outfit", 11, QFont.Weight.Normal))
            qp.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, "Controla con las flechas\n¿Estás listo?")
            
            qp.setPen(QColor(self.colores['acento']))
            qp.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
            qp.drawText(card_rect.adjusted(0, 0, 0, -25), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, "Presiona INICIAR o Enter")

        # Pantalla de Game Over
        if self.is_game_over:
            qp.fillRect(board_rect, QColor(10, 10, 15, 180))
            card_rect = board_rect.adjusted(40, 60, -40, -60)
            qp.setBrush(QBrush(QColor(30, 30, 46, 230)))
            qp.setPen(QPen(QColor(self.colores['error']), 1.5))
            qp.drawRoundedRect(card_rect, 16, 16)
            
            qp.setPen(QColor(self.colores['error']))
            qp.setFont(QFont("Outfit", 24, QFont.Weight.Bold))
            qp.drawText(card_rect.adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "FIN DEL JUEGO")
            
            qp.setPen(QColor("white"))
            qp.setFont(QFont("Outfit", 16, QFont.Weight.Medium))
            qp.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, f"Puntuación final\n{self.score}")
            
            qp.setPen(QColor(self.colores['fg_secundario']))
            qp.setFont(QFont("Outfit", 10, QFont.Weight.Normal))
            qp.drawText(card_rect.adjusted(0, 0, 0, -25), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, "Presiona Enter o Reintentar")

class SnakeGUI(QWidget):
    def __init__(self, parent, colores, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario or ".")
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 20, 30, 20)
        self.layout.setSpacing(15)
        
        # Stats container - glassmorphic style
        self.stats_widget = QFrame()
        self.stats_widget.setObjectName("StatsWidget")
        self.stats_widget.setStyleSheet(f"""
            QFrame#StatsWidget {{
                background: rgba(30, 30, 46, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 10px;
            }}
        """)
        stats = QHBoxLayout(self.stats_widget)
        stats.setContentsMargins(15, 6, 15, 6)
        
        # Score label
        self.lbl_score = QLabel("🏆 PUNTOS: 0")
        self.lbl_score.setStyleSheet("""
            color: white; 
            font-size: 15px; 
            font-weight: bold; 
            font-family: 'Outfit';
        """)
        stats.addWidget(self.lbl_score)
        
        stats.addStretch()
        
        # Segmented Difficulty Buttons
        diff_container = QFrame()
        diff_container.setStyleSheet("background: rgba(0, 0, 0, 0.25); border-radius: 6px; border: none; padding: 2px;")
        diff_lay = QHBoxLayout(diff_container)
        diff_lay.setContentsMargins(2, 2, 2, 2)
        diff_lay.setSpacing(2)
        
        self.btn_easy = QPushButton("Fácil")
        self.btn_medium = QPushButton("Normal")
        self.btn_hard = QPushButton("Difícil")
        
        self.diff_buttons = [self.btn_easy, self.btn_medium, self.btn_hard]
        for btn in self.diff_buttons:
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
            diff_lay.addWidget(btn)
            
        self.btn_easy.clicked.connect(lambda: self.change_difficulty("Fácil"))
        self.btn_medium.clicked.connect(lambda: self.change_difficulty("Normal"))
        self.btn_hard.clicked.connect(lambda: self.change_difficulty("Difícil"))
        
        stats.addWidget(diff_container)
        stats.addStretch()
        
        # Action button
        self.btn_action = QPushButton("▶️ INICIAR")
        self.btn_action.setObjectName("BtnAction")
        self.btn_action.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_action.setStyleSheet(f"""
            QPushButton#BtnAction {{
                background: {self.colores['exito']}; 
                color: {self.colores['bg_principal']};
                padding: 8px 20px; 
                border-radius: 8px; 
                font-weight: bold;
                font-size: 13px;
                font-family: 'Outfit', 'Segoe UI';
            }}
            QPushButton#BtnAction:hover {{
                background: {self.colores['exito']}cc;
            }}
        """)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.clicked.connect(self.handle_action)
        stats.addWidget(self.btn_action)
        
        self.layout.addWidget(self.stats_widget)
        
        # Active state default
        self.btn_easy.setChecked(True)
        self._update_difficulty_btn_styles("Fácil")
        
        # Main area (horizontal split)
        self.main_content = QHBoxLayout()
        self.main_content.setSpacing(20)
        
        # Left: Game canvas container (Expanding)
        self.game_container = QFrame()
        self.game_container.setObjectName("GameContainer")
        self.game_container.setStyleSheet("""
            QFrame#GameContainer {
                border: 2px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                background: #111116;
            }
        """)
        game_layout = QVBoxLayout(self.game_container)
        game_layout.setContentsMargins(0, 0, 0, 0)
        
        self.game = SnakeGame(self.colores, self.ruta_usuario)
        self.game.score_changed.connect(lambda s: self.lbl_score.setText(f"🏆 PUNTOS: {s}"))
        self.game.game_over_signal.connect(self.on_game_over)
        self.game.game_state_changed.connect(self.on_game_state_changed)
        game_layout.addWidget(self.game)
        
        self.main_content.addWidget(self.game_container, 3)
        
        # Right: Sidebar (Highscores + history)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet(f"""
            QFrame#Sidebar {{
                background: rgba(30, 30, 46, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 15px;
            }}
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(12)
        
        # Records
        lbl_hs_tit = QLabel("🏆 RÉCORDS")
        lbl_hs_tit.setFont(QFont("Outfit", 11, QFont.Weight.Bold))
        lbl_hs_tit.setStyleSheet(f"color: {self.colores['acento']}; border: none;")
        sidebar_layout.addWidget(lbl_hs_tit)
        
        self.lbl_rec_hard = QLabel("Difícil: 0 pts")
        self.lbl_rec_medium = QLabel("Normal: 0 pts")
        self.lbl_rec_easy = QLabel("Fácil: 0 pts")
        
        for lbl in [self.lbl_rec_hard, self.lbl_rec_medium, self.lbl_rec_easy]:
            lbl.setFont(QFont("Outfit", 10, QFont.Weight.Medium))
            lbl.setStyleSheet("color: white; border: none;")
            sidebar_layout.addWidget(lbl)
            
        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background: rgba(255, 255, 255, 0.08); border: none; height: 1px;")
        sidebar_layout.addWidget(div)
        
        # Recent matches history header
        hist_header = QHBoxLayout()
        hist_header.setContentsMargins(0, 0, 0, 0)
        
        lbl_hist_tit = QLabel("📜 HISTORIAL")
        lbl_hist_tit.setFont(QFont("Outfit", 11, QFont.Weight.Bold))
        lbl_hist_tit.setStyleSheet(f"color: {self.colores['fg_secundario']}; border: none;")
        hist_header.addWidget(lbl_hist_tit)
        
        hist_header.addStretch()
        
        self.btn_clear_history = QPushButton("🧹")
        self.btn_clear_history.setToolTip("Limpiar historial (mantiene récords)")
        self.btn_clear_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_history.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_clear_history.setFixedSize(24, 24)
        self.btn_clear_history.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                color: {self.colores['fg_secundario']};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid {self.colores['error']};
                color: white;
            }}
        """)
        self.btn_clear_history.clicked.connect(self.clear_history_keep_records)
        hist_header.addWidget(self.btn_clear_history)
        
        sidebar_layout.addLayout(hist_header)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.1);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        self.history_list_widget = QWidget()
        self.history_list_widget.setStyleSheet("background: transparent; border: none;")
        self.history_list_lay = QVBoxLayout(self.history_list_widget)
        self.history_list_lay.setContentsMargins(0, 0, 0, 0)
        self.history_list_lay.setSpacing(6)
        self.history_list_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.history_list_widget)
        sidebar_layout.addWidget(self.scroll_area)
        
        self.main_content.addWidget(self.sidebar, 1)
        self.layout.addLayout(self.main_content, 1)
        
        # Help
        lbl_help = QLabel("🎮 Flechas para moverse · Espacio/Enter para Pausar · R para reiniciar")
        lbl_help.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-style: italic; font-size: 11px; font-family: 'Outfit';")
        lbl_help.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_help)
        
        # Update records and history
        self.update_scores_ui()

    def _update_difficulty_btn_styles(self, active_diff):
        for btn, name in zip(self.diff_buttons, ["Fácil", "Normal", "Difícil"]):
            if name == active_diff:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {self.colores['acento']};
                        color: white;
                        border-radius: 4px;
                        padding: 4px 12px;
                        border: none;
                    }}
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {self.colores['fg_secundario']};
                        border-radius: 4px;
                        padding: 4px 12px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background: rgba(255,255,255,0.05);
                        color: white;
                    }}
                """)

    def change_difficulty(self, diff):
        self._update_difficulty_btn_styles(diff)
        self.game.dificultad = diff
        self.game.reset_game()
        self.lbl_score.setText("🏆 PUNTOS: 0")
        self.btn_action.setText("▶️ INICIAR")
        self.on_game_state_changed(False)
        self.game.setFocus()

    def update_scores_ui(self):
        try:
            path = Path(self.ruta_usuario) / "extras_scores.json"
            scores = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    scores = json.load(f)
            
            # Highscores
            self.lbl_rec_easy.setText(f"Fácil: {scores.get('snake_highscore_facil', 0)} pts")
            self.lbl_rec_medium.setText(f"Normal: {scores.get('snake_highscore_normal', 0)} pts")
            self.lbl_rec_hard.setText(f"Difícil: {scores.get('snake_highscore_dificil', 0)} pts")
            # History
            # Clear previous widgets
            for i in range(self.history_list_lay.count()):
                widget = self.history_list_lay.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
                    
            history = scores.get("snake_history", [])
            if not history:
                lbl_empty = QLabel("Sin partidas recientes")
                lbl_empty.setFont(QFont("Outfit", 9))
                lbl_empty.setStyleSheet("color: rgba(255, 255, 255, 0.4); border: none;")
                self.history_list_lay.addWidget(lbl_empty)
            else:
                # Sort history hierarchically: Difícil (0) > Normal (1) > Fácil (2).
                # Secondary sort by score descending, then by date.
                diff_order = {"Difícil": 0, "Normal": 1, "Fácil": 2}
                sorted_history = sorted(
                    history,
                    key=lambda x: (diff_order.get(x.get("difficulty", "Fácil"), 2), -x.get("score", 0))
                )
                for match in sorted_history:
                    item_frame = QFrame()
                    item_frame.setStyleSheet("""
                        QFrame {
                            background: rgba(255, 255, 255, 0.03);
                            border: 1px solid rgba(255, 255, 255, 0.05);
                            border-radius: 6px;
                            padding: 4px;
                        }
                    """)
                    h_lay = QHBoxLayout(item_frame)
                    h_lay.setContentsMargins(6, 4, 6, 4)
                    h_lay.setSpacing(4)
                    
                    lbl_date = QLabel(match.get("date", ""))
                    lbl_date.setFont(QFont("Outfit", 8))
                    lbl_date.setStyleSheet("color: rgba(255, 255, 255, 0.4); border: none;")
                    h_lay.addWidget(lbl_date)
                    
                    diff = match.get("difficulty", "Fácil")
                    lbl_diff = QLabel(diff)
                    lbl_diff.setFont(QFont("Outfit", 8, QFont.Weight.Bold))
                    diff_color = self.colores['acento'] if diff == "Normal" else (self.colores['exito'] if diff == "Fácil" else self.colores['error'])
                    lbl_diff.setStyleSheet(f"color: {diff_color}; border: none;")
                    h_lay.addWidget(lbl_diff)
                    
                    h_lay.addStretch()
                    
                    lbl_pts = QLabel(f"{match.get('score', 0)} pts")
                    lbl_pts.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
                    lbl_pts.setStyleSheet("color: white; border: none;")
                    h_lay.addWidget(lbl_pts)
                    
                    self.history_list_lay.addWidget(item_frame)
        except Exception as e:
            print("Error al actualizar UI de récord:", e)

    def clear_history_keep_records(self):
        try:
            path = Path(self.ruta_usuario) / "extras_scores.json"
            scores = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    scores = json.load(f)
            
            history = scores.get("snake_history", [])
            if not history:
                return
                
            # Group by difficulty and find the best match for each
            best_by_diff = {}
            for match in history:
                diff = match.get("difficulty", "Fácil")
                score = match.get("score", 0)
                if diff not in best_by_diff or score > best_by_diff[diff].get("score", 0):
                    best_by_diff[diff] = match
            
            # Reconstruct history ordered strictly: Difícil, Normal, Fácil
            new_history = []
            for diff in ["Difícil", "Normal", "Fácil"]:
                if diff in best_by_diff:
                    new_history.append(best_by_diff[diff])
            
            scores["snake_history"] = new_history
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=4)
                
            self.update_scores_ui()
        except Exception as e:
            print("Error al limpiar historial de Snake:", e)

    def handle_action(self):
        if self.game.is_game_over:
            self.game.reset_game()
            self.lbl_score.setText("🏆 PUNTOS: 0")
            self.btn_action.setText("▶️ INICIAR")
            self.btn_action.setStyleSheet(f"""
                QPushButton#BtnAction {{
                    background: {self.colores['exito']}; 
                    color: {self.colores['bg_principal']};
                    padding: 8px 20px; border-radius: 8px; font-weight: bold; font-size: 13px;
                }}
                QPushButton#BtnAction:hover {{ background: {self.colores['exito']}cc; }}
            """)
        
        if not self.game.is_running:
            self.game.start_game()
            self.game.setFocus()
        else:
            self.game.timer.stop()
            self.game.is_running = False
            self.on_game_state_changed(False)
            self.game.update()

    def on_game_state_changed(self, is_running):
        if is_running:
            self.btn_action.setText("⏸️ PAUSAR")
            self.btn_action.setStyleSheet(f"""
                QPushButton#BtnAction {{
                    background: {self.colores['acento']}; 
                    color: white;
                    padding: 8px 20px; border-radius: 8px; font-weight: bold; font-size: 13px;
                }}
                QPushButton#BtnAction:hover {{ background: {self.colores['acento_hover']}; }}
            """)
        else:
            self.btn_action.setText("▶️ INICIAR")
            self.btn_action.setStyleSheet(f"""
                QPushButton#BtnAction {{
                    background: {self.colores['exito']}; 
                    color: {self.colores['bg_principal']};
                    padding: 8px 20px; border-radius: 8px; font-weight: bold; font-size: 13px;
                }}
                QPushButton#BtnAction:hover {{ background: {self.colores['exito']}cc; }}
            """)

    def on_game_over(self):
        self.btn_action.setText("🔄 REINTENTAR")
        self.btn_action.setStyleSheet(f"""
            QPushButton#BtnAction {{
                background: {self.colores['error']}; 
                color: white;
                padding: 8px 20px; border-radius: 8px; font-weight: bold; font-size: 13px;
            }}
            QPushButton#BtnAction:hover {{ background: {self.colores['error']}cc; }}
        """)
        self.update_scores_ui()
