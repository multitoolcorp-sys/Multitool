import os
import sys
import subprocess
import time
import datetime
import threading
import platform
import string
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QFrame, QScrollArea, QMessageBox, QFileDialog, QSplitter,
    QProgressBar, QStackedLayout, QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QPixmap, QColor, QImage, QPainter, QPainterPath, QPen, QBrush, QIcon, QLinearGradient


from .adb_engine import ADBEngine, CREATE_NO_WINDOW


class PhoneCanvasWidget(QFrame):
    """Lienzo interactivo de renderizado del teléfono celular"""
    mouse_clicked = pyqtSignal(int, int)
    mouse_swiped = pyqtSignal(int, int, int, int)
    
    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.orientacion = "vertical"  # "vertical" | "horizontal"
        self.color_carcasa = "Negro Mate"
        self.drag_start = None
        self.pixmap_pantalla = None
        self.modo_demo = True
        
        # Estado del Teléfono Virtual
        self.app_activa = "Home"
        self.hora_actual = datetime.datetime.now().strftime("%H:%M")
        self.bateria_nivel = 95
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_pixmap(self, pixmap):
        self.pixmap_pantalla = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w, h = self.width(), self.height()
        
        # Paletas de Carcasa
        paleta_carcasa = {
            "Negro Mate": ("#1E1E28", "#0F0F14", "#38BDF8"),
            "Plata Titanio": ("#E2E8F0", "#94A3B8", "#6366F1"),
            "Violeta Neón": ("#3B0764", "#2E1065", "#A855F7"),
            "Azul Medianoche": ("#0F172A", "#0284C7", "#38BDF8")
        }
        c_outer, c_inner, c_accent = paleta_carcasa.get(self.color_carcasa, paleta_carcasa["Negro Mate"])

        # Dimensiones del teléfono
        margin_x = 20 if self.orientacion == "vertical" else 40
        margin_y = 20 if self.orientacion == "vertical" else 20
        phone_w = w - (margin_x * 2)
        phone_h = h - (margin_y * 2)

        # Dibujar Carcasa Exterior
        rect_phone = QPainterPath()
        rect_phone.addRoundedRect(margin_x, margin_y, phone_w, phone_h, 28, 28)
        
        painter.fillPath(rect_phone, QColor(c_outer))
        painter.setPen(QPen(QColor(c_accent), 2))
        painter.drawPath(rect_phone)

        # Pantalla Interior
        screen_margin = 12
        sx = margin_x + screen_margin
        sy = margin_y + screen_margin + 16
        sw = phone_w - (screen_margin * 2)
        sh = phone_h - (screen_margin * 2) - 32

        self.screen_rect = (sx, sy, sw, sh)

        path_screen = QPainterPath()
        path_screen.addRoundedRect(sx, sy, sw, sh, 14, 14)
        
        painter.save()
        painter.setClipPath(path_screen)

        if self.pixmap_pantalla and not self.pixmap_pantalla.isNull():
            painter.drawPixmap(sx, sy, sw, sh, self.pixmap_pantalla)
        else:
            # Dibujar Interfaz Virtual de Android
            self._dibujar_pantalla_virtual(painter, sx, sy, sw, sh)

        painter.restore()

        # Dibujar Notch / Cámara frontal
        notch_w = 60 if self.orientacion == "vertical" else 12
        notch_h = 10 if self.orientacion == "vertical" else 40
        nx = margin_x + (phone_w - notch_w) // 2
        ny = margin_y + 8
        painter.setBrush(QBrush(QColor("#000000")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(nx, ny, notch_w, notch_h, 5, 5)

        # Dibujar Altavoz / Micrófono
        painter.setBrush(QBrush(QColor(c_accent)))
        painter.drawEllipse(nx + 10, ny + 3, 4, 4)

    def _dibujar_pantalla_virtual(self, painter, sx, sy, sw, sh):
        # Fondo de Pantalla Gradiente Neón
        grad = QLinearGradient(sx, sy, sx + sw, sy + sh)
        grad.setColorAt(0.0, QColor("#0F172A"))
        grad.setColorAt(0.5, QColor("#1E1B4B"))
        grad.setColorAt(1.0, QColor("#311042"))
        painter.fillRect(sx, sy, sw, sh, grad)

        # 1. Barra de Estado Superior
        painter.setPen(QPen(QColor("#FFFFFF")))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(sx + 12, sy + 18, self.hora_actual)

        bateria_txt = f"📶 5G  🔋 {self.bateria_nivel}%"
        painter.drawText(sx + sw - 95, sy + 18, bateria_txt)

        # 2. Contenido según App activa
        if self.app_activa == "Home":
            # Widget Reloj Grande
            painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
            painter.drawText(sx, sy + 70, sw, 40, Qt.AlignmentFlag.AlignCenter, self.hora_actual)
            
            painter.setFont(QFont("Segoe UI", 10))
            painter.setPen(QPen(QColor("#AAB0B8")))
            painter.drawText(sx, sy + 105, sw, 20, Qt.AlignmentFlag.AlignCenter, "Martes, 18 de Agosto")

            # Parrilla de Apps
            apps = [
                ("📷", "Cámara", "#EF4444"),
                ("🌐", "Navegador", "#3B82F6"),
                ("⚙️", "Ajustes", "#64748B"),
                ("🖼️", "Fotos", "#10B981"),
                ("💬", "Mensajes", "#8B5CF6"),
                ("🎵", "Música", "#EC4899"),
                ("🎮", "Juegos", "#F59E0B"),
                ("📁", "Archivos", "#6366F1")
            ]

            cols = 4
            icon_size = 42
            start_x = sx + (sw - (cols * 55)) // 2 + 5
            start_y = sy + 140

            for i, (icon, name, color) in enumerate(apps):
                r = i // cols
                c = i % cols
                ix = start_x + (c * 55)
                iy = start_y + (r * 65)

                # Caja del Icono
                path_icon = QPainterPath()
                path_icon.addRoundedRect(ix, iy, icon_size, icon_size, 10, 10)
                painter.fillPath(path_icon, QColor(color))
                
                painter.setPen(QPen(QColor("#FFFFFF")))
                painter.setFont(QFont("Segoe UI Emoji", 16))
                painter.drawText(ix, iy, icon_size, icon_size, Qt.AlignmentFlag.AlignCenter, icon)

                painter.setFont(QFont("Segoe UI", 8))
                painter.setPen(QPen(QColor("#CBD5E1")))
                painter.drawText(ix - 5, iy + icon_size + 2, icon_size + 10, 14, Qt.AlignmentFlag.AlignCenter, name)

            # Dock Inferior (Apps Favoritas)
            painter.setBrush(QBrush(QColor("rgba(255,255,255,0.1)")))
            painter.drawRoundedRect(sx + 15, sy + sh - 65, sw - 30, 50, 15, 15)

            dock_apps = ["📞", "💬", "🌐", "⚙️"]
            d_start_x = sx + (sw - (len(dock_apps) * 45)) // 2 + 5
            for i, icon in enumerate(dock_apps):
                dx = d_start_x + (i * 45)
                dy = sy + sh - 57
                painter.setFont(QFont("Segoe UI Emoji", 18))
                painter.drawText(dx, dy, 36, 36, Qt.AlignmentFlag.AlignCenter, icon)

        else:
            # Vista de App Abierta
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.drawText(sx, sy + 60, sw, 30, Qt.AlignmentFlag.AlignCenter, f"📱 {self.app_activa}")

            painter.setFont(QFont("Segoe UI", 10))
            painter.setPen(QPen(QColor("#94A3B8")))
            painter.drawText(sx + 20, sy + 110, sw - 40, 100, Qt.AlignmentFlag.AlignCenter, f"Ejecutando {self.app_activa} en pantalla completa.\nUsa la barra inferior o el ratón para navegar.")

        # 3. Barra de Navegación Inferior de Android (Gestos)
        bar_w = 100
        bar_h = 4
        bx = sx + (sw - bar_w) // 2
        by = sy + sh - 8
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawRoundedRect(bx, by, bar_w, bar_h, 2, 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = event.position().toPoint()
            # Mapear clic a coordenadas de pantalla del celular
            sx, sy, sw, sh = getattr(self, "screen_rect", (0, 0, 1, 1))
            pos = event.position().toPoint()
            if sx <= pos.x() <= sx + sw and sy <= pos.y() <= sy + sh:
                rel_x = (pos.x() - sx) / sw
                rel_y = (pos.y() - sy) / sh
                self.mouse_clicked.emit(int(rel_x * 1080), int(rel_y * 2340))

                # Interacción con la App Virtual en Modo Demo
                if self.modo_demo:
                    if rel_y > 0.88:
                        self.app_activa = "Home"
                    elif self.app_activa == "Home" and 0.25 <= rel_y <= 0.65:
                        self.app_activa = "Aplicación Android"
                    self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drag_start:
            drag_end = event.position().toPoint()
            dx = drag_end.x() - self.drag_start.x()
            dy = drag_end.y() - self.drag_start.y()

            if abs(dx) > 20 or abs(dy) > 20:
                sx, sy, sw, sh = getattr(self, "screen_rect", (0, 0, 1, 1))
                x1 = int(((self.drag_start.x() - sx) / sw) * 1080)
                y1 = int(((self.drag_start.y() - sy) / sh) * 2340)
                x2 = int(((drag_end.x() - sx) / sw) * 1080)
                y2 = int(((drag_end.y() - sy) / sh) * 2340)
                self.mouse_swiped.emit(x1, y1, x2, y2)
            self.drag_start = None


class EspejoCelularGUI(QWidget):
    """Submódulo Core Espejo Celular: Duplicado y Control de Celular Android"""
    def __init__(self, parent=None, colores=None, ruta_usuario=None):
        super().__init__(parent)
        self.colores = colores or {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        self.ruta_usuario = Path(ruta_usuario or ".")
        
        self.adb_bin = ADBEngine.buscar_adb() or "adb"
        self.scrcpy_bin = ADBEngine.buscar_scrcpy()
        self.dispositivo_actual = None

        self._build_ui()

        # Timer para reloj y actualización de estado
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._actualizar_estado)
        self.timer.start(2000)

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ── PANEL IZQUIERDO: Controles y Herramientas (Con ScrollArea) ────────
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        scroll_left.setFixedWidth(350)
        scroll_left.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: {self.colores['bg_principal']}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colores['bg_terciario']}; border-radius: 4px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.colores['acento']};
            }}
        """)

        left_panel = QFrame()
        left_panel.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(18, 18, 18, 18)
        left_lay.setSpacing(12)

        # Título
        lbl_title = QLabel("📱 ESPEJO CELULAR")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.colores['acento']}; letter-spacing: 1px;")
        left_lay.addWidget(lbl_title)

        lbl_subtitle = QLabel("Control remoto y duplicado de Android por USB / Wi-Fi")
        lbl_subtitle.setWordWrap(True)
        lbl_subtitle.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 11px;")
        left_lay.addWidget(lbl_subtitle)

        # Estado Conexión
        self.card_status = QFrame()
        self.card_status.setStyleSheet("background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);")
        st_lay = QHBoxLayout(self.card_status)
        st_lay.setContentsMargins(10, 8, 10, 8)
        
        self.lbl_status = QLabel("🟢 Modo Virtual Activo")
        self.lbl_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #34D399;")
        st_lay.addWidget(self.lbl_status)
        st_lay.addStretch()

        left_lay.addWidget(self.card_status)

        # Panel de Detección de Instancia Móvil / Celular
        self.card_device_info = QFrame()
        self.card_device_info.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }}
        """)
        self.lay_device_info = QVBoxLayout(self.card_device_info)
        self.lay_device_info.setContentsMargins(12, 10, 12, 10)
        self.lay_device_info.setSpacing(4)
        
        self.lbl_device_title = QLabel("📱 ESTADO DE DISPOSITIVO MÓVIL")
        self.lbl_device_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_device_title.setStyleSheet("color: #818CF8;")
        self.lay_device_info.addWidget(self.lbl_device_title)
        
        self.lbl_device_name = QLabel("Comprobando conexión...")
        self.lbl_device_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_device_name.setStyleSheet("color: white;")
        self.lbl_device_name.setWordWrap(True)
        self.lay_device_info.addWidget(self.lbl_device_name)
        
        self.lbl_device_detail = QLabel("")
        self.lbl_device_detail.setFont(QFont("Segoe UI", 9))
        self.lbl_device_detail.setStyleSheet("color: #AAB0B8;")
        self.lbl_device_detail.setWordWrap(True)
        self.lay_device_info.addWidget(self.lbl_device_detail)
        
        self.lbl_device_state = QLabel("")
        self.lbl_device_state.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lay_device_info.addWidget(self.lbl_device_state)
        
        left_lay.addWidget(self.card_device_info)
        
        # Mantener cb_devices oculto para compatibilidad interna
        self.cb_devices = QComboBox()
        self.cb_devices.addItem("📱 Simulador Virtual Android", "virtual")
        self.cb_devices.hide()
        left_lay.addWidget(self.cb_devices)

        btn_refresh = QPushButton("🔄 Comprobar Conexión de Celular")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 7px; border: none; font-size: 11px; font-weight: bold;")
        btn_refresh.clicked.connect(self._buscar_dispositivos)
        left_lay.addWidget(btn_refresh)

        btn_guide = QPushButton("📖 ¿Cómo conectar por USB?")
        btn_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guide.setStyleSheet("background: rgba(99, 102, 241, 0.2); color: #818CF8; border-radius: 6px; padding: 6px; font-weight: bold; border: 1px solid rgba(99, 102, 241, 0.3); font-size: 11px;")
        btn_guide.clicked.connect(self._mostrar_guia_conexion)
        left_lay.addWidget(btn_guide)

        # Conexión Wi-Fi Inalámbrica
        wifi_box = QFrame()
        wifi_box.setStyleSheet(f"background: {self.colores['bg_terciario']}; border-radius: 8px;")
        wf_lay = QVBoxLayout(wifi_box)
        wf_lay.setContentsMargins(10, 10, 10, 10)
        wf_lay.setSpacing(6)

        lbl_wf = QLabel("📶 Conexión Wi-Fi Sin Cables:")
        lbl_wf.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
        wf_lay.addWidget(lbl_wf)

        self.ent_ip = QLineEdit()
        self.ent_ip.setPlaceholderText("192.168.1.X:5555")
        self.ent_ip.setStyleSheet("background: rgba(0,0,0,0.2); color: white; padding: 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1);")
        wf_lay.addWidget(self.ent_ip)

        btn_connect_wifi = QPushButton("⚡ Conectar por IP")
        btn_connect_wifi.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_connect_wifi.setStyleSheet(f"background: {self.colores['acento']}; color: white; border-radius: 6px; padding: 6px; font-weight: bold; border: none; font-size: 11px;")
        btn_connect_wifi.clicked.connect(self._conectar_wifi)
        wf_lay.addWidget(btn_connect_wifi)

        left_lay.addWidget(wifi_box)

        # Acciones Rápidas del Celular
        lbl_act = QLabel("Acciones del Dispositivo:")
        lbl_act.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
        left_lay.addWidget(lbl_act)

        grid_act = QHBoxLayout()
        grid_act.setSpacing(6)

        btn_home = QPushButton("🏠 Inicio")
        btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_home.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px; border: none;")
        btn_home.clicked.connect(lambda: self._enviar_tecla(3))
        grid_act.addWidget(btn_home)

        btn_back = QPushButton("⬅ Atrás")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px; border: none;")
        btn_back.clicked.connect(lambda: self._enviar_tecla(4))
        grid_act.addWidget(btn_back)

        btn_rec = QPushButton("🔳 Recientes")
        btn_rec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rec.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px; border: none;")
        btn_rec.clicked.connect(lambda: self._enviar_tecla(187))
        grid_act.addWidget(btn_rec)

        left_lay.addLayout(grid_act)

        grid_vol = QHBoxLayout()
        grid_vol.setSpacing(6)

        btn_vup = QPushButton("🔊 Vol +")
        btn_vup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_vup.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px; border: none;")
        btn_vup.clicked.connect(lambda: self._enviar_tecla(24))
        grid_vol.addWidget(btn_vup)

        btn_vdown = QPushButton("🔉 Vol -")
        btn_vdown.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_vdown.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px; border: none;")
        btn_vdown.clicked.connect(lambda: self._enviar_tecla(25))
        grid_vol.addWidget(btn_vdown)

        btn_pwr = QPushButton("🔒 Encender")
        btn_pwr.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pwr.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px; border: none;")
        btn_pwr.clicked.connect(lambda: self._enviar_tecla(26))
        grid_vol.addWidget(btn_pwr)

        left_lay.addLayout(grid_vol)

        # Capturas y Grabación
        grid_cap = QHBoxLayout()
        grid_cap.setSpacing(6)

        btn_shot = QPushButton("📸 Captura PNG")
        btn_shot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_shot.setStyleSheet(f"background: {self.colores['bg_terciario']}; color: white; border-radius: 6px; padding: 8px; border: none;")
        btn_shot.clicked.connect(self._capturar_pantalla)
        grid_cap.addWidget(btn_shot)

        btn_scrcpy = QPushButton("🚀 Modo HD (scrcpy)")
        btn_scrcpy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_scrcpy.setStyleSheet("background: #10B981; color: white; border-radius: 6px; padding: 8px; font-weight: bold; border: none;")
        btn_scrcpy.clicked.connect(self._lanzar_scrcpy)
        grid_cap.addWidget(btn_scrcpy)

        left_lay.addLayout(grid_cap)

        # Opciones Estilo Enlace Móvil
        lbl_opts = QLabel("📱 Opciones Estilo Enlace Móvil:")
        lbl_opts.setStyleSheet("color: white; font-size: 11px; font-weight: bold; margin-top: 5px;")
        left_lay.addWidget(lbl_opts)

        self.chk_screen_off = QCheckBox("🌙 Apagar pantalla física del celular")
        self.chk_screen_off.setChecked(True)
        self.chk_screen_off.setToolTip("El celular permanecerá con la pantalla apagada mientras lo ves y controlas en la PC (Ahorro Batería)")
        self.chk_screen_off.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_screen_off)

        self.chk_stay_awake = QCheckBox("💡 Evitar que el celular se suspenda")
        self.chk_stay_awake.setChecked(True)
        self.chk_stay_awake.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_stay_awake)

        self.chk_always_on_top = QCheckBox("📌 Ventana siempre visible (Always on top)")
        self.chk_always_on_top.setChecked(False)
        self.chk_always_on_top.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_always_on_top)

        self.chk_power_off_close = QCheckBox("🔒 Bloquear celular al cerrar ventana")
        self.chk_power_off_close.setChecked(True)
        self.chk_power_off_close.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_power_off_close)

        self.chk_audio = QCheckBox("🔊 Transmitir Audio del celular a la PC")
        self.chk_audio.setChecked(True)
        self.chk_audio.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_audio)

        # ── SECCIÓN MODO GAMER & PERIFÉRICOS (Roblox, Free Fire, Juegos 3D) ──
        lbl_gamer = QLabel("🎮 Modo Gamer & Periféricos (Roblox / 3D):")
        lbl_gamer.setStyleSheet("color: #FBBF24; font-size: 11px; font-weight: bold; margin-top: 8px;")
        left_lay.addWidget(lbl_gamer)

        self.chk_kbd_uhid = QCheckBox("🎮 Teclado Físico UHID (WASD / Espacio / Shift)")
        self.chk_kbd_uhid.setChecked(True)
        self.chk_kbd_uhid.setToolTip("Simula un teclado USB físico real en el kernel de Android. Necesario para mover personajes con WASD en Roblox.")
        self.chk_kbd_uhid.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_kbd_uhid)

        self.chk_mouse_uhid = QCheckBox("🖱️ Mouse Físico Hardware (Clic derecho & Cámara 360°)")
        self.chk_mouse_uhid.setChecked(True)
        self.chk_mouse_uhid.setToolTip("Emula un ratón USB físico. Permite clic derecho y rotar la cámara en juegos 3D.")
        self.chk_mouse_uhid.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_mouse_uhid)

        self.chk_raw_keys = QCheckBox("⚡ Eventos RAW de Teclado (Modo Estándar SDK)")
        self.chk_raw_keys.setChecked(False)
        self.chk_raw_keys.setStyleSheet("color: #E2E2E2; font-size: 11px;")
        left_lay.addWidget(self.chk_raw_keys)

        lbl_hint_gamer = QLabel("💡 En juegos como Roblox, presiona 'Alt Izquierdo' para capturar o liberar el cursor del ratón.")
        lbl_hint_gamer.setWordWrap(True)
        lbl_hint_gamer.setStyleSheet("color: #AAB0B8; font-size: 10px; font-style: italic; margin-bottom: 5px;")
        left_lay.addWidget(lbl_hint_gamer)

        # Personalización de Carcasa
        lbl_style = QLabel("Estilo de Carcasa del Simulador:")
        lbl_style.setStyleSheet("color: white; font-size: 11px; font-weight: bold; margin-top: 5px;")
        left_lay.addWidget(lbl_style)

        self.cb_style = QComboBox()
        self.cb_style.addItems(["Negro Mate", "Plata Titanio", "Violeta Neón", "Azul Medianoche"])
        self.cb_style.setStyleSheet(f"""
            QComboBox {{
                background: {self.colores['bg_terciario']}; color: white; padding: 6px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        self.cb_style.currentTextChanged.connect(self._cambiar_carcasa)
        left_lay.addWidget(self.cb_style)

        left_lay.addStretch()
        scroll_left.setWidget(left_panel)
        main_layout.addWidget(scroll_left)

        # ── PANEL DERECHO: Carcasa y Lienzo del Teléfono Celular ───────────────
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background: {self.colores['bg_secundario']}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(20, 20, 20, 20)

        # Lienzo del Celular
        self.phone_canvas = PhoneCanvasWidget(self, self.colores)
        self.phone_canvas.mouse_clicked.connect(self._on_phone_clicked)
        self.phone_canvas.mouse_swiped.connect(self._on_phone_swiped)
        right_lay.addWidget(self.phone_canvas)

        main_layout.addWidget(right_panel, 1)

        self._buscar_dispositivos()

    def _buscar_dispositivos(self):
        # Actualizar ruta de ADB por si se acaba de instalar
        self.adb_bin = ADBEngine.buscar_adb() or self.adb_bin

        info = ADBEngine.detectar_instancia_movil(self.adb_bin)
        self.instancia_movil_actual = info

        self.cb_devices.blockSignals(True)
        self.cb_devices.clear()
        self.cb_devices.addItem("📱 Simulador Virtual Android", "virtual")

        if info["conectado"]:
            self.lbl_status.setText(f"🟢 {info['nombre']} Conectado")
            self.lbl_status.setStyleSheet("color: #34D399;")
            self.card_status.setStyleSheet("background: rgba(16, 185, 129, 0.15); border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.4);")

            self.lbl_device_title.setText("📲 DISPOSITIVO MÓVIL DETECTADO")
            self.lbl_device_title.setStyleSheet("color: #34D399; font-weight: bold;")
            self.lbl_device_name.setText(f"📱 {info['nombre']}")
            self.lbl_device_name.setStyleSheet("color: white; font-size: 11pt; font-weight: bold;")

            detalles = []
            if info.get("almacenamiento"):
                detalles.append(f"📁 <b>Almacenamiento:</b> {info['almacenamiento']}")
            if info.get("tipo"):
                detalles.append(f"🔌 <b>Conexión:</b> {info['tipo']}")
            if info.get("id") and info["id"] != "virtual":
                detalles.append(f"🆔 <b>Serie / ID:</b> {info['id']}")
            self.lbl_device_detail.setText("<br>".join(detalles) if detalles else "Conectado al sistema.")

            st_text = "🟢 Listo para duplicar en pantalla" if info.get("estado") in ["listo", "conectado"] else "⚠️ Conectado (Permiso Pendiente)"
            st_color = "#34D399" if info.get("estado") in ["listo", "conectado"] else "#FBBF24"
            self.lbl_device_state.setText(st_text)
            self.lbl_device_state.setStyleSheet(f"color: {st_color}; font-size: 9pt; font-weight: bold;")

            self.card_device_info.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.colores.get('bg_principal', '#121218')};
                    border: 1px solid rgba(16, 185, 129, 0.4);
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            self.dispositivo_actual = info.get("id", "virtual")
            self.cb_devices.addItem(f"📱 {info['nombre']}", self.dispositivo_actual)
            self.cb_devices.setCurrentIndex(1)
            self.phone_canvas.modo_demo = (self.dispositivo_actual == "virtual")
        else:
            self.lbl_status.setText("⚪ Esperando Conexión USB")
            self.lbl_status.setStyleSheet("color: #94A3B8;")
            self.card_status.setStyleSheet("background: rgba(255, 255, 255, 0.05); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);")

            self.lbl_device_title.setText("📱 ESTADO DE DISPOSITIVO MÓVIL")
            self.lbl_device_title.setStyleSheet("color: #818CF8; font-weight: bold;")
            self.lbl_device_name.setText("Ningún celular detectado")
            self.lbl_device_name.setStyleSheet("color: #94A3B8; font-size: 10pt;")
            self.lbl_device_detail.setText("Conecta tu celular a la PC con cable USB y selecciona 'Transferencia de archivos' o activa 'Depuración por USB'.")
            self.lbl_device_state.setText("⚠️ Simulador virtual activo")
            self.lbl_device_state.setStyleSheet("color: #FBBF24; font-size: 9pt;")

            self.card_device_info.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.colores.get('bg_principal', '#121218')};
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            self.dispositivo_actual = "virtual"
            self.cb_devices.setCurrentIndex(0)
            self.phone_canvas.modo_demo = True

        self.cb_devices.blockSignals(False)
        self.phone_canvas.update()

    def _on_device_combo_changed(self, index):
        dev_id = self.cb_devices.currentData()
        self.dispositivo_actual = dev_id

        if not dev_id or dev_id == "virtual":
            self.phone_canvas.modo_demo = True
            self.phone_canvas.update()
            return

        # Buscar info del dispositivo seleccionado
        target_dev = None
        for d in getattr(self, "dispositivos_detectados", []):
            if d.get("id") == dev_id:
                target_dev = d
                break

        if target_dev:
            if target_dev["state"] == "unauthorized":
                self.lbl_status.setText(f"⚠️ Permiso Pendiente en Celular ({target_dev['id']})")
                self.card_status.setStyleSheet("background: rgba(251, 191, 36, 0.15); border-radius: 8px; border: 1px solid rgba(251, 191, 36, 0.4);")
                self.lbl_status.setStyleSheet("color: #FBBF24;")
                self.phone_canvas.modo_demo = True

                QMessageBox.warning(
                    self, "🔑 Acepta el Permiso en tu Celular",
                    f"¡Se detectó tu celular conectado ({target_dev['id']})!\n\n"
                    "Por favor, mira la PANTALLA DE TU CELULAR. Debe aparecer una ventana flotante diciéndote:\n\n"
                    "   '¿Permitir depuración por USB desde esta computadora?'\n\n"
                    "1. Marca la casilla 'Permitir siempre desde esta computadora'.\n"
                    "2. Presiona ACEPTAR en tu teléfono.\n"
                    "3. Luego vuelve a presionar '🔄 Buscar Dispositivos ADB' aquí."
                )
            else:
                self.lbl_status.setText(f"🟢 Conectado: {target_dev['model']}")
                self.lbl_status.setStyleSheet("color: #34D399;")
                self.card_status.setStyleSheet("background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);")
                self.phone_canvas.modo_demo = False
        self.phone_canvas.update()

    def _conectar_wifi(self):
        ip = self.ent_ip.text().strip()
        if not ip:
            QMessageBox.warning(self, "Conexión Wi-Fi", "Ingresa la dirección IP del teléfono (ej: 192.168.1.15:5555).")
            return

        try:
            res = subprocess.run([self.adb_bin, "connect", ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if "connected" in res.stdout.lower():
                QMessageBox.information(self, "Wi-Fi Conectado", f"¡Conectado exitosamente con {ip}!")
                self._buscar_dispositivos()
            else:
                QMessageBox.warning(self, "Error de Conexión", f"No se pudo conectar con {ip}.\nAsegúrate de tener la depuración por Wi-Fi activa.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al intentar conectar: {e}")

    def _enviar_tecla(self, keycode):
        dev_id = self.cb_devices.currentData()
        if dev_id and dev_id != "virtual":
            ok = ADBEngine.enviar_tecla(self.adb_bin, dev_id, keycode)
            if not ok:
                QMessageBox.information(
                    self, "🚀 Inicia el Modo HD (scrcpy)",
                    "Los botones simples requieren que inicies el **Modo HD (scrcpy)** para omitir las restricciones de seguridad de tu teléfono (POCO / Xiaomi / Samsung).\n\n"
                    "¡Haz clic en el botón verde **'🚀 Modo HD (scrcpy)'** para controlar tu celular a 60 FPS sin ningún límite!"
                )
        else:
            # Acciones en el simulador virtual
            if keycode == 3:  # Home
                self.phone_canvas.app_activa = "Home"
            elif keycode == 4:  # Back
                self.phone_canvas.app_activa = "Home"
            self.phone_canvas.update()

    def _on_phone_clicked(self, x, y):
        dev_id = self.cb_devices.currentData()
        if dev_id and dev_id != "virtual":
            ADBEngine.enviar_tap(self.adb_bin, dev_id, x, y)

    def _on_phone_swiped(self, x1, y1, x2, y2):
        dev_id = self.cb_devices.currentData()
        if dev_id and dev_id != "virtual":
            ADBEngine.enviar_swipe(self.adb_bin, dev_id, x1, y1, x2, y2)

    def _capturar_pantalla(self):
        dev_id = self.cb_devices.currentData()
        dest, _ = QFileDialog.getSaveFileName(self, "Guardar Captura", "captura_pantalla.png", "Imágenes PNG (*.png)")
        if not dest:
            return

        if dev_id and dev_id != "virtual":
            if ADBEngine.capturar_pantalla(self.adb_bin, dev_id, dest):
                QMessageBox.information(self, "Captura Guardada", f"Captura guardada en:\n{dest}")
            else:
                QMessageBox.warning(self, "Error", "No se pudo realizar la captura mediante ADB.")
        else:
            # Captura del simulador virtual
            pix = self.phone_canvas.grab()
            pix.save(dest)
            QMessageBox.information(self, "Captura Guardada", f"Captura del simulador guardada en:\n{dest}")

    def _lanzar_scrcpy(self):
        self.scrcpy_bin = ADBEngine.buscar_scrcpy()
        if not self.scrcpy_bin:
            confirm = QMessageBox.question(
                self, "⚡ Descargar Motor scrcpy HD",
                "scrcpy es el motor profesional que permite transmitir y controlar tu celular a 60 FPS sin errores de permisos en POCO, Samsung, Xiaomi o cualquier marca.\n\n"
                "¿Deseas descargar scrcpy HD automáticamente ahora mismo (1 clic)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    import urllib.request
                    import zipfile
                    tools_dir = Path.home() / "Documents" / "Multitool" / "tools" / "scrcpy"
                    tools_dir.mkdir(parents=True, exist_ok=True)
                    zip_path = tools_dir / "scrcpy.zip"
                    url = "https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-win64-v2.4.zip"

                    dlg = QMessageBox(self)
                    dlg.setWindowTitle("Descargando scrcpy HD...")
                    dlg.setText("Descargando e instalando el motor scrcpy HD en tu PC...\nPor favor espera unos segundos.")
                    dlg.show()
                    QApplication.processEvents()

                    urllib.request.urlretrieve(url, zip_path)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(tools_dir)
                    dlg.close()

                    self.scrcpy_bin = ADBEngine.buscar_scrcpy()
                    if self.scrcpy_bin:
                        QMessageBox.information(self, "¡Instalación Exitosa!", "¡scrcpy HD instalado correctamente! Iniciando espejo de pantalla...")
                except Exception as e:
                    QMessageBox.critical(self, "Error de Descarga", f"No se pudo descargar scrcpy automáticamente:\n{e}")
                    return
            else:
                return

        dev_id = self.cb_devices.currentData()
        try:
            cmd = [self.scrcpy_bin]
            if dev_id and dev_id != "virtual":
                cmd += ["-s", dev_id]

            # Parámetros avanzados estilo Enlace Móvil
            if hasattr(self, 'chk_screen_off') and self.chk_screen_off.isChecked():
                cmd.append("--turn-screen-off")
            if hasattr(self, 'chk_stay_awake') and self.chk_stay_awake.isChecked():
                cmd.append("--stay-awake")
            if hasattr(self, 'chk_always_on_top') and self.chk_always_on_top.isChecked():
                cmd.append("--always-on-top")
            if hasattr(self, 'chk_power_off_close') and self.chk_power_off_close.isChecked():
                cmd.append("--power-off-on-close")
            if hasattr(self, 'chk_audio') and not self.chk_audio.isChecked():
                cmd.append("--no-audio")

            # Modo Gamer & Periféricos (Roblox / Juegos 3D)
            if hasattr(self, 'chk_kbd_uhid') and self.chk_kbd_uhid.isChecked():
                cmd.append("--keyboard=uhid")
            elif hasattr(self, 'chk_raw_keys') and self.chk_raw_keys.isChecked():
                cmd.append("--raw-key-events")

            if hasattr(self, 'chk_mouse_uhid') and self.chk_mouse_uhid.isChecked():
                cmd.append("--mouse=uhid")

            subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            QMessageBox.critical(self, "Error al Iniciar scrcpy", f"Ocurrió un error al lanzar scrcpy:\n{e}")

    def _cambiar_carcasa(self, nombre):
        self.phone_canvas.color_carcasa = nombre
        self.phone_canvas.update()

    def _actualizar_estado(self):
        self.phone_canvas.hora_actual = datetime.datetime.now().strftime("%H:%M")
        self.phone_canvas.update()

    def _mostrar_guia_conexion(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("📖 Guía de Conexión Celular Android por USB")
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setText(
            "<b>Pasos necesarios en tu Celular Android:</b><br><br>"
            "1. <b>Activar Opciones de Desarrollador:</b><br>"
            "   • Ve a <i>Ajustes ➔ Acerca del teléfono</i>.<br>"
            "   • Toca 7 veces seguidas en <b>Número de compilación</b> (o Versión de OS/MIUI/HyperOS).<br><br>"
            "2. <b>Activar Depuración por USB:</b><br>"
            "   • Ve a <i>Ajustes ➔ Ajustes adicionales ➔ Opciones de desarrollador</i>.<br>"
            "   • Activa el interruptor <b>Depuración por USB</b>.<br><br>"
            "3. <b>⚠️ IMPORTANTE para dispositivos Xiaomi / POCO / Redmi:</b><br>"
            "   • En Opciones de desarrollador, activa la opción: <b>'Depuración por USB (Ajustes de seguridad)'</b>.<br>"
            "   • Esta opción es imprescindible en POCO/Xiaomi para permitir clics y eventos táctiles desde la PC.<br><br>"
            "4. <b>Aceptar Permiso RSA en tu Celular:</b><br>"
            "   • Al conectar el cable USB, marca <b>'Permitir siempre'</b> y presiona <b>Aceptar</b>.<br><br>"
            "5. Presiona <b>'🔄 Buscar Dispositivos ADB'</b> en la aplicación."
        )
        dlg.exec()
