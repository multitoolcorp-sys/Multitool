"""
casino.py - Submódulo de Casino & Apuestas con Saldo Real del Usuario
Diseño visual de alta gama con Ruleta Circular animada, Cartas de Blackjack y Tragamonedas Neón.
"""
import random
import platform
import time
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QSpinBox, QComboBox, 
    QTabWidget, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from ..utils.score_manager import ScoreManager
from ..utils.casino_widgets import (
    RouletteWheelWidget, PlayingCardWidget, ROULETTE_COLORS, EUROPEAN_ROULETTE_ORDER
)

try:
    import winsound
except ImportError:
    winsound = None


# ── SIMBOLOS Y MULTIPLICADORES TRAGAMONEDAS ──
SLOT_SYMBOLS = [
    {"sym": "🍒", "name": "Cereza", "mult": 2, "weight": 35},
    {"sym": "🍋", "name": "Limón", "mult": 3, "weight": 25},
    {"sym": "🍇", "name": "Uva", "mult": 5, "weight": 18},
    {"sym": "🔔", "name": "Campana", "mult": 8, "weight": 12},
    {"sym": "⭐", "name": "Estrella", "mult": 15, "weight": 6},
    {"sym": "💎", "name": "Diamante", "mult": 25, "weight": 3},
    {"sym": "7️⃣", "name": "Siete Dorado", "mult": 50, "weight": 1}
]


class CasinoSubmodule(QWidget):
    """
    Submódulo de Casino & Apuestas con Puntos Reales del Usuario:
    1. 🎰 Tragamonedas Neón Arcade (Slots 3 carretes grandes con animación fluida)
    2. 🎡 Ruleta Europea Circular Realista (Plato giratorio con bola animada)
    3. 🃏 Blackjack 21 (Cartas de baraja francesa grandes y mesa de fieltro)
    4. 📜 Bitácora de Transacciones y control de saldo seguro.
    """
    def __init__(self, parent, context, colores, ruta_usuario):
        super().__init__(parent)
        self.context = context
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario or ".")
        self.score_mgr = ScoreManager(self.ruta_usuario)
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        # Estado del Casino
        self.apuesta_actual = 10
        self.anim_timer_slots = QTimer(self)
        self.anim_timer_slots.timeout.connect(self._step_anim_slots)
        self.slots_ticks = 0

        # Estado Blackjack
        self.bj_deck = []
        self.bj_player_hand = []
        self.bj_dealer_hand = []
        self.bj_active = False

        self.inicializar_ui()
        self.actualizar_saldo_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')
        error = self.colores.get('error', '#F87171')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(10)

        # ── Barra Superior: Saldo de Puntos en Vivo ──
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background: {bg_sec};
                border: 1px solid rgba(251, 191, 36, 0.3);
                border-radius: 12px;
                padding: 6px;
            }}
        """)
        h_lay = QHBoxLayout(header_frame)
        h_lay.setContentsMargins(14, 8, 14, 8)
        h_lay.setSpacing(15)

        tit_casino = QLabel("🎰 CASINO ROYAL MULTITOOL")
        tit_casino.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        tit_casino.setStyleSheet("color: #FBBF24; letter-spacing: 1px; border: none;")
        h_lay.addWidget(tit_casino)

        h_lay.addStretch()

        self.lbl_saldo = QLabel("💰 SALDO DISPONIBLE: 0 PTS")
        self.lbl_saldo.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.lbl_saldo.setStyleSheet(f"color: {exito}; border: none;")
        h_lay.addWidget(self.lbl_saldo)

        btn_ref_saldo = QPushButton("🔄")
        btn_ref_saldo.setToolTip("Actualizar Saldo de Puntos")
        btn_ref_saldo.setFixedSize(32, 32)
        btn_ref_saldo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ref_saldo.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; border: none;")
        btn_ref_saldo.clicked.connect(self.actualizar_saldo_ui)
        h_lay.addWidget(btn_ref_saldo)

        # Botón Bono si el saldo es 0
        self.btn_bono = QPushButton("🎁 Bono +50")
        self.btn_bono.setToolTip("Recibir bono de cortesía si tu saldo es 0")
        self.btn_bono.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bono.setStyleSheet("background: #EC4899; color: white; font-weight: bold; border-radius: 6px; padding: 6px 12px; border: none;")
        self.btn_bono.clicked.connect(self._reclamar_bono)
        h_lay.addWidget(self.btn_bono)

        main_layout.addWidget(header_frame)

        # ── Barra de Selección de Apuesta ──
        bet_bar = QFrame()
        bet_bar.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        b_lay = QHBoxLayout(bet_bar)
        b_lay.setContentsMargins(12, 6, 12, 6)
        b_lay.setSpacing(8)

        lbl_bet = QLabel("🎯 MONTO DE APUESTA:")
        lbl_bet.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_bet.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; border: none;")
        b_lay.addWidget(lbl_bet)

        for val in [5, 10, 25, 50, 100]:
            btn_chip = QPushButton(f"{val} pts")
            btn_chip.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_chip.setStyleSheet(f"""
                QPushButton {{
                    background: {bg_terc}; color: white; font-weight: bold;
                    border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 5px 12px; font-size: 10px;
                }}
                QPushButton:hover {{ background: {acento}; border: 1px solid white; }}
            """)
            btn_chip.clicked.connect(lambda ch, v=val: self._set_apuesta(v))
            b_lay.addWidget(btn_chip)

        self.spin_apuesta = QSpinBox()
        self.spin_apuesta.setRange(1, 100000)
        self.spin_apuesta.setValue(self.apuesta_actual)
        self.spin_apuesta.setStyleSheet(f"""
            QSpinBox {{
                background: {bg_terc}; color: #FBBF24; font-weight: bold;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 4px 8px; font-size: 11px;
            }}
        """)
        self.spin_apuesta.valueChanged.connect(self._on_spin_apuesta_changed)
        b_lay.addWidget(self.spin_apuesta)

        btn_max = QPushButton("MAX (Todo)")
        btn_max.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_max.setStyleSheet(f"background: {error}; color: white; font-weight: bold; border-radius: 5px; padding: 5px 10px; font-size: 10px; border: none;")
        btn_max.clicked.connect(self._apuesta_maxima)
        b_lay.addWidget(btn_max)

        b_lay.addStretch()
        main_layout.addWidget(bet_bar)

        # ── Pestañas de Juegos de Casino con Scroll Responsivo ──
        self.tabs_casino = QTabWidget()
        self.tabs_casino.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        self.tabs_casino.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: {bg_main};
                border-radius: 10px;
            }}
            QTabBar::tab {{
                background: {bg_sec};
                color: #AAB0B8;
                padding: 8px 18px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
            }}
            QTabBar::tab:selected {{
                background: {acento};
                color: white;
            }}
        """)

        # 1. Tragamonedas
        self.tab_slots = self._wrap_scroll(self._crear_tab_slots())
        self.tabs_casino.addTab(self.tab_slots, "🎰 Tragamonedas Neón")

        # 2. Ruleta Europea
        self.tab_roulette = self._wrap_scroll(self._crear_tab_roulette())
        self.tabs_casino.addTab(self.tab_roulette, "🎡 Ruleta Europea")

        # 3. Blackjack 21
        self.tab_blackjack = self._wrap_scroll(self._crear_tab_blackjack())
        self.tabs_casino.addTab(self.tab_blackjack, "🃏 Blackjack 21")

        # 4. Historial
        self.tab_historial = self._crear_tab_historial()
        self.tabs_casino.addTab(self.tab_historial, "📜 Historial de Apuestas")

        main_layout.addWidget(self.tabs_casino, 1)

    def _wrap_scroll(self, widget):
        """Envuelve un widget en QScrollArea responsivo sin bordes ni desbordamientos."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(widget)
        return scroll

    # ─────────────────────────────────────────────────────────────────
    # 🎰 JUEGO 1: TRAGAMONEDAS NEON
    # ─────────────────────────────────────────────────────────────────
    def _crear_tab_slots(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Gabinete Arcade Tragamonedas
        reels_frame = QFrame()
        reels_frame.setStyleSheet("""
            QFrame {
                background: #0A0A12;
                border: 3px solid #FBBF24;
                border-radius: 18px;
            }
        """)
        rf_lay = QHBoxLayout(reels_frame)
        rf_lay.setContentsMargins(25, 25, 25, 25)
        rf_lay.setSpacing(20)

        self.reel_labels = []
        for i in range(3):
            lbl = QLabel("7️⃣")
            lbl.setFont(QFont("Segoe UI Emoji", 56))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                QLabel {
                    background: #151526;
                    border: 2px solid rgba(251, 191, 36, 0.4);
                    border-radius: 14px;
                    min-width: 125px;
                    min-height: 135px;
                }
            """)
            rf_lay.addWidget(lbl)
            self.reel_labels.append(lbl)

        lay.addWidget(reels_frame, 0, Qt.AlignmentFlag.AlignCenter)

        # Resultado de tirada
        self.lbl_slots_res = QLabel("¡Presiona GIRAR para probar tu suerte en los rodillos!")
        self.lbl_slots_res.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        self.lbl_slots_res.setStyleSheet("color: #FBBF24; border: none; padding: 4px;")
        self.lbl_slots_res.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_slots_res)

        # Botón Girar
        btn_spin = QPushButton("🎰 ¡GIRAR RODILLOS! (Apostar)")
        btn_spin.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        btn_spin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_spin.setFixedHeight(50)
        btn_spin.setFixedWidth(340)
        btn_spin.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #EC4899);
                color: white; border-radius: 10px; font-weight: bold; border: none;
            }
            QPushButton:hover { background: #FBBF24; color: black; }
        """)
        btn_spin.clicked.connect(self._girar_slots)
        lay.addWidget(btn_spin, 0, Qt.AlignmentFlag.AlignCenter)

        # Tabla de Premios (Leyenda)
        paga_frame = QFrame()
        paga_frame.setStyleSheet("background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 8px;")
        pf_lay = QVBoxLayout(paga_frame)
        paga_lbl = QLabel("🏆 TABLA DE PAGOS: 🍒 x2 | 🍋 x3 | 🍇 x5 | 🔔 x8 | ⭐ x15 | 💎 x25 | 7️⃣7️⃣7️⃣ JACKPOT x50 | 2 Coincidentes: x1.5")
        paga_lbl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        paga_lbl.setStyleSheet("color: rgba(255,255,255,0.7); border: none;")
        paga_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pf_lay.addWidget(paga_lbl)
        lay.addWidget(paga_frame, 0, Qt.AlignmentFlag.AlignCenter)

        return w

    def _girar_slots(self):
        if self.anim_timer_slots.isActive():
            return

        saldo = self.score_mgr.get_total_puntos()
        if saldo < self.apuesta_actual:
            QMessageBox.warning(self, "Saldo Insuficiente", f"No tienes suficientes puntos ({saldo} pts) para apostar {self.apuesta_actual} pts.\n¡Usa el botón de Bono o gana puntos en otros minijuegos!")
            return

        # Deducir apuesta
        self.score_mgr.restar_puntos("casino", self.apuesta_actual)
        self.actualizar_saldo_ui()

        self.slots_ticks = 0
        self.lbl_slots_res.setText("GIRANDO RODILLOS... 🎰")
        self.lbl_slots_res.setStyleSheet("color: #60A5FA;")
        self.anim_timer_slots.start(65)

    def _step_anim_slots(self):
        self.slots_ticks += 1
        symbols_pool = [s["sym"] for s in SLOT_SYMBOLS]
        for lbl in self.reel_labels:
            lbl.setText(random.choice(symbols_pool))

        if self.slots_ticks >= 18:
            self.anim_timer_slots.stop()
            self._finalizar_slots()

    def _finalizar_slots(self):
        try:
            from console import CheatManager
            cm = CheatManager.get_instance()
            if cm.consume_jackpot():
                seven = next(s for s in SLOT_SYMBOLS if s["sym"] == "7️⃣")
                resultado = [seven, seven, seven]
            elif cm.has_casino_luck() and random.random() < 0.85:
                win_sym = random.choice([s for s in SLOT_SYMBOLS if s["mult"] >= 5])
                resultado = [win_sym, win_sym, win_sym if random.random() < 0.6 else win_sym]
            else:
                weights = [s["weight"] for s in SLOT_SYMBOLS]
                resultado = random.choices(SLOT_SYMBOLS, weights=weights, k=3)
        except Exception:
            weights = [s["weight"] for s in SLOT_SYMBOLS]
            resultado = random.choices(SLOT_SYMBOLS, weights=weights, k=3)

        for i, s in enumerate(resultado):
            self.reel_labels[i].setText(s["sym"])

        s1, s2, s3 = resultado[0], resultado[1], resultado[2]

        if s1["sym"] == s2["sym"] == s3["sym"]:
            mult = s1["mult"]
            ganancia = self.apuesta_actual * mult
            self.score_mgr.sumar_puntos("casino", ganancia)
            self._beep(800, 150)
            self._beep(1000, 200)
            self.lbl_slots_res.setText(f"🎉 ¡¡PREMIO MAYOR!! 3x {s1['name']} -> Ganaste +{ganancia} PTS (x{mult})")
            self.lbl_slots_res.setStyleSheet("color: #34D399; font-weight: bold;")
            self._registrar_historial("Tragamonedas", f"3x {s1['sym']}", self.apuesta_actual, ganancia, True)
        elif s1["sym"] == s2["sym"] or s2["sym"] == s3["sym"] or s1["sym"] == s3["sym"]:
            ganancia = int(self.apuesta_actual * 1.5)
            self.score_mgr.sumar_puntos("casino", ganancia)
            self._beep(600, 100)
            self.lbl_slots_res.setText(f"✨ ¡Par de símbolos coincidentes! Recuperas +{ganancia} PTS (x1.5)")
            self.lbl_slots_res.setStyleSheet("color: #FBBF24;")
            self._registrar_historial("Tragamonedas", "2x Par", self.apuesta_actual, ganancia, True)
        else:
            self.lbl_slots_res.setText(f"❌ Sin coincidencia. Has perdido {self.apuesta_actual} PTS.")
            self.lbl_slots_res.setStyleSheet("color: #F87171;")
            self._registrar_historial("Tragamonedas", f"{s1['sym']}|{s2['sym']}|{s3['sym']}", self.apuesta_actual, 0, False)

        self.actualizar_saldo_ui()

    # ─────────────────────────────────────────────────────────────────
    # 🎡 JUEGO 2: RULETA EUROPEA CON RUEDA CIRCULAR Y BOLA REALISTA
    # ─────────────────────────────────────────────────────────────────
    def _crear_tab_roulette(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 15, 20, 15)
        lay.setSpacing(25)

        # ── Panel Izquierdo: Ruleta Circular Animada con Pelota ──
        left_box = QFrame()
        left_box.setStyleSheet("background: #090910; border: 2px solid #34D399; border-radius: 16px; padding: 10px;")
        l_lay = QVBoxLayout(left_box)
        l_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_lay.setSpacing(10)

        # Rueda animada con pelota orbital
        self.wheel_widget = RouletteWheelWidget(self)
        self.wheel_widget.setFixedSize(300, 300)
        self.wheel_widget.spinFinished.connect(self._finalizar_roulette)
        l_lay.addWidget(self.wheel_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # Estado del número ganador
        self.lbl_roulette_num = QLabel("0")
        self.lbl_roulette_num.setVisible(False)  # Mantenido para retrocompatibilidad
        self.lbl_roulette_desc = QLabel("🎯 Rueda Europea Oficial (37 Casillas)")
        self.lbl_roulette_desc.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_roulette_desc.setStyleSheet("color: #34D399; border: none;")
        self.lbl_roulette_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_lay.addWidget(self.lbl_roulette_desc)

        lay.addWidget(left_box, 0, Qt.AlignmentFlag.AlignCenter)

        # ── Panel Derecho: Tablero de Pronósticos & Controles ──
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 15px;")
        r_lay = QVBoxLayout(right_panel)
        r_lay.setSpacing(12)

        tit_r = QLabel("🎯 PRONÓSTICOS DE LA RULETA")
        tit_r.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        tit_r.setStyleSheet("color: #FBBF24;")
        r_lay.addWidget(tit_r)

        r_lay.addWidget(QLabel("Selecciona a qué deseas apostar tu ficha:"))

        self.cb_roulette_tipo = QComboBox()
        self.cb_roulette_tipo.setFont(QFont(self.font_family, 10))
        self.cb_roulette_tipo.setStyleSheet("""
            QComboBox {
                background: #2D2D3D; color: white; border-radius: 6px; padding: 8px; border: 1px solid rgba(255,255,255,0.1);
            }
        """)
        self.cb_roulette_tipo.addItems([
            "🔴 Color Rojo (Paga x2)",
            "⚫ Color Negro (Paga x2)",
            "⚡ Número Par (Paga x2)",
            "🎲 Número Impar (Paga x2)",
            "⬇️ Bajo (1 al 18) (Paga x2)",
            "⬆️ Alto (19 al 36) (Paga x2)",
            "🎯 Número Pleno Exacto (Paga x36)"
        ])
        self.cb_roulette_tipo.currentIndexChanged.connect(self._on_roulette_type_changed)
        r_lay.addWidget(self.cb_roulette_tipo)

        self.pleno_box = QFrame()
        p_lay = QHBoxLayout(self.pleno_box)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.addWidget(QLabel("Número exacto (0-36):"))
        self.spin_roulette_pleno = QSpinBox()
        self.spin_roulette_pleno.setRange(0, 36)
        self.spin_roulette_pleno.setValue(7)
        self.spin_roulette_pleno.setStyleSheet("background: #2D2D3D; color: #FBBF24; font-weight: bold; padding: 4px 10px; border-radius: 4px;")
        p_lay.addWidget(self.spin_roulette_pleno)
        self.pleno_box.setVisible(False)
        r_lay.addWidget(self.pleno_box)

        # Botón Lanzar Bola
        btn_spin_r = QPushButton("🎡 ¡LANZAR BOLA EN LA RULETA!")
        btn_spin_r.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        btn_spin_r.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_spin_r.setFixedHeight(46)
        btn_spin_r.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
                color: white; border-radius: 8px; font-weight: bold; border: none;
            }
            QPushButton:hover { background: #34D399; color: black; }
        """)
        btn_spin_r.clicked.connect(self._girar_roulette)
        r_lay.addWidget(btn_spin_r)

        self.lbl_roulette_res = QLabel("Elige tu pronóstico y lanza la bola para verla girar en el plato.")
        self.lbl_roulette_res.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_roulette_res.setWordWrap(True)
        self.lbl_roulette_res.setStyleSheet("color: #60A5FA; padding: 4px;")
        r_lay.addWidget(self.lbl_roulette_res)

        r_lay.addStretch()
        lay.addWidget(right_panel, 1)

        return w

    def _on_roulette_type_changed(self, idx):
        self.spin_roulette_pleno.setVisible(idx == 6)
        if hasattr(self, 'pleno_box'):
            self.pleno_box.setVisible(idx == 6)

    def _girar_roulette(self):
        if getattr(self.wheel_widget, 'spinning', False):
            return
        saldo = self.score_mgr.get_total_puntos()
        if saldo < self.apuesta_actual:
            QMessageBox.warning(self, "Saldo Insuficiente", f"No tienes suficientes puntos ({saldo} pts) para apostar {self.apuesta_actual} pts.")
            return

        self.score_mgr.restar_puntos("casino", self.apuesta_actual)
        self.actualizar_saldo_ui()

        # Elegir número ganador de forma auténtica
        num = random.randint(0, 36)
        try:
            from console import CheatManager
            if CheatManager.get_instance().has_casino_luck():
                tipo_idx = self.cb_roulette_tipo.currentIndex()
                if tipo_idx == 0:
                    num = random.choice([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36])
                elif tipo_idx == 1:
                    num = random.choice([2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35])
                elif tipo_idx == 6:
                    num = self.spin_roulette_pleno.value()
        except Exception: pass

        self.lbl_roulette_res.setText("GIRANDO LA BOLA EN LA RULETA... 🎡")
        self.lbl_roulette_res.setStyleSheet("color: #60A5FA;")
        self.wheel_widget.spin_to(num)

    def _finalizar_roulette(self, num, color):
        tipo_idx = self.cb_roulette_tipo.currentIndex()
        ganador = False
        mult = 2

        if tipo_idx == 0 and color == "red":
            ganador = True
        elif tipo_idx == 1 and color == "black":
            ganador = True
        elif tipo_idx == 2 and num > 0 and num % 2 == 0:
            ganador = True
        elif tipo_idx == 3 and num > 0 and num % 2 == 1:
            ganador = True
        elif tipo_idx == 4 and 1 <= num <= 18:
            ganador = True
        elif tipo_idx == 5 and 19 <= num <= 36:
            ganador = True
        elif tipo_idx == 6:
            mult = 36
            if num == self.spin_roulette_pleno.value():
                ganador = True

        color_es = "Rojo" if color == "red" else ("Negro" if color == "black" else "Verde")
        self.lbl_roulette_desc.setText(f"Número Ganador: {num} ({color_es})")

        if ganador:
            premio = self.apuesta_actual * mult
            self.score_mgr.sumar_puntos("casino", premio)
            self._beep(850, 200)
            self.lbl_roulette_res.setText(f"🎉 ¡ACERTASTE EN LA RULETA! Salió {num} ({color_es}) -> Ganaste +{premio} PTS (x{mult})")
            self.lbl_roulette_res.setStyleSheet("color: #34D399; font-weight: bold;")
            self._registrar_historial("Ruleta", f"Num {num} ({color_es})", self.apuesta_actual, premio, True)
        else:
            self.lbl_roulette_res.setText(f"❌ La bola cayó en {num} ({color_es}). Pierdes {self.apuesta_actual} PTS.")
            self.lbl_roulette_res.setStyleSheet("color: #F87171;")
            self._registrar_historial("Ruleta", f"Num {num} ({color_es})", self.apuesta_actual, 0, False)

        self.actualizar_saldo_ui()

    # ─────────────────────────────────────────────────────────────────
    # 🃏 JUEGO 3: BLACKJACK 21 CON CARTAS REALISTAS GRANDES
    # ─────────────────────────────────────────────────────────────────
    def _crear_tab_blackjack(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 15, 20, 15)
        lay.setSpacing(12)

        # Tablero de Fieltro Verde Casino
        board = QFrame()
        board.setStyleSheet("""
            QFrame {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 #104828, stop:1 #062314);
                border: 3px solid #15803D;
                border-radius: 16px;
                padding: 18px;
            }
        """)
        b_lay = QVBoxLayout(board)
        b_lay.setSpacing(12)

        # ── Crupier ──
        d_header = QHBoxLayout()
        d_header.addWidget(QLabel("🎩 CRUPIER (LA CASA):", font=QFont(self.font_family, 10, QFont.Weight.Bold)))
        self.lbl_bj_dealer_pts = QLabel("Puntos: ?")
        self.lbl_bj_dealer_pts.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_bj_dealer_pts.setStyleSheet("color: #FBBF24; background: rgba(0,0,0,0.3); border-radius: 4px; padding: 2px 8px;")
        d_header.addWidget(self.lbl_bj_dealer_pts)
        d_header.addStretch()
        b_lay.addLayout(d_header)

        # Contenedor visual de cartas del Crupier
        self.dealer_cards_layout = QHBoxLayout()
        self.dealer_cards_layout.setSpacing(10)
        self.dealer_cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        b_lay.addLayout(self.dealer_cards_layout)

        # Separador de mesa
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.12);")
        b_lay.addWidget(sep)

        # ── Jugador ──
        p_header = QHBoxLayout()
        p_header.addWidget(QLabel("👤 TU MANO:", font=QFont(self.font_family, 10, QFont.Weight.Bold)))
        self.lbl_bj_player_pts = QLabel("Puntos: 0")
        self.lbl_bj_player_pts.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_bj_player_pts.setStyleSheet("color: #34D399; background: rgba(0,0,0,0.3); border-radius: 4px; padding: 2px 8px;")
        p_header.addWidget(self.lbl_bj_player_pts)
        p_header.addStretch()
        b_lay.addLayout(p_header)

        # Contenedor visual de cartas del Jugador
        self.player_cards_layout = QHBoxLayout()
        self.player_cards_layout.setSpacing(10)
        self.player_cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        b_lay.addLayout(self.player_cards_layout)

        # Labels ocultos para retrocompatibilidad con tests
        self.lbl_bj_dealer = QLabel("")
        self.lbl_bj_dealer.setVisible(False)
        self.lbl_bj_player = QLabel("")
        self.lbl_bj_player.setVisible(False)
        b_lay.addWidget(self.lbl_bj_dealer)
        b_lay.addWidget(self.lbl_bj_player)

        lay.addWidget(board)

        # Botones de Acción de Blackjack
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_bj_deal = QPushButton("🃏 Repartir Cartas")
        self.btn_bj_deal.setFixedHeight(40)
        self.btn_bj_deal.setStyleSheet("background: #6366F1; color: white; font-weight: bold; border-radius: 6px;")
        self.btn_bj_deal.clicked.connect(self._iniciar_blackjack)
        btn_box.addWidget(self.btn_bj_deal)

        self.btn_bj_hit = QPushButton("➕ Pedir Carta (Hit)")
        self.btn_bj_hit.setFixedHeight(40)
        self.btn_bj_hit.setEnabled(False)
        self.btn_bj_hit.setStyleSheet("background: #10B981; color: white; font-weight: bold; border-radius: 6px;")
        self.btn_bj_hit.clicked.connect(self._bj_hit)
        btn_box.addWidget(self.btn_bj_hit)

        self.btn_bj_stand = QPushButton("✋ Plantarse (Stand)")
        self.btn_bj_stand.setFixedHeight(40)
        self.btn_bj_stand.setEnabled(False)
        self.btn_bj_stand.setStyleSheet("background: #F59E0B; color: white; font-weight: bold; border-radius: 6px;")
        self.btn_bj_stand.clicked.connect(self._bj_stand)
        btn_box.addWidget(self.btn_bj_stand)

        self.btn_bj_double = QPushButton("⚡ Doblar (x2)")
        self.btn_bj_double.setFixedHeight(40)
        self.btn_bj_double.setEnabled(False)
        self.btn_bj_double.setStyleSheet("background: #EC4899; color: white; font-weight: bold; border-radius: 6px;")
        self.btn_bj_double.clicked.connect(self._bj_double)
        btn_box.addWidget(self.btn_bj_double)

        lay.addLayout(btn_box)

        self.lbl_bj_res = QLabel("Presiona Repartir Cartas para apostar e iniciar la ronda.")
        self.lbl_bj_res.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_bj_res.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bj_res.setStyleSheet("color: #60A5FA; padding: 4px;")
        lay.addWidget(self.lbl_bj_res)

        # Cargar cartas iniciales vacías
        self._limpiar_cartas_ui()
        return w

    def _limpiar_cartas_ui(self):
        while self.dealer_cards_layout.count():
            item = self.dealer_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.player_cards_layout.count():
            item = self.player_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Colocar 2 reversos por defecto
        for _ in range(2):
            self.dealer_cards_layout.addWidget(PlayingCardWidget(hidden=True))
            self.player_cards_layout.addWidget(PlayingCardWidget(hidden=True))

    def _render_mano_ui(self, layout, mano, ocultar_segunda=False):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, c in enumerate(mano):
            es_oculta = (ocultar_segunda and idx == 1)
            card_w = PlayingCardWidget(rank=c["rank"], suit=c["suit"], hidden=es_oculta)
            layout.addWidget(card_w)

    def _crear_baraja(self):
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        deck = [{"rank": r, "suit": s} for s in suits for r in ranks]
        random.shuffle(deck)
        return deck

    def _calc_mano(self, mano):
        pts = 0
        ases = 0
        for c in mano:
            r = c["rank"]
            if r in ["J", "Q", "K"]:
                pts += 10
            elif r == "A":
                pts += 11
                ases += 1
            else:
                pts += int(r)

        while pts > 21 and ases > 0:
            pts -= 10
            ases -= 1
        return pts

    def _iniciar_blackjack(self):
        saldo = self.score_mgr.get_total_puntos()
        if saldo < self.apuesta_actual:
            QMessageBox.warning(self, "Saldo Insuficiente", f"No tienes suficientes puntos para apostar {self.apuesta_actual} pts.")
            return

        self.score_mgr.restar_puntos("casino", self.apuesta_actual)
        self.actualizar_saldo_ui()

        self.bj_deck = self._crear_baraja()
        try:
            from console import CheatManager
            if CheatManager.get_instance().has_casino_luck():
                self.bj_player_hand = [{"rank": "A", "suit": "♠"}, {"rank": "K", "suit": "♠"}]
                self.bj_dealer_hand = [self.bj_deck.pop(), self.bj_deck.pop()]
            else:
                self.bj_player_hand = [self.bj_deck.pop(), self.bj_deck.pop()]
                self.bj_dealer_hand = [self.bj_deck.pop(), self.bj_deck.pop()]
        except Exception:
            self.bj_player_hand = [self.bj_deck.pop(), self.bj_deck.pop()]
            self.bj_dealer_hand = [self.bj_deck.pop(), self.bj_deck.pop()]

        self.bj_active = True

        p_pts = self._calc_mano(self.bj_player_hand)
        self._render_mano_ui(self.player_cards_layout, self.bj_player_hand)
        self._render_mano_ui(self.dealer_cards_layout, self.bj_dealer_hand, ocultar_segunda=True)

        self.lbl_bj_player_pts.setText(f"Puntos: {p_pts}")
        d_first = self.bj_dealer_hand[0]["rank"]
        d_val = 11 if d_first == "A" else (10 if d_first in ["J","Q","K"] else int(d_first))
        self.lbl_bj_dealer_pts.setText(f"Puntos visibles: {d_val}")

        self.btn_bj_deal.setEnabled(False)
        self.btn_bj_hit.setEnabled(True)
        self.btn_bj_stand.setEnabled(True)
        self.btn_bj_double.setEnabled(saldo >= self.apuesta_actual)

        if p_pts == 21:
            self._bj_stand()
        else:
            self.lbl_bj_res.setText("¿Deseas pedir carta, plantarte o doblar apuesta?")
            self.lbl_bj_res.setStyleSheet("color: #60A5FA;")

    def _bj_hit(self):
        if not self.bj_active: return
        self.btn_bj_double.setEnabled(False)
        self.bj_player_hand.append(self.bj_deck.pop())
        p_pts = self._calc_mano(self.bj_player_hand)
        self._render_mano_ui(self.player_cards_layout, self.bj_player_hand)
        self.lbl_bj_player_pts.setText(f"Puntos: {p_pts}")

        if p_pts > 21:
            self._finalizar_blackjack("bust")
        elif p_pts == 21:
            self._bj_stand()

    def _bj_stand(self):
        if not self.bj_active: return
        self.btn_bj_hit.setEnabled(False)
        self.btn_bj_stand.setEnabled(False)
        self.btn_bj_double.setEnabled(False)

        while self._calc_mano(self.bj_dealer_hand) < 17:
            self.bj_dealer_hand.append(self.bj_deck.pop())

        d_pts = self._calc_mano(self.bj_dealer_hand)
        p_pts = self._calc_mano(self.bj_player_hand)

        self._render_mano_ui(self.dealer_cards_layout, self.bj_dealer_hand, ocultar_segunda=False)
        self.lbl_bj_dealer_pts.setText(f"Puntos: {d_pts}")

        if d_pts > 21:
            self._finalizar_blackjack("dealer_bust")
        elif p_pts > d_pts:
            self._finalizar_blackjack("win")
        elif p_pts < d_pts:
            self._finalizar_blackjack("lose")
        else:
            self._finalizar_blackjack("push")

    def _bj_double(self):
        if not self.bj_active: return
        saldo = self.score_mgr.get_total_puntos()
        if saldo >= self.apuesta_actual:
            self.score_mgr.restar_puntos("casino", self.apuesta_actual)
            self.apuesta_actual *= 2
            self.spin_apuesta.setValue(self.apuesta_actual)
            self.actualizar_saldo_ui()
            self._bj_hit()
            if self.bj_active:
                self._bj_stand()

    def _finalizar_blackjack(self, outcome):
        self.bj_active = False
        self.btn_bj_deal.setEnabled(True)
        self.btn_bj_hit.setEnabled(False)
        self.btn_bj_stand.setEnabled(False)
        self.btn_bj_double.setEnabled(False)

        p_pts = self._calc_mano(self.bj_player_hand)
        d_pts = self._calc_mano(self.bj_dealer_hand)
        self._render_mano_ui(self.dealer_cards_layout, self.bj_dealer_hand, ocultar_segunda=False)
        self.lbl_bj_dealer_pts.setText(f"Puntos: {d_pts}")

        if outcome == "bust":
            self.lbl_bj_res.setText(f"💥 ¡Te pasaste de 21 ({p_pts})! Pierdes {self.apuesta_actual} PTS.")
            self.lbl_bj_res.setStyleSheet("color: #F87171;")
            self._registrar_historial("Blackjack", f"Bust ({p_pts})", self.apuesta_actual, 0, False)
        elif outcome == "dealer_bust":
            premio = self.apuesta_actual * 2
            self.score_mgr.sumar_puntos("casino", premio)
            self._beep(800, 150)
            self.lbl_bj_res.setText(f"🎉 ¡El crupier se pasó ({d_pts})! Ganas +{premio} PTS (x2)")
            self.lbl_bj_res.setStyleSheet("color: #34D399; font-weight: bold;")
            self._registrar_historial("Blackjack", f"Dealer Bust ({d_pts})", self.apuesta_actual, premio, True)
        elif outcome == "win":
            if p_pts == 21 and len(self.bj_player_hand) == 2:
                premio = int(self.apuesta_actual * 2.5)
                msg = f"🌟 ¡¡BLACKJACK NATURAL 21!! Ganaste +{premio} PTS (x2.5)"
            else:
                premio = self.apuesta_actual * 2
                msg = f"🎉 ¡Ganaste a la casa! ({p_pts} vs {d_pts}) +{premio} PTS (x2)"
            self.score_mgr.sumar_puntos("casino", premio)
            self._beep(850, 180)
            self.lbl_bj_res.setText(msg)
            self.lbl_bj_res.setStyleSheet("color: #34D399; font-weight: bold;")
            self._registrar_historial("Blackjack", f"Victoria {p_pts}v{d_pts}", self.apuesta_actual, premio, True)
        elif outcome == "lose":
            self.lbl_bj_res.setText(f"❌ La casa gana ({d_pts} vs {p_pts}). Pierdes {self.apuesta_actual} PTS.")
            self.lbl_bj_res.setStyleSheet("color: #F87171;")
            self._registrar_historial("Blackjack", f"Derrota {p_pts}v{d_pts}", self.apuesta_actual, 0, False)
        elif outcome == "push":
            self.score_mgr.sumar_puntos("casino", self.apuesta_actual)
            self.lbl_bj_res.setText(f"🤝 ¡Empate / Push! ({p_pts} pts) Se devuelve tu apuesta de {self.apuesta_actual} PTS.")
            self.lbl_bj_res.setStyleSheet("color: #FBBF24;")
            self._registrar_historial("Blackjack", f"Empate ({p_pts})", self.apuesta_actual, self.apuesta_actual, True)

        self.actualizar_saldo_ui()

    # ─────────────────────────────────────────────────────────────────
    # 📜 HISTORIAL & BITÁCORA DE APUESTAS
    # ─────────────────────────────────────────────────────────────────
    def _crear_tab_historial(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)

        lay.addWidget(QLabel("📜 Registro de Últimas Apuestas y Transacciones:"))
        self.tabla_hist = QTableWidget()
        self.tabla_hist.setColumnCount(5)
        self.tabla_hist.setHorizontalHeaderLabels(["Hora", "Juego", "Detalle", "Apuesta", "Resultado"])
        self.tabla_hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_hist.setStyleSheet(f"""
            QTableWidget {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
            }}
            QHeaderView::section {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: {self.colores.get('acento', '#6366F1')}; font-weight: bold; border: none; padding: 6px;
            }}
        """)
        lay.addWidget(self.tabla_hist, 1)
        return w

    def _registrar_historial(self, juego, detalle, apuesta, premio, gano):
        hora = time.strftime("%H:%M:%S")
        self.tabla_hist.insertRow(0)

        self.tabla_hist.setItem(0, 0, QTableWidgetItem(hora))
        self.tabla_hist.setItem(0, 1, QTableWidgetItem(juego))
        self.tabla_hist.setItem(0, 2, QTableWidgetItem(detalle))
        self.tabla_hist.setItem(0, 3, QTableWidgetItem(f"-{apuesta} pts"))

        res_item = QTableWidgetItem(f"+{premio} pts" if gano else "0 pts (Perdido)")
        res_item.setForeground(QColor("#34D399" if gano else "#F87171"))
        self.tabla_hist.setItem(0, 4, res_item)

        if self.tabla_hist.rowCount() > 50:
            self.tabla_hist.removeRow(50)

    # ─────────────────────────────────────────────────────────────────
    # MÉTODOS AUXILIARES Y CONTROL DE SALDO
    # ─────────────────────────────────────────────────────────────────
    def _set_apuesta(self, v):
        self.apuesta_actual = v
        self.spin_apuesta.setValue(v)

    def _on_spin_apuesta_changed(self, v):
        self.apuesta_actual = v

    def _apuesta_maxima(self):
        saldo = self.score_mgr.get_total_puntos()
        if saldo > 0:
            self._set_apuesta(saldo)

    def _reclamar_bono(self):
        saldo = self.score_mgr.get_total_puntos()
        if saldo <= 0:
            self.score_mgr.sumar_puntos("casino", 50)
            self.actualizar_saldo_ui()
            self._beep(800, 120)
            QMessageBox.information(self, "🎁 Bono de Cortesía", "¡Has recibido +50 puntos de bienvenida para jugar en el Casino!")
        else:
            QMessageBox.information(self, "Bono No Disponible", f"Aún tienes {saldo} puntos disponibles.\nEl bono solo se activa si tu saldo llega a 0 pts.")

    def actualizar_saldo_ui(self):
        saldo = self.score_mgr.get_total_puntos()
        self.lbl_saldo.setText(f"💰 SALDO DISPONIBLE: {saldo:,} PTS")
        if hasattr(self, 'btn_bono'):
            self.btn_bono.setEnabled(saldo == 0)

    def _beep(self, freq, duration):
        if winsound:
            try:
                winsound.Beep(freq, duration)
            except Exception:
                pass

    def actualizar_tema(self, colores):
        self.colores = colores
        bg_main = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_main}; color: white;")
        self.actualizar_saldo_ui()

    def cleanup(self):
        if self.anim_timer_slots.isActive():
            self.anim_timer_slots.stop()
        if hasattr(self, 'wheel_widget') and hasattr(self.wheel_widget, 'spin_timer'):
            if self.wheel_widget.spin_timer.isActive():
                self.wheel_widget.spin_timer.stop()
