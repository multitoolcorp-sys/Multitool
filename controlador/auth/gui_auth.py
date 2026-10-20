import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QScrollArea, QMessageBox, QFileDialog, QSizePolicy,
    QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPixmap, QColor, QPalette

from .autenticacion import login, register
from vistas.utils.selector_avatar import SelectorAvatar
from vistas.utils.avatar import AvatarUtils

# Definición de colores premium
COLORES = {
    "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
    "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
    "acento_hover": "#818CF8", "error": "#F87171", "exito": "#34D399", "advertencia": "#FBBF24"
}

class AuthGUI:
    # Fuente adaptable
    FONT_FAMILY = "Segoe UI" if platform.system() == "Windows" else "Inter"
    if platform.system() == "Darwin": FONT_FAMILY = ".AppleSystemUIFont"

    @staticmethod
    def create_infopoint(parent, text):
        label = QLabel(" ℹ️ ")
        label.setFont(QFont(AuthGUI.FONT_FAMILY, 10))
        label.setStyleSheet(f"color: {COLORES['acento']}; border: none; background: transparent;")
        label.setToolTip(text)
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        return label

    @staticmethod
    def create_scrollable_area(parent_widget):
        scroll = QScrollArea(parent_widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {COLORES['bg_principal']}; }}
            QScrollBar:vertical {{ border: none; background: {COLORES['bg_principal']}; width: 8px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: {COLORES['bg_terciario']}; min-height: 20px; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}
        """)
        container = QWidget()
        container.setStyleSheet(f"background: {COLORES['bg_principal']};")
        scroll.setWidget(container)
        return scroll, container

    @staticmethod
    def setup_password_field(layout, label_text, placeholder):
        lbl = QLabel(label_text)
        lbl.setFont(QFont(AuthGUI.FONT_FAMILY, 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {COLORES['fg_secundario']};")
        layout.addWidget(lbl)

        h_lay = QHBoxLayout()
        h_lay.setSpacing(0)
        
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFont(QFont(AuthGUI.FONT_FAMILY, 10))
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setStyleSheet(f"""
            QLineEdit {{ 
                background: {COLORES['bg_terciario']}; color: white; padding: 10px; 
                border-top-left-radius: 6px; border-bottom-left-radius: 6px; 
                border: 1px solid transparent; border-right: none;
            }}
            QLineEdit:focus {{ border: 1px solid {COLORES['acento']}; border-right: none; }}
        """)
        
        btn_toggle = QPushButton("👁️")
        btn_toggle.setFixedSize(40, 42) # Ajustar a la altura del QLineEdit
        btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_toggle.setStyleSheet(f"""
            QPushButton {{ 
                background: {COLORES['bg_terciario']}; border: 1px solid transparent; border-left: none;
                border-top-right-radius: 6px; border-bottom-right-radius: 6px;
                color: {COLORES['fg_secundario']}; font-size: 14px;
            }}
            QPushButton:hover {{ color: {COLORES['acento']}; }}
        """)
        
        def toggle():
            if edit.echoMode() == QLineEdit.EchoMode.Password:
                edit.setEchoMode(QLineEdit.EchoMode.Normal)
                btn_toggle.setText("🙈")
            else:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
                btn_toggle.setText("👁️")
        
        btn_toggle.clicked.connect(toggle)
        
        h_lay.addWidget(edit)
        h_lay.addWidget(btn_toggle)
        layout.addLayout(h_lay)
        return edit

    @staticmethod
    def init_login_tab(app):
        scroll, container = AuthGUI.create_scrollable_area(app.login_tab)
        if hasattr(app.login_tab, "layout") and app.login_tab.layout():
            layout = app.login_tab.layout()
            while layout.count():
                layout.itemAt(0).widget().setParent(None)
            layout.addWidget(scroll)
        else:
            layout = QVBoxLayout(app.login_tab)
            layout.addWidget(scroll)
        
        layout.setContentsMargins(0, 0, 0, 0)
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(40, 30, 40, 30)
        inner_layout.setSpacing(12)

        # Usuario
        lbl_user = QLabel("Usuario")
        lbl_user.setFont(QFont(AuthGUI.FONT_FAMILY, 11, QFont.Weight.Bold))
        lbl_user.setStyleSheet(f"color: {COLORES['fg_secundario']};")
        inner_layout.addWidget(lbl_user)
        
        app.login_username = QLineEdit()
        app.login_username.setPlaceholderText("Tu nombre de usuario")
        app.login_username.setFont(QFont(AuthGUI.FONT_FAMILY, 10))
        app.login_username.setStyleSheet(f"""
            QLineEdit {{ 
                background: {COLORES['bg_terciario']}; color: white; padding: 12px; 
                border-radius: 8px; border: 1px solid transparent;
            }}
            QLineEdit:focus {{ border: 1px solid {COLORES['acento']}; }}
        """)
        inner_layout.addWidget(app.login_username)
        
        # Contraseña
        app.login_password = AuthGUI.setup_password_field(inner_layout, "Contraseña", "••••••••")
        
        app.login_remember = QCheckBox("Recordar mi cuenta")
        app.login_remember.setFont(QFont(AuthGUI.FONT_FAMILY, 9))
        app.login_remember.setStyleSheet(f"color: {COLORES['fg_secundario']}; margin-top: 5px;")
        inner_layout.addWidget(app.login_remember)

        inner_layout.addSpacing(25)
        btn_login = QPushButton("INICIAR SESIÓN")
        btn_login.setFont(QFont(AuthGUI.FONT_FAMILY, 12, QFont.Weight.Bold))
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setStyleSheet(f"""
            QPushButton {{ 
                background: {COLORES['acento']}; color: white; padding: 14px; 
                border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: {COLORES['acento_hover']}; }}
        """)
        btn_login.clicked.connect(lambda: login(app))
        inner_layout.addWidget(btn_login)

        def _login_facial():
            from .facial_auth import FacialLoginDialog
            def _on_facial_success(user_data):
                app.hide()
                app.cargar_aplicacion(user_data["usuario"], user_data["persona"], user_data.get("avatar", ""))
            dialog = FacialLoginDialog(app, COLORES, _on_facial_success)
            dialog.exec()

        btn_facial = QPushButton("📷 INICIAR SESIÓN CON ROSTRO")
        btn_facial.setFont(QFont(AuthGUI.FONT_FAMILY, 10, QFont.Weight.Bold))
        btn_facial.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_facial.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; color: {COLORES['acento']}; padding: 10px; 
                border-radius: 8px; border: 1px solid {COLORES['acento']}; margin-top: 8px;
            }}
            QPushButton:hover {{ background: {COLORES['acento']}; color: white; }}
        """)
        btn_facial.clicked.connect(_login_facial)
        inner_layout.addWidget(btn_facial)

        inner_layout.addStretch()

    @staticmethod
    def init_register_tab(app):
        scroll, container = AuthGUI.create_scrollable_area(app.register_tab)
        if app.register_tab.layout():
            layout = app.register_tab.layout()
            while layout.count(): layout.itemAt(0).widget().setParent(None)
            layout.addWidget(scroll)
        else:
            layout = QVBoxLayout(app.register_tab)
            layout.addWidget(scroll)
        
        layout.setContentsMargins(0, 0, 0, 0)
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(40, 30, 40, 30)
        inner_layout.setSpacing(12)

        # SECCIÓN AVATAR CIRCULAR
        lbl_av = QLabel("PERSONALIZAR PERFIL")
        lbl_av.setFont(QFont(AuthGUI.FONT_FAMILY, 11, QFont.Weight.Bold))
        lbl_av.setStyleSheet(f"color: {COLORES['acento']}; letter-spacing: 1px;")
        inner_layout.addWidget(lbl_av)
        
        av_h = QHBoxLayout()
        av_h.setSpacing(20)
        app.avatar_preview = QLabel()
        app.avatar_preview.setFixedSize(80, 80)
        app.avatar_preview.setStyleSheet(f"background: {COLORES['bg_terciario']}; border-radius: 40px; border: 2px solid {COLORES['acento']};")
        av_h.addWidget(app.avatar_preview)
        
        app.avatar_image = None
        
        btn_av = QPushButton("Elegir Imagen")
        btn_av.setFont(QFont(AuthGUI.FONT_FAMILY, 9, QFont.Weight.Bold))
        btn_av.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_av.setStyleSheet(f"""
            QPushButton {{ 
                background: {COLORES['bg_terciario']}; color: {COLORES['fg_principal']}; 
                border-radius: 6px; padding: 10px 15px; border: 1px solid {COLORES['bg_terciario']};
            }}
            QPushButton:hover {{ background: transparent; border-color: {COLORES['acento']}; }}
        """)
        btn_av.clicked.connect(lambda: AuthGUI._solicitar_avatar(app))
        av_h.addWidget(btn_av)
        
        app.btn_change_shape = QPushButton("Cambiar Forma")
        app.btn_change_shape.setFont(QFont(AuthGUI.FONT_FAMILY, 9))
        app.btn_change_shape.setCursor(Qt.CursorShape.PointingHandCursor)
        app.btn_change_shape.setVisible(False)
        app.btn_change_shape.setStyleSheet(f"color: {COLORES['acento']}; background: transparent; border: none; text-decoration: underline;")
        app.btn_change_shape.clicked.connect(lambda: AuthGUI._reabrir_editor_forma(app))
        av_h.addWidget(app.btn_change_shape)
        
        av_h.addStretch()
        inner_layout.addLayout(av_h)
        
        inner_layout.addSpacing(10)

        # Campos
        campos = [
            ("register_persona", "Nombre Real", "Ej: Luna"),
            ("register_username", "Usuario", "Ej: luna_dev"),
            ("register_password", "Contraseña", "••••••••"),
            ("register_confirm", "Confirmar Contraseña", "••••••••")
        ]

        for attr, label_text, placeholder in campos:
            if "password" in attr or "confirm" in attr:
                edit = AuthGUI.setup_password_field(inner_layout, label_text, placeholder)
            else:
                lbl = QLabel(label_text)
                lbl.setFont(QFont(AuthGUI.FONT_FAMILY, 10, QFont.Weight.Bold))
                lbl.setStyleSheet(f"color: {COLORES['fg_secundario']};")
                inner_layout.addWidget(lbl)
                
                edit = QLineEdit()
                edit.setPlaceholderText(placeholder)
                edit.setFont(QFont(AuthGUI.FONT_FAMILY, 10))
                edit.setStyleSheet(f"""
                    QLineEdit {{ 
                        background: {COLORES['bg_terciario']}; color: white; padding: 10px; 
                        border-radius: 6px; border: 1px solid transparent;
                    }}
                    QLineEdit:focus {{ border: 1px solid {COLORES['acento']}; }}
                """)
                inner_layout.addWidget(edit)
                
            setattr(app, attr, edit)
            
            if attr == "register_username":
                edit.textChanged.connect(lambda: AuthGUI._update_avatar_preview(app))

        inner_layout.addSpacing(20)
        btn_reg = QPushButton("CREAR CUENTA")
        btn_reg.setFont(QFont(AuthGUI.FONT_FAMILY, 12, QFont.Weight.Bold))
        btn_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reg.setStyleSheet(f"""
            QPushButton {{ 
                background: {COLORES['exito']}; color: white; padding: 14px; 
                border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: #2EB886; }}
        """)
        btn_reg.clicked.connect(lambda: register(app))
        inner_layout.addWidget(btn_reg)
        inner_layout.addStretch()
        
        AuthGUI._update_avatar_preview(app)

    @staticmethod
    def _update_avatar_preview(app):
        if app.avatar_image: return
        usr = app.register_username.text()
        initial = usr[0].upper() if usr else "?"
        pix = AvatarUtils.get_initials_avatar(initial, size=80, bg_color=COLORES['acento'])
        app.avatar_preview.setPixmap(pix)

    @staticmethod
    def _solicitar_avatar(app):
        selector = SelectorAvatar(app, 
            on_pixel_art_callback=lambda: AuthGUI._abrir_editor_pixel(app),
            on_desktop_callback=lambda: AuthGUI._seleccionar_del_escritorio(app),
            colores=COLORES)
        selector.show()

    @staticmethod
    def _seleccionar_del_escritorio(app):
        from vistas.utils.img_editor import ImageEditorDialog
        fn, _ = QFileDialog.getOpenFileName(app, "Elegir Avatar", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)")
        if fn:
            def on_crop_save(img_pil, shape):
                app.avatar_image = img_pil
                app.avatar_shape = shape
                import io
                byte_arr = io.BytesIO()
                img_pil.save(byte_arr, format='PNG')
                qpix = QPixmap()
                qpix.loadFromData(byte_arr.getvalue())
                AuthGUI._update_avatar_preview_image(app, qpix, shape)
                app.btn_change_shape.setVisible(True)
                app.last_avatar_path = fn # Guardar para re-editar si es necesario

            ed = ImageEditorDialog(app, fn, on_crop_save, COLORES)
            ed.exec()

    @staticmethod
    def _reabrir_editor_forma(app):
        if hasattr(app, 'last_avatar_path') and app.last_avatar_path:
            AuthGUI._seleccionar_del_escritorio(app)

    @staticmethod
    def _update_avatar_preview_image(app, qpix, shape="circle"):
        if shape == "circle":
            from vistas.utils.avatar import AvatarUtils
            processed = AvatarUtils.get_circular_pixmap(qpix, size=80)
            app.avatar_preview.clearMask()
            app.avatar_preview.setPixmap(processed)
        else:
            app.avatar_preview.setPixmap(qpix.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            app.avatar_preview.clearMask()
            app.avatar_preview.setStyleSheet(f"background: {COLORES['bg_terciario']}; border-radius: 8px; border: 2px solid {COLORES['acento']};")

    @staticmethod
    def _abrir_editor_pixel(app):
        from controlador.utils.avatar import AvatarEditor
        def on_save(img):
            import io
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='PNG')
            qpix = QPixmap()
            qpix.loadFromData(byte_arr.getvalue())
            app.avatar_image = img
            AuthGUI._update_avatar_preview_image(app, qpix)
        ed = AvatarEditor(app, on_save)
        ed.show()
