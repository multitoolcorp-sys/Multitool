"""
battleship.py - Batalla Naval Dinámica
Características:
- Selector lateral interactivo estilo Kanban con los 4 tipos de barcos (Portaviones 5, Acorazado 4, Crucero 3, Destructor 2).
- Colocación dinámica con rotación ('R') y botón para quitar/reubicar cada barco.
- En fase de colocación sólo se muestra 1 tablero para desplegar la flota.
- Botón '🚀 EMPEZAR JUEGO' cuando todos los barcos están posicionados.
- En fase de batalla:
  * Tablero Radar de Disparos: Coloca puntos rojos (💥 Impacto) y agua (💧) de tus ataques.
  * Tablero Defensivo: Registra los ataques del enemigo sobre tus barcos.
- Modos: Vs Inteligencia Artificial y 1v1 Red LAN (2 personas en computadoras distintas).
"""

import random
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QComboBox, QMessageBox, 
    QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..utils.game_socket_manager import GameSocketManager
from ..utils.score_manager import ScoreManager

SHIPS_DEFINED = [
    {"id": "carrier", "nombre": "🚢 Portaviones", "tam": 5, "color": "#6366F1"},
    {"id": "battleship", "nombre": "🛳️ Acorazado", "tam": 4, "color": "#3B82F6"},
    {"id": "cruiser", "nombre": "⛴️ Crucero", "tam": 3, "color": "#10B981"},
    {"id": "destroyer", "nombre": "🚤 Destructor", "tam": 2, "color": "#F59E0B"}
]


class BattleshipGUI(QWidget):
    def __init__(self, parent, colores, ruta_usuario):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#FFFFFF", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#4F46E5", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        self.ruta_usuario = ruta_usuario
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.score_mgr = ScoreManager(ruta_usuario)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.orientacion = "H"  # "H" | "V"
        self.modo_juego = "vs_ia"  # "vs_ia" | "lan_1v1"
        self.socket_mgr = GameSocketManager(usuario="Almirante")
        self.socket_mgr.configurar_callbacks(self._on_lan_move_received, self._on_lan_status)

        self.fase = "colocacion"  # "colocacion" | "batalla"
        self.barco_seleccionado = "carrier"  # id del barco activo en el dock

        # Registro de colocación de barcos: {ship_id: {"pos": [(r, c), ...], "colocado": bool}}
        self.barcos_colocados = {s["id"]: {"pos": [], "colocado": False} for s in SHIPS_DEFINED}

        # Matrices 10x10
        self.mi_tablero = [[0]*10 for _ in range(10)]      # 0: agua, 1: barco, 2: agua atacada, 3: impacto
        self.radar_disparos = [[0]*10 for _ in range(10)]  # 0: no disparado, 2: agua, 3: impacto rojo
        self.ia_barcos = [[0]*10 for _ in range(10)]

        self.mis_botones = {}
        self.radar_botones = {}
        self.ship_cards = {}

        self.inicializar_ui()
        self.nuevo_juego()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R:
            self._toggle_orientacion()
            event.accept()
        else:
            super().keyPressEvent(event)

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(10)

        # 1. Header & Modos
        hdr = QHBoxLayout()
        lbl_tit = QLabel("🚢 BATALLA NAVAL TÁCTICA")
        lbl_tit.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {acento}; letter-spacing: 1px;")
        hdr.addWidget(lbl_tit)

        hdr.addStretch()

        self.cb_modo = QComboBox()
        self.cb_modo.addItems(["🤖 Vs Inteligencia Artificial", "📡 1v1 Red LAN (2 Computadoras)"])
        self.cb_modo.setFont(QFont(self.font_family, 9))
        self.cb_modo.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 5px 10px;")
        self.cb_modo.currentIndexChanged.connect(self._on_modo_changed)
        hdr.addWidget(self.cb_modo)

        self.btn_rotar = QPushButton("🔄 Rotar (R): HORIZONTAL")
        self.btn_rotar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.btn_rotar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rotar.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        self.btn_rotar.clicked.connect(self._toggle_orientacion)
        hdr.addWidget(self.btn_rotar)

        btn_new = QPushButton("🔄 Reiniciar Partida")
        btn_new.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setStyleSheet(f"background: {self.colores['exito']}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        btn_new.clicked.connect(self.nuevo_juego)
        hdr.addWidget(btn_new)

        layout.addLayout(hdr)

        # Panel LAN (Host / IP)
        self.lan_panel = QFrame()
        self.lan_panel.setStyleSheet(f"background: {bg_sec}; border-radius: 8px; padding: 6px;")
        self.lan_panel.hide()
        l_lay = QHBoxLayout(self.lan_panel)
        l_lay.addWidget(QLabel("IP Host:"))
        self.txt_ip_lan = QLineEdit("127.0.0.1")
        self.txt_ip_lan.setFixedWidth(110)
        self.txt_ip_lan.setStyleSheet(f"background: {bg_main}; color: white; border-radius: 4px; padding: 4px;")
        l_lay.addWidget(self.txt_ip_lan)

        btn_host = QPushButton("📡 Crear Host LAN")
        btn_host.setStyleSheet(f"background: {self.colores['exito']}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
        btn_host.clicked.connect(self._iniciar_lan_host)
        l_lay.addWidget(btn_host)

        btn_join = QPushButton("🔗 Conectar a Host")
        btn_join.setStyleSheet(f"background: {acento}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
        btn_join.clicked.connect(self._unirse_lan_host)
        l_lay.addWidget(btn_join)
        l_lay.addStretch()
        layout.addWidget(self.lan_panel)

        # Barra de Estado / Alertas
        self.lbl_status = QLabel("📍 Selecciona un barco del muelle y haz clic en tu cuadrícula para ubicarlo.")
        self.lbl_status.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #38BDF8; padding: 4px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        # Área Central Principal de Juego
        self.main_game_area = QHBoxLayout()
        self.main_game_area.setSpacing(20)
        self.main_game_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Muelle Lateral de Barcos (Estilo Kanban)
        self.dock_frame = QFrame()
        self.dock_frame.setFixedWidth(240)
        self.dock_frame.setStyleSheet(f"""
            QFrame {{
                background: {bg_sec};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 10px;
            }}
        """)
        self.dock_layout = QVBoxLayout(self.dock_frame)
        self.dock_layout.setSpacing(8)

        lbl_dock_tit = QLabel("⚓ MUELLE DE LA FLOTA")
        lbl_dock_tit.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_dock_tit.setStyleSheet(f"color: {acento}; letter-spacing: 0.5px;")
        lbl_dock_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dock_layout.addWidget(lbl_dock_tit)

        self._construir_dock_barcos()

        self.btn_empezar = QPushButton("🚀 EMPEZAR JUEGO")
        self.btn_empezar.setFixedHeight(40)
        self.btn_empezar.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.btn_empezar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empezar.setStyleSheet(f"""
            QPushButton {{
                background: #10B981;
                color: white;
                border-radius: 8px;
                border: 2px solid #34D399;
            }}
            QPushButton:hover {{ background: #059669; }}
            QPushButton:disabled {{ background: #2D2D3D; color: #6B7280; border: none; }}
        """)
        self.btn_empezar.setEnabled(False)
        self.btn_empezar.clicked.connect(self._iniciar_fase_batalla)
        self.dock_layout.addWidget(self.btn_empezar)
        self.dock_layout.addStretch()

        self.main_game_area.addWidget(self.dock_frame)

        # 3. Tablero de Tu Flota (Defensivo)
        self.frame_mi = QFrame()
        self.frame_mi.setFixedWidth(310)
        self.frame_mi.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 8px;")
        f1 = QVBoxLayout(self.frame_mi)
        self.lbl_mi_flota_tit = QLabel("🛡️ TU FLOTA (DEFENSA)", font=QFont(self.font_family, 9, QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_mi_flota_tit.setStyleSheet("color: #38BDF8;")
        f1.addWidget(self.lbl_mi_flota_tit)

        g1_w = QWidget()
        self.grid_mi = QGridLayout(g1_w)
        self.grid_mi.setSpacing(2)
        self._build_grid_mi()
        f1.addWidget(g1_w)
        self.main_game_area.addWidget(self.frame_mi)

        # 4. Tablero Radar de Ataque / Disparos Enemigos (Se muestra en batalla)
        self.frame_radar = QFrame()
        self.frame_radar.setFixedWidth(310)
        self.frame_radar.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 8px;")
        f2 = QVBoxLayout(self.frame_radar)
        lbl_radar_tit = QLabel("🎯 RADAR DE ATAQUE (DISPAROS)", font=QFont(self.font_family, 9, QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignCenter)
        lbl_radar_tit.setStyleSheet("color: #F87171;")
        f2.addWidget(lbl_radar_tit)

        g2_w = QWidget()
        self.grid_radar = QGridLayout(g2_w)
        self.grid_radar.setSpacing(2)
        self._build_grid_radar()
        f2.addWidget(g2_w)
        self.main_game_area.addWidget(self.frame_radar)

        # En colocación, sólo se muestra el tablero propio
        self.frame_radar.hide()

        layout.addLayout(self.main_game_area)
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _construir_dock_barcos(self):
        """Construye las tarjetas interactivas de cada barco en el muelle."""
        for s in SHIPS_DEFINED:
            card = QFrame()
            card.setFixedHeight(58)
            card.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores['bg_principal']};
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.08);
                }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(8, 4, 8, 4)

            v_info = QVBoxLayout()
            v_info.setSpacing(1)
            lbl_n = QLabel(s["nombre"])
            lbl_n.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            lbl_n.setStyleSheet("color: white;")
            v_info.addWidget(lbl_n)

            lbl_t = QLabel(f"Tamaño: {s['tam']} celdas")
            lbl_t.setStyleSheet("color: #9CA3AF; font-size: 8pt;")
            v_info.addWidget(lbl_t)
            c_lay.addLayout(v_info, 1)

            btn_sel = QPushButton("Colocar")
            btn_sel.setFixedSize(65, 28)
            btn_sel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_sel.setStyleSheet(f"background: {s['color']}; color: white; border-radius: 5px; font-weight: bold; font-size: 8pt;")
            btn_sel.clicked.connect(lambda ch, sid=s["id"]: self._seleccionar_barco_dock(sid))
            c_lay.addWidget(btn_sel)

            self.dock_layout.addWidget(card)
            self.ship_cards[s["id"]] = {"card": card, "btn": btn_sel, "lbl_t": lbl_t}

    def _seleccionar_barco_dock(self, ship_id):
        if self.fase != "colocacion": return

        # Si ya estaba colocado, permitir quitarlo para reubicarlo
        if self.barcos_colocados[ship_id]["colocado"]:
            # Borrar del tablero
            for r, c in self.barcos_colocados[ship_id]["pos"]:
                self.mi_tablero[r][c] = 0
            self.barcos_colocados[ship_id]["colocado"] = False
            self.barcos_colocados[ship_id]["pos"] = []
            self._render_mi_tablero()
            self._actualizar_estado_dock()

        self.barco_seleccionado = ship_id
        self._actualizar_estado_dock()

        ship = next(s for s in SHIPS_DEFINED if s["id"] == ship_id)
        self.lbl_status.setText(f"📍 Barco seleccionado: {ship['nombre']} ({ship['tam']} celdas). Haz clic en tu tablero para colocarlo.")

    def _actualizar_estado_dock(self):
        todos_colocados = True
        for s in SHIPS_DEFINED:
            sid = s["id"]
            card_info = self.ship_cards[sid]
            es_activo = (self.barco_seleccionado == sid)
            colocado = self.barcos_colocados[sid]["colocado"]

            if not colocado:
                todos_colocados = False

            if colocado:
                card_info["card"].setStyleSheet(f"background: rgba(16,185,129,0.15); border: 1px solid #10B981; border-radius: 8px;")
                card_info["btn"].setText("🗑️ Quitar")
                card_info["btn"].setStyleSheet("background: #EF4444; color: white; border-radius: 5px; font-weight: bold; font-size: 8pt;")
                card_info["lbl_t"].setText(f"✅ Colocado ({s['tam']} celdas)")
            elif es_activo:
                card_info["card"].setStyleSheet(f"background: rgba(99,102,241,0.2); border: 2px solid {self.colores['acento']}; border-radius: 8px;")
                card_info["btn"].setText("Activo")
                card_info["btn"].setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 5px; font-weight: bold; font-size: 8pt;")
                card_info["lbl_t"].setText(f"Listo para ubicar ({s['tam']} celdas)")
            else:
                card_info["card"].setStyleSheet(f"background: {self.colores['bg_principal']}; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;")
                card_info["btn"].setText("Colocar")
                card_info["btn"].setStyleSheet(f"background: {s['color']}; color: white; border-radius: 5px; font-weight: bold; font-size: 8pt;")
                card_info["lbl_t"].setText(f"Tamaño: {s['tam']} celdas")

        self.btn_empezar.setEnabled(todos_colocados)
        if todos_colocados and self.fase == "colocacion":
            self.lbl_status.setText("🌟 ¡Todos los 4 barcos colocados! Haz clic en '🚀 EMPEZAR JUEGO'.")

    def _toggle_orientacion(self):
        self.orientacion = "V" if self.orientacion == "H" else "H"
        self.btn_rotar.setText(f"🔄 Rotar (R): {'VERTICAL' if self.orientacion == 'V' else 'HORIZONTAL'}")

    def _build_grid_mi(self):
        for c, h in enumerate([""] + [chr(65+i) for i in range(10)]):
            lbl = QLabel(h, font=QFont("Consolas", 8, QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(25, 20)
            self.grid_mi.addWidget(lbl, 0, c)

        for r in range(10):
            lbl_r = QLabel(str(r+1), font=QFont("Consolas", 8, QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignCenter)
            lbl_r.setFixedSize(20, 25)
            self.grid_mi.addWidget(lbl_r, r+1, 0)
            for c in range(10):
                btn = QPushButton()
                btn.setFixedSize(25, 25)
                btn.setStyleSheet("background: rgba(30,30,46,0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 3px;")
                btn.clicked.connect(lambda ch, row=r, col=c: self._on_mi_tablero_click(row, col))
                self.grid_mi.addWidget(btn, r+1, c+1)
                self.mis_botones[(r, c)] = btn

    def _build_grid_radar(self):
        for c, h in enumerate([""] + [chr(65+i) for i in range(10)]):
            lbl = QLabel(h, font=QFont("Consolas", 8, QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(25, 20)
            self.grid_radar.addWidget(lbl, 0, c)

        for r in range(10):
            lbl_r = QLabel(str(r+1), font=QFont("Consolas", 8, QFont.Weight.Bold), alignment=Qt.AlignmentFlag.AlignCenter)
            lbl_r.setFixedSize(20, 25)
            self.grid_radar.addWidget(lbl_r, r+1, 0)
            for c in range(10):
                btn = QPushButton()
                btn.setFixedSize(25, 25)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("background: rgba(30,30,46,0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 3px;")
                btn.clicked.connect(lambda ch, row=r, col=c: self._disparar_al_radar_enemigo(row, col))
                self.grid_radar.addWidget(btn, r+1, c+1)
                self.radar_botones[(r, c)] = btn

    def _on_mi_tablero_click(self, r, c):
        if self.fase != "colocacion": return
        if not self.barco_seleccionado:
            self.lbl_status.setText("⚠️ Primero selecciona un barco disponible en el Muelle.")
            return

        ship = next(s for s in SHIPS_DEFINED if s["id"] == self.barco_seleccionado)
        size = ship["tam"]

        # Validar posición
        if self.orientacion == "H":
            if c + size > 10:
                self.lbl_status.setText("❌ El barco no cabe horizontalmente aquí.")
                return
            if any(self.mi_tablero[r][c+i] != 0 for i in range(size)):
                self.lbl_status.setText("❌ Posición ocupada por otro navío.")
                return
            coords = [(r, c+i) for i in range(size)]
        else:
            if r + size > 10:
                self.lbl_status.setText("❌ El barco no cabe verticalmente aquí.")
                return
            if any(self.mi_tablero[r+i][c] != 0 for i in range(size)):
                self.lbl_status.setText("❌ Posición ocupada por otro navío.")
                return
            coords = [(r+i, c) for i in range(size)]

        # Colocar barco
        for cr, cc in coords:
            self.mi_tablero[cr][cc] = 1

        self.barcos_colocados[self.barco_seleccionado]["colocado"] = True
        self.barcos_colocados[self.barco_seleccionado]["pos"] = coords

        # Auto-seleccionar siguiente barco no colocado
        siguientes = [s["id"] for s in SHIPS_DEFINED if not self.barcos_colocados[s["id"]]["colocado"]]
        self.barco_seleccionado = siguientes[0] if siguientes else None

        self._render_mi_tablero()
        self._actualizar_estado_dock()

    def _iniciar_fase_batalla(self):
        self.fase = "batalla"
        self.dock_frame.hide()
        self.frame_radar.show()
        self.lbl_status.setText("🎯 ¡BATALLA NAVAL EN CURSO! Haz clic en el Radar de Ataque para lanzar tus torpedos.")
        self.lbl_status.setStyleSheet("color: #FBBF24; font-weight: bold;")

    def _disparar_al_radar_enemigo(self, r, c):
        if self.fase != "batalla": return
        if self.radar_disparos[r][c] != 0: return

        # Determinar si hay impacto
        hit = (self.ia_barcos[r][c] == 1)
        self.radar_disparos[r][c] = 3 if hit else 2

        coord_str = f"{chr(65+c)}{r+1}"
        if hit:
            self.lbl_status.setText(f"💥 ¡IMPACTO ROJO en {coord_str}! Has tocado un barco enemigo.")
        else:
            self.lbl_status.setText(f"🌊 AGUA en {coord_str}. Torpedo fallido.")

        if self.modo_juego == "lan_1v1" and self.socket_mgr.activo:
            self.socket_mgr.enviar_movimiento("battleship", {"row": r, "col": c, "hit": hit})

        self._render_radar_tablero()

        # Comprobar si ganaste
        if self._comprobar_victoria(self.ia_barcos, self.radar_disparos):
            QMessageBox.information(self, "¡Victoria Naval!", "🎉 ¡Has hundido toda la flota enemiga!")
            try: self.score_mgr.sumar_puntos("battleship", 10)
            except Exception: pass
            self.nuevo_juego()
            return

        # Respuesta IA
        if self.modo_juego == "vs_ia":
            self._disparo_enemigo_ia()

    def _disparo_enemigo_ia(self):
        candidatos = [(r, c) for r in range(10) for c in range(10) if self.mi_tablero[r][c] in (0, 1)]
        if not candidatos: return

        r, c = random.choice(candidatos)
        hit = (self.mi_tablero[r][c] == 1)
        self.mi_tablero[r][c] = 3 if hit else 2
        self._render_mi_tablero()

        # Comprobar derrota
        barcos_mios_restantes = any(self.mi_tablero[r][c] == 1 for r in range(10) for c in range(10))
        if not barcos_mios_restantes:
            QMessageBox.critical(self, "Derrota", "💥 Tu flota ha sido totalmente destruida.")
            self.nuevo_juego()

    def _comprobar_victoria(self, mapa_barcos, mapa_disparos):
        for r in range(10):
            for c in range(10):
                if mapa_barcos[r][c] == 1 and mapa_disparos[r][c] != 3:
                    return False
        return True

    def nuevo_juego(self):
        self.fase = "colocacion"
        self.barco_seleccionado = "carrier"
        self.barcos_colocados = {s["id"]: {"pos": [], "colocado": False} for s in SHIPS_DEFINED}

        self.mi_tablero = [[0]*10 for _ in range(10)]
        self.radar_disparos = [[0]*10 for _ in range(10)]
        self.ia_barcos = [[0]*10 for _ in range(10)]

        self.dock_frame.show()
        self.frame_radar.hide()

        self._colocar_flota_ia()
        self._render_mi_tablero()
        self._render_radar_tablero()
        self._actualizar_estado_dock()

        self.lbl_status.setText("📍 Selecciona un barco del muelle y haz clic en tu cuadrícula para ubicarlo (Presiona 'R' para rotar).")
        self.lbl_status.setStyleSheet("color: #38BDF8; font-weight: bold;")

    def _colocar_flota_ia(self):
        for s in SHIPS_DEFINED:
            size = s["tam"]
            colocado = False
            attempts = 0
            while not colocado and attempts < 200:
                attempts += 1
                orient = random.choice(["H", "V"])
                if orient == "H":
                    r = random.randint(0, 9)
                    c = random.randint(0, 10 - size)
                    if all(self.ia_barcos[r][c+i] == 0 for i in range(size)):
                        for i in range(size): self.ia_barcos[r][c+i] = 1
                        colocado = True
                else:
                    r = random.randint(0, 10 - size)
                    c = random.randint(0, 9)
                    if all(self.ia_barcos[r+i][c] == 0 for i in range(size)):
                        for i in range(size): self.ia_barcos[r+i][c] = 1
                        colocado = True

    def _render_mi_tablero(self):
        for r in range(10):
            for c in range(10):
                val = self.mi_tablero[r][c]
                btn = self.mis_botones[(r, c)]
                if val == 1:
                    btn.setStyleSheet("background: #6366F1; border: 1px solid #FFFFFF; border-radius: 3px;")
                    btn.setText("🚢")
                elif val == 2:
                    btn.setStyleSheet("background: #1E293B; color: #60A5FA; border: none; border-radius: 3px;")
                    btn.setText("💧")
                elif val == 3:
                    btn.setStyleSheet("background: #DC2626; color: white; border: 1px solid #FFFFFF; border-radius: 3px;")
                    btn.setText("💥")
                else:
                    btn.setStyleSheet("background: rgba(30,30,46,0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 3px;")
                    btn.setText("")

    def _render_radar_tablero(self):
        for r in range(10):
            for c in range(10):
                val = self.radar_disparos[r][c]
                btn = self.radar_botones[(r, c)]
                if val == 2:
                    btn.setStyleSheet("background: #1E293B; color: #60A5FA; border: none; border-radius: 3px;")
                    btn.setText("💧")
                elif val == 3:
                    btn.setStyleSheet("background: #DC2626; color: white; border: 2px solid #FDE047; border-radius: 3px;")
                    btn.setText("🔴")
                else:
                    btn.setStyleSheet("background: rgba(30,30,46,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 3px;")
                    btn.setText("")

    def _on_modo_changed(self, idx):
        self.modo_juego = "vs_ia" if idx == 0 else "lan_1v1"
        self.lan_panel.setVisible(self.modo_juego == "lan_1v1")
        self.nuevo_juego()

    def _iniciar_lan_host(self):
        ok, ip = self.socket_mgr.iniciar_servidor_host()
        if ok: self.lbl_status.setText(f"📡 Servidor LAN activo en {ip}. Esperando rival...")

    def _unirse_lan_host(self):
        ip = self.txt_ip_lan.text().strip()
        if self.socket_mgr.conectar_a_host(ip):
            self.lbl_status.setText(f"🟢 Conectado a Host LAN {ip}. Despliega tus barcos.")

    def _on_lan_move_received(self, data):
        payload = data.get("payload", {})
        r = payload.get("row")
        c = payload.get("col")
        if r is not None and c is not None:
            hit = (self.mi_tablero[r][c] == 1)
            self.mi_tablero[r][c] = 3 if hit else 2
            self._render_mi_tablero()
            if not any(self.mi_tablero[i][j] == 1 for i in range(10) for j in range(10)):
                QMessageBox.critical(self, "Derrota", "💥 Tu flota ha sido destruida.")
                self.nuevo_juego()

    def _on_lan_status(self, status_msg):
        self.lbl_status.setText(status_msg)
