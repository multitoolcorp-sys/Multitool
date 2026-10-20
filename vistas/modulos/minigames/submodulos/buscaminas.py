import random
import time
import json
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QGridLayout, QPushButton, QVBoxLayout, QLabel, 
                             QHBoxLayout, QMessageBox, QFrame, QSizePolicy, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor

class MinesweeperCell(QPushButton):
    """Celda individual ajustable para buscaminas."""
    clicked_left = pyqtSignal(int, int)
    clicked_right = pyqtSignal(int, int)

    def __init__(self, r, c, colores):
        super().__init__()
        self.r, self.c = r, c
        self.colores = colores
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.ExtraBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.neighbor_mines = 0
        self.reset_ui()

    def reset_ui(self):
        self.setText("")
        self.is_revealed = False
        self.is_flagged = False
        self.setStyleSheet(f"""
            MinesweeperCell {{
                background: {self.colores['bg_secundario']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 5px;
            }}
            MinesweeperCell:hover {{
                background: {self.colores['bg_terciario']};
                border: 1.5px solid {self.colores['acento']};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_left.emit(self.r, self.c)
        elif event.button() == Qt.MouseButton.RightButton:
            self.clicked_right.emit(self.r, self.c)

class BuscaminasGUI(QWidget):
    def __init__(self, parent, colores, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario or ".")
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.dificultad = "Fácil"
        self.rows, self.cols = 9, 9
        self.num_mines = 10
        self.mines_left = self.num_mines
        self.game_over = False
        self.cells = []
        self._build_ui()
        self.new_game()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 20, 30, 20)
        self.layout.setSpacing(15)
        
        # Header (Mines counter + Difficulty + Reset)
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_secundario']};
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(15, 8, 15, 8)
        
        self.lbl_mines = QLabel(f"💣 {self.num_mines:02d}")
        self.lbl_mines.setStyleSheet(f"color: {self.colores['error']}; font-size: 20px; font-weight: 900;")
        header.addWidget(self.lbl_mines)
        
        header.addStretch()
        
        # Selector de Dificultad
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
        
        header.addWidget(diff_container)
        header.addStretch()
        
        self.btn_reset = QPushButton("😊 NUEVO JUEGO")
        self.btn_reset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                font-weight: 800;
                font-size: 11px;
                padding: 8px 16px;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            QPushButton:hover {{
                background: {self.colores['acento']};
                border: 1px solid white;
            }}
        """)
        self.btn_reset.clicked.connect(self.new_game)
        header.addWidget(self.btn_reset)
        
        # Setup Dificultad por defecto
        self.btn_easy.setChecked(True)
        self._update_difficulty_btn_styles("Fácil")
        
        # Contenedor Principal (Layout Horizontal para el sidebar)
        self.main_content = QHBoxLayout()
        self.main_content.setSpacing(20)
        
        # Tablero de Buscaminas
        self.grid_frame = QFrame()
        self.grid_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.colores['bg_principal']};
                border: 2px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
        """)
        self.grid_layout = QGridLayout(self.grid_frame)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Panel Izquierdo que agrupa Header y Tablero
        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("background: transparent; border: none;")
        self.left_lay = QVBoxLayout(self.left_panel)
        self.left_lay.setContentsMargins(0, 0, 0, 0)
        self.left_lay.setSpacing(15)
        self.left_lay.addWidget(header_frame)
        self.left_lay.addWidget(self.grid_frame)
        
        self.main_content.addWidget(self.left_panel, 3)
        
        # Panel Derecho (Sidebar de Historial y Puntos)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(280)
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
        
        self.lbl_points_accum = QLabel("⭐ PUNTOS: 0")
        self.lbl_points_accum.setFont(QFont("Outfit", 12, QFont.Weight.Bold))
        self.lbl_points_accum.setStyleSheet(f"color: {self.colores['advertencia']}; border: none;")
        sidebar_layout.addWidget(self.lbl_points_accum)
        
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setStyleSheet("background: rgba(255, 255, 255, 0.08); border: none; height: 1px;")
        sidebar_layout.addWidget(div1)
        
        # Récords
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
            
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setStyleSheet("background: rgba(255, 255, 255, 0.08); border: none; height: 1px;")
        sidebar_layout.addWidget(div2)
        
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
        
        # Help text
        lbl_help = QLabel("🎮 Click Izquierdo para revelar · Click Derecho para marcar · Enter/R para reiniciar")
        lbl_help.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-style: italic; font-size: 11px; font-family: 'Outfit';")
        lbl_help.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_help)

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
        self.dificultad = diff
        if diff == "Fácil":
            self.rows, self.cols = 9, 9
            self.num_mines = 10
        elif diff == "Normal":
            self.rows, self.cols = 12, 12
            self.num_mines = 20
        else:
            self.rows, self.cols = 15, 15
            self.num_mines = 30
        self.new_game()
    def update_scores_ui(self):
        try:
            path = Path(self.ruta_usuario) / "extras_scores.json"
            scores = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    scores = json.load(f)
            
            # Puntos acumulados
            self.lbl_points_accum.setText(f"⭐ PUNTOS: {scores.get('buscaminas_puntos', 0)}")
            
            # Highscores
            self.lbl_rec_easy.setText(f"Fácil: {scores.get('buscaminas_highscore_facil', 0)} pts")
            self.lbl_rec_medium.setText(f"Normal: {scores.get('buscaminas_highscore_normal', 0)} pts")
            self.lbl_rec_hard.setText(f"Difícil: {scores.get('buscaminas_highscore_dificil', 0)} pts")
            
            # Historial
            for i in range(self.history_list_lay.count()):
                widget = self.history_list_lay.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
                    
            history = scores.get("buscaminas_history", [])
            if not history:
                lbl_empty = QLabel("Sin partidas recientes")
                lbl_empty.setFont(QFont("Outfit", 9))
                lbl_empty.setStyleSheet("color: rgba(255, 255, 255, 0.4); border: none;")
                self.history_list_lay.addWidget(lbl_empty)
            else:
                # Sort history hierarchically: Difícil (0) > Normal (1) > Fácil (2).
                # Secondary sort by points descending, then by date.
                diff_order = {"Difícil": 0, "Normal": 1, "Fácil": 2}
                sorted_history = sorted(
                    history,
                    key=lambda x: (diff_order.get(x.get("difficulty", "Fácil"), 2), -x.get("points", 0))
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
                    
                    status = match.get("status", "Perdido")
                    lbl_status = QLabel("Win" if status == "Ganado" else "Loss")
                    lbl_status.setFont(QFont("Outfit", 8, QFont.Weight.Bold))
                    status_color = self.colores['exito'] if status == "Ganado" else self.colores['error']
                    lbl_status.setStyleSheet(f"color: {status_color}; border: none;")
                    h_lay.addWidget(lbl_status)
                    
                    diff = match.get("difficulty", "Fácil")
                    lbl_diff = QLabel(diff)
                    lbl_diff.setFont(QFont("Outfit", 8, QFont.Weight.Bold))
                    diff_color = self.colores['acento'] if diff == "Normal" else (self.colores['exito'] if diff == "Fácil" else self.colores['error'])
                    lbl_diff.setStyleSheet(f"color: {diff_color}; border: none;")
                    h_lay.addWidget(lbl_diff)
                    
                    h_lay.addStretch()
                    
                    pts = match.get("points", 0)
                    lbl_pts = QLabel(f"+{pts}" if pts > 0 else "0")
                    lbl_pts.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
                    lbl_pts.setStyleSheet("color: white; border: none;")
                    h_lay.addWidget(lbl_pts)
                    
                    self.history_list_lay.addWidget(item_frame)
        except Exception as e:
            print("Error al actualizar récords de Buscaminas:", e)

    def clear_history_keep_records(self):
        try:
            path = Path(self.ruta_usuario) / "extras_scores.json"
            scores = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    scores = json.load(f)
            
            history = scores.get("buscaminas_history", [])
            if not history:
                return
                
            # Group by difficulty and find the best match (highest points)
            best_by_diff = {}
            for match in history:
                diff = match.get("difficulty", "Fácil")
                pts = match.get("points", 0)
                if diff not in best_by_diff or pts > best_by_diff[diff].get("points", 0):
                    best_by_diff[diff] = match
            
            # Reconstruct history ordered strictly: Difícil, Normal, Fácil
            new_history = []
            for diff in ["Difícil", "Normal", "Fácil"]:
                if diff in best_by_diff:
                    new_history.append(best_by_diff[diff])
                    
            scores["buscaminas_history"] = new_history
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=4)
                
            self.update_scores_ui()
        except Exception as e:
            print("Error al limpiar historial de Buscaminas:", e)

    def save_game_to_history(self, status, pts_won):
        try:
            path_scores = self.ruta_usuario / "extras_scores.json"
            scores = {}
            if path_scores.exists():
                with open(path_scores, "r", encoding="utf-8") as f:
                    scores = json.load(f)
            
            # Sumar puntos acumulados
            old_p = scores.get("buscaminas_puntos", 0)
            scores["buscaminas_puntos"] = old_p + pts_won
            
            # Guardar récord de dificultad activa
            diff_key = "buscaminas_highscore_" + ("facil" if self.dificultad == "Fácil" else ("normal" if self.dificultad == "Normal" else "dificil"))
            old_high = scores.get(diff_key, 0)
            if pts_won > old_high:
                scores[diff_key] = pts_won
            
            # Registrar en historial
            history = scores.get("buscaminas_history", [])
            ahora = time.strftime("%d/%m %H:%M")
            history.insert(0, {
                "date": ahora,
                "status": status,
                "points": pts_won,
                "difficulty": self.dificultad
            })
            scores["buscaminas_history"] = history[:30]
            
            with open(path_scores, "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=4)
        except Exception as e:
            print("Error al registrar partida de Buscaminas:", e)

    def new_game(self):
        self.game_over = False
        self.first_click = True
        self.mines_left = self.num_mines
        self.lbl_mines.setText(f"💣 {self.mines_left:02d}")
        self.btn_reset.setText("😊 NUEVO JUEGO")
        
        # Limpiar grid anterior
        for c_list in self.cells:
            for c in c_list:
                self.grid_layout.removeWidget(c)
                c.deleteLater()
        
        self.cells = []
        cell_size = 38 if self.dificultad == "Fácil" else (32 if self.dificultad == "Normal" else 26)
        
        for r in range(self.rows):
            row_cells = []
            for c in range(self.cols):
                cell = MinesweeperCell(r, c, self.colores)
                cell.setFixedSize(cell_size, cell_size)
                cell.clicked_left.connect(self.handle_reveal)
                cell.clicked_right.connect(self.handle_flag)
                self.grid_layout.addWidget(cell, r, c)
                row_cells.append(cell)
            self.cells.append(row_cells)
            
        # Colocar minas
        mine_pos = random.sample(range(self.rows * self.cols), self.num_mines)
        for p in mine_pos:
            self.cells[p // self.cols][p % self.cols].is_mine = True
            
        # Calcular vecinos
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.cells[r][c].is_mine:
                    self.cells[r][c].neighbor_mines = self.count_neighbors(r, c)
                    
        self.update_scores_ui()
        self.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        if key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            self.new_game()
        elif key == Qt.Key.Key_R:
            self.new_game()

    def count_neighbors(self, r, c):
        cnt = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if self.cells[nr][nc].is_mine: cnt += 1
        return cnt

    def handle_reveal(self, r, c):
        if self.game_over: return
        cell = self.cells[r][c]
        if cell.is_revealed or cell.is_flagged: return
        
        if self.first_click:
            self.first_click = False
            if cell.is_mine:
                cell.is_mine = False
                # Recopilar celdas libres (sin minas y que no sea la celda clickeada)
                empty_cells = []
                for nr in range(self.rows):
                    for nc in range(self.cols):
                        if (nr, nc) != (r, c) and not self.cells[nr][nc].is_mine:
                            empty_cells.append((nr, nc))
                if empty_cells:
                    new_r, new_c = random.choice(empty_cells)
                    self.cells[new_r][new_c].is_mine = True
                
                # Recalcular todos los conteos de vecinos
                for nr in range(self.rows):
                    for nc in range(self.cols):
                        if not self.cells[nr][nc].is_mine:
                            self.cells[nr][nc].neighbor_mines = self.count_neighbors(nr, nc)
                        else:
                            self.cells[nr][nc].neighbor_mines = 0

        cell.is_revealed = True
        if cell.is_mine:
            self.reveal_all_mines()
            self.game_over = True
            self.btn_reset.setText("😵 ¡BOOM!")
            self.save_game_to_history("Perdido", 0)
            self.update_scores_ui()
            QMessageBox.critical(self, "Buscaminas", "¡Has pisado una mina!")
        else:
            style = f"background: {self.colores['bg_principal']}; border: 1px solid rgba(255,255,255,0.03); border-radius: 5px; font-weight: 900;"
            if cell.neighbor_mines > 0:
                cell.setText(str(cell.neighbor_mines))
                colors = ["#38BDF8", "#34D399", "#F87171", "#C084FC", "#FBBF24", "#22D3EE", "#F472B6", "#E2E2E2"]
                cell.setStyleSheet(style + f"color: {colors[min(cell.neighbor_mines-1, 7)]};")
            else:
                cell.setStyleSheet(style)
                # Auto-revelar vecinos vacíos
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            self.handle_reveal(nr, nc)
        self.check_win()

    def handle_flag(self, r, c):
        if self.game_over: return
        cell = self.cells[r][c]
        if cell.is_revealed: return
        
        cell.is_flagged = not cell.is_flagged
        if cell.is_flagged:
            cell.setText("🚩")
            cell.setStyleSheet(f"background: rgba(239, 68, 68, 0.15); border: 1.5px solid {self.colores['error']}; border-radius: 5px; font-size: 11px;")
            self.mines_left -= 1
        else:
            cell.setText("")
            cell.reset_ui()
            self.mines_left += 1
        self.lbl_mines.setText(f"💣 {self.mines_left:02d}")

    def reveal_all_mines(self):
        for r_list in self.cells:
            for c in r_list:
                if c.is_mine:
                    c.setText("💣")
                    c.setStyleSheet(f"background: rgba(239, 68, 68, 0.25); border: 1.5px solid {self.colores['error']}; border-radius: 5px; font-size: 12px;")
                elif c.is_flagged and not c.is_mine:
                    # Banderas erróneas marcadas con X roja
                    c.setText("❌")
                    c.setStyleSheet("background: rgba(239, 68, 68, 0.45); border: 1.5px solid #EF4444; border-radius: 5px; font-size: 12px;")

    def check_win(self):
        revealed_count = sum(c.is_revealed for row in self.cells for c in row)
        if revealed_count == (self.rows * self.cols - self.num_mines):
            self.game_over = True
            self.btn_reset.setText("😎 ¡GANASTE!")
            
            # Autocompletar banderas en minas no marcadas
            for row in self.cells:
                for c in row:
                    if c.is_mine and not c.is_flagged:
                        c.is_flagged = True
                        c.setText("🚩")
                        c.setStyleSheet(f"background: rgba(52, 211, 153, 0.2); border: 1.5px solid {self.colores['exito']}; border-radius: 5px; font-size: 11px;")
            self.lbl_mines.setText("💣 00")

            pts = 5 if self.dificultad == "Fácil" else (7 if self.dificultad == "Normal" else 10)
            from ..utils.score_manager import ScoreManager
            ScoreManager(self.ruta_usuario).sumar_puntos("buscaminas", pts)
            self.save_game_to_history("Ganado", pts)
            self.update_scores_ui()

            QMessageBox.information(
                self, "🎉 ¡Felicidades!",
                f"¡Has despejado todo el tablero en dificultad {self.dificultad}!\n\n"
                f"Ganaste +{pts} puntos de recompensa."
            )
