"""
email_helpers.py - Componentes auxiliares para el cliente de correo de MultiTool (widgets de lista y worker IMAP)
"""

import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont


class EmailListItemWidget(QWidget):
    """Widget personalizado para items de correo en la lista."""
    def __init__(self, subject, sender, date, preview, colores):
        super().__init__()
        self.colores = colores
        
        # Layout principal del item
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        
        # Fila superior: Remitente y Fecha
        header_lay = QHBoxLayout()
        header_lay.setSpacing(5)
        
        # Limpiar y extraer nombre del remitente
        clean_sender = sender
        if " <" in sender:
            clean_sender = sender.split(" <")[0]
        clean_sender = clean_sender.replace('"', '').strip()
        if len(clean_sender) > 20:
            clean_sender = clean_sender[:18] + "..."
            
        lbl_sender = QLabel(clean_sender)
        lbl_sender.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_sender.setStyleSheet(f"color: {colores.get('acento', '#6366F1')}; border: none; background: transparent;")
        
        # Extraer fecha corta
        short_date = date
        if "," in date:
            parts = date.split(",")
            if len(parts) > 1:
                short_date = parts[1].strip()
        # Tomar los primeros 3 bloques (ej. "21 May 2026")
        date_blocks = short_date.split()
        if len(date_blocks) >= 3:
            short_date = f"{date_blocks[0]} {date_blocks[1]}"
            
        lbl_date = QLabel(short_date)
        lbl_date.setFont(QFont("Segoe UI", 8))
        lbl_date.setStyleSheet(f"color: {colores.get('fg_secundario', '#888')}; border: none; background: transparent;")
        
        header_lay.addWidget(lbl_sender, 1)
        header_lay.addWidget(lbl_date)
        
        # Asunto
        if len(subject) > 28:
            display_subject = subject[:26] + "..."
        else:
            display_subject = subject
            
        lbl_subject = QLabel(display_subject)
        lbl_subject.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_subject.setStyleSheet("color: white; border: none; background: transparent;")
        
        # Preview del cuerpo
        if len(preview) > 35:
            display_preview = preview[:33] + "..."
        else:
            display_preview = preview
        if not display_preview:
            display_preview = "(Sin vista previa)"
            
        lbl_preview = QLabel(display_preview)
        lbl_preview.setFont(QFont("Segoe UI", 8))
        lbl_preview.setStyleSheet(f"color: {colores.get('fg_secundario', '#8A94A6')}; border: none; background: transparent;")
        
        lay.addLayout(header_lay)
        lay.addWidget(lbl_subject)
        lay.addWidget(lbl_preview)


class EmailFetchThread(QThread):
    """Hilo para descargar correos en segundo plano (IMAP)."""
    emails_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, rem, pwd):
        super().__init__()
        self.rem = rem
        self.pwd = pwd.replace(" ", "")

    def run(self):
        try:
            import imaplib
            import email
            from email.header import decode_header
            
            # Conexión SSL segura a Gmail IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(self.rem, self.pwd)
            mail.select("INBOX")
            
            # Buscar correos
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                self.error_occurred.emit("No se pudo buscar en el buzón.")
                return
                
            mail_ids = messages[0].split()
            # Tomar los últimos 15 correos (más recientes)
            recent_ids = mail_ids[-15:]
            recent_ids.reverse() # Orden descendente: más nuevo a más antiguo
            
            fetched_emails = []
            for m_id in recent_ids:
                status, data = mail.fetch(m_id, "(RFC822)")
                if status != "OK":
                    continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Descodificar asunto
                subject = self.clean_header(msg.get("Subject", "(Sin Asunto)"))
                
                # Descodificar remitente
                sender = self.clean_header(msg.get("From", "Desconocido"))
                
                # Fecha
                date_str = msg.get("Date", "")
                
                # Cuerpo y Adjuntos
                body = ""
                html_body = ""
                attachments = []
                
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                decoded_filename, encoding = decode_header(filename)[0]
                                if isinstance(decoded_filename, bytes):
                                    filename = decoded_filename.decode(encoding or "utf-8", errors="replace")
                                attachments.append(filename)
                        else:
                            if content_type == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                                except: pass
                            elif content_type == "text/html":
                                try:
                                    html_body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                                except: pass
                else:
                    content_type = msg.get_content_type()
                    if content_type == "text/plain":
                        try:
                            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
                        except: pass
                    elif content_type == "text/html":
                        try:
                            html_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
                        except: pass
                
                final_body = html_body if html_body else body
                if not final_body:
                    final_body = "(Buzón: Mensaje sin texto legible)"
                
                # Preview del mensaje
                text_preview = body
                if not text_preview and html_body:
                    text_preview = re.sub(r'<[^>]+>', ' ', html_body)
                    text_preview = re.sub(r'\s+', ' ', text_preview)
                text_preview = text_preview.strip()[:80].replace('\n', ' ')
                
                fetched_emails.append({
                    "id": m_id.decode("utf-8"),
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "body": final_body,
                    "preview": text_preview,
                    "attachments": attachments
                })
                
            mail.close()
            mail.logout()
            self.emails_fetched.emit(fetched_emails)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def clean_header(self, header_val):
        if not header_val:
            return ""
        from email.header import decode_header
        try:
            parts = decode_header(header_val)
            decoded_parts = []
            for part, encoding in parts:
                if isinstance(part, bytes):
                    decoded_parts.append(part.decode(encoding or "utf-8", errors="replace"))
                else:
                    decoded_parts.append(str(part))
            return "".join(decoded_parts)
        except:
            return str(header_val)
