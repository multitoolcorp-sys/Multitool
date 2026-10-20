"""
galaga.py - Juego Retro Arcade Galaga
Implementación auténtica del clásico Galaga: enjambres en formación, ataque en picada con trayectorias curvas,
estrellas con desplazamiento parallax, jefes Galaga resistentes (2 impactos), disparos rápidos y récords.
"""

import math
import random
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QPen, QPolygonF

from ..utils.score_manager import ScoreManager


class GalagaCanvas(QWidget):
    """Lienzo de juego para Galaga con campo estelar animado y sprites vectoriales."""
    def __init__(self, parent_game):
        super().__init__()
        self.game = parent_game
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(560, 480)
        self.keys_pressed = set()

    def keyPressEvent(self, event):
        self.keys_pressed.add(event.key())
        if event.key() == Qt.Key.Key_Space:
            self.game.disparar()
        elif event.key() in (Qt.Key.Key_P, Qt.Key.Key_Pause):
            self.game.toggle_pausa()

    def keyReleaseEvent(self, event):
        if event.key() in self.keys_pressed:
            self.keys_pressed.remove(event.key())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Fondo Espacial Negro
        painter.fillRect(0, 0, w, h, QColor("#05050C"))

        # 2. Campo Estelar con Efecto Parallax de Desplazamiento
        for s in self.game.estrellas:
            px = int(s["x"] * w)
            py = int((s["y"] * h) % h)
            col = QColor(s["color"])
            painter.setPen(QPen(col, s["size"]))
            painter.drawPoint(px, py)

        # 3. Dibujar Enjambre de Enemigos Galaga
        for en in self.game.enemigos:
            if not en["vivo"]:
                continue
            ex = en["x"] * w
            ey = en["y"] * h
            ew = en["w"] * w
            eh = en["h"] * h
            tipo = en["tipo"]
            hp = en.get("hp", 1)

            self._dibujar_enemigo(painter, ex, ey, ew, eh, tipo, hp)

        # 4. Rayo Tractor del Jefe Galaga (si está activo)
        for beam in self.game.tractor_beams:
            bx = beam["x"] * w
            by = beam["y"] * h
            bw = beam["w"] * w
            bh = beam["h"] * h
            painter.setBrush(QBrush(QColor(56, 189, 248, 60)))
            painter.setPen(QPen(QColor(56, 189, 248, 180), 1, Qt.PenStyle.DashLine))
            poly = QPolygonF([
                QPointF(bx - bw*0.2, by),
                QPointF(bx + bw*0.2, by),
                QPointF(bx + bw*1.2, by + bh),
                QPointF(bx - bw*1.2, by + bh)
            ])
            painter.drawPolygon(poly)

        # 5. Dibujar Disparos Láser del Jugador (Dual/Single)
        painter.setPen(QPen(QColor("#F43F5E"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for shot in self.game.disparos_jugador:
            sx = shot["x"] * w
            sy = shot["y"] * h
            painter.drawLine(int(sx), int(sy), int(sx), int(sy - h * 0.03))

        # 6. Dibujar Misiles Enemigos
        painter.setPen(QPen(QColor("#FBBF24"), 2))
        for m in self.game.misiles_enemigos:
            mx = m["x"] * w
            my = m["y"] * h
            painter.drawEllipse(QRectF(mx - 2, my - 2, 4, 4))

        # 7. Partículas de Explosión Cósmica
        for p in self.game.particulas:
            painter.setPen(QPen(p["color"], p["tam"]))
            painter.drawPoint(int(p["x"] * w), int(p["y"] * h))

        # 8. Dibujar Caza Espacial del Jugador (Galaga Fighter)
        px = self.game.player_x * w
        py = self.game.player_y * h
        pw = self.game.player_w * w
        ph = self.game.player_h * h

        self._dibujar_nave_jugador(painter, px, py, pw, ph)

        # 9. Overlays de Estado
        if self.game.estado != "JUGANDO":
            painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 185))
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Inter", 18, QFont.Weight.Bold))

            if self.game.estado == "GAME_OVER":
                painter.setPen(QColor("#F87171"))
                painter.drawText(0, int(h * 0.45), w, 40, Qt.AlignmentFlag.AlignCenter, "🚀 GAME OVER 🚀")
                painter.setFont(QFont("Inter", 11))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(0, int(h * 0.53), w, 30, Qt.AlignmentFlag.AlignCenter, "Presiona [REINICIAR] para intentarlo de nuevo")
            elif self.game.estado == "STAGE_CLEAR":
                painter.setPen(QColor("#38BDF8"))
                painter.drawText(0, int(h * 0.45), w, 40, Qt.AlignmentFlag.AlignCenter, "⭐ STAGE CLEAR ⭐")
                painter.setFont(QFont("Inter", 11))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(0, int(h * 0.53), w, 30, Qt.AlignmentFlag.AlignCenter, "Preparando siguiente oleada estelar...")
            elif self.game.estado == "PAUSA":
                painter.setPen(QColor("#FBBF24"))
                painter.drawText(0, int(h * 0.48), w, 40, Qt.AlignmentFlag.AlignCenter, "⏸ PAUSA")

    def _dibujar_enemigo(self, painter, x, y, w, h, tipo, hp):
        """Dibuja las diferentes clases de alienígenas Galaga."""
        if tipo == "BOSS":  # Boss Galaga (Verde/Azul, 2 Vidas)
            col_prim = QColor("#10B981") if hp == 2 else QColor("#3B82F6")
            painter.setBrush(QBrush(col_prim))
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            # Escudo y cuerpo
            poly = QPolygonF([
                QPointF(x, y + h*0.2),
                QPointF(x + w*0.5, y),
                QPointF(x + w, y + h*0.2),
                QPointF(x + w*0.8, y + h),
                QPointF(x + w*0.5, y + h*0.8),
                QPointF(x + w*0.2, y + h)
            ])
            painter.drawPolygon(poly)
            # Ojos / Cuernos
            painter.setBrush(QBrush(QColor("#F59E0B")))
            painter.drawEllipse(QRectF(x + w*0.3, y + h*0.35, w*0.16, h*0.2))
            painter.drawEllipse(QRectF(x + w*0.54, y + h*0.35, w*0.16, h*0.2))

        elif tipo == "BUTTERFLY":  # Red Butterfly / Goei (Rojo/Amarillo)
            painter.setBrush(QBrush(QColor("#EF4444")))
            painter.setPen(QPen(QColor("#FDE047"), 1))
            # Alas y forma de mariposa espacial
            poly = QPolygonF([
                QPointF(x, y + h*0.5),
                QPointF(x + w*0.3, y),
                QPointF(x + w*0.5, y + h*0.3),
                QPointF(x + w*0.7, y),
                QPointF(x + w, y + h*0.5),
                QPointF(x + w*0.5, y + h)
            ])
            painter.drawPolygon(poly)

        else:  # BEES (Abejas Amarillas Zako)
            painter.setBrush(QBrush(QColor("#FACC15")))
            painter.setPen(QPen(QColor("#3B82F6"), 1))
            # Cuerpo ovalado y alas azules
            painter.drawEllipse(QRectF(x + w*0.2, y + h*0.2, w*0.6, h*0.7))
            painter.setBrush(QBrush(QColor("#38BDF8")))
            painter.drawEllipse(QRectF(x, y + h*0.3, w*0.25, h*0.4))
            painter.drawEllipse(QRectF(x + w*0.75, y + h*0.3, w*0.25, h*0.4))

    def _dibujar_nave_jugador(self, painter, x, y, w, h):
        """Dibuja el clásico caza blanco con alerones rojos de Galaga."""
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(QColor("#E2E8F0"), 1))

        # Fuselaje principal
        poly = QPolygonF([
            QPointF(x, y),
            QPointF(x + w*0.2, y + h*0.6),
            QPointF(x + w*0.2, y + h),
            QPointF(x - w*0.2, y + h),
            QPointF(x - w*0.2, y + h*0.6)
        ])
        painter.drawPolygon(poly)

        # Alerones rojos
        painter.setBrush(QBrush(QColor("#EF4444")))
        painter.setPen(Qt.PenStyle.NoPen)
        # Ala Izquierda
        poly_l = QPolygonF([
            QPointF(x - w*0.2, y + h*0.4),
            QPointF(x - w*0.5, y + h*0.8),
            QPointF(x - w*0.5, y + h),
            QPointF(x - w*0.2, y + h*0.85)
        ])
        painter.drawPolygon(poly_l)

        # Ala Derecha
        poly_r = QPolygonF([
            QPointF(x + w*0.2, y + h*0.4),
            QPointF(x + w*0.5, y + h*0.8),
            QPointF(x + w*0.5, y + h),
            QPointF(x + w*0.2, y + h*0.85)
        ])
        painter.drawPolygon(poly_r)

        # Propulsor azul brillante
        painter.setBrush(QBrush(QColor("#38BDF8")))
        painter.drawRect(QRectF(x - w*0.1, y + h*0.9, w*0.2, h*0.2))


class TabGalaga(QWidget):
    """Submódulo del juego Galaga Arcade con oleadas, picadas y récords."""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.score_mgr = ScoreManager(ruta_usuario)
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        # Estado del juego
        self.estado = "JUGANDO"
        self.score = 0
        self.stage = 1
        self.vidas = 3
        self.highscore = self.score_mgr.cargar().get("galaga_highscore", 0)

        # Jugador
        self.player_x = 0.5
        self.player_y = 0.88
        self.player_w = 0.05
        self.player_h = 0.04
        self.player_vel = 0.013

        # Listas de entidades
        self.disparos_jugador = []
        self.misiles_enemigos = []
        self.particulas = []
        self.enemigos = []
        self.tractor_beams = []

        # Estrellas de fondo animadas
        random.seed(1337)
        self.estrellas = []
        colores_estrellas = ["#FFFFFF", "#93C5FD", "#FDE047", "#F472B6"]
        for _ in range(70):
            self.estrellas.append({
                "x": random.random(),
                "y": random.random(),
                "speed": random.uniform(0.002, 0.007),
                "size": random.randint(1, 2),
                "color": random.choice(colores_estrellas)
            })

        self.inicializar_ui()
        self.reiniciar_juego()

        # Timer a 60 FPS
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._game_loop)
        self.timer.start()

    def inicializar_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #121218;
                width: 8px;
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #2D2D3D;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: #EF4444;
            }
        """)

        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Panel Lateral Izquierdo Vertical (HUD & Controles)
        side_panel = QFrame()
        side_panel.setFixedWidth(220)
        side_panel.setMinimumHeight(520)
        side_panel.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)
        side_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Título
        lbl_tit = QLabel("🚀 GALAGA ARCADE")
        lbl_tit.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: #EF4444; padding-bottom: 2px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(lbl_tit)

        # Tarjeta 1UP SCORE
        card_score = QFrame()
        card_score.setFixedHeight(54)
        card_score.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_sc = QVBoxLayout(card_score)
        v_sc.setContentsMargins(10, 6, 10, 6)
        v_sc.setSpacing(2)
        lbl_sc_tit = QLabel("1UP SCORE")
        lbl_sc_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_sc.addWidget(lbl_sc_tit)
        self.lbl_score = QLabel("00000")
        self.lbl_score.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.lbl_score.setStyleSheet("color: #EF4444;")
        v_sc.addWidget(self.lbl_score)
        side_layout.addWidget(card_score)

        # Tarjeta HI-SCORE
        card_hi = QFrame()
        card_hi.setFixedHeight(54)
        card_hi.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_hi = QVBoxLayout(card_hi)
        v_hi.setContentsMargins(10, 6, 10, 6)
        v_hi.setSpacing(2)
        lbl_hi_tit = QLabel("HI-SCORE")
        lbl_hi_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_hi.addWidget(lbl_hi_tit)
        self.lbl_highscore = QLabel(f"{self.highscore:05d}")
        self.lbl_highscore.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.lbl_highscore.setStyleSheet("color: #FBBF24;")
        v_hi.addWidget(self.lbl_highscore)
        side_layout.addWidget(card_hi)

        # Tarjeta STAGE
        card_st = QFrame()
        card_st.setFixedHeight(54)
        card_st.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_st = QVBoxLayout(card_st)
        v_st.setContentsMargins(10, 6, 10, 6)
        v_st.setSpacing(2)
        lbl_st_tit = QLabel("STAGE")
        lbl_st_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_st.addWidget(lbl_st_tit)
        self.lbl_stage = QLabel("1")
        self.lbl_stage.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.lbl_stage.setStyleSheet("color: #38BDF8;")
        v_st.addWidget(self.lbl_stage)
        side_layout.addWidget(card_st)

        # Tarjeta SHIPS
        card_sh = QFrame()
        card_sh.setFixedHeight(54)
        card_sh.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_sh = QVBoxLayout(card_sh)
        v_sh.setContentsMargins(10, 6, 10, 6)
        v_sh.setSpacing(2)
        lbl_sh_tit = QLabel("NAVES (SHIPS)")
        lbl_sh_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_sh.addWidget(lbl_sh_tit)
        self.lbl_vidas = QLabel("🚀🚀🚀")
        self.lbl_vidas.setFont(QFont("Segoe UI Emoji", 11, QFont.Weight.Bold))
        self.lbl_vidas.setStyleSheet("color: #34D399;")
        v_sh.addWidget(self.lbl_vidas)
        side_layout.addWidget(card_sh)

        side_layout.addSpacing(4)

        # Botones de Acción
        self.btn_pausa = QPushButton("⏸ Pausar")
        self.btn_pausa.setFixedHeight(34)
        self.btn_pausa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pausa.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')};
                color: #FFFFFF;
                border-radius: 8px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#4F46E5')}; }}
        """)
        self.btn_pausa.clicked.connect(self.toggle_pausa)
        side_layout.addWidget(self.btn_pausa)

        self.btn_reiniciar = QPushButton("🔄 Reiniciar")
        self.btn_reiniciar.setFixedHeight(34)
        self.btn_reiniciar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reiniciar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #FFFFFF;
                border-radius: 8px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.colores.get('error', '#F87171')}; }}
        """)
        self.btn_reiniciar.clicked.connect(self.reiniciar_juego)
        side_layout.addWidget(self.btn_reiniciar)

        # Guía de Teclas
        lbl_guia = QLabel("🎮 <b>Controles:</b><br>• [A/D] o [←/→] Mover<br>• [Espacio] Doble Láser<br>• [P] Pausa")
        lbl_guia.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; color: #9CA3AF; font-size: 8pt; border-radius: 8px; padding: 6px;")
        side_layout.addWidget(lbl_guia)

        side_layout.addStretch()
        main_layout.addWidget(side_panel)

        # 2. Área Central / Derecha con el Canvas Proporcional
        canvas_container = QWidget()
        c_layout = QVBoxLayout(canvas_container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.canvas = GalagaCanvas(self)
        self.canvas.setFixedSize(560, 490)
        self.canvas.setStyleSheet("border-radius: 12px; border: 2px solid rgba(239, 68, 68, 0.25);")
        c_layout.addWidget(self.canvas)

        main_layout.addWidget(canvas_container)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def reiniciar_juego(self):
        self.estado = "JUGANDO"
        self.score = 0
        self.stage = 1
        self.vidas = 3
        try:
            from console import CheatManager
            v_ovr = CheatManager.get_instance().get_lives_override()
            if v_ovr:
                self.vidas = v_ovr
        except Exception: pass
        self.player_x = 0.5
        self.disparos_jugador.clear()
        self.misiles_enemigos.clear()
        self.particulas.clear()
        self.tractor_beams.clear()
        self._crear_escuadron()
        self._actualizar_hud()
        self.canvas.setFocus()

    def _crear_escuadron(self):
        self.enemigos.clear()
        # Formación clásica Galaga:
        # Fila 0: 4 Bosses (Jefes)
        # Fila 1-2: 8 Mariposas Rojas cada una
        # Fila 3-4: 10 Abejas Amarillas cada una

        # Bosses
        for c in range(4):
            self.enemigos.append({
                "home_x": 0.28 + c * 0.14, "home_y": 0.12,
                "x": 0.28 + c * 0.14, "y": 0.12,
                "w": 0.055, "h": 0.045,
                "tipo": "BOSS", "hp": 2, "pts_grid": 150, "pts_dive": 400,
                "vivo": True, "en_picada": False, "t_dive": 0
            })

        # Mariposas Rojas (Goeis)
        for r in range(2):
            for c in range(8):
                self.enemigos.append({
                    "home_x": 0.18 + c * 0.09, "home_y": 0.18 + r * 0.055,
                    "x": 0.18 + c * 0.09, "y": 0.18 + r * 0.055,
                    "w": 0.045, "h": 0.038,
                    "tipo": "BUTTERFLY", "hp": 1, "pts_grid": 80, "pts_dive": 160,
                    "vivo": True, "en_picada": False, "t_dive": 0
                })

        # Abejas Amarillas (Zako)
        for r in range(2):
            for c in range(10):
                self.enemigos.append({
                    "home_x": 0.14 + c * 0.08, "home_y": 0.30 + r * 0.055,
                    "x": 0.14 + c * 0.08, "y": 0.30 + r * 0.055,
                    "w": 0.042, "h": 0.035,
                    "tipo": "BEE", "hp": 1, "pts_grid": 50, "pts_dive": 100,
                    "vivo": True, "en_picada": False, "t_dive": 0
                })

    def toggle_pausa(self):
        if self.estado == "JUGANDO":
            self.estado = "PAUSA"
            self.btn_pausa.setText("▶ Reanudar")
        elif self.estado == "PAUSA":
            self.estado = "JUGANDO"
            self.btn_pausa.setText("⏸ Pausar")
            self.canvas.setFocus()

    def disparar(self):
        if self.estado == "JUGANDO" and len(self.disparos_jugador) < 4:
            # Doble cañón láser
            self.disparos_jugador.append({"x": self.player_x - 0.012, "y": self.player_y - 0.02, "vel": 0.018})
            self.disparos_jugador.append({"x": self.player_x + 0.012, "y": self.player_y - 0.02, "vel": 0.018})

    def _game_loop(self):
        if self.estado != "JUGANDO":
            self.canvas.update()
            return

        # 1. Animar Estrellas de Fondo
        for s in self.estrellas:
            s["y"] = (s["y"] + s["speed"]) % 1.0

        # 2. Movimiento del Jugador
        keys = self.canvas.keys_pressed
        if Qt.Key.Key_Left in keys or Qt.Key.Key_A in keys:
            self.player_x = max(0.04, self.player_x - self.player_vel)
        if Qt.Key.Key_Right in keys or Qt.Key.Key_D in keys:
            self.player_x = min(0.96, self.player_x + self.player_vel)

        # 3. Movimiento y Colisiones de Láseres del Jugador
        for shot in self.disparos_jugador[:]:
            shot["y"] -= shot["vel"]
            if shot["y"] < 0:
                self.disparos_jugador.remove(shot)
                continue

            sx = shot["x"]
            sy = shot["y"]
            impacto = False

            for en in self.enemigos:
                if en["vivo"] and (en["x"] <= sx <= en["x"] + en["w"]) and (en["y"] <= sy <= en["y"] + en["h"]):
                    en["hp"] -= 1
                    impacto = True
                    if en["hp"] <= 0:
                        en["vivo"] = False
                        pts = en["pts_dive"] if en["en_picada"] else en["pts_grid"]
                        self.score += pts
                        self._crear_explosion(en["x"] + en["w"]/2, en["y"] + en["h"]/2, QColor("#F43F5E"))
                    else:
                        # Jefe dañado cambia de color
                        self._crear_explosion(sx, sy, QColor("#38BDF8"))

                    vivos = [e for e in self.enemigos if e["vivo"]]
                    if not vivos:
                        self._stage_clear()
                    break

            if impacto and shot in self.disparos_jugador:
                self.disparos_jugador.remove(shot)

        # 4. Dinámica del Enjambre & Ataques en Picada (Diving)
        vivos = [e for e in self.enemigos if e["vivo"]]
        en_dive_count = sum(1 for e in vivos if e["en_picada"])

        # Lanzar nuevos atacantes en picada periódicamente
        if en_dive_count < 3 and vivos and random.random() < 0.025:
            candidatos = [e for e in vivos if not e["en_picada"]]
            if candidatos:
                atacante = random.choice(candidatos)
                atacante["en_picada"] = True
                atacante["t_dive"] = 0
                atacante["start_x"] = atacante["x"]
                atacante["dir_loop"] = random.choice([-1, 1])

        # Actualizar posiciones de enemigos
        time_sec = QTimer().remainingTime()  # oscilación de formación
        for en in vivos:
            if not en["en_picada"]:
                # Suave balanceo en la formación del nido
                en["x"] = en["home_x"] + math.sin(random.random() * 0.1 + en["home_y"] * 10) * 0.005
                en["y"] = en["home_y"]
            else:
                # Trayectoria curva en S de ataque hacia el jugador
                en["t_dive"] += 0.015
                t = en["t_dive"]
                en["y"] += 0.008 + self.stage * 0.001
                en["x"] = en["start_x"] + math.sin(t * 4.0) * (0.12 * en["dir_loop"])

                # Disparo enemigo durante la picada
                if random.random() < 0.03 and len(self.misiles_enemigos) < 5:
                    self.misiles_enemigos.append({
                        "x": en["x"] + en["w"]/2,
                        "y": en["y"] + en["h"],
                        "vel": 0.009 + self.stage * 0.001
                    })

                # Si sale de pantalla, reaparece arriba en formación
                if en["y"] > 1.05:
                    en["y"] = -0.05
                    en["x"] = en["home_x"]
                    en["en_picada"] = False

                # Colisión con la nave del jugador
                if abs(en["x"] + en["w"]/2 - self.player_x) < (self.player_w/2 + en["w"]/2) and abs(en["y"] + en["h"]/2 - self.player_y) < (self.player_h/2 + en["h"]/2):
                    en["vivo"] = False
                    self._crear_explosion(self.player_x, self.player_y, QColor("#FFFFFF"))
                    self.vidas -= 1
                    if self.vidas <= 0:
                        self._game_over()
                        return

        # 5. Movimiento de Misiles Enemigos
        for m in self.misiles_enemigos[:]:
            m["y"] += m["vel"]
            if m["y"] > 0.96:
                self.misiles_enemigos.remove(m)
                continue

            # Colisión con el Jugador
            if abs(m["x"] - self.player_x) < self.player_w/2 and abs(m["y"] - self.player_y) < self.player_h/2:
                self._crear_explosion(self.player_x, self.player_y, QColor("#EF4444"))
                self.misiles_enemigos.remove(m)
                try:
                    from console import CheatManager
                    god = CheatManager.get_instance().is_godmode()
                except Exception:
                    god = False
                if not god:
                    self.vidas -= 1
                    if self.vidas <= 0:
                        self._game_over()
                        return
                    else:
                        self._actualizar_hud()

        # 6. Partículas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vida"] -= 1
            if p["vida"] <= 0:
                self.particulas.remove(p)

        self._actualizar_hud()
        self.canvas.update()

    def _crear_explosion(self, x, y, color):
        for _ in range(16):
            ang = random.uniform(0, 6.28)
            spd = random.uniform(0.003, 0.01)
            self.particulas.append({
                "x": x, "y": y,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd,
                "vida": random.randint(12, 24),
                "tam": random.randint(2, 4),
                "color": color
            })

    def _stage_clear(self):
        self.estado = "STAGE_CLEAR"
        self.score += 1000
        self.stage += 1
        self.score_mgr.sumar_puntos("galaga", 10)
        QTimer.singleShot(2200, self._continuar_siguiente_stage)

    def _continuar_siguiente_stage(self):
        self.disparos_jugador.clear()
        self.misiles_enemigos.clear()
        self._crear_escuadron()
        self.estado = "JUGANDO"
        self.canvas.setFocus()

    def _game_over(self):
        self.estado = "GAME_OVER"
        if self.score > self.highscore:
            self.highscore = self.score
            self.score_mgr.actualizar_highscore("galaga", self.highscore)
        self.score_mgr.sumar_puntos("galaga", max(5, self.score // 100))
        self._actualizar_hud()

    def _actualizar_hud(self):
        self.lbl_score.setText(f"1UP: {self.score:05d}")
        self.lbl_highscore.setText(f"HI-SCORE: {self.highscore:05d}")
        self.lbl_stage.setText(f"STAGE: {self.stage}")
        naves = "🚀" * max(0, self.vidas)
        self.lbl_vidas.setText(f"SHIPS: {naves}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background-color: {colores.get('bg_principal', '#121218')}; color: white;")

    def cleanup(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        if self.score > 0 and getattr(self, 'estado', '') == "JUGANDO":
            self.score_mgr.sumar_puntos("galaga", max(3, self.score // 100))
            self.score_mgr.actualizar_highscore("galaga", self.score)
