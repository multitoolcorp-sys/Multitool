import json
import random
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QMessageBox, QLineEdit,
    QCheckBox, QScrollArea, QDialog, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap

from ..utils.game_socket_manager import GameSocketManager
from ..utils.score_manager import ScoreManager

PERSONAJES_DEFAULT = [
    {"nombre": "Alex", "icon": "🧔"},
    {"nombre": "Beatriz", "icon": "👩‍🦰"},
    {"nombre": "Carlos", "icon": "👨‍🦱"},
    {"nombre": "Daniela", "icon": "👱‍♀️"},
    {"nombre": "Eduardo", "icon": "👴"},
    {"nombre": "Fabiola", "icon": "👩‍🦲"},
    {"nombre": "Gabriel", "icon": "👨‍🦰"},
    {"nombre": "Helena", "icon": "👧"},
    {"nombre": "Ignacio", "icon": "🧔‍♂️"},
    {"nombre": "Julia", "icon": "👩‍🦱"},
    {"nombre": "Kevin", "icon": "👦"},
    {"nombre": "Laura", "icon": "👩"}
]


class ConfigBarajaDialog(QDialog):
    """Diálogo para personalizar baraja (imágenes/emojis), exportar, importar y reiniciar a predeterminado"""
    def __init__(self, parent, personajes, colores):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configuración & Exportación de Baraja - Adivina Quién")
        self.resize(600, 480)
        self.personajes = [dict(p) for p in personajes]
        self.colores = colores
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        bg_main = colores.get('bg_principal', '#121218')
        bg_sec = colores.get('bg_secundario', '#1E1E2E')
        acento = colores.get('acento', '#6366F1')
        exito = colores.get('exito', '#34D399')
        error = colores.get('error', '#F87171')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        lbl = QLabel("⚙️ PERSONALIZAR Y BARAJA DE PERSONAJES (IMÁGENES Y EMOJIS)")
        lbl.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {acento};")
        layout.addWidget(lbl)

        # Botones Exportar, Importar y Reset
        btn_bar = QHBoxLayout()
        btn_exp = QPushButton("📤 Exportar Baraja (.json)")
        btn_exp.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_exp.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        btn_exp.clicked.connect(self.exportar_json)
        btn_bar.addWidget(btn_exp)

        btn_imp = QPushButton("📥 Importar Baraja (.json)")
        btn_imp.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_imp.setStyleSheet(f"background: {exito}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        btn_imp.clicked.connect(self.importar_json)
        btn_bar.addWidget(btn_imp)

        btn_reset = QPushButton("🔄 Reset Predeterminado")
        btn_reset.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_reset.setStyleSheet(f"background: {error}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        btn_reset.clicked.connect(self.reset_predeterminado)
        btn_bar.addWidget(btn_reset)
        btn_bar.addStretch()

        layout.addLayout(btn_bar)

        # Scroll de lista de personajes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {bg_sec}; border-radius: 8px; border: none;")

        w_list = QWidget()
        self.v_list = QVBoxLayout(w_list)
        self.inputs = []

        self._build_inputs_list()

        scroll.setWidget(w_list)
        layout.addWidget(scroll, 1)

        btn_save = QPushButton("💾 Guardar Cambios")
        btn_save.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        btn_save.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 10px; border: none;")
        btn_save.clicked.connect(self.guardar_cambios)
        layout.addWidget(btn_save)

    def _build_inputs_list(self):
        while self.v_list.count():
            item = self.v_list.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        self.inputs.clear()
        for idx, p in enumerate(self.personajes):
            row_w = QFrame()
            row_w.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 6px; padding: 4px;")
            r_lay = QHBoxLayout(row_w)
            
            txt_icon = QLineEdit(p.get("icon", "👤"))
            txt_icon.setFixedWidth(60)
            txt_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            txt_icon.setFont(QFont("Segoe UI Emoji", 12))
            r_lay.addWidget(txt_icon)

            txt_nom = QLineEdit(p.get("nombre", "Personaje"))
            txt_nom.setFont(QFont(self.font_family, 9))
            r_lay.addWidget(txt_nom)

            btn_img = QPushButton("🖼️ Imagen")
            btn_img.setFont(QFont(self.font_family, 8))
            btn_img.setStyleSheet("background: rgba(255,255,255,0.1); border-radius: 4px; padding: 4px 8px;")
            btn_img.clicked.connect(lambda ch, i=idx: self._examinar_imagen(i))
            r_lay.addWidget(btn_img)

            self.inputs.append((txt_icon, txt_nom))
            self.v_list.addWidget(row_w)

    def _examinar_imagen(self, index):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen de Personaje", "", "Imágenes (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.personajes[index]["icon"] = f"img:{path}"
            self.inputs[index][0].setText("🖼️ Imagen")

    def reset_predeterminado(self):
        self.personajes = [dict(p) for p in PERSONAJES_DEFAULT]
        self._build_inputs_list()
        QMessageBox.information(self, "Reset", "Se restauró la baraja predeterminada.")

    def guardar_cambios(self):
        new_list = []
        for idx, (txt_icon, txt_nom) in enumerate(self.inputs):
            ico = txt_icon.text().strip() or "👤"
            if self.personajes[idx].get("icon", "").startswith("img:"):
                ico = self.personajes[idx]["icon"]
            nom = txt_nom.text().strip() or "Personaje"
            new_list.append({"nombre": nom, "icon": ico})
        self.personajes = new_list
        self.accept()

    def exportar_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Baraja Personajes", "baraja_adivina_quien.json", "JSON (*.json)")
        if path:
            self.guardar_cambios()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.personajes, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Exportación Éxito", f"Baraja exportada correctamente a:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Exportar", f"No se pudo guardar:\n{e}")

    def importar_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Baraja Personajes", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.personajes = data
                    self._build_inputs_list()
                    QMessageBox.information(self, "Importación Éxito", f"Se importaron {len(data)} personajes correctamente.")
                    self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error Importar", f"Archivo no válido:\n{e}")


class AdivinaQuienGUI(QWidget):
    """Juego Adivina Quién con Elección Manual de Secreto, Anotador de Preguntas y Baraja Personalizable"""
    def __init__(self, parent, colores, ruta_usuario):
        super().__init__(parent)
        self.colores = colores
        self.ruta_usuario = ruta_usuario
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.socket_mgr = GameSocketManager(usuario="Jugador Adivina")
        self.personajes = list(PERSONAJES_DEFAULT)
        self.descartados = set()

        self.mi_secreto = None
        self.fase_seleccion_secreto = True
        self.cards_buttons = {}

        self.inicializar_ui()
        self.nuevo_juego()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')
        error = self.colores.get('error', '#F87171')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Barra Superior Unificada con Estado y Botones de Control
        top_bar = QFrame()
        top_bar.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 8px 15px;")
        t_lay = QHBoxLayout(top_bar)
        
        self.lbl_mi_secreto = QLabel("👉 Haz clic en una carta para elegir tu Personaje Secreto.")
        self.lbl_mi_secreto.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        self.lbl_mi_secreto.setStyleSheet(f"color: {acento};")
        t_lay.addWidget(self.lbl_mi_secreto)

        t_lay.addStretch()

        btn_cfg = QPushButton("⚙️ Configurar Baraja")
        btn_cfg.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cfg.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        btn_cfg.clicked.connect(self._abrir_config_baraja)
        t_lay.addWidget(btn_cfg)

        btn_new = QPushButton("🎲 Barajar & Nuevo Juego")
        btn_new.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setStyleSheet(f"background: {exito}; color: white; border-radius: 6px; padding: 6px 12px; border: none;")
        btn_new.clicked.connect(self.nuevo_juego)
        t_lay.addWidget(btn_new)

        layout.addWidget(top_bar)

        # Panel Central: Anotador vs Cuadrícula
        main_row = QHBoxLayout()
        main_row.setSpacing(15)

        # Anotador de Preguntas
        q_frame = QFrame()
        q_frame.setFixedWidth(280)
        q_frame.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px;")
        q_lay = QVBoxLayout(q_frame)
        q_lay.setSpacing(8)

        q_lay.addWidget(QLabel("📝 ANOTADOR DE PREGUNTAS", font=QFont(self.font_family, 9, QFont.Weight.Bold)))

        self.txt_pregunta = QLineEdit()
        self.txt_pregunta.setPlaceholderText("Escribe tu pregunta aquí...")
        self.txt_pregunta.setFont(QFont(self.font_family, 9))
        self.txt_pregunta.setStyleSheet(f"background: {bg_terc}; color: white; border-radius: 6px; padding: 6px;")
        self.txt_pregunta.returnPressed.connect(self._agregar_pregunta_anotador)
        q_lay.addWidget(self.txt_pregunta)

        btn_add_q = QPushButton("➕ Agregar Pregunta")
        btn_add_q.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_add_q.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; padding: 6px; border: none;")
        btn_add_q.clicked.connect(self._agregar_pregunta_anotador)
        q_lay.addWidget(btn_add_q)

        # Lista de preguntas anotadas
        q_scroll = QScrollArea()
        q_scroll.setWidgetResizable(True)
        q_scroll.setStyleSheet("background: transparent; border: none;")

        self.w_q_list = QWidget()
        self.v_q_list = QVBoxLayout(self.w_q_list)
        self.v_q_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.v_q_list.setSpacing(6)
        q_scroll.setWidget(self.w_q_list)

        q_lay.addWidget(q_scroll, 1)
        main_row.addWidget(q_frame)

        # Grid de Sospechosos
        grid_frame = QFrame()
        grid_frame.setStyleSheet(f"background: {bg_sec}; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px;")
        g_lay = QVBoxLayout(grid_frame)

        grid_w = QWidget()
        self.cards_grid = QGridLayout(grid_w)
        self.cards_grid.setSpacing(10)
        g_lay.addWidget(grid_w, 1)

        main_row.addWidget(grid_frame, 1)
        layout.addLayout(main_row, 1)

    def nuevo_juego(self):
        self.descartados.clear()
        self.mi_secreto = None
        self.fase_seleccion_secreto = True

        # Barajar aleatoriamente el orden de las cartas
        random.shuffle(self.personajes)

        self.lbl_mi_secreto.setText("👉 Haz clic en una carta de la cuadrícula para elegir tu Personaje Secreto.")

        # Limpiar anotador
        while self.v_q_list.count():
            item = self.v_q_list.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        self._render_cards_grid()

    def _abrir_config_baraja(self):
        dlg = ConfigBarajaDialog(self, self.personajes, self.colores)
        if dlg.exec():
            self.personajes = dlg.personajes
            self.nuevo_juego()

    def _agregar_pregunta_anotador(self):
        texto = self.txt_pregunta.text().strip()
        if not texto: return
        self.txt_pregunta.clear()

        item_w = QFrame()
        item_w.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 6px; padding: 6px;")
        i_lay = QVBoxLayout(item_w)
        i_lay.setSpacing(4)

        top_r = QHBoxLayout()
        lbl_p = QLabel(f"❓ {texto}", font=QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_p.setWordWrap(True)
        top_r.addWidget(lbl_p, 1)

        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(24, 24)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        btn_del.clicked.connect(lambda: item_w.deleteLater())
        top_r.addWidget(btn_del)

        i_lay.addLayout(top_r)

        chk_lay = QHBoxLayout()
        chk_si = QCheckBox("SÍ")
        chk_no = QCheckBox("NO")
        chk_si.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        chk_no.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        chk_si.setStyleSheet("color: #34D399;")
        chk_no.setStyleSheet("color: #F87171;")
        
        chk_si.stateChanged.connect(lambda state: chk_no.setChecked(False) if state == 2 else None)
        chk_no.stateChanged.connect(lambda state: chk_si.setChecked(False) if state == 2 else None)

        chk_lay.addWidget(chk_si)
        chk_lay.addWidget(chk_no)
        chk_lay.addStretch()

        i_lay.addLayout(chk_lay)
        self.v_q_list.insertWidget(0, item_w)

    def _on_card_clicked(self, personaje):
        nombre = personaje['nombre']
        if self.fase_seleccion_secreto:
            self.mi_secreto = personaje
            self.fase_seleccion_secreto = False
            self.lbl_mi_secreto.setText(f"🔒 Tu personaje secreto es: {nombre}. (Voltea sospechosos haciendo clic).")
            self._render_cards_grid()
        else:
            if nombre in self.descartados:
                self.descartados.remove(nombre)
            else:
                self.descartados.add(nombre)
            self._render_cards_grid()

            # Si queda exactamente 1 personaje sin descartar, ¡el jugador ha deducido el misterio!
            if len(self.descartados) == len(self.personajes) - 1:
                ganador = [p['nombre'] for p in self.personajes if p['nombre'] not in self.descartados]
                if ganador:
                    nombre_ganador = ganador[0]
                    ScoreManager(self.ruta_usuario).sumar_puntos("adivina_quien", 15)
                    QMessageBox.information(
                        self, "🎉 ¡Sospechoso Identificado!",
                        f"¡Felicidades! Has deducido que el personaje secreto es: <b>{nombre_ganador}</b>.\n\n"
                        f"Ganaste +15 puntos para tu cuenta."
                    )

    def _render_cards_grid(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        self.cards_buttons.clear()

        for idx, p in enumerate(self.personajes):
            name = p['nombre']
            ico = p.get('icon', '👤')

            btn = QPushButton()
            btn.setFixedSize(105, 95)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if ico.startswith("img:") and Path(ico[4:]).exists():
                pix = QPixmap(ico[4:])
                btn.setIcon(QIcon(pix))
                btn.setIconSize(btn.size() * 0.6)
                btn.setText(name)
            else:
                btn.setText(f"{ico}\n{name}")
                btn.setFont(QFont("Segoe UI Emoji", 13, QFont.Weight.Bold))
            
            # El estilo volcado / descartado sobrescribe cualquier estado
            if name in self.descartados:
                btn.setStyleSheet("background: rgba(15, 15, 20, 0.7); color: #444; border: 1px solid rgba(255,255,255,0.02); border-radius: 8px;")
            else:
                btn.setStyleSheet("""
                    QPushButton { background: rgba(30, 30, 46, 0.85); border: 1.5px solid rgba(255,255,255,0.12); border-radius: 8px; color: white; }
                    QPushButton:hover { border: 2px solid #6366F1; background: rgba(99, 102, 241, 0.25); }
                """)

            btn.clicked.connect(lambda ch, p_item=p: self._on_card_clicked(p_item))

            r, c = idx // 4, idx % 4
            self.cards_grid.addWidget(btn, r, c)
            self.cards_buttons[name] = btn
