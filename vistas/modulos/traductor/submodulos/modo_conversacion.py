import os
import time
import datetime
import platform
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QScrollArea, QFrame, QComboBox, QFileDialog, 
    QMessageBox, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

class WhatsAppBubble(QFrame):
    """Burbuja de mensaje con diseño y estética idéntica a WhatsApp (Dark Mode)."""
    def __init__(self, emisor, idioma_orig, idioma_dest, texto_orig, texto_trad, colores=None, tts_callback=None, parent=None):
        super().__init__(parent)
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.emisor = emisor
        self.idioma_orig = idioma_orig
        self.idioma_dest = idioma_dest
        self.texto_orig = texto_orig
        self.texto_trad = texto_trad
        self.tts_callback = tts_callback

        is_a = (emisor == "A")
        # Colores oficiales de WhatsApp Web / Desktop (Modo Oscuro)
        bg_bubble = "#005C4B" if is_a else "#202C33"      # Verde WhatsApp (enviado) vs Gris WhatsApp (recibido)
        tag_color = "#25D366" if is_a else "#53BDEB"      # Verde vibrante A vs Celeste B
        quote_border = "#25D366" if is_a else "#34B7F1"
        radius_corner = "border-top-right-radius: 2px;" if is_a else "border-top-left-radius: 2px;"

        self.setMinimumWidth(260)
        self.setMaximumWidth(580)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self.setStyleSheet(f"""
            QFrame#WhatsAppBubble {{
                background-color: {bg_bubble};
                border-radius: 10px;
                {radius_corner}
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        self.setObjectName("WhatsAppBubble")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        # Header de la burbuja (Interlocutor y dirección)
        top = QHBoxLayout()
        top.setSpacing(6)
        icon = "👤 Persona A" if is_a else "👥 Persona B"
        lbl_who = QLabel(f"{icon}  •  {idioma_orig.upper()} ➔ {idioma_dest.upper()}")
        lbl_who.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        lbl_who.setStyleSheet(f"color: {tag_color}; background: transparent; border: none;")
        top.addWidget(lbl_who)
        top.addStretch()

        lay.addLayout(top)

        # Texto original (Mensaje escrito)
        lbl_orig = QLabel(texto_orig)
        lbl_orig.setWordWrap(True)
        lbl_orig.setFont(QFont(self.font_family, 10))
        lbl_orig.setStyleSheet("color: #E9EDEF; background: transparent; border: none; line-height: 1.3;")
        lay.addWidget(lbl_orig)

        # Tarjeta de Traducción Simultánea (Estilo Caja de Cita de WhatsApp)
        self.quote_box = QFrame()
        self.quote_box.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.22);
                border-left: 3px solid {quote_border};
                border-radius: 6px;
                padding: 4px;
            }}
        """)
        quote_lay = QHBoxLayout(self.quote_box)
        quote_lay.setContentsMargins(8, 6, 8, 6)
        quote_lay.setSpacing(8)

        quote_text_lay = QVBoxLayout()
        quote_text_lay.setSpacing(2)

        lbl_trad_tag = QLabel(f"🌐 TRADUCCIÓN ({idioma_dest.upper()}):")
        lbl_trad_tag.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
        lbl_trad_tag.setStyleSheet(f"color: {tag_color}; background: transparent; border: none;")
        quote_text_lay.addWidget(lbl_trad_tag)

        self.lbl_trad = QLabel()
        self.lbl_trad.setWordWrap(True)
        self.lbl_trad.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        quote_text_lay.addWidget(self.lbl_trad)
        quote_lay.addLayout(quote_text_lay, 1)

        # Botón de Pronunciación TTS
        self.btn_speak = QPushButton("🔊")
        self.btn_speak.setFixedSize(28, 28)
        self.btn_speak.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_speak.setToolTip("Escuchar pronunciación")
        self.btn_speak.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                border: none;
                font-size: 13px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }
        """)
        self.btn_speak.clicked.connect(self._reproducir_audio)
        quote_lay.addWidget(self.btn_speak, 0, Qt.AlignmentFlag.AlignCenter)

        self._actualizar_texto_trad_ui(texto_trad)
        lay.addWidget(self.quote_box)

        # Footer con hora y ticks azules (estilo WhatsApp)
        footer = QHBoxLayout()
        footer.setSpacing(4)
        footer.addStretch()

        ts = datetime.datetime.now().strftime("%H:%M")
        lbl_time = QLabel(ts)
        lbl_time.setFont(QFont(self.font_family, 7))
        lbl_time.setStyleSheet("color: #8696A0; background: transparent; border: none;")
        footer.addWidget(lbl_time)

        lbl_checks = QLabel("✓✓")
        lbl_checks.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        check_color = "#53BDEB" if is_a else "#8696A0"  # Check azul WhatsApp
        lbl_checks.setStyleSheet(f"color: {check_color}; background: transparent; border: none;")
        footer.addWidget(lbl_checks)

        lay.addLayout(footer)

    def _actualizar_texto_trad_ui(self, texto_trad):
        if texto_trad == "⏳ Traduciendo...":
            self.lbl_trad.setText("⏳ Traduciendo...")
            self.lbl_trad.setStyleSheet("color: #FBBF24; font-style: italic; background: transparent; border: none;")
            self.btn_speak.setVisible(False)
        else:
            self.lbl_trad.setText(texto_trad)
            self.lbl_trad.setStyleSheet("color: #FFFFFF; font-style: normal; background: transparent; border: none;")
            self.btn_speak.setVisible(True)

    def actualizar_traduccion(self, texto_trad, idioma_dest):
        self.texto_trad = texto_trad
        self.idioma_dest = idioma_dest
        self._actualizar_texto_trad_ui(texto_trad)

    def _reproducir_audio(self):
        if self.tts_callback and self.texto_trad and self.texto_trad != "⏳ Traduciendo...":
            self.tts_callback(self.texto_trad, self.idioma_dest)


class WhatsAppBubbleRow(QWidget):
    """Fila que alinea la burbuja a la derecha (Persona A) o a la izquierda (Persona B)."""
    def __init__(self, bubble, emisor, parent=None):
        super().__init__(parent)
        self.bubble = bubble
        self.emisor = emisor
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.setSpacing(0)

        if emisor == "A":
            lay.addStretch(1)
            lay.addWidget(bubble, 0)
        else:
            lay.addWidget(bubble, 0)
            lay.addStretch(1)


class ModoConversacionSubmodule(QWidget):
    """Submódulo 5: Modo Conversación Bilingüe / Diálogo con diseño WhatsApp Web"""
    traduccion_completada_signal = pyqtSignal(object, str, str)  # bubble, texto_trad, dest_lang

    def __init__(self, parent=None, context=None, manager=None, colores=None, callbacks=None):
        super().__init__(parent)
        self.context = context
        self.manager = manager
        self.colores = colores or {}
        self.callbacks = callbacks or {}
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        self.mensajes_dialogo = []

        self.traduccion_completada_signal.connect(self._on_traduccion_completada)

        self.inicializar_ui()

    def inicializar_ui(self):
        # Paleta WhatsApp Dark Mode
        self.wa_bg = "#0B141A"        # Fondo del chat de WhatsApp
        self.wa_header = "#202C33"    # Fondo de barras superiores e inferiores
        self.wa_card = "#111B21"      # Fondo de paneles secundarios
        self.wa_green = "#00A884"     # Verde principal de WhatsApp
        self.wa_green_hover = "#06CF9C"
        self.wa_input_bg = "#2A3942"  # Fondo de campos de entrada redondeados
        self.wa_text = "#E9EDEF"      # Texto principal
        self.wa_subtext = "#8696A0"   # Texto secundario

        self.setStyleSheet(f"background-color: {self.wa_bg}; color: {self.wa_text};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Barra Superior de WhatsApp ──────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.wa_header};
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(16, 10, 16, 10)
        top_lay.setSpacing(12)

        # Avatar / Icono WhatsApp
        icon_wa = QLabel("💬")
        icon_wa.setFont(QFont(self.font_family, 16))
        top_lay.addWidget(icon_wa)

        title_lay = QVBoxLayout()
        title_lay.setSpacing(1)
        lbl_title = QLabel("Conversación Bilingüe en Tiempo Real")
        lbl_title.setFont(QFont(self.font_family, 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {self.wa_text};")
        title_lay.addWidget(lbl_title)

        lbl_status = QLabel("🟢 En línea • Traducción simultánea asistida")
        lbl_status.setFont(QFont(self.font_family, 8))
        lbl_status.setStyleSheet("color: #00A884;")
        title_lay.addWidget(lbl_status)
        top_lay.addLayout(title_lay)

        top_lay.addStretch()

        btn_export = QPushButton("💾 Guardar Chat")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.wa_input_bg};
                color: {self.wa_text};
                padding: 6px 14px;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """)
        btn_export.clicked.connect(self._exportar_transcripcion)
        top_lay.addWidget(btn_export)

        btn_clear = QPushButton("🗑️ Vaciar Chat")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        btn_clear.setStyleSheet(btn_export.styleSheet())
        btn_clear.clicked.connect(self._limpiar_conversacion)
        top_lay.addWidget(btn_clear)

        layout.addWidget(top_bar)

        # ── Barra de Selección de Idiomas (Estilo Pestaña de Configuración WhatsApp) ────
        bar_idiomas = QFrame()
        bar_idiomas.setStyleSheet(f"""
            QFrame {{
                background-color: {self.wa_card};
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        b_lay = QHBoxLayout(bar_idiomas)
        b_lay.setContentsMargins(16, 8, 16, 8)
        b_lay.setSpacing(10)

        lbl_a = QLabel("👤 Persona A:")
        lbl_a.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_a.setStyleSheet("color: #25D366;")
        b_lay.addWidget(lbl_a)

        self.combo_lang_a = QComboBox()
        self.combo_lang_a.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.wa_input_bg};
                color: {self.wa_text};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 11px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.wa_header};
                color: white;
                selection-background-color: {self.wa_green};
            }}
        """)
        idiomas_lista = self.manager.obtener_lista_formatada(incluir_auto=False) if self.manager else []
        self.combo_lang_a.addItems(idiomas_lista)
        self._set_combo_code(self.combo_lang_a, "es")
        b_lay.addWidget(self.combo_lang_a, 1)

        btn_swap_dialog = QPushButton("⇄")
        btn_swap_dialog.setFixedSize(34, 28)
        btn_swap_dialog.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_swap_dialog.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        btn_swap_dialog.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.wa_input_bg};
                color: {self.wa_text};
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QPushButton:hover {{
                background-color: {self.wa_green};
                color: white;
            }}
        """)
        btn_swap_dialog.clicked.connect(self._intercambiar_idiomas)
        b_lay.addWidget(btn_swap_dialog)

        lbl_b = QLabel("👥 Persona B:")
        lbl_b.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_b.setStyleSheet("color: #53BDEB;")
        b_lay.addWidget(lbl_b)

        self.combo_lang_b = QComboBox()
        self.combo_lang_b.setStyleSheet(self.combo_lang_a.styleSheet())
        self.combo_lang_b.addItems(idiomas_lista)
        self._set_combo_code(self.combo_lang_b, "en")
        b_lay.addWidget(self.combo_lang_b, 1)

        layout.addWidget(bar_idiomas)

        # ── Área Central de Mensajes (Chat Wallpaper WhatsApp) ───────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.wa_bg};
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.35);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet(f"background-color: {self.wa_bg};")
        self.chat_lay = QVBoxLayout(self.chat_container)
        self.chat_lay.setContentsMargins(12, 12, 12, 12)
        self.chat_lay.setSpacing(6)

        # Mensaje de bienvenida tipo WhatsApp (caja flotante)
        self.lbl_vacio = QLabel("🔒 Los mensajes se traducen automáticamente de extremo a extremo.\nEscribe en el panel inferior para chatear entre Persona A y Persona B.")
        self.lbl_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio.setFont(QFont(self.font_family, 9))
        self.lbl_vacio.setStyleSheet("""
            QLabel {
                background-color: #182229;
                color: #FFEECD;
                border-radius: 8px;
                padding: 12px 18px;
                margin: 20px 60px;
                line-height: 1.4;
            }
        """)
        self.chat_lay.addWidget(self.lbl_vacio)

        self.chat_lay.addStretch()

        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll, 1)

        # ── Barra Inferior de Entrada (Doble Input WhatsApp) ────────────────────
        bottom_panel = QFrame()
        bottom_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {self.wa_header};
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)
        bottom_lay = QHBoxLayout(bottom_panel)
        bottom_lay.setContentsMargins(14, 10, 14, 10)
        bottom_lay.setSpacing(14)

        # Panel Input Persona A
        a_container = QHBoxLayout()
        a_container.setSpacing(6)

        self.inp_a = QLineEdit()
        self.inp_a.setPlaceholderText("Persona A: escribe un mensaje...")
        self.inp_a.setFont(QFont(self.font_family, 9))
        self.inp_a.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.wa_input_bg};
                color: {self.wa_text};
                border-radius: 18px;
                padding: 8px 14px;
                border: 1px solid rgba(37, 211, 102, 0.3);
            }}
            QLineEdit:focus {{
                border: 1px solid #25D366;
            }}
        """)
        self.inp_a.returnPressed.connect(self._enviar_mensaje_a)
        a_container.addWidget(self.inp_a, 1)

        btn_send_a = QPushButton("➤")
        btn_send_a.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        btn_send_a.setFixedSize(36, 36)
        btn_send_a.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send_a.setToolTip("Enviar mensaje de Persona A")
        btn_send_a.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.wa_green};
                color: white;
                border-radius: 18px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.wa_green_hover};
            }}
        """)
        btn_send_a.clicked.connect(self._enviar_mensaje_a)
        a_container.addWidget(btn_send_a)
        bottom_lay.addLayout(a_container, 1)

        # Separador vertical fino entre usuarios
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.1);")
        bottom_lay.addWidget(sep)

        # Panel Input Persona B
        b_container = QHBoxLayout()
        b_container.setSpacing(6)

        self.inp_b = QLineEdit()
        self.inp_b.setPlaceholderText("Persona B: escribe un mensaje...")
        self.inp_b.setFont(QFont(self.font_family, 9))
        self.inp_b.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.wa_input_bg};
                color: {self.wa_text};
                border-radius: 18px;
                padding: 8px 14px;
                border: 1px solid rgba(83, 189, 235, 0.3);
            }}
            QLineEdit:focus {{
                border: 1px solid #53BDEB;
            }}
        """)
        self.inp_b.returnPressed.connect(self._enviar_mensaje_b)
        b_container.addWidget(self.inp_b, 1)

        btn_send_b = QPushButton("➤")
        btn_send_b.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        btn_send_b.setFixedSize(36, 36)
        btn_send_b.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send_b.setToolTip("Enviar mensaje de Persona B")
        btn_send_b.setStyleSheet(f"""
            QPushButton {{
                background-color: #027EB5;
                color: white;
                border-radius: 18px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #34B7F1;
            }}
        """)
        btn_send_b.clicked.connect(self._enviar_mensaje_b)
        b_container.addWidget(btn_send_b)
        bottom_lay.addLayout(b_container, 1)

        layout.addWidget(bottom_panel)

    def _set_combo_code(self, combo, target_code):
        for i in range(combo.count()):
            if f"({target_code})" in combo.itemText(i):
                combo.setCurrentIndex(i)
                break

    def _get_code(self, combo):
        txt = combo.currentText()
        if "(" in txt and ")" in txt:
            return txt.rsplit("(", 1)[1].rstrip(")")
        return "es"

    def _intercambiar_idiomas(self):
        txt_a = self.combo_lang_a.currentText()
        txt_b = self.combo_lang_b.currentText()

        for i in range(self.combo_lang_a.count()):
            if self.combo_lang_a.itemText(i) == txt_b:
                self.combo_lang_a.setCurrentIndex(i)
                break
        for i in range(self.combo_lang_b.count()):
            if self.combo_lang_b.itemText(i) == txt_a:
                self.combo_lang_b.setCurrentIndex(i)
                break

    def _enviar_mensaje_a(self):
        txt = self.inp_a.text().strip()
        if not txt:
            return
        self.inp_a.clear()
        lang_a = self._get_code(self.combo_lang_a)
        lang_b = self._get_code(self.combo_lang_b)
        self._crear_y_procesar_mensaje("A", txt, lang_a, lang_b)

    def _enviar_mensaje_b(self):
        txt = self.inp_b.text().strip()
        if not txt:
            return
        self.inp_b.clear()
        lang_a = self._get_code(self.combo_lang_a)
        lang_b = self._get_code(self.combo_lang_b)
        self._crear_y_procesar_mensaje("B", txt, lang_b, lang_a)

    def _crear_y_procesar_mensaje(self, emisor, texto, src_lang, dest_lang):
        """Crea la burbuja en WhatsApp con alineación correspondiente e inicia traducción."""
        if hasattr(self, 'lbl_vacio'):
            self.lbl_vacio.hide()

        bubble = WhatsAppBubble(
            emisor, src_lang, dest_lang, texto, "⏳ Traduciendo...", 
            self.colores, tts_callback=self._pronunciar_texto
        )
        row = WhatsAppBubbleRow(bubble, emisor)

        msg_data = {
            "emisor": emisor,
            "origen": src_lang,
            "destino": dest_lang,
            "texto_original": texto,
            "texto_traducido": "⏳ Traduciendo...",
            "hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bubble": bubble,
            "row": row
        }
        self.mensajes_dialogo.append(msg_data)

        # Insertar antes del stretch final
        idx = max(0, self.chat_lay.count() - 1)
        self.chat_lay.insertWidget(idx, row)
        self._scroll_abajo()

        # Ejecutar traducción asíncrona
        def worker():
            trad = ""
            try:
                if hasattr(self.manager, "traducir_sincrono"):
                    trad = self.manager.traducir_sincrono(texto, src_lang, dest_lang)
                elif hasattr(self.manager, "_traducir_sincrono"):
                    trad = self.manager._traducir_sincrono(texto, src_lang, dest_lang)
                elif hasattr(self.manager, "_traducir_online_robusto"):
                    trad = self.manager._traducir_online_robusto(texto, src_lang, dest_lang)
                elif hasattr(self.manager, "traducir_palabra_por_palabra"):
                    trad = self.manager.traducir_palabra_por_palabra(texto, src_lang, dest_lang)
                else:
                    trad = texto
            except Exception as e:
                trad = f"[Error: {str(e)}]"

            if not trad:
                trad = texto

            self.traduccion_completada_signal.emit(bubble, trad, dest_lang)

        threading.Thread(target=worker, daemon=True).start()

    def _on_traduccion_completada(self, bubble, trad, dest_lang):
        """Actualización segura en el hilo de interfaz."""
        if bubble:
            bubble.actualizar_traduccion(trad, dest_lang)

        for m in self.mensajes_dialogo:
            if m.get("bubble") is bubble:
                m["texto_traducido"] = trad
                break

        self._scroll_abajo()

    def _agregar_burbuja(self, emisor, src_lang, dest_lang, texto_orig, texto_trad):
        """Método compatible para tests o adición directa."""
        if hasattr(self, 'lbl_vacio'):
            self.lbl_vacio.hide()

        bubble = WhatsAppBubble(
            emisor, src_lang, dest_lang, texto_orig, texto_trad, 
            self.colores, tts_callback=self._pronunciar_texto
        )
        row = WhatsAppBubbleRow(bubble, emisor)

        msg_data = {
            "emisor": emisor,
            "origen": src_lang,
            "destino": dest_lang,
            "texto_original": texto_orig,
            "texto_traducido": texto_trad,
            "hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bubble": bubble,
            "row": row
        }
        self.mensajes_dialogo.append(msg_data)

        idx = max(0, self.chat_lay.count() - 1)
        self.chat_lay.insertWidget(idx, row)
        self._scroll_abajo()

    def _scroll_abajo(self):
        QTimer.singleShot(20, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def _pronunciar_texto(self, texto, lang):
        if hasattr(self.manager, "pronunciar"):
            self.manager.pronunciar(texto, lang)

    def _limpiar_conversacion(self):
        for i in reversed(range(self.chat_lay.count())):
            item = self.chat_lay.itemAt(i)
            if item:
                w = item.widget()
                if isinstance(w, WhatsAppBubbleRow):
                    w.deleteLater()
        self.mensajes_dialogo.clear()
        if hasattr(self, 'lbl_vacio'):
            self.lbl_vacio.show()

    def _exportar_transcripcion(self):
        if not self.mensajes_dialogo:
            QMessageBox.information(self, "Chat Vacío", "No hay mensajes en la conversación para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Diálogo de WhatsApp", str(Path.home() / "conversacion_whatsapp.txt"),
            "Archivos de Texto (*.txt)"
        )
        if path:
            lineas = [
                "===========================================================",
                "      CHAT DE CONVERSACIÓN BILINGÜE (WHATSAPP)",
                f"      Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "===========================================================\n"
            ]
            for m in self.mensajes_dialogo:
                who = "Persona A" if m["emisor"] == "A" else "Persona B"
                lineas.append(f"[{m['hora']}] {who} ({m['origen'].upper()} ➔ {m['destino'].upper()}):")
                lineas.append(f"  Mensaje original: {m['texto_original']}")
                lineas.append(f"  Traducción:       {m['texto_traducido']}\n")

            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lineas))
                QMessageBox.information(self, "Exportación Exitosa", f"Transcripción guardada en:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")

    def actualizar_tema(self, colores: dict):
        # Mantiene la coherencia visual WhatsApp dark mode
        pass

    def cleanup(self):
        pass
