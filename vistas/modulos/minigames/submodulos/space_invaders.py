"""
space_invaders.py - Juego Retro Arcade Space Invaders
Implementación con formato arcade clásico: oleadas de invasores con marcha sincronizada,
platillo volador OVNI misterioso, 4 búnkeres destructibles, cañón láser, vidas y récord.
"""

import random
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QPen, QPainterPath

from ..utils.score_manager import ScoreManager


class SpaceInvadersCanvas(QWidget):
    """Lienzo de juego para Space Invaders con gráficos vectoriales y física arcade."""
    def __init__(self, parent_game):
        super().__init__()
        self.game = parent_game
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(560, 480)
        self.keys_pressed = set()

    def keyPressEvent(self, event):
        self.keys_pressed.add(event.key())
        if event.key() == Qt.Key.Key_Space:
            self.game.disparar_jugador()
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

        # Fondo Espacial Oscuro con estrellas
        painter.fillRect(0, 0, w, h, QColor("#080810"))
        
        # Estrellas de fondo
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        for sx, sy in self.game.estrellas:
            px = int((sx * w) % w)
            py = int((sy * h) % h)
            painter.drawPoint(px, py)

        # Línea de defensa inferior
        painter.setPen(QPen(QColor("#34D399"), 2))
        painter.drawLine(0, int(h * 0.92), w, int(h * 0.92))

        # 1. Dibujar Búnkeres / Escudos Protectores
        for b in self.game.bunkers:
            if b["hp"] > 0:
                alpha = int((b["hp"] / 4.0) * 255)
                painter.setBrush(QBrush(QColor(52, 211, 153, alpha)))
                painter.setPen(QPen(QColor(16, 185, 129, alpha), 1))
                bx = b["x"] * w
                by = b["y"] * h
                bw = b["w"] * w
                bh = b["h"] * h
                painter.drawRoundedRect(QRectF(bx, by, bw, bh), 2, 2)

        # 2. Dibujar Invasores
        for inv in self.game.invaders:
            if not inv["vivo"]:
                continue
            ix = inv["x"] * w
            iy = inv["y"] * h
            iw = inv["w"] * w
            ih = inv["h"] * h
            tipo = inv["tipo"]
            anim = self.game.anim_frame

            if tipo == 0:  # Pulpo / Squid (Fila superior - Púrpura)
                col = QColor("#C084FC")
            elif tipo == 1:  # Cangrejo / Crab (Filas medias - Azul Cyan)
                col = QColor("#38BDF8")
            else:  # Calamar / Octopus (Filas inferiores - Verde Lima)
                col = QColor("#4ADE80")

            painter.setBrush(QBrush(col))
            painter.setPen(Qt.PenStyle.NoPen)
            self._dibujar_alien(painter, ix, iy, iw, ih, tipo, anim, col)

        # 3. Dibujar Platillo Volador / OVNI
        if self.game.ufo["activo"]:
            ux = self.game.ufo["x"] * w
            uy = self.game.ufo["y"] * h
            uw = self.game.ufo["w"] * w
            uh = self.game.ufo["h"] * h
            painter.setBrush(QBrush(QColor("#F43F5E")))
            painter.setPen(QPen(QColor("#FFE4E6"), 1))
            painter.drawEllipse(QRectF(ux, uy + uh*0.2, uw, uh*0.6))
            painter.drawEllipse(QRectF(ux + uw*0.25, uy, uw*0.5, uh*0.5))

        # 4. Dibujar Disparos del Jugador
        painter.setPen(QPen(QColor("#FBBF24"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for laser in self.game.lasers_jugador:
            lx = laser["x"] * w
            ly = laser["y"] * h
            painter.drawLine(int(lx), int(ly), int(lx), int(ly - h * 0.025))

        # 5. Dibujar Bombas de Invasores
        painter.setPen(QPen(QColor("#F87171"), 2))
        for bomba in self.game.bombas_alien:
            bx = bomba["x"] * w
            by = bomba["y"] * h
            painter.drawLine(int(bx - 2), int(by), int(bx + 2), int(by))
            painter.drawLine(int(bx), int(by), int(bx), int(by + h * 0.02))

        # 6. Dibujar Partículas de Explosión
        for p in self.game.particulas:
            painter.setPen(QPen(p["color"], p["tam"]))
            painter.drawPoint(int(p["x"] * w), int(p["y"] * h))

        # 7. Dibujar Cañón Láser del Jugador
        px = self.game.player_x * w
        py = self.game.player_y * h
        pw = self.game.player_w * w
        ph = self.game.player_h * h

        painter.setBrush(QBrush(QColor("#34D399")))
        painter.setPen(QPen(QColor("#10B981"), 1.5))
        # Base
        painter.drawRect(QRectF(px - pw/2, py + ph*0.4, pw, ph*0.6))
        # Torreta central
        painter.drawRect(QRectF(px - pw*0.3, py + ph*0.2, pw*0.6, ph*0.3))
        # Cañón
        painter.drawRect(QRectF(px - pw*0.08, py, pw*0.16, ph*0.3))

        # 8. Overlays de Estado (Game Over / Pausa / Victoria)
        if self.game.estado != "JUGANDO":
            painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 180))
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Inter", 18, QFont.Weight.Bold))
            
            if self.game.estado == "GAME_OVER":
                painter.setPen(QColor("#F87171"))
                painter.drawText(0, int(h * 0.45), w, 40, Qt.AlignmentFlag.AlignCenter, "👾 GAME OVER 👾")
                painter.setFont(QFont("Inter", 11))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(0, int(h * 0.53), w, 30, Qt.AlignmentFlag.AlignCenter, "Presiona [REINICIAR] o [ESPACIO] para jugar de nuevo")
            elif self.game.estado == "VICTORIA":
                painter.setPen(QColor("#34D399"))
                painter.drawText(0, int(h * 0.45), w, 40, Qt.AlignmentFlag.AlignCenter, "⭐ ¡OLEADA COMPLETADA! ⭐")
                painter.setFont(QFont("Inter", 11))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(0, int(h * 0.53), w, 30, Qt.AlignmentFlag.AlignCenter, "Siguiente oleada cargando...")
            elif self.game.estado == "PAUSA":
                painter.setPen(QColor("#FBBF24"))
                painter.drawText(0, int(h * 0.48), w, 40, Qt.AlignmentFlag.AlignCenter, "⏸ PAUSA")

    def _dibujar_alien(self, painter, x, y, w, h, tipo, anim, color):
        """Dibuja un sprite estilizado del alienígena."""
        painter.drawRoundedRect(QRectF(x, y + h*0.2, w, h*0.6), 3, 3)
        # Ojos
        painter.setBrush(QBrush(QColor("#080810")))
        painter.drawRect(QRectF(x + w*0.2, y + h*0.35, w*0.18, h*0.2))
        painter.drawRect(QRectF(x + w*0.62, y + h*0.35, w*0.18, h*0.2))
        # Antenas / Tentáculos animados
        painter.setBrush(QBrush(color))
        if anim == 0:
            painter.drawRect(QRectF(x + w*0.1, y + h*0.8, w*0.2, h*0.2))
            painter.drawRect(QRectF(x + w*0.7, y + h*0.8, w*0.2, h*0.2))
        else:
            painter.drawRect(QRectF(x + w*0.3, y + h*0.8, w*0.15, h*0.2))
            painter.drawRect(QRectF(x + w*0.55, y + h*0.8, w*0.15, h*0.2))


class TabSpaceInvaders(QWidget):
    """Submódulo Arcade de Space Invaders con tabla de récords y ciclo de juego."""
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.score_mgr = ScoreManager(ruta_usuario)
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        # Variables de estado
        self.estado = "JUGANDO"  # JUGANDO, PAUSA, GAME_OVER, VICTORIA
        self.score = 0
        self.oleada = 1
        self.vidas = 3
        self.highscore = self.score_mgr.cargar().get("space_invaders_highscore", 0)

        # Entidades
        self.player_x = 0.5
        self.player_y = 0.88
        self.player_w = 0.06
        self.player_h = 0.035
        self.player_vel = 0.012

        self.lasers_jugador = []
        self.bombas_alien = []
        self.particulas = []
        self.invaders = []
        self.bunkers = []
        self.ufo = {"activo": False, "x": 0.0, "y": 0.06, "w": 0.08, "h": 0.035, "vel": 0.004}

        self.dir_invaders = 1  # 1: derecha, -1: izquierda
        self.vel_invaders = 0.0018
        self.anim_frame = 0
        self.tick_count = 0

        # Estrellas de fondo
        random.seed(42)
        self.estrellas = [(random.random(), random.random()) for _ in range(50)]

        self.inicializar_ui()
        self.reiniciar_juego()

        # Timer principal del bucle de juego (60 FPS)
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
                background: #6366F1;
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
        lbl_tit = QLabel("👾 SPACE INVADERS")
        lbl_tit.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: #6366F1; padding-bottom: 2px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(lbl_tit)

        # Tarjeta SCORE
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
        self.lbl_score.setStyleSheet("color: #34D399;")
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

        # Tarjeta OLEADA
        card_ol = QFrame()
        card_ol.setFixedHeight(54)
        card_ol.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_ol = QVBoxLayout(card_ol)
        v_ol.setContentsMargins(10, 6, 10, 6)
        v_ol.setSpacing(2)
        lbl_ol_tit = QLabel("OLEADA")
        lbl_ol_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_ol.addWidget(lbl_ol_tit)
        self.lbl_oleada = QLabel("1")
        self.lbl_oleada.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.lbl_oleada.setStyleSheet("color: #38BDF8;")
        v_ol.addWidget(self.lbl_oleada)
        side_layout.addWidget(card_ol)

        # Tarjeta VIDAS
        card_vi = QFrame()
        card_vi.setFixedHeight(54)
        card_vi.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_vi = QVBoxLayout(card_vi)
        v_vi.setContentsMargins(10, 6, 10, 6)
        v_vi.setSpacing(2)
        lbl_vi_tit = QLabel("VIDAS")
        lbl_vi_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_vi.addWidget(lbl_vi_tit)
        self.lbl_vidas = QLabel("❤️❤️❤️")
        self.lbl_vidas.setFont(QFont("Segoe UI Emoji", 11, QFont.Weight.Bold))
        self.lbl_vidas.setStyleSheet("color: #F87171;")
        v_vi.addWidget(self.lbl_vidas)
        side_layout.addWidget(card_vi)

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
        lbl_guia = QLabel("🎮 <b>Controles:</b><br>• [A/D] o [←/→] Mover<br>• [Espacio] Disparar<br>• [P] Pausa")
        lbl_guia.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; color: #9CA3AF; font-size: 8pt; border-radius: 8px; padding: 6px;")
        side_layout.addWidget(lbl_guia)

        side_layout.addStretch()
        main_layout.addWidget(side_panel)

        # 2. Área Central / Derecha con el Canvas Proporcional
        canvas_container = QWidget()
        c_layout = QVBoxLayout(canvas_container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.canvas = SpaceInvadersCanvas(self)
        self.canvas.setFixedSize(560, 490)
        self.canvas.setStyleSheet("border-radius: 12px; border: 2px solid rgba(99, 102, 241, 0.25);")
        c_layout.addWidget(self.canvas)

        main_layout.addWidget(canvas_container)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def reiniciar_juego(self):
        self.estado = "JUGANDO"
        self.score = 0
        self.oleada = 1
        self.vidas = 3
        try:
            from console import CheatManager
            v_ovr = CheatManager.get_instance().get_lives_override()
            if v_ovr:
                self.vidas = v_ovr
        except Exception: pass
        self.player_x = 0.5
        self.lasers_jugador.clear()
        self.bombas_alien.clear()
        self.particulas.clear()
        self._crear_oleada()
        self._crear_bunkers()
        self._actualizar_hud()
        self.canvas.setFocus()

    def _crear_oleada(self):
        self.invaders.clear()
        self.dir_invaders = 1
        self.vel_invaders = 0.0015 + (self.oleada - 1) * 0.0004
        
        # 5 filas x 10 columnas
        filas = 5
        cols = 10
        start_x = 0.12
        start_y = 0.14
        step_x = 0.075
        step_y = 0.055

        for r in range(filas):
            tipo = 0 if r == 0 else (1 if r in (1, 2) else 2)
            pts = 30 if tipo == 0 else (20 if tipo == 1 else 10)
            for c in range(cols):
                self.invaders.append({
                    "x": start_x + c * step_x,
                    "y": start_y + r * step_y,
                    "w": 0.05,
                    "h": 0.035,
                    "tipo": tipo,
                    "puntos": pts,
                    "vivo": True
                })

    def _crear_bunkers(self):
        self.bunkers.clear()
        # 4 búnkeres distribuidos
        for i in range(4):
            bx_center = 0.18 + i * 0.22
            by = 0.74
            # Cada búnker tiene una rejilla de bloques destructibles 3x2
            for rx in range(3):
                for ry in range(2):
                    self.bunkers.append({
                        "x": bx_center + (rx - 1) * 0.025,
                        "y": by + ry * 0.025,
                        "w": 0.024,
                        "h": 0.022,
                        "hp": 4
                    })

    def toggle_pausa(self):
        if self.estado == "JUGANDO":
            self.estado = "PAUSA"
            self.btn_pausa.setText("▶ Reanudar")
        elif self.estado == "PAUSA":
            self.estado = "JUGANDO"
            self.btn_pausa.setText("⏸ Pausar")
            self.canvas.setFocus()

    def disparar_jugador(self):
        if self.estado == "JUGANDO" and len(self.lasers_jugador) < 2:
            self.lasers_jugador.append({
                "x": self.player_x,
                "y": self.player_y - 0.02,
                "vel": 0.016
            })

    def _game_loop(self):
        if self.estado != "JUGANDO":
            self.canvas.update()
            return

        self.tick_count += 1
        if self.tick_count % 20 == 0:
            self.anim_frame = 1 - self.anim_frame

        # 1. Movimiento del Jugador
        keys = self.canvas.keys_pressed
        if Qt.Key.Key_Left in keys or Qt.Key.Key_A in keys:
            self.player_x = max(0.04, self.player_x - self.player_vel)
        if Qt.Key.Key_Right in keys or Qt.Key.Key_D in keys:
            self.player_x = min(0.96, self.player_x + self.player_vel)

        # 2. Movimiento de Láseres del Jugador
        for laser in self.lasers_jugador[:]:
            laser["y"] -= laser["vel"]
            if laser["y"] < 0:
                self.lasers_jugador.remove(laser)
                continue

            # Colisión Láser vs Invasores
            lx = laser["x"]
            ly = laser["y"]
            impacto = False
            for inv in self.invaders:
                if inv["vivo"] and (inv["x"] <= lx <= inv["x"] + inv["w"]) and (inv["y"] <= ly <= inv["y"] + inv["h"]):
                    inv["vivo"] = False
                    self.score += inv["puntos"]
                    self._crear_explosion(inv["x"] + inv["w"]/2, inv["y"] + inv["h"]/2, QColor("#FBBF24"))
                    impacto = True
                    # Acelerar invasores restantes
                    vivos = [i for i in self.invaders if i["vivo"]]
                    if vivos:
                        self.vel_invaders = 0.0015 + (1.0 - len(vivos)/50.0) * 0.005
                    else:
                        self._oleada_ganada()
                    break

            # Colisión Láser vs Búnkeres
            if not impacto:
                for b in self.bunkers:
                    if b["hp"] > 0 and (b["x"] <= lx <= b["x"] + b["w"]) and (b["y"] <= ly <= b["y"] + b["h"]):
                        b["hp"] -= 1
                        impacto = True
                        break

            # Colisión Láser vs OVNI
            if not impacto and self.ufo["activo"]:
                ux = self.ufo["x"]
                uy = self.ufo["y"]
                if (ux <= lx <= ux + self.ufo["w"]) and (uy <= ly <= uy + self.ufo["h"]):
                    self.ufo["activo"] = False
                    ufo_pts = random.choice([50, 100, 150, 300])
                    self.score += ufo_pts
                    self._crear_explosion(ux + self.ufo["w"]/2, uy + self.ufo["h"]/2, QColor("#F43F5E"))
                    impacto = True

            if impacto and laser in self.lasers_jugador:
                self.lasers_jugador.remove(laser)

        # 3. Movimiento en Bloque de Invasores
        vivos = [i for i in self.invaders if i["vivo"]]
        if vivos:
            min_x = min(i["x"] for i in vivos)
            max_x = max(i["x"] + i["w"] for i in vivos)

            cambio_fila = False
            if self.dir_invaders == 1 and max_x >= 0.96:
                self.dir_invaders = -1
                cambio_fila = True
            elif self.dir_invaders == -1 and min_x <= 0.04:
                self.dir_invaders = 1
                cambio_fila = True

            for inv in vivos:
                if cambio_fila:
                    inv["y"] += 0.025
                    if inv["y"] + inv["h"] >= self.player_y - 0.04:
                        self._game_over()
                        return
                else:
                    inv["x"] += self.dir_invaders * self.vel_invaders

            # 4. Disparo aleatorio de bombas por aliens
            if random.random() < 0.035 and len(self.bombas_alien) < 4:
                shooter = random.choice(vivos)
                self.bombas_alien.append({
                    "x": shooter["x"] + shooter["w"] / 2,
                    "y": shooter["y"] + shooter["h"],
                    "vel": 0.007 + self.oleada * 0.001
                })

        # 5. Movimiento y Colisiones de Bombas Alien
        for bomba in self.bombas_alien[:]:
            bomba["y"] += bomba["vel"]
            if bomba["y"] > 0.95:
                self.bombas_alien.remove(bomba)
                continue

            bx = bomba["x"]
            by = bomba["y"]
            impacto_b = False

            # Colisión con Búnkeres
            for b in self.bunkers:
                if b["hp"] > 0 and (b["x"] <= bx <= b["x"] + b["w"]) and (b["y"] <= by <= b["y"] + b["h"]):
                    b["hp"] -= 1
                    impacto_b = True
                    break

            # Colisión con Jugador
            if not impacto_b:
                if abs(bx - self.player_x) < self.player_w/2 and abs(by - self.player_y) < self.player_h/2:
                    self._crear_explosion(self.player_x, self.player_y, QColor("#34D399"))
                    impacto_b = True
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

            if impacto_b and bomba in self.bombas_alien:
                self.bombas_alien.remove(bomba)

        # 6. Platillo Volador OVNI (Spawn periódico)
        if not self.ufo["activo"] and random.random() < 0.0015:
            self.ufo["activo"] = True
            self.ufo["x"] = -0.1
        elif self.ufo["activo"]:
            self.ufo["x"] += self.ufo["vel"]
            if self.ufo["x"] > 1.1:
                self.ufo["activo"] = False

        # 7. Actualizar Partículas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vida"] -= 1
            if p["vida"] <= 0:
                self.particulas.remove(p)

        self._actualizar_hud()
        self.canvas.update()

    def _crear_explosion(self, x, y, color):
        for _ in range(12):
            ang = random.uniform(0, 6.28)
            spd = random.uniform(0.002, 0.008)
            self.particulas.append({
                "x": x,
                "y": y,
                "vx": spd * random.cos(ang) if hasattr(random, 'cos') else spd * 0.5,
                "vy": spd * random.sin(ang) if hasattr(random, 'sin') else spd * 0.5,
                "vida": random.randint(10, 20),
                "tam": random.randint(2, 4),
                "color": color
            })

    def _oleada_ganada(self):
        self.estado = "VICTORIA"
        self.score += 500
        self.oleada += 1
        self.score_mgr.sumar_puntos("space_invaders", 10)
        QTimer.singleShot(2000, self._continuar_oleada)

    def _continuar_oleada(self):
        self.lasers_jugador.clear()
        self.bombas_alien.clear()
        self._crear_oleada()
        self.estado = "JUGANDO"
        self.canvas.setFocus()

    def _game_over(self):
        self.estado = "GAME_OVER"
        if self.score > self.highscore:
            self.highscore = self.score
            self.score_mgr.actualizar_highscore("space_invaders", self.highscore)
        self.score_mgr.sumar_puntos("space_invaders", max(5, self.score // 80))
        self._actualizar_hud()

    def _actualizar_hud(self):
        self.lbl_score.setText(f"SCORE: {self.score:05d}")
        self.lbl_highscore.setText(f"HI-SCORE: {self.highscore:05d}")
        self.lbl_oleada.setText(f"OLEADA: {self.oleada}")
        corazones = "❤️" * max(0, self.vidas)
        self.lbl_vidas.setText(f"VIDAS: {corazones}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background-color: {colores.get('bg_principal', '#121218')}; color: white;")

    def cleanup(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        if self.score > 0 and getattr(self, 'estado', '') == "JUGANDO":
            self.score_mgr.sumar_puntos("space_invaders", max(3, self.score // 80))
            self.score_mgr.actualizar_highscore("space_invaders", self.score)
