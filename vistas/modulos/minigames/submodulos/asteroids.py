"""
asteroids.py - Juego Retro Arcade Asteroids (1979)
Física auténtica con inercia vectorial (deslizamiento sobre hielo / patinaje),
rotación angular, envoltura toroidal de pantalla (wrap-around), división de asteroides
(Grande -> Mediano -> Pequeño), propulsor, botón de hiperspacio, platillo ovni y récords.
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


class AsteroidsCanvas(QWidget):
    """Lienzo vectorial para Asteroids con renderizado de líneas de fósforo verde / blanco."""
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
        elif event.key() in (Qt.Key.Key_H, Qt.Key.Key_Down, Qt.Key.Key_S):
            self.game.hiperspacio()
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

        # Fondo Espacial Negro Puro
        painter.fillRect(0, 0, w, h, QColor("#050508"))

        # Estrellas de fondo fijas
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        for sx, sy in self.game.estrellas:
            painter.drawPoint(int(sx * w), int(sy * h))

        # 1. Dibujar Asteroides con Geometría Poligonal Vectorial
        pen_ast = QPen(QColor("#E2E8F0"), 2)
        painter.setPen(pen_ast)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for ast in self.game.asteroides:
            ax = ast["x"] * w
            ay = ast["y"] * h
            r = ast["r"]
            verts = ast["verts"]
            poly = QPolygonF()
            for vx, vy in verts:
                poly.append(QPointF(ax + vx * r, ay + vy * r))
            painter.drawPolygon(poly)

        # 2. Dibujar Platillo Volador (UFO)
        if self.game.saucer["activo"]:
            sx = self.game.saucer["x"] * w
            sy = self.game.saucer["y"] * h
            sr = self.game.saucer["r"]
            painter.setPen(QPen(QColor("#F43F5E"), 2))
            # Cúpula y base
            painter.drawEllipse(QRectF(sx - sr, sy - sr*0.3, sr*2, sr*0.6))
            painter.drawEllipse(QRectF(sx - sr*0.5, sy - sr*0.6, sr, sr*0.5))

        # 3. Dibujar Disparos Láser
        painter.setPen(QPen(QColor("#38BDF8"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for b in self.game.balas:
            bx = b["x"] * w
            by = b["y"] * h
            painter.drawPoint(int(bx), int(by))

        # Disparos del Platillo
        painter.setPen(QPen(QColor("#F87171"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for b in self.game.balas_saucer:
            bx = b["x"] * w
            by = b["y"] * h
            painter.drawPoint(int(bx), int(by))

        # 4. Dibujar Partículas de Fragmentación
        for p in self.game.particulas:
            painter.setPen(QPen(p["color"], p["tam"]))
            painter.drawPoint(int(p["x"] * w), int(p["y"] * h))

        # 5. Dibujar Nave Espacial Clásica (Triangular Vectorial)
        if self.game.vidas > 0 and self.game.invulnerable_timer % 4 < 2:
            self._dibujar_nave(painter, w, h)

        # 6. Overlays de Estado
        if self.game.estado != "JUGANDO":
            painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 185))
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Inter", 18, QFont.Weight.Bold))

            if self.game.estado == "GAME_OVER":
                painter.setPen(QColor("#F87171"))
                painter.drawText(0, int(h * 0.45), w, 40, Qt.AlignmentFlag.AlignCenter, "☄️ GAME OVER ☄️")
                painter.setFont(QFont("Inter", 11))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(0, int(h * 0.53), w, 30, Qt.AlignmentFlag.AlignCenter, "Presiona [REINICIAR] para despegar de nuevo")
            elif self.game.estado == "SECTOR_CLEARED":
                painter.setPen(QColor("#34D399"))
                painter.drawText(0, int(h * 0.45), w, 40, Qt.AlignmentFlag.AlignCenter, "⭐ ¡SECTOR LIMPIO! ⭐")
                painter.setFont(QFont("Inter", 11))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(0, int(h * 0.53), w, 30, Qt.AlignmentFlag.AlignCenter, "Cargando siguiente cinturón de asteroides...")
            elif self.game.estado == "PAUSA":
                painter.setPen(QColor("#FBBF24"))
                painter.drawText(0, int(h * 0.48), w, 40, Qt.AlignmentFlag.AlignCenter, "⏸ PAUSA")

    def _dibujar_nave(self, painter, w, h):
        nx = self.game.ship_x * w
        ny = self.game.ship_y * h
        ang = self.game.ship_ang
        r = 16.0

        painter.save()
        painter.translate(nx, ny)
        painter.rotate(math.degrees(ang))

        # Triángulo de la nave
        painter.setPen(QPen(QColor("#34D399"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        poly = QPolygonF([
            QPointF(r, 0),
            QPointF(-r * 0.8, -r * 0.6),
            QPointF(-r * 0.4, 0),
            QPointF(-r * 0.8, r * 0.6)
        ])
        painter.drawPolygon(poly)

        # Llama de propulsión cuando empuja
        if self.game.is_thrusting and random.random() < 0.8:
            painter.setPen(QPen(QColor("#F97316"), 2))
            poly_fuego = QPolygonF([
                QPointF(-r * 0.4, -r * 0.25),
                QPointF(-r * 1.1 - random.uniform(0, 4), 0),
                QPointF(-r * 0.4, r * 0.25)
            ])
            painter.drawPolyline(poly_fuego)

        painter.restore()


class TabAsteroids(QWidget):
    """Submódulo de Asteroids Arcade con física inercial de patinaje y envolvente de pantalla."""
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
        self.nivel = 1
        self.vidas = 3
        self.highscore = self.score_mgr.cargar().get("asteroids_highscore", 0)
        self.invulnerable_timer = 0

        # Nave espacial (Física Newtoniana / Patinaje en Hielo)
        self.ship_x = 0.5
        self.ship_y = 0.5
        self.ship_vx = 0.0
        self.ship_vy = 0.0
        self.ship_ang = -math.pi / 2.0  # apuntando hacia arriba
        self.ship_rot_speed = 0.085
        self.thrust_accel = 0.00075
        self.friction = 0.991  # Fricción casi nula -> patinaje fluido
        self.is_thrusting = False

        # Entidades
        self.asteroides = []
        self.balas = []
        self.balas_saucer = []
        self.particulas = []
        self.saucer = {"activo": False, "x": 0.0, "y": 0.3, "vx": 0.002, "vy": 0.0, "r": 18, "timer": 0}

        # Estrellas de fondo
        random.seed(999)
        self.estrellas = [(random.random(), random.random()) for _ in range(60)]

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
                background: #34D399;
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
        lbl_tit = QLabel("☄️ ASTEROIDS")
        lbl_tit.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        lbl_tit.setStyleSheet("color: #34D399; padding-bottom: 2px;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(lbl_tit)

        # Tarjeta SCORE
        card_score = QFrame()
        card_score.setFixedHeight(54)
        card_score.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_sc = QVBoxLayout(card_score)
        v_sc.setContentsMargins(10, 6, 10, 6)
        v_sc.setSpacing(2)
        lbl_sc_tit = QLabel("SCORE")
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

        # Tarjeta SECTOR
        card_sec = QFrame()
        card_sec.setFixedHeight(54)
        card_sec.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_sec = QVBoxLayout(card_sec)
        v_sec.setContentsMargins(10, 6, 10, 6)
        v_sec.setSpacing(2)
        lbl_sec_tit = QLabel("SECTOR")
        lbl_sec_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_sec.addWidget(lbl_sec_tit)
        self.lbl_nivel = QLabel("1")
        self.lbl_nivel.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.lbl_nivel.setStyleSheet("color: #38BDF8;")
        v_sec.addWidget(self.lbl_nivel)
        side_layout.addWidget(card_sec)

        # Tarjeta NAVES
        card_nv = QFrame()
        card_nv.setFixedHeight(54)
        card_nv.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; border-radius: 8px;")
        v_nv = QVBoxLayout(card_nv)
        v_nv.setContentsMargins(10, 6, 10, 6)
        v_nv.setSpacing(2)
        lbl_nv_tit = QLabel("NAVES")
        lbl_nv_tit.setStyleSheet("color: #8E8E93; font-size: 8pt; font-weight: bold;")
        v_nv.addWidget(lbl_nv_tit)
        self.lbl_vidas = QLabel("🚀🚀🚀")
        self.lbl_vidas.setFont(QFont("Segoe UI Emoji", 11, QFont.Weight.Bold))
        self.lbl_vidas.setStyleSheet("color: #F43F5E;")
        v_nv.addWidget(self.lbl_vidas)
        side_layout.addWidget(card_nv)

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

        self.btn_hyper = QPushButton("🌀 Hiperspacio [H]")
        self.btn_hyper.setFixedHeight(34)
        self.btn_hyper.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hyper.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #0284C7; color: white; }}
        """)
        self.btn_hyper.clicked.connect(self.hiperspacio)
        side_layout.addWidget(self.btn_hyper)

        # Guía de Teclas
        lbl_guia = QLabel("🎮 <b>Controles:</b><br>• [A/D/←/→] Girar<br>• [W/↑] Propulsor<br>• [Espacio] Disparo<br>• [H/↓] Hiperspacio")
        lbl_guia.setStyleSheet(f"background: {self.colores.get('bg_principal', '#121218')}; color: #9CA3AF; font-size: 8pt; border-radius: 8px; padding: 6px;")
        side_layout.addWidget(lbl_guia)

        side_layout.addStretch()
        main_layout.addWidget(side_panel)

        # 2. Área Central / Derecha con el Canvas Proporcional
        canvas_container = QWidget()
        c_layout = QVBoxLayout(canvas_container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.canvas = AsteroidsCanvas(self)
        self.canvas.setFixedSize(560, 490)
        self.canvas.setStyleSheet("border-radius: 12px; border: 2px solid rgba(52, 211, 153, 0.25);")
        c_layout.addWidget(self.canvas)

        main_layout.addWidget(canvas_container)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def reiniciar_juego(self):
        self.estado = "JUGANDO"
        self.score = 0
        self.nivel = 1
        self.vidas = 3
        try:
            from console import CheatManager
            v_ovr = CheatManager.get_instance().get_lives_override()
            if v_ovr:
                self.vidas = v_ovr
        except Exception: pass
        self.ship_x = 0.5
        self.ship_y = 0.5
        self.ship_vx = 0.0
        self.ship_vy = 0.0
        self.ship_ang = -math.pi / 2.0
        self.invulnerable_timer = 60
        self.balas.clear()
        self.balas_saucer.clear()
        self.particulas.clear()
        self.saucer["activo"] = False
        self._crear_asteroides_iniciales()
        self._actualizar_hud()
        self.canvas.setFocus()

    def _crear_asteroides_iniciales(self):
        self.asteroides.clear()
        num_ast = 4 + self.nivel
        for _ in range(num_ast):
            # Aparecer lejos de la nave central
            while True:
                ax = random.random()
                ay = random.random()
                if math.hypot(ax - 0.5, ay - 0.5) > 0.25:
                    break

            ang = random.uniform(0, 6.28)
            spd = random.uniform(0.001, 0.0028)
            self.asteroides.append(self._generar_asteroide(ax, ay, spd * math.cos(ang), spd * math.sin(ang), tam="GRANDE"))

    def _generar_asteroide(self, x, y, vx, vy, tam="GRANDE"):
        if tam == "GRANDE":
            r = 34.0
            pts = 20
        elif tam == "MEDIANO":
            r = 20.0
            pts = 50
        else: # PEQUEÑO
            r = 11.0
            pts = 100

        # Generar polígono dentado aleatorio
        num_puntos = random.randint(9, 13)
        verts = []
        for i in range(num_puntos):
            a = (2 * math.pi / num_puntos) * i
            dist = random.uniform(0.75, 1.25)
            verts.append((math.cos(a) * dist, math.sin(a) * dist))

        return {
            "x": x, "y": y,
            "vx": vx, "vy": vy,
            "r": r, "tam": tam,
            "puntos": pts,
            "verts": verts
        }

    def toggle_pausa(self):
        if self.estado == "JUGANDO":
            self.estado = "PAUSA"
            self.btn_pausa.setText("▶ Reanudar")
        elif self.estado == "PAUSA":
            self.estado = "JUGANDO"
            self.btn_pausa.setText("⏸ Pausar")
            self.canvas.setFocus()

    def disparar(self):
        if self.estado == "JUGANDO" and len(self.balas) < 4:
            bullet_speed = 0.016
            bx = self.ship_x + math.cos(self.ship_ang) * 0.03
            by = self.ship_y + math.sin(self.ship_ang) * 0.03
            bvx = self.ship_vx + math.cos(self.ship_ang) * bullet_speed
            bvy = self.ship_vy + math.sin(self.ship_ang) * bullet_speed
            self.balas.append({"x": bx, "y": by, "vx": bvx, "vy": bvy, "vida": 45})

    def hiperspacio(self):
        """Teletransporte aleatorio a cualquier parte del mapa."""
        if self.estado == "JUGANDO":
            self.ship_x = random.uniform(0.1, 0.9)
            self.ship_y = random.uniform(0.1, 0.9)
            self.ship_vx = 0.0
            self.ship_vy = 0.0
            self.invulnerable_timer = 40
            self._crear_explosion(self.ship_x, self.ship_y, QColor("#38BDF8"), num=10)
            self.canvas.update()

    def _game_loop(self):
        if self.estado != "JUGANDO":
            self.canvas.update()
            return

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1

        w = self.canvas.width()
        h = self.canvas.height()

        # 1. Controles y Rotación Angular
        keys = self.canvas.keys_pressed
        if Qt.Key.Key_Left in keys or Qt.Key.Key_A in keys:
            self.ship_ang -= self.ship_rot_speed
        if Qt.Key.Key_Right in keys or Qt.Key.Key_D in keys:
            self.ship_ang += self.ship_rot_speed

        # 2. Empuje Inercial Newtoniano (Efecto Patinaje sobre Hielo)
        self.is_thrusting = (Qt.Key.Key_Up in keys or Qt.Key.Key_W in keys)
        if self.is_thrusting:
            self.ship_vx += math.cos(self.ship_ang) * self.thrust_accel
            self.ship_vy += math.sin(self.ship_ang) * self.thrust_accel

        # Aplicar fricción muy baja
        self.ship_vx *= self.friction
        self.ship_vy *= self.friction

        # Mover nave
        self.ship_x += self.ship_vx
        self.ship_y += self.ship_vy

        # Envoltura Toroidal de Pantalla (Wrap-Around)
        self.ship_x = self.ship_x % 1.0
        self.ship_y = self.ship_y % 1.0

        # 3. Mover y Envolver Asteroides
        for ast in self.asteroides:
            ast["x"] = (ast["x"] + ast["vx"]) % 1.0
            ast["y"] = (ast["y"] + ast["vy"]) % 1.0

        # 4. Mover Balas del Jugador y Colisiones
        for b in self.balas[:]:
            b["x"] = (b["x"] + b["vx"]) % 1.0
            b["y"] = (b["y"] + b["vy"]) % 1.0
            b["vida"] -= 1
            if b["vida"] <= 0:
                self.balas.remove(b)
                continue

            # Colisión con Asteroides
            bx_px = b["x"] * w
            by_px = b["y"] * h
            impacto = False

            for ast in self.asteroides[:]:
                ax_px = ast["x"] * w
                ay_px = ast["y"] * h
                if math.hypot(bx_px - ax_px, by_px - ay_px) < ast["r"]:
                    self.score += ast["puntos"]
                    self._crear_explosion(ast["x"], ast["y"], QColor("#E2E8F0"), num=12)
                    self._dividir_asteroide(ast)
                    impacto = True
                    break

            # Colisión con Platillo
            if not impacto and self.saucer["activo"]:
                sx_px = self.saucer["x"] * w
                sy_px = self.saucer["y"] * h
                if math.hypot(bx_px - sx_px, by_px - sy_px) < self.saucer["r"]:
                    self.score += 200
                    self._crear_explosion(self.saucer["x"], self.saucer["y"], QColor("#F43F5E"), num=18)
                    self.saucer["activo"] = False
                    impacto = True

            if impacto and b in self.balas:
                self.balas.remove(b)

        # 5. Colisión de la Nave con Asteroides
        if self.invulnerable_timer <= 0:
            nx_px = self.ship_x * w
            ny_px = self.ship_y * h
            for ast in self.asteroides:
                ax_px = ast["x"] * w
                ay_px = ast["y"] * h
                if math.hypot(nx_px - ax_px, ny_px - ay_px) < (ast["r"] + 12):
                    self._destruir_nave()
                    break

        # 6. Platillo Ovni Alienígena
        if not self.saucer["activo"] and random.random() < 0.0018:
            self.saucer["activo"] = True
            self.saucer["x"] = 0.0
            self.saucer["y"] = random.uniform(0.15, 0.85)
            self.saucer["vx"] = 0.0025
            self.saucer["vy"] = random.uniform(-0.001, 0.001)
        elif self.saucer["activo"]:
            self.saucer["x"] += self.saucer["vx"]
            self.saucer["y"] = (self.saucer["y"] + self.saucer["vy"]) % 1.0
            if self.saucer["x"] > 1.05:
                self.saucer["activo"] = False

            # Disparar hacia la posición de la nave
            if random.random() < 0.02 and len(self.balas_saucer) < 3:
                dx = self.ship_x - self.saucer["x"]
                dy = self.ship_y - self.saucer["y"]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    spd = 0.009
                    self.balas_saucer.append({
                        "x": self.saucer["x"], "y": self.saucer["y"],
                        "vx": (dx/dist)*spd + random.uniform(-0.001, 0.001),
                        "vy": (dy/dist)*spd + random.uniform(-0.001, 0.001),
                        "vida": 50
                    })

        # Mover balas del saucer
        for sb in self.balas_saucer[:]:
            sb["x"] = (sb["x"] + sb["vx"]) % 1.0
            sb["y"] = (sb["y"] + sb["vy"]) % 1.0
            sb["vida"] -= 1
            if sb["vida"] <= 0:
                self.balas_saucer.remove(sb)
                continue

            if self.invulnerable_timer <= 0:
                if math.hypot(sb["x"]*w - self.ship_x*w, sb["y"]*h - self.ship_y*h) < 14:
                    self._destruir_nave()
                    self.balas_saucer.remove(sb)
                    break

        # 7. Partículas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vida"] -= 1
            if p["vida"] <= 0:
                self.particulas.remove(p)

        # 8. Verificar Limpieza del Sector
        if not self.asteroides:
            self._sector_limpio()

        self._actualizar_hud()
        self.canvas.update()

    def _dividir_asteroide(self, ast):
        self.asteroides.remove(ast)
        x = ast["x"]
        y = ast["y"]

        if ast["tam"] == "GRANDE":
            nuevo_tam = "MEDIANO"
        elif ast["tam"] == "MEDIANO":
            nuevo_tam = "PEQUEÑO"
        else:
            return  # El pequeño se destruye totalmente

        # Dividir en 2 fragmentos con trayectorias divergentes
        for _ in range(2):
            ang = random.uniform(0, 6.28)
            spd = random.uniform(0.002, 0.0045)
            self.asteroides.append(self._generar_asteroide(
                x, y, spd * math.cos(ang), spd * math.sin(ang), tam=nuevo_tam
            ))

    def _destruir_nave(self):
        try:
            from console import CheatManager
            if CheatManager.get_instance().is_godmode():
                return
        except Exception: pass
        self._crear_explosion(self.ship_x, self.ship_y, QColor("#34D399"), num=25)
        self.vidas -= 1
        self.ship_x = 0.5
        self.ship_y = 0.5
        self.ship_vx = 0.0
        self.ship_vy = 0.0
        self.invulnerable_timer = 90
        if self.vidas <= 0:
            self._game_over()
        else:
            self._actualizar_hud()

    def _crear_explosion(self, x, y, color, num=16):
        for _ in range(num):
            ang = random.uniform(0, 6.28)
            spd = random.uniform(0.002, 0.009)
            self.particulas.append({
                "x": x, "y": y,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd,
                "vida": random.randint(15, 30),
                "tam": random.randint(2, 4),
                "color": color
            })

    def _sector_limpio(self):
        self.estado = "SECTOR_CLEARED"
        self.score += 1000
        self.nivel += 1
        self.score_mgr.sumar_puntos("asteroids", 10)
        QTimer.singleShot(2000, self._continuar_siguiente_nivel)

    def _continuar_siguiente_nivel(self):
        self.balas.clear()
        self.balas_saucer.clear()
        self._crear_asteroides_iniciales()
        self.estado = "JUGANDO"
        self.canvas.setFocus()

    def _game_over(self):
        self.estado = "GAME_OVER"
        if self.score > self.highscore:
            self.highscore = self.score
            self.score_mgr.actualizar_highscore("asteroids", self.highscore)
        self.score_mgr.sumar_puntos("asteroids", max(5, self.score // 100))
        self._actualizar_hud()

    def _actualizar_hud(self):
        self.lbl_score.setText(f"SCORE: {self.score:05d}")
        self.lbl_highscore.setText(f"HI-SCORE: {self.highscore:05d}")
        self.lbl_nivel.setText(f"SECTOR: {self.nivel}")
        naves = "🚀" * max(0, self.vidas)
        self.lbl_vidas.setText(f"NAVES: {naves}")

    def actualizar_tema(self, colores):
        self.colores = colores
        self.setStyleSheet(f"background-color: {colores.get('bg_principal', '#121218')}; color: white;")

    def cleanup(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        if self.score > 0 and getattr(self, 'estado', '') == "JUGANDO":
            self.score_mgr.sumar_puntos("asteroids", max(3, self.score // 100))
            self.score_mgr.actualizar_highscore("asteroids", self.score)
