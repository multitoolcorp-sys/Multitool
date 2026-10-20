import time
import platform
import urllib.request
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QApplication, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, pyqtProperty, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QScreen, QPixmap, QIcon, QPainter, QBrush, QPen
from PyQt6.sip import isdeleted


class IconLoaderBridge(QObject):
    iconLoaded = pyqtSignal(object)


class ToastNotification(QWidget):
    """Componente visual de notificación enriquecida para MultiTool con soporte de iconos de origen y aplicación."""
    def __init__(self, parent, title, message, type="info", colores=None, duration=6000, idx=0, on_click=None, actions=None, source_icon=None):
        super().__init__(None)
        self.target_parent = parent
        self.on_click_callback = on_click
        self.closing = False
        
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.colores = colores or {
            "bg_secundario": "#1A1B26", "fg_principal": "white", 
            "acento": "#6366F1", "error": "#F87171", "exito": "#34D399", "advertencia": "#FBBF24"
        }
        
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        if platform.system() == "Darwin": self.font_family = ".AppleSystemUIFont"

        self.duration = duration
        self.width_toast = 380
        self.height_toast = 100
        
        colors_map = {
            "info": self.colores.get("acento", "#6366F1"),
            "error": self.colores.get("error", "#F87171"),
            "success": self.colores.get("exito", "#34D399"),
            "warning": self.colores.get("advertencia", "#FBBF24")
        }
        accent_color = colors_map.get(type, self.colores.get("acento", "#6366F1"))
        
        # Contenedor Principal (Estilo Tarjeta Elevada)
        self.main_container = QFrame(self)
        self.main_container.setFixedSize(self.width_toast, self.height_toast)
        self.main_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1A1B26')};
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }}
        """)
        
        main_layout = QHBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Barra lateral de color de acento
        side_bar = QFrame()
        side_bar.setFixedWidth(5)
        side_bar.setStyleSheet(f"background-color: {accent_color}; border-top-left-radius: 12px; border-bottom-left-radius: 12px;")
        main_layout.addWidget(side_bar)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 12)
        content_layout.setSpacing(6)
        
        # 1. Cabecera (Icono de la App MultiTool + "MULTITOOL" + Botón Cerrar)
        header = QHBoxLayout()
        header.setSpacing(6)
        
        # Icono de la Aplicación MultiTool
        lbl_app_icon = QLabel()
        lbl_app_icon.setFixedSize(18, 18)
        lbl_app_icon.setStyleSheet("background: transparent; border: none;")
        app_icon_path = Path(__file__).resolve().parent / "icono.ico"
        if app_icon_path.exists():
            app_pix = QPixmap(str(app_icon_path)).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_app_icon.setPixmap(app_pix)
        else:
            lbl_app_icon.setText("🛠️")
        header.addWidget(lbl_app_icon)
        
        lbl_app_name = QLabel("MULTITOOL")
        lbl_app_name.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_app_name.setStyleSheet("color: #94A3B8; letter-spacing: 1px; border: none; background: transparent;")
        header.addWidget(lbl_app_name)
        
        header.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton { 
                border: none; 
                color: #94A3B8; 
                font-size: 11px; 
                background: transparent; 
                border-radius: 11px;
            } 
            QPushButton:hover { 
                color: white; 
                background: rgba(255, 255, 255, 0.12); 
            }
        """)
        btn_close.clicked.connect(self.animar_salida)
        header.addWidget(btn_close)
        content_layout.addLayout(header)
        
        # 2. Cuerpo Central (Icono de Origen / Favicon a la izquierda + Textos a la derecha)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)
        
        self.lbl_source_icon = QLabel()
        self.lbl_source_icon.setFixedSize(36, 36)
        self.lbl_source_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_source_icon.setStyleSheet("""
            background: rgba(255, 255, 255, 0.05); 
            border: 1px solid rgba(255, 255, 255, 0.08); 
            border-radius: 8px;
        """)
        body_layout.addWidget(self.lbl_source_icon)
        
        # Cargar Icono de Origen de forma segura
        self._cargar_icono_origen(source_icon, title)
        
        # Contenedor de Texto (Título + Mensaje)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")
        lbl_title.setWordWrap(False)
        text_layout.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setFont(QFont(self.font_family, 8))
        lbl_msg.setStyleSheet("color: #CBD5E1; border: none; background: transparent;")
        lbl_msg.setWordWrap(True)
        text_layout.addWidget(lbl_msg)
        
        body_layout.addLayout(text_layout)
        content_layout.addLayout(body_layout)
        
        # 3. Botones de Acción Opcionales
        if actions:
            act_lay = QHBoxLayout()
            act_lay.setSpacing(8)
            for text_btn, cb in actions.items():
                btn = QPushButton(text_btn)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(f"""
                    background: {accent_color}33; 
                    color: white; 
                    border-radius: 5px; 
                    padding: 4px 12px; 
                    border: 1px solid {accent_color}; 
                    font-size: 11px;
                    font-weight: 600;
                """)
                btn.clicked.connect(lambda ch, callback=cb: self._action_triggered(callback))
                act_lay.addWidget(btn)
            act_lay.addStretch()
            content_layout.addLayout(act_lay)
            self.height_toast += 32
            self.main_container.setFixedHeight(self.height_toast)
        
        main_layout.addWidget(content)
        
        self.posicionar(idx)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        self.show()
        self.animar_entrada()

    def _cargar_icono_origen(self, source_icon, title):
        """Asigna o descarga el icono de origen de la notificación (favicon o imagen de la web)."""
        if isinstance(source_icon, QPixmap) and not source_icon.isNull():
            self._set_rounded_pixmap(source_icon)
            return
        elif isinstance(source_icon, QIcon) and not source_icon.isNull():
            pix = source_icon.pixmap(36, 36)
            if not pix.isNull():
                self._set_rounded_pixmap(pix)
                return
        elif isinstance(source_icon, str) and source_icon.strip():
            # Puede ser URL http/https o archivo local
            if source_icon.startswith(("http://", "https://")):
                self.icon_bridge = IconLoaderBridge()
                self.icon_bridge.iconLoaded.connect(self._on_remote_icon_loaded)
                
                def _fetch():
                    try:
                        req = urllib.request.Request(source_icon, headers={'User-Agent': 'Mozilla/5.0 MultiTool'})
                        with urllib.request.urlopen(req, timeout=3) as resp:
                            data = resp.read()
                            pix = QPixmap()
                            if pix.loadFromData(data):
                                self.icon_bridge.iconLoaded.emit(pix)
                                return
                    except Exception:
                        pass
                
                threading.Thread(target=_fetch, daemon=True).start()
                self._dibujar_icono_fallback(title)
                return
            elif Path(source_icon).exists():
                pix = QPixmap(source_icon)
                if not pix.isNull():
                    self._set_rounded_pixmap(pix)
                    return

        # Fallback predeterminado elegante
        self._dibujar_icono_fallback(title)

    def _on_remote_icon_loaded(self, pixmap):
        if not isdeleted(self) and pixmap and not pixmap.isNull():
            self._set_rounded_pixmap(pixmap)

    def _set_rounded_pixmap(self, pixmap):
        scaled = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_source_icon.setPixmap(scaled)

    def _dibujar_icono_fallback(self, title):
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#6366F1")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 32, 32, 6, 6)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        initial = title.strip()[:1].upper() if title and title.strip() else "🌐"
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, initial)
        p.end()
        self.lbl_source_icon.setPixmap(pix)

    def mousePressEvent(self, event):
        """Si se hace clic en la notificación, ejecuta la acción de navegación y la cierra."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.on_click_callback:
                try:
                    self.on_click_callback()
                except Exception as e:
                    print(f"[ToastNotification] Error en on_click: {e}")
            self.animar_salida()
            event.accept()
            return
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Pausa el temporizador de auto-cierre mientras el ratón esté sobre la notificación."""
        if hasattr(self, "dismiss_timer") and self.dismiss_timer.isActive():
            self.dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Reanuda el auto-cierre tras 3 segundos cuando el usuario quita el cursor."""
        if hasattr(self, "dismiss_timer") and not self.closing:
            self.dismiss_timer.start(3000)
        super().leaveEvent(event)

    def _action_triggered(self, cb):
        if cb: 
            try: cb()
            except Exception: pass
        self.animar_salida()

    def posicionar(self, idx):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + screen.width() - self.width_toast - 20
        y = screen.top() + screen.height() - (self.height_toast + 15) * (idx + 1) - 15
        self.move(x, y)

    def animar_entrada(self):
        if isdeleted(self): return
        self.entry_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.entry_anim.setDuration(400)
        self.entry_anim.setStartValue(0)
        self.entry_anim.setEndValue(1.0)
        self.entry_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.entry_anim.start()
        
        # Auto-cierre con duración configurable (6 segundos por defecto)
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.animar_salida)
        self.dismiss_timer.start(self.duration)

    def animar_salida(self):
        if isdeleted(self) or self.closing: return
        self.closing = True
        
        if hasattr(self, "dismiss_timer"): self.dismiss_timer.stop()
        if hasattr(self, "entry_anim"): self.entry_anim.stop()
        
        self.exit_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.exit_anim.setDuration(450)
        self.exit_anim.setStartValue(self.opacity_effect.opacity())
        self.exit_anim.setEndValue(0)
        self.exit_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.exit_anim.finished.connect(self.safe_close)
        self.exit_anim.start()

    def safe_close(self):
        if not isdeleted(self):
            self.close()


def _normalize_notification_args(*args, **kwargs):
    parent = kwargs.pop("parent", None)
    title = kwargs.pop("title", None)
    message = kwargs.pop("message", None)
    tipo = kwargs.pop("type", None)
    colores = kwargs.pop("colores", None)
    duration = kwargs.pop("duration", 6000)
    on_click = kwargs.pop("on_click", None)
    actions = kwargs.pop("actions", None)
    source_icon = kwargs.pop("source_icon", None)

    args_list = list(args)

    # Si el primer argumento es un widget / ventana padre
    if args_list:
        first = args_list[0]
        if first is not None and not isinstance(first, str) and (hasattr(first, "isWidgetType") or hasattr(first, "window") or hasattr(first, "parent")):
            parent = args_list.pop(0)
        elif first is None and len(args_list) >= 2 and isinstance(args_list[1], str):
            parent = args_list.pop(0)

    # Extraer título
    if title is None and args_list:
        title = args_list.pop(0)

    # Extraer mensaje
    if message is None and args_list:
        message = args_list.pop(0)

    # Extraer tipo o colores si vienen en posicionales
    if args_list:
        next_arg = args_list.pop(0)
        if isinstance(next_arg, dict) and colores is None:
            colores = next_arg
        elif isinstance(next_arg, str) and tipo is None:
            tipo = next_arg

    if args_list:
        next_arg = args_list.pop(0)
        if isinstance(next_arg, dict) and colores is None:
            colores = next_arg

    if tipo is None:
        tipo = "info"
    if title is None:
        title = "MultiTool"
    if message is None:
        message = ""

    return {
        "parent": parent,
        "title": str(title),
        "message": str(message),
        "type": tipo,
        "colores": colores,
        "duration": duration,
        "on_click": on_click,
        "actions": actions,
        "source_icon": source_icon,
    }


class _NotificationShowDispatcher:
    def __get__(self, instance, owner):
        if instance is not None:
            return instance._show_impl
        return owner._class_show

    def __call__(self, *args, **kwargs):
        return NotificationManager._class_show(*args, **kwargs)


class NotificationManager:
    """Gestiona el apilamiento y ciclo de vida de las notificaciones de forma segura."""
    def __init__(self, colores=None):
        self.colores = colores
        self.notifications = []

    def _show_impl(self, *args, **kwargs):
        norm = _normalize_notification_args(*args, **kwargs)
        parent = norm["parent"]
        title = norm["title"]
        message = norm["message"]
        tipo = norm["type"]
        colores = norm["colores"] or self.colores
        duration = norm["duration"]
        on_click = norm["on_click"]
        actions = norm["actions"]
        source_icon = norm["source_icon"]

        new_list = []
        for n in self.notifications:
            try:
                if n is not None and not isdeleted(n) and n.isVisible():
                    new_list.append(n)
            except Exception:
                continue
        self.notifications = new_list
        
        if on_click is None and parent and hasattr(parent, "parent") and not isinstance(parent, str):
            on_click = self._create_redirect(parent)

        try:
            idx = len(self.notifications)
            toast = ToastNotification(
                parent=parent, 
                title=title, 
                message=message, 
                type=tipo, 
                colores=colores, 
                duration=duration, 
                idx=idx, 
                on_click=on_click, 
                actions=actions, 
                source_icon=source_icon
            )
            self.notifications.append(toast)
            return toast
        except Exception as e:
            print(f"[NotificationManager] Error al mostrar notificación: {e}")
            return None

    @classmethod
    def _class_show(cls, *args, **kwargs):
        global _global_notification_manager
        if _global_notification_manager is None:
            _global_notification_manager = NotificationManager()
        return _global_notification_manager._show_impl(*args, **kwargs)

    show = _NotificationShowDispatcher()

    def _create_redirect(self, target):
        def redirect():
            try:
                if target and not isdeleted(target) and hasattr(target, "parent"):
                    app_gui = None
                    current = target
                    while current:
                        from vistas.gui import BaseAppGUI
                        if isinstance(current, BaseAppGUI):
                            app_gui = current
                            break
                        if hasattr(current, "parent"):
                            current = current.parent()
                        else: break
                    
                    if app_gui:
                        if not app_gui.isVisible() or app_gui.isMinimized():
                            app_gui.showNormal()
                        app_gui.raise_()
                        app_gui.activateWindow()
                        if hasattr(app_gui, "notebook") and hasattr(target, "parent"):
                            idx = app_gui.notebook.indexOf(target)
                            if idx == -1:
                                p = target.parent()
                                while p:
                                    idx = app_gui.notebook.indexOf(p)
                                    if idx != -1: break
                                    p = p.parent()
                            
                            if idx != -1:
                                app_gui.notebook.setCurrentIndex(idx)
            except Exception:
                pass
        return redirect


_global_notification_manager = None

def get_global_notification_manager(colores=None):
    global _global_notification_manager
    if _global_notification_manager is None:
        _global_notification_manager = NotificationManager(colores)
    elif colores and not _global_notification_manager.colores:
        _global_notification_manager.colores = colores
    return _global_notification_manager

def show_notification(*args, **kwargs):
    """Interfaz global para mostrar notificaciones enriquecidas."""
    return NotificationManager.show(*args, **kwargs)
