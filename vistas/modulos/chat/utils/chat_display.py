import os
import html
import base64
from pathlib import Path

from PyQt6.QtWidgets import QTextBrowser, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QStandardPaths
from PyQt6.QtGui import QFont, QTextCursor

class ChatDisplay(QTextBrowser):
    """Visualizador de Chat con estética idéntica a WhatsApp Web (Dark Mode) y soporte de Zoom"""
    zoom_changed = pyqtSignal(int)

    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.shared_files = {}  # {file_name: b64_data}

        self.zoom_level = 100
        self.base_font_size = 10
        self.setFont(QFont("Segoe UI", self.base_font_size))

        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self._handle_link)

        self.init_style()

    def init_style(self):
        # Paleta oficial WhatsApp Dark Mode (sin forzar font-size en px para permitir zoom suave)
        self.setStyleSheet("""
            QTextBrowser {
                background-color: #0B141A;
                border: none;
                color: #E9EDEF;
                padding: 6px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.35);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def zoom_in(self):
        """Aumenta el tamaño del texto del chat hasta un máximo de 200%"""
        if self.zoom_level < 200:
            self.zoomIn(1)
            self.zoom_level += 15
            self.zoom_changed.emit(self.zoom_level)

    def zoom_out(self):
        """Disminuye el tamaño del texto del chat hasta un mínimo de 70%"""
        if self.zoom_level > 70:
            self.zoomOut(1)
            self.zoom_level -= 15
            self.zoom_changed.emit(self.zoom_level)

    def reset_zoom(self):
        """Restablece el tamaño del texto al 100% normal"""
        steps = (self.zoom_level - 100) // 15
        if steps > 0:
            self.zoomOut(steps)
        elif steps < 0:
            self.zoomIn(-steps)
        self.zoom_level = 100
        self.zoom_changed.emit(self.zoom_level)

    def set_zoom(self, percent):
        """Ajusta directamente el porcentaje de zoom"""
        percent = max(70, min(200, int(percent)))
        target_steps = (percent - 100) // 15
        current_steps = (self.zoom_level - 100) // 15
        diff = target_steps - current_steps
        if diff > 0:
            self.zoomIn(diff)
        elif diff < 0:
            self.zoomOut(-diff)
        self.zoom_level = percent
        self.zoom_changed.emit(self.zoom_level)

    def wheelEvent(self, event):
        """Permite hacer zoom con Ctrl + Rueda del ratón"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Permite hacer zoom con atajos de teclado Ctrl + +, Ctrl + -, Ctrl + 0"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            key = event.key()
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_in()
                event.accept()
                return
            elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                self.zoom_out()
                event.accept()
                return
            elif key == Qt.Key.Key_0:
                self.reset_zoom()
                event.accept()
                return
        super().keyPressEvent(event)

    def clear_chat(self):
        self.clear()
        self.shared_files.clear()

    def add_system_message(self, text):
        escaped = html.escape(text)
        bubble_html = f"""
        <table width='100%' cellpadding='0' cellspacing='0' border='0'>
        <tr>
            <td align='center' style='padding: 6px 0;'>
                <div style='background-color: #182229; color: #FFEECD; border-radius: 8px; padding: 5px 14px; font-size: 0.82em; display: inline-block;'>
                    🔒 {escaped}
                </div>
            </td>
        </tr>
        </table>
        """
        self.append(bubble_html)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def add_message(self, usuario, text, ts, es_mio=False):
        self.agregar_mensaje({
            "tipo": "mensaje",
            "usuario": usuario,
            "mensaje": text,
            "timestamp": ts,
            "es_mio": es_mio
        })

    def add_image_message(self, usuario, img_b64, ts, es_mio=False, ext="png", es_sticker=False):
        self.agregar_mensaje({
            "tipo": "imagen",
            "usuario": usuario,
            "imagen": img_b64,
            "timestamp": ts,
            "es_mio": es_mio,
            "ext": ext,
            "es_sticker": es_sticker
        })

    def add_file_message(self, usuario, fname, fdata, ts, es_mio=False):
        self.agregar_mensaje({
            "tipo": "archivo",
            "usuario": usuario,
            "file_name": fname,
            "file_data": fdata,
            "timestamp": ts,
            "es_mio": es_mio
        })

    def get_html_content(self):
        return self.toHtml()

    def get_text_content(self):
        return self.toPlainText()

    def agregar_mensaje(self, msg):
        tipo = msg.get("tipo", "mensaje")
        usuario = msg.get("usuario", "Usuario")
        ts = msg.get("timestamp", "")
        es_mio = bool(msg.get("es_mio", False))

        # Color del remitente para mensajes recibidos
        color_nombre = "#FFD700" if "(Host)" in usuario else "#53BDEB"

        if tipo == "sistema":
            self.add_system_message(msg.get("mensaje", ""))
            return

        elif tipo == "mensaje":
            text = msg.get("mensaje", "")
            escaped = html.escape(text).replace("\n", "<br>")

            if es_mio:
                is_multiline = ("<br>" in escaped or len(text) > 35)
                if is_multiline:
                    body = f"<div style='font-size: 1.05em; color: #FFFFFF; line-height: 1.3;'>{escaped}</div><div style='text-align: right; font-size: 0.75em; color: #8696A0; margin-top: 3px;'>{ts} <span style='color: #53BDEB; font-weight: bold;'>✓✓</span></div>"
                else:
                    body = f"<span style='font-size: 1.05em; color: #FFFFFF;'>{escaped}</span><span style='font-size: 0.75em; color: #8696A0; margin-left: 10px; white-space: nowrap;'>{ts} <span style='color: #53BDEB; font-weight: bold;'>✓✓</span></span>"

                # Burbuja enviada (Derecha, verde WhatsApp #005C4B con ajuste de ancho al contenido)
                html_code = f"""
                <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                <tr>
                    <td width='25%'></td>
                    <td align='right' style='padding: 2px 6px;'>
                        <table cellpadding='0' cellspacing='0' border='0' bgcolor='#005C4B' style='border-radius: 10px; border-top-right-radius: 2px;'>
                        <tr>
                            <td style='padding: 6px 12px; color: #FFFFFF;'>
                                {body}
                            </td>
                        </tr>
                        </table>
                    </td>
                </tr>
                </table>
                """
            else:
                is_multiline = ("<br>" in escaped or len(text) > 35)
                header = f"<div style='font-size: 0.82em; font-weight: bold; color: {color_nombre}; margin-bottom: 2px;'>{html.escape(usuario)}</div>"
                if is_multiline:
                    body = f"{header}<div style='font-size: 1.05em; color: #E9EDEF; line-height: 1.3;'>{escaped}</div><div style='text-align: right; font-size: 0.75em; color: #8696A0; margin-top: 3px;'>{ts} <span style='color: #8696A0;'>✓✓</span></div>"
                else:
                    body = f"{header}<div><span style='font-size: 1.05em; color: #E9EDEF;'>{escaped}</span><span style='font-size: 0.75em; color: #8696A0; margin-left: 10px; white-space: nowrap;'>{ts} <span style='color: #8696A0;'>✓✓</span></span></div>"

                # Burbuja recibida (Izquierda, gris oscuro WhatsApp #202C33 con ajuste de ancho al contenido)
                html_code = f"""
                <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                <tr>
                    <td align='left' style='padding: 2px 6px;'>
                        <table cellpadding='0' cellspacing='0' border='0' bgcolor='#202C33' style='border-radius: 10px; border-top-left-radius: 2px;'>
                        <tr>
                            <td style='padding: 6px 12px; color: #E9EDEF;'>
                                {body}
                            </td>
                        </tr>
                        </table>
                    </td>
                    <td width='25%'></td>
                </tr>
                </table>
                """

        elif tipo == "imagen":
            img_b64 = msg.get("imagen", "")
            ext = msg.get("ext", "png")
            es_sticker = bool(msg.get("es_sticker", False))
            width = "120" if es_sticker else "240"
            bg_bubble = "#005C4B" if es_mio else "#202C33"
            check_str = "<span style='color: #53BDEB;'>✓✓</span>" if es_mio else "<span style='color: #8696A0;'>✓✓</span>"
            header_sender = f"<div style='font-size: 0.82em; font-weight: bold; color: {color_nombre}; margin-bottom: 4px;'>{html.escape(usuario)}</div>" if not es_mio else ""

            if es_mio:
                html_code = f"""
                <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                <tr>
                    <td width='25%'></td>
                    <td align='right' style='padding: 2px 6px;'>
                        <table cellpadding='0' cellspacing='0' border='0' bgcolor='{bg_bubble}' style='border-radius: 10px; border-top-right-radius: 2px;'>
                        <tr>
                            <td style='padding: 6px;'>
                                <div><img src="data:image/{ext};base64,{img_b64}" width="{width}" style="border-radius: 6px;" /></div>
                                <div style='text-align: right; font-size: 0.75em; color: #8696A0; margin-top: 3px;'>
                                    {ts} {check_str}
                                </div>
                            </td>
                        </tr>
                        </table>
                    </td>
                </tr>
                </table>
                """
            else:
                html_code = f"""
                <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                <tr>
                    <td align='left' style='padding: 2px 6px;'>
                        <table cellpadding='0' cellspacing='0' border='0' bgcolor='{bg_bubble}' style='border-radius: 10px; border-top-left-radius: 2px;'>
                        <tr>
                            <td style='padding: 6px;'>
                                {header_sender}
                                <div><img src="data:image/{ext};base64,{img_b64}" width="{width}" style="border-radius: 6px;" /></div>
                                <div style='text-align: right; font-size: 0.75em; color: #8696A0; margin-top: 3px;'>
                                    {ts} {check_str}
                                </div>
                            </td>
                        </tr>
                        </table>
                    </td>
                    <td width='25%'></td>
                </tr>
                </table>
                """

        elif tipo == "archivo":
            fname = msg.get("file_name", "archivo")
            fdata = msg.get("file_data", "")
            self.shared_files[fname] = fdata
            bg_bubble = "#005C4B" if es_mio else "#202C33"
            check_str = "<span style='color: #53BDEB;'>✓✓</span>" if es_mio else "<span style='color: #8696A0;'>✓✓</span>"
            header_sender = f"<div style='font-size: 0.82em; font-weight: bold; color: {color_nombre}; margin-bottom: 4px;'>{html.escape(usuario)}</div>" if not es_mio else ""

            content_html = f"""
                <div style='background-color: rgba(0,0,0,0.2); border-radius: 6px; padding: 8px 12px; margin-bottom: 2px;'>
                    <span style='color: white; font-weight: bold; font-size: 0.95em;'>📁 {html.escape(fname)}</span>
                    <br>
                    <a href="localfile:{html.escape(fname)}" style='color: #25D366; font-weight: bold; text-decoration: none; font-size: 0.82em;'>📥 Descargar Archivo</a>
                </div>
            """

            if es_mio:
                html_code = f"""
                <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                <tr>
                    <td width='25%'></td>
                    <td align='right' style='padding: 2px 6px;'>
                        <table cellpadding='0' cellspacing='0' border='0' bgcolor='{bg_bubble}' style='border-radius: 10px; border-top-right-radius: 2px;'>
                        <tr>
                            <td style='padding: 8px 12px;'>
                                {content_html}
                                <div style='text-align: right; font-size: 0.75em; color: #8696A0; margin-top: 3px;'>
                                    {ts} {check_str}
                                </div>
                            </td>
                        </tr>
                        </table>
                    </td>
                </tr>
                </table>
                """
            else:
                html_code = f"""
                <table width='100%' cellpadding='0' cellspacing='0' border='0'>
                <tr>
                    <td align='left' style='padding: 2px 6px;'>
                        <table cellpadding='0' cellspacing='0' border='0' bgcolor='{bg_bubble}' style='border-radius: 10px; border-top-left-radius: 2px;'>
                        <tr>
                            <td style='padding: 8px 12px;'>
                                {header_sender}
                                {content_html}
                                <div style='text-align: right; font-size: 0.75em; color: #8696A0; margin-top: 3px;'>
                                    {ts} {check_str}
                                </div>
                            </td>
                        </tr>
                        </table>
                    </td>
                    <td width='25%'></td>
                </tr>
                </table>
                """

        self.append(html_code)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def _handle_link(self, qurl):
        url_str = qurl.toString()
        if url_str.startswith("localfile:"):
            fname = url_str.split("localfile:")[1]
            b64_data = self.shared_files.get(fname)
            if b64_data:
                self.guardar_archivo_local(fname, b64_data)
            else:
                QMessageBox.warning(self, "Descarga", "El archivo ya no está disponible en memoria.")
        else:
            import webbrowser
            webbrowser.open(url_str)

    def guardar_archivo_local(self, filename, base64_str):
        docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        default_path = os.path.join(docs_dir, filename)

        path, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo Compartido", default_path, "Todos los Archivos (*.*)")
        if not path:
            return

        try:
            file_bytes = base64.b64decode(base64_str)
            with open(path, "wb") as f:
                f.write(file_bytes)
            QMessageBox.information(self, "Éxito", f"Archivo guardado correctamente en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo:\n{e}")

    def actualizar_tema(self, colores=None):
        self.init_style()
