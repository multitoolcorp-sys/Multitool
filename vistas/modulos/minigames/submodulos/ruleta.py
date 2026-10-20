import math
import random
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QGraphicsView, 
    QGraphicsScene, QFrame, QMessageBox, QTextEdit,
    QSpinBox, QCheckBox, QStackedWidget, QTabWidget, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QFont, QColor, QBrush, QPen, QPainter, QPainterPath, QRadialGradient, QLinearGradient


class RouletteGUI(QWidget):
    """
    Submódulo de Ruletas y Sorteos Aleatorios:
    - 🎡 Ruleta Decisora Clásica
    - 👥 Generador de Equipos Aleatorios
    - 🎲 Lanzador de Dados N-Caras (D4, D6, D8, D10, D12, D20, D100)
    - 🔢 Sorteo de Números Aleatorios
    - 🪙 Lanzamiento de Moneda (Cara / Cruz)
    """
    def __init__(self, parent, colores, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = Path(ruta_usuario or ".")
        self.ruta_data = self.ruta_usuario / "ruleta_opciones.json"
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ── Barra Superior de Navegación por Tipos de Sorteo / Ruletas ──
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: {self.colores.get('bg_principal', '#121218')};
                border-radius: 10px;
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                padding: 10px 16px;
                font-weight: bold;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                background: {self.colores.get('bg_principal', '#121218')};
                color: {self.colores.get('acento', '#6366F1')};
                border-bottom: 3px solid {self.colores.get('acento', '#6366F1')};
            }}
            QTabBar::tab:hover:!selected {{
                background: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
            }}
        """)

        # 1. Ruleta Decisora
        self.tab_decisora = RuletaDecisoraView(self, self.colores, self.ruta_data)
        self.tabs.addTab(self.tab_decisora, "🎡 Ruleta Decisora")

        # 2. Generador de Equipos
        self.tab_equipos = GeneradorEquiposView(self, self.colores)
        self.tabs.addTab(self.tab_equipos, "👥 Generador de Equipos")

        # 3. Lanzador de Dados N-Caras
        self.tab_dados = LanzadorDadosView(self, self.colores)
        self.tabs.addTab(self.tab_dados, "🎲 Dado de N-Caras")

        # 4. Sorteo de Números
        self.tab_numeros = SorteoNumerosView(self, self.colores)
        self.tabs.addTab(self.tab_numeros, "🔢 Sorteo de Números")

        # 5. Moneda (Cara / Cruz)
        self.tab_moneda = LanzamientoMonedaView(self, self.colores)
        self.tabs.addTab(self.tab_moneda, "🪙 Lanzar Moneda")

        main_layout.addWidget(self.tabs)


# ─────────────────────────────────────────────────────────────────────────
# 1. RULETA DECISORA CLÁSICA
# ─────────────────────────────────────────────────────────────────────────
class RuletaDecisoraView(QWidget):
    def __init__(self, parent, colores, ruta_data):
        super().__init__(parent)
        self.colores = colores
        self.ruta_data = ruta_data
        
        self.opciones = self.cargar_datos()
        if not self.opciones:
            self.opciones = ["Opción 1", "Opción 2", "Opción 3", "Opción 4"]
            
        self.angulo_actual = 0
        self.velocidad = 0
        self.girando = False
        
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._girar_paso)

    def init_ui(self):
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(20, 20, 20, 20)
        main_lay.setSpacing(20)
        
        # Lado Izquierdo: Ruleta Visual
        area_ruleta = QVBoxLayout()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setFixedSize(400, 400)
        area_ruleta.addWidget(self.view, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_resultado = QLabel("¡PRUEBA TU SUERTE!")
        self.lbl_resultado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_resultado.setStyleSheet(f"""
            color: white; 
            background: rgba(30, 30, 46, 0.65); 
            padding: 12px; 
            border-radius: 10px; 
            border: 1px solid rgba(255, 255, 255, 0.08);
        """)
        area_ruleta.addWidget(self.lbl_resultado)
        main_lay.addLayout(area_ruleta, 2)
        
        # Lado Derecho: Controles
        panel_ctrl = QFrame()
        panel_ctrl.setFixedWidth(270)
        panel_ctrl.setStyleSheet(f"""
            QFrame {{
                background: rgba(30, 30, 46, 0.65); 
                border-radius: 14px; 
                padding: 15px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)
        ctrl_lay = QVBoxLayout(panel_ctrl)
        ctrl_lay.setSpacing(10)
        
        lbl_tit = QLabel("🎡 OPCIONES DE RULETA")
        lbl_tit.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores['acento']};")
        ctrl_lay.addWidget(lbl_tit)
        
        self.txt_opciones = QLineEdit()
        self.txt_opciones.setPlaceholderText("Agregar opción...")
        self.txt_opciones.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.04); 
                color: white; border-radius: 6px; padding: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        self.txt_opciones.returnPressed.connect(self.agregar_opcion)
        ctrl_lay.addWidget(self.txt_opciones)

        lbl_edit = QLabel("📝 Edición rápida (una por línea):")
        lbl_edit.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        ctrl_lay.addWidget(lbl_edit)

        self.edit_masa = QTextEdit()
        self.edit_masa.setPlaceholderText("Opción 1\nOpción 2...")
        self.edit_masa.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.2); color: white; border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.08); padding: 6px;
            }
        """)
        self.edit_masa.setPlainText("\n".join(self.opciones))
        self.edit_masa.textChanged.connect(self._sync_opciones)
        ctrl_lay.addWidget(self.edit_masa)
        
        btn_clear = QPushButton("🗑️ Limpiar Todo")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background: rgba(248, 113, 113, 0.1); color: #F87171; 
                border: 1px solid rgba(248, 113, 113, 0.2); border-radius: 6px; padding: 6px;
            }
            QPushButton:hover { background: rgba(248, 113, 113, 0.2); }
        """)
        btn_clear.clicked.connect(self.limpiar_todo)
        ctrl_lay.addWidget(btn_clear)
        
        self.btn_spin = QPushButton("🚀 ¡GIRAR RULETA!")
        self.btn_spin.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_spin.setFixedHeight(44)
        self.btn_spin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_spin.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; color: white; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        self.btn_spin.clicked.connect(self.iniciar_giro)
        ctrl_lay.addWidget(self.btn_spin)
        
        main_lay.addWidget(panel_ctrl)
        self.dibujar_ruleta()

    def dibujar_ruleta(self):
        self.scene.clear()
        n = len(self.opciones)
        if n == 0: return
        
        radio = 180
        centro = QPointF(200, 200)
        arco_por_opcion = 360 / n
        colores_arco = ["#6366F1", "#10B981", "#EC4899", "#FBBF24", "#3B82F6", "#EF4444", "#8B5CF6", "#06B6D4"]
        
        for i in range(n):
            gradient = QRadialGradient(centro, radio)
            base_col = QColor(colores_arco[i % len(colores_arco)])
            gradient.setColorAt(0.0, QColor(base_col.red(), base_col.green(), base_col.blue(), 180))
            gradient.setColorAt(0.8, QColor(base_col.red(), base_col.green(), base_col.blue(), 230))
            gradient.setColorAt(1.0, QColor(base_col.darker(140)))
            
            path = QPainterPath(centro)
            ang_start = i * arco_por_opcion + self.angulo_actual
            path.arcTo(centro.x()-radio, centro.y()-radio, radio*2, radio*2, ang_start, arco_por_opcion)
            path.lineTo(centro)
            
            p_item = self.scene.addPath(path, QPen(QColor(255, 255, 255, 30), 1.5), QBrush(gradient))
            p_item.setZValue(0)
            
            txt_cont = self.opciones[i]
            if len(txt_cont) > 12: txt_cont = txt_cont[:10] + ".."
            txt_item = self.scene.addText(txt_cont, QFont("Segoe UI", 10, QFont.Weight.Bold))
            txt_item.setDefaultTextColor(Qt.GlobalColor.white)
            
            angulo_grados = ang_start + arco_por_opcion / 2
            ang_rad = math.radians(angulo_grados)
            dist_centro = radio * 0.65
            tx = centro.x() + dist_centro * math.cos(ang_rad)
            ty = centro.y() - dist_centro * math.sin(ang_rad)
            
            rect = txt_item.boundingRect()
            txt_item.setTransformOriginPoint(rect.center())
            txt_item.setRotation(-angulo_grados)
            txt_item.setPos(tx - rect.width()/2, ty - rect.height()/2)
            txt_item.setZValue(10)
        
        # Pivote central
        pivot_r = 22
        pivot_gradient = QRadialGradient(centro, pivot_r)
        pivot_gradient.setColorAt(0.0, QColor("#FFFFFF"))
        pivot_gradient.setColorAt(1.0, QColor("#1F2937"))
        self.scene.addEllipse(centro.x()-pivot_r, centro.y()-pivot_r, pivot_r*2, pivot_r*2, QPen(QColor("#E5E7EB"), 1.5), QBrush(pivot_gradient))

        # Puntero
        tip_y = centro.y() - radio + 10
        base_y = centro.y() - radio - 18
        puntero = QPainterPath()
        puntero.moveTo(centro.x(), tip_y)
        puntero.lineTo(centro.x() - 16, base_y)
        puntero.lineTo(centro.x() + 16, base_y)
        puntero.closeSubpath()
        
        pointer_gradient = QLinearGradient(QPointF(centro.x() - 16, base_y), QPointF(centro.x() + 16, tip_y))
        pointer_gradient.setColorAt(0.0, QColor("#FBBF24"))
        pointer_gradient.setColorAt(1.0, QColor("#78350F"))
        self.scene.addPath(puntero, QPen(QColor("#FFFBEB"), 1.5), QBrush(pointer_gradient))

    def cargar_datos(self):
        if self.ruta_data.exists():
            try:
                with open(self.ruta_data, "r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return []

    def guardar_datos(self):
        try:
            with open(self.ruta_data, "w", encoding="utf-8") as f: json.dump(self.opciones, f, indent=4)
        except: pass

    def _sync_opciones(self):
        new_text = self.edit_masa.toPlainText()
        self.opciones = [line.strip() for line in new_text.split("\n") if line.strip()]
        self.guardar_datos()
        self.dibujar_ruleta()

    def agregar_opcion(self):
        txt = self.txt_opciones.text().strip()
        if txt:
            self.opciones.append(txt)
            self.txt_opciones.clear()
            self._actualizar_editor_masa()
            self.guardar_datos()
            self.dibujar_ruleta()

    def limpiar_todo(self):
        self.opciones = []
        self._actualizar_editor_masa()
        self.guardar_datos()
        self.dibujar_ruleta()

    def _actualizar_editor_masa(self):
        self.edit_masa.blockSignals(True)
        self.edit_masa.setPlainText("\n".join(self.opciones))
        self.edit_masa.blockSignals(False)

    def iniciar_giro(self):
        if self.girando: return
        if len(self.opciones) < 2:
            QMessageBox.warning(self, "Ruleta", "Se necesitan al menos 2 opciones para girar.")
            return
        self.girando = True
        self.velocidad = random.uniform(15, 25)
        self.lbl_resultado.setText("🎰 ¡Girando...!")
        self.timer.start(20)

    def _girar_paso(self):
        self.angulo_actual = (self.angulo_actual + self.velocidad) % 360
        self.velocidad *= 0.985
        if self.velocidad < 0.15:
            self.timer.stop()
            self.girando = False
            self.determinar_ganador()
        self.dibujar_ruleta()

    def determinar_ganador(self):
        n = len(self.opciones)
        if n == 0: return
        paso = 360 / n
        actual_norm = (90 - self.angulo_actual) % 360
        idx_ganador = int(actual_norm / paso) % n
        ganador = self.opciones[idx_ganador]
        self.lbl_resultado.setText(f"🎯 GANADOR: {ganador.upper()}")


# ─────────────────────────────────────────────────────────────────────────
# 2. GENERADOR / RULETA DE EQUIPOS ALEATORIOS
# ─────────────────────────────────────────────────────────────────────────
class GeneradorEquiposView(QWidget):
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Panel Izquierdo: Lista de Integrantes y Config
        panel_left = QFrame()
        panel_left.setFixedWidth(280)
        panel_left.setStyleSheet("background: rgba(30, 30, 46, 0.65); border-radius: 12px; padding: 12px;")
        lay_left = QVBoxLayout(panel_left)

        lbl_tit = QLabel("👥 Participantes:")
        lbl_tit.setStyleSheet("color: white; font-weight: bold;")
        lay_left.addWidget(lbl_tit)

        self.txt_integrantes = QTextEdit()
        self.txt_integrantes.setPlaceholderText("Escribe un nombre por línea...\nEj:\nAna\nCarlos\nDavid\nElena\nGabriel\nIsabel")
        self.txt_integrantes.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; padding: 6px;")
        self.txt_integrantes.setPlainText("Ana\nCarlos\nDavid\nElena\nGabriel\nIsabel\nLucas\nMaria")
        lay_left.addWidget(self.txt_integrantes)

        h_spin = QHBoxLayout()
        lbl_n_eq = QLabel("Nº de Equipos:")
        lbl_n_eq.setStyleSheet("color: white; font-size: 11px;")
        h_spin.addWidget(lbl_n_eq)

        self.spin_equipos = QSpinBox()
        self.spin_equipos.setRange(2, 12)
        self.spin_equipos.setValue(2)
        self.spin_equipos.setStyleSheet("QSpinBox { background: rgba(0,0,0,0.3); color: white; padding: 4px; border-radius: 4px; }")
        h_spin.addWidget(self.spin_equipos)
        lay_left.addLayout(h_spin)

        btn_generar = QPushButton("⚡ GENERAR EQUIPOS")
        btn_generar.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn_generar.setFixedHeight(40)
        btn_generar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_generar.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; border: none;")
        btn_generar.clicked.connect(self.generar_equipos)
        lay_left.addWidget(btn_generar)

        layout.addWidget(panel_left)

        # Panel Derecho: Visualización de Equipos
        self.scroll_equipos = QScrollArea()
        self.scroll_equipos.setWidgetResizable(True)
        self.scroll_equipos.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.cont_equipos = QWidget()
        self.grid_equipos = QGridLayout(self.cont_equipos)
        self.grid_equipos.setSpacing(15)
        self.scroll_equipos.setWidget(self.cont_equipos)

        layout.addWidget(self.scroll_equipos, 1)

    def generar_equipos(self):
        raw = self.txt_integrantes.toPlainText().strip()
        nombres = [n.strip() for n in raw.split("\n") if n.strip()]
        if not nombres:
            QMessageBox.warning(self, "Equipos", "Por favor ingresa al menos un participante.")
            return

        num_equipos = self.spin_equipos.value()
        random.shuffle(nombres)

        # Limpiar grid
        while self.grid_equipos.count():
            item = self.grid_equipos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        colores_equipos = ["#6366F1", "#10B981", "#EC4899", "#FBBF24", "#3B82F6", "#EF4444", "#8B5CF6", "#06B6D4", "#F59E0B", "#10B981"]

        equipos = [[] for _ in range(num_equipos)]
        for idx, nombre in enumerate(nombres):
            equipos[idx % num_equipos].append(nombre)

        for i, miembros in enumerate(equipos):
            card = QFrame()
            col = colores_equipos[i % len(colores_equipos)]
            card.setStyleSheet(f"""
                QFrame {{
                    background: rgba(30, 30, 46, 0.7);
                    border: 2px solid {col};
                    border-radius: 10px;
                    padding: 10px;
                }}
            """)
            c_lay = QVBoxLayout(card)
            
            lbl_e_title = QLabel(f"🛡️ EQUIPO {i+1}")
            lbl_e_title.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
            c_lay.addWidget(lbl_e_title)

            for m in miembros:
                lbl_m = QLabel(f"• {m}")
                lbl_m.setStyleSheet("color: white; font-size: 12px;")
                c_lay.addWidget(lbl_m)
            c_lay.addStretch()

            r, c = divmod(i, 2)
            self.grid_equipos.addWidget(card, r, c)


# ─────────────────────────────────────────────────────────────────────────
# 3. LANZADOR DE DADOS 3D (D4, D6, D8, D10, D12, D20 - LÍMITE D20 D&D)
# ─────────────────────────────────────────────────────────────────────────
class Dice3DWidget(QWidget):
    """
    Widget de animación 3D de Dado cerámico blanco con bordes redondeados y puntos (pips),
    inspirado en dados reales tridimensionales. Límite máximo: D20.
    """
    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.setMinimumSize(250, 230)

        self.rot_y = 0.3        # Ángulo isométrica Y
        self.rot_x = 0.3        # Ángulo isométrica X
        self.altura_z = 0.0      # Elevación en el aire
        self.val_top = 3
        self.val_left = 5
        self.val_right = 6
        self.caras = 6
        self.animando = False
        self.resultado_final = 6

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animar_step)
        self.frame_actual = 0
        self.total_frames = 60

    def iniciar_lanzamiento(self, caras, resultado):
        self.caras = min(20, caras)  # Límite máximo 20 caras (D&D)
        self.resultado_final = resultado
        self.animando = True
        self.frame_actual = 0
        self.total_frames = 60
        self.timer.start(16)  # 60 FPS

    def _animar_step(self):
        self.frame_actual += 1
        progress = self.frame_actual / self.total_frames

        # Elevación Z (parábola de salto)
        self.altura_z = 150.0 * math.sin(progress * math.pi)

        # Rotación rápida 3D isométrica
        ease = 1.0 - math.pow(1.0 - progress, 3)
        self.rot_y = ease * 6.0 * math.pi + 0.3
        self.rot_x = ease * 4.0 * math.pi + 0.3

        # Cambiar valores mostrados mientras gira
        if self.frame_actual % 3 == 0:
            self.val_top = random.randint(1, self.caras)
            self.val_left = random.randint(1, self.caras)
            self.val_right = random.randint(1, self.caras)

        self.update()

        if self.frame_actual >= self.total_frames:
            self.timer.stop()
            self.animando = False
            self.altura_z = 0.0
            self.rot_y = 0.3
            self.rot_x = 0.3
            self.val_top = self.resultado_final
            self.val_left = (self.resultado_final % self.caras) + 1
            self.val_right = ((self.resultado_final + 2) % self.caras) + 1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0 + 20.0

        # ── 1. Sombra 3D Proyectada en el Suelo ──
        factor_sombra = max(0.2, 1.0 - (self.altura_z / 170.0))
        ancho_sombra = 95.0 * factor_sombra
        alto_sombra = 28.0 * factor_sombra
        opacidad_sombra = int(120 * factor_sombra)

        sombra_grad = QRadialGradient(QPointF(cx, cy + 30), ancho_sombra / 2.0)
        sombra_grad.setColorAt(0.0, QColor(0, 0, 0, opacidad_sombra))
        sombra_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(sombra_grad))
        painter.drawEllipse(QPointF(cx, cy + 30), ancho_sombra / 2.0, alto_sombra / 2.0)

        # ── 2. Dado Cerámico Blanco 3D (Cubo Redondeado) ──
        dice_cy = cy - self.altura_z
        sz = 46.0

        cos_y = math.cos(self.rot_y)
        sin_y = math.sin(self.rot_y)

        # Caras del Cubo Isométrico
        # Cara Superior (Top)
        top_p = [
            QPointF(cx, dice_cy - sz * 1.1),
            QPointF(cx + sz * 0.9, dice_cy - sz * 0.55),
            QPointF(cx, dice_cy - sz * 0.05),
            QPointF(cx - sz * 0.9, dice_cy - sz * 0.55)
        ]
        path_top = QPainterPath()
        path_top.moveTo(top_p[0])
        path_top.lineTo(top_p[1])
        path_top.lineTo(top_p[2])
        path_top.lineTo(top_p[3])
        path_top.closeSubpath()

        # Cara Izquierda (Left)
        left_p = [
            QPointF(cx - sz * 0.9, dice_cy - sz * 0.55),
            QPointF(cx, dice_cy - sz * 0.05),
            QPointF(cx, dice_cy + sz * 0.95),
            QPointF(cx - sz * 0.9, dice_cy + sz * 0.45)
        ]
        path_left = QPainterPath()
        path_left.moveTo(left_p[0])
        path_left.lineTo(left_p[1])
        path_left.lineTo(left_p[2])
        path_left.lineTo(left_p[3])
        path_left.closeSubpath()

        # Cara Derecha (Right)
        right_p = [
            QPointF(cx, dice_cy - sz * 0.05),
            QPointF(cx + sz * 0.9, dice_cy - sz * 0.55),
            QPointF(cx + sz * 0.9, dice_cy + sz * 0.45),
            QPointF(cx, dice_cy + sz * 0.95)
        ]
        path_right = QPainterPath()
        path_right.moveTo(right_p[0])
        path_right.lineTo(right_p[1])
        path_right.lineTo(right_p[2])
        path_right.lineTo(right_p[3])
        path_right.closeSubpath()

        # Estilo Cerámico Blanco / Marfil con sombras suaves
        grad_top = QLinearGradient(cx, dice_cy - sz * 1.1, cx, dice_cy)
        grad_top.setColorAt(0.0, QColor("#FFFFFF"))
        grad_top.setColorAt(1.0, QColor("#F1F5F9"))

        grad_left = QLinearGradient(cx - sz, dice_cy, cx, dice_cy + sz)
        grad_left.setColorAt(0.0, QColor("#E2E8F0"))
        grad_left.setColorAt(1.0, QColor("#CBD5E1"))

        grad_right = QLinearGradient(cx, dice_cy, cx + sz, dice_cy + sz)
        grad_right.setColorAt(0.0, QColor("#CBD5E1"))
        grad_right.setColorAt(1.0, QColor("#94A3B8"))

        border_pen = QPen(QColor("#94A3B8"), 1.8)

        # Dibujar caras en 3D
        painter.setPen(border_pen)

        painter.setBrush(QBrush(grad_top))
        painter.drawPath(path_top)

        painter.setBrush(QBrush(grad_left))
        painter.drawPath(path_left)

        painter.setBrush(QBrush(grad_right))
        painter.drawPath(path_right)

        # ── 3. Dibujar Puntos (Pips) o Números en las caras ──
        # Cara Superior (Resultado Principal)
        self._dibujar_contenido_cara(painter, cx, dice_cy - sz * 0.58, sz * 0.7, self.val_top, "#1E293B")
        # Cara Izquierda
        self._dibujar_contenido_cara(painter, cx - sz * 0.45, dice_cy + sz * 0.2, sz * 0.6, self.val_left, "#334155")
        # Cara Derecha
        self._dibujar_contenido_cara(painter, cx + sz * 0.45, dice_cy + sz * 0.2, sz * 0.6, self.val_right, "#475569")

    def _dibujar_contenido_cara(self, painter, x, y, size, valor, color_hex):
        """Si es D6 dibuja los puntos (pips) clásicos como la imagen; si es D4/D8/D10/D12/D20 dibuja número."""
        if self.caras == 6 and 1 <= valor <= 6:
            self._dibujar_pips_dado(painter, x, y, size, valor, color_hex)
        else:
            painter.setPen(QColor(color_hex))
            font_sz = int(size * 0.7)
            painter.setFont(QFont("Segoe UI", font_sz, QFont.Weight.Bold))
            rect = QRectF(x - size, y - size, size * 2, size * 2)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(valor))

    def _dibujar_pips_dado(self, painter, x, y, size, val, color_hex):
        """Dibuja los puntos incrustados del dado de 6 caras igual que la imagen de referencia."""
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        r = size * 0.14  # Radio de cada punto

        d = size * 0.35  # Desplazamiento desde el centro

        coords = []
        if val == 1:
            coords = [(0, 0)]
        elif val == 2:
            coords = [(-d, -d), (d, d)]
        elif val == 3:
            coords = [(-d, -d), (0, 0), (d, d)]
        elif val == 4:
            coords = [(-d, -d), (d, -d), (-d, d), (d, d)]
        elif val == 5:
            coords = [(-d, -d), (d, -d), (0, 0), (-d, d), (d, d)]
        elif val == 6:
            coords = [(-d, -d), (d, -d), (-d, 0), (d, 0), (-d, d), (d, d)]

        for dx, dy in coords:
            painter.drawEllipse(QPointF(x + dx, y + dy * 0.5), r, r * 0.75)


class LanzadorDadosView(QWidget):
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.caras_actuales = 6
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Botones de Selección de Tipo de Dado (Máximo D20 para D&D)
        lbl_tipo = QLabel("🎲 Selecciona el tipo de dado (Límite D20 D&D):")
        lbl_tipo.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(lbl_tipo)

        h_dados_btn = QHBoxLayout()
        h_dados_btn.setSpacing(8)

        self.tipo_btns = {}
        # Tipos estándar hasta D20 (D4, D6, D8, D10, D12, D20)
        for d in [4, 6, 8, 10, 12, 20]:
            btn = QPushButton(f"D{d}")
            btn.setFixedSize(52, 38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._get_btn_style(d == 6))
            btn.clicked.connect(lambda checked, n=d: self.set_tipo_dado(n))
            h_dados_btn.addWidget(btn)
            self.tipo_btns[d] = btn

        h_dados_btn.addStretch()

        lbl_cant = QLabel("Cantidad:")
        lbl_cant.setStyleSheet("color: white; font-size: 11px;")
        h_dados_btn.addWidget(lbl_cant)

        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, 6)
        self.spin_cant.setValue(1)
        self.spin_cant.setStyleSheet("QSpinBox { background: rgba(0,0,0,0.3); color: white; padding: 4px; border-radius: 4px; }")
        h_dados_btn.addWidget(self.spin_cant)

        layout.addLayout(h_dados_btn)

        # Widget 3D del Dado Cerámico
        self.dice_3d = Dice3DWidget(self.colores, self)
        layout.addWidget(self.dice_3d, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_resultado_dado = QLabel("Resultado: D6")
        self.lbl_resultado_dado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado_dado.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_resultado_dado.setStyleSheet("color: #FBBF24;")
        layout.addWidget(self.lbl_resultado_dado)

        self.lbl_detalle_dado = QLabel("Presiona para lanzar el dado")
        self.lbl_detalle_dado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detalle_dado.setStyleSheet("color: #AAB0B8; font-size: 12px;")
        layout.addWidget(self.lbl_detalle_dado)

        btn_lanzar = QPushButton("🎲 LANZAR DADO")
        btn_lanzar.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn_lanzar.setFixedHeight(44)
        btn_lanzar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_lanzar.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; color: white; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_lanzar.clicked.connect(self.lanzar_dados)
        layout.addWidget(btn_lanzar)

    def _get_btn_style(self, selected=False):
        if selected:
            return f"background: {self.colores['acento']}; color: white; font-weight: bold; border-radius: 6px; border: none;"
        return "background: rgba(255,255,255,0.05); color: #AAA; font-weight: bold; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);"

    def set_tipo_dado(self, caras):
        # Límite máximo 20 caras (D20)
        self.caras_actuales = min(20, caras)
        for d, btn in self.tipo_btns.items():
            btn.setStyleSheet(self._get_btn_style(d == self.caras_actuales))
        self.lbl_resultado_dado.setText(f"Resultado: D{self.caras_actuales}")

    def lanzar_dados(self):
        if self.dice_3d.animando:
            return
        cant = self.spin_cant.value()
        res = [random.randint(1, self.caras_actuales) for _ in range(cant)]
        self.dice_3d.iniciar_lanzamiento(self.caras_actuales, res[0])

        def _on_finish():
            total = sum(res)
            if cant > 1:
                self.lbl_resultado_dado.setText(" ".join(str(v) for v in res))
                self.lbl_detalle_dado.setText(f"Suma Total: {total} (Valores: {', '.join(str(v) for v in res)})")
            else:
                self.lbl_resultado_dado.setText(f"¡Salió {res[0]}!")
                self.lbl_detalle_dado.setText(f"Resultado D{self.caras_actuales}: {res[0]}")

        QTimer.singleShot(1100, _on_finish)


# ─────────────────────────────────────────────────────────────────────────
# 4. SORTEO DE NÚMEROS ALEATORIOS
# ─────────────────────────────────────────────────────────────────────────
class SorteoNumerosView(QWidget):
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Panel de Configuración
        panel_cfg = QFrame()
        panel_cfg.setFixedWidth(260)
        panel_cfg.setStyleSheet("background: rgba(30, 30, 46, 0.65); border-radius: 12px; padding: 15px;")
        lay_cfg = QVBoxLayout(panel_cfg)

        lbl_tit = QLabel("🔢 Parámetros de Sorteo:")
        lbl_tit.setStyleSheet("color: white; font-weight: bold;")
        lay_cfg.addWidget(lbl_tit)

        lay_cfg.addWidget(QLabel("Número Mínimo:", styleSheet="color: white; font-size: 11px;"))
        self.spin_min = QSpinBox()
        self.spin_min.setRange(0, 999999)
        self.spin_min.setValue(1)
        self.spin_min.setStyleSheet("QSpinBox { background: rgba(0,0,0,0.3); color: white; padding: 4px; }")
        lay_cfg.addWidget(self.spin_min)

        lay_cfg.addWidget(QLabel("Número Máximo:", styleSheet="color: white; font-size: 11px;"))
        self.spin_max = QSpinBox()
        self.spin_max.setRange(0, 999999)
        self.spin_max.setValue(100)
        self.spin_max.setStyleSheet("QSpinBox { background: rgba(0,0,0,0.3); color: white; padding: 4px; }")
        lay_cfg.addWidget(self.spin_max)

        lay_cfg.addWidget(QLabel("Cantidad a Sortear:", styleSheet="color: white; font-size: 11px;"))
        self.spin_cant = QSpinBox()
        self.spin_cant.setRange(1, 50)
        self.spin_cant.setValue(1)
        self.spin_cant.setStyleSheet("QSpinBox { background: rgba(0,0,0,0.3); color: white; padding: 4px; }")
        lay_cfg.addWidget(self.spin_cant)

        self.chk_no_repeat = QCheckBox("Sin números repetidos")
        self.chk_no_repeat.setChecked(True)
        self.chk_no_repeat.setStyleSheet("color: white; font-size: 11px; margin-top: 5px;")
        lay_cfg.addWidget(self.chk_no_repeat)

        lay_cfg.addStretch()

        btn_sortear = QPushButton("🎰 SORTEAR NÚMEROS")
        btn_sortear.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn_sortear.setFixedHeight(42)
        btn_sortear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sortear.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 8px; border: none;")
        btn_sortear.clicked.connect(self.realizar_sorteo)
        lay_cfg.addWidget(btn_sortear)

        layout.addWidget(panel_cfg)

        # Display Resultados
        panel_res = QFrame()
        panel_res.setStyleSheet("background: rgba(30, 30, 46, 0.65); border-radius: 12px; padding: 20px;")
        lay_res = QVBoxLayout(panel_res)
        lay_res.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_ganadores = QLabel("🎯")
        self.lbl_ganadores.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ganadores.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        self.lbl_ganadores.setStyleSheet("color: #34D399;")
        self.lbl_ganadores.setWordWrap(True)
        lay_res.addWidget(self.lbl_ganadores)

        layout.addWidget(panel_res, 1)

    def realizar_sorteo(self):
        n_min = self.spin_min.value()
        n_max = self.spin_max.value()
        cant = self.spin_cant.value()
        no_rep = self.chk_no_repeat.isChecked()

        if n_min >= n_max:
            QMessageBox.warning(self, "Sorteo", "El mínimo debe ser menor que el máximo.")
            return

        if no_rep and (n_max - n_min + 1) < cant:
            QMessageBox.warning(self, "Sorteo", "El rango es demasiado pequeño para sortear esa cantidad sin repetir.")
            return

        if no_rep:
            res = random.sample(range(n_min, n_max + 1), cant)
        else:
            res = [random.randint(n_min, n_max) for _ in range(cant)]

        res.sort()
        self.lbl_ganadores.setText("  •  ".join(str(n) for n in res))


# ─────────────────────────────────────────────────────────────────────────
# 5. LANZAMIENTO DE MONEDA (CARA / CRUZ)
# ─────────────────────────────────────────────────────────────────────────
class Coin3DWidget(QWidget):
    """Widget de animación 3D de Lanzamiento de Moneda mediante perspectiva QPainter."""
    def __init__(self, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.setMinimumSize(280, 240)

        self.angulo_rad = 0.0    # Ángulo de giro en el eje Y
        self.altura_z = 0.0      # Altura en el aire (parábola Z)
        self.es_cara = True      # Cara visible actual (True: Cara, False: Cruz)
        self.animando = False

        self.resultado_final = "CARA"  # "CARA" | "CRUZ"

        # Timer de 60 FPS
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animar_step)
        self.frame_actual = 0
        self.total_frames = 60

    def iniciar_lanzamiento(self, resultado):
        self.resultado_final = resultado
        self.animando = True
        self.frame_actual = 0
        self.total_frames = 70
        self.timer.start(16)  # ~60 FPS

    def _animar_step(self):
        self.frame_actual += 1
        progress = self.frame_actual / self.total_frames

        # Parábola de elevación Z (sube y cae)
        self.altura_z = 160.0 * math.sin(progress * math.pi)

        # Giro en eje Y (varias vueltas completas)
        vueltas = 6
        if self.resultado_final == "CARA":
            target_rot = vueltas * 2 * math.pi
        else:
            target_rot = (vueltas + 0.5) * 2 * math.pi

        # Easing cubic out para deceleración
        ease = 1.0 - math.pow(1.0 - progress, 3)
        self.angulo_rad = ease * target_rot

        # Determinar cara visible
        cos_val = math.cos(self.angulo_rad)
        self.es_cara = cos_val >= 0

        self.update()

        if self.frame_actual >= self.total_frames:
            self.timer.stop()
            self.animando = False
            self.altura_z = 0.0
            self.angulo_rad = 0.0 if self.resultado_final == "CARA" else math.pi
            self.es_cara = self.resultado_final == "CARA"
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0 + 30.0  # centro de suelo

        # ── 1. Sombra 3D Proyectada en el Suelo ──
        factor_sombra = max(0.2, 1.0 - (self.altura_z / 180.0))
        ancho_sombra = 90.0 * factor_sombra
        alto_sombra = 20.0 * factor_sombra
        opacidad_sombra = int(120 * factor_sombra)

        sombra_grad = QRadialGradient(QPointF(cx, cy + 20), ancho_sombra / 2.0)
        sombra_grad.setColorAt(0.0, QColor(0, 0, 0, opacidad_sombra))
        sombra_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(sombra_grad))
        painter.drawEllipse(QPointF(cx, cy + 20), ancho_sombra / 2.0, alto_sombra / 2.0)

        # ── 2. Moneda 3D ──
        coin_cy = cy - self.altura_z
        radius = 45.0
        cos_val = abs(math.cos(self.angulo_rad))
        scale_y = max(0.06, cos_val)  # Perspectiva 3D

        # Grosor metálico 3D (cuando está de canto)
        grosor_3d = 8.0 * (1.0 - cos_val)
        if grosor_3d > 1.0:
            painter.setBrush(QBrush(QColor("#B45309")))
            painter.drawEllipse(QPointF(cx, coin_cy + grosor_3d), radius, radius * scale_y)

        # Cuerpo de la Moneda
        if self.es_cara:
            grad = QLinearGradient(cx - radius, coin_cy - radius, cx + radius, coin_cy + radius)
            grad.setColorAt(0.0, QColor("#FBBF24"))  # Dorado claro
            grad.setColorAt(0.7, QColor("#F59E0B"))  # Dorado intenso
            grad.setColorAt(1.0, QColor("#D97706"))  # Borde oscuro
            border_color = QColor("#FEF3C7")
            text_val = "👑\nCARA"
        else:
            grad = QLinearGradient(cx - radius, coin_cy - radius, cx + radius, coin_cy + radius)
            grad.setColorAt(0.0, QColor("#9CA3AF"))  # Plateado claro
            grad.setColorAt(0.7, QColor("#6B7280"))  # Plateado medio
            grad.setColorAt(1.0, QColor("#374151"))  # Sombra
            border_color = QColor("#F3F4F6")
            text_val = "🦅\nCRUZ"

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(border_color, 2))
        painter.drawEllipse(QPointF(cx, coin_cy), radius, radius * scale_y)

        # Círculo interior grabado
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1.5, Qt.PenStyle.DashLine))
        painter.drawEllipse(QPointF(cx, coin_cy), radius * 0.82, radius * 0.82 * scale_y)

        # Texto/Icono Grabado 3D
        if scale_y > 0.3:
            painter.setPen(QColor("#FFFFFF" if self.es_cara else "#F9FAFB"))
            font_sz = int(14 * scale_y)
            if font_sz >= 6:
                painter.setFont(QFont("Segoe UI", font_sz, QFont.Weight.Bold))
                rect_text = QRectF(cx - radius, coin_cy - (radius * scale_y), radius * 2, radius * 2 * scale_y)
                painter.drawText(rect_text, Qt.AlignmentFlag.AlignCenter, text_val)


class LanzamientoMonedaView(QWidget):
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.caras_cnt = 0
        self.cruz_cnt = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Widget 3D de Moneda
        self.coin_3d = Coin3DWidget(self.colores, self)
        layout.addWidget(self.coin_3d, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_resultado_coin = QLabel("Presiona para lanzar la moneda")
        self.lbl_resultado_coin.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.lbl_resultado_coin.setStyleSheet("color: white; margin-top: 10px; margin-bottom: 10px;")
        self.lbl_resultado_coin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_resultado_coin)

        btn_flip = QPushButton("🪙 LANZAR MONEDA")
        btn_flip.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn_flip.setFixedSize(240, 46)
        btn_flip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_flip.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']}; color: white; border-radius: 10px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores['acento_hover']}; }}
        """)
        btn_flip.clicked.connect(self.lanzar_moneda)
        layout.addWidget(btn_flip, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_stats = QLabel("👑 Cara: 0  |  🦅 Cruz: 0")
        self.lbl_stats.setStyleSheet("color: #AAB0B8; font-size: 13px; font-weight: bold; margin-top: 12px;")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_stats)

    def lanzar_moneda(self):
        if self.coin_3d.animando:
            return
        resultado = random.choice(["CARA", "CRUZ"])
        self.coin_3d.iniciar_lanzamiento(resultado)

        # Esperar a que la animación termine para actualizar texto final
        def _on_finish():
            if resultado == "CARA":
                self.caras_cnt += 1
            else:
                self.cruz_cnt += 1
            self.lbl_resultado_coin.setText(f"¡Salió {'CARA 👑' if resultado == 'CARA' else 'CRUZ 🦅'}!")
            self.lbl_stats.setText(f"👑 Cara: {self.caras_cnt}  |  🦅 Cruz: {self.cruz_cnt}")

        QTimer.singleShot(1150, _on_finish)


