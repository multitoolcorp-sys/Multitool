import re
from PyQt6.QtGui import QColor, QTextCharFormat, QFont, QTextCursor

class AnsiParser:
    """Parseador avanzado de secuencias de escape ANSI para PyQt6 (8/16 colores, 256 colores y RGB TrueColor)"""
    def __init__(self, default_fg="#10B981", default_bg="#07090e"):
        self.default_fg = QColor(default_fg)
        self.default_bg = QColor(default_bg)
        
        # Mapeo de 16 colores ANSI estándar
        self.standard_colors = {
            '30': QColor('#000000'), '31': QColor('#EF4444'), '32': QColor('#10B981'), '33': QColor('#F59E0B'),
            '34': QColor('#3B82F6'), '35': QColor('#EC4899'), '36': QColor('#06B6D4'), '37': QColor('#E5E7EB'),
            '90': QColor('#6B7280'), '91': QColor('#F87171'), '92': QColor('#34D399'), '93': QColor('#FBBF24'),
            '94': QColor('#60A5FA'), '95': QColor('#F472B6'), '96': QColor('#22D3EE'), '97': QColor('#F9FAFB')
        }
        
        self.standard_bg_colors = {
            '40': QColor('#000000'), '41': QColor('#991B1B'), '42': QColor('#065F46'), '43': QColor('#92400E'),
            '44': QColor('#1E40AF'), '45': QColor('#831843'), '46': QColor('#155E75'), '47': QColor('#374151'),
            '100': QColor('#4B5563'), '101': QColor('#DC2626'), '102': QColor('#059669'), '103': QColor('#D97706'),
            '104': QColor('#2563EB'), '105': QColor('#DB2777'), '106': QColor('#0891B2'), '107': QColor('#F3F4F6')
        }

    def _ansi_256_color(self, code):
        """Convierte un índice de paleta 256 ANSI (0-255) a QColor"""
        try:
            n = int(code)
            if n < 16:
                palette_16 = [
                    '#000000', '#800000', '#008000', '#808000', '#000080', '#800080', '#008080', '#c0c0c0',
                    '#808080', '#ff0000', '#00ff00', '#ffff00', '#0000ff', '#ff00ff', '#00ffff', '#ffffff'
                ]
                return QColor(palette_16[n])
            elif 16 <= n <= 231:
                # Cubo 6x6x6 de color
                n -= 16
                r = (n // 36) * 51
                g = ((n % 36) // 6) * 51
                b = (n % 6) * 51
                return QColor(r, g, b)
            elif 232 <= n <= 255:
                # Escala de grises (24 niveles)
                gray = (n - 232) * 10 + 8
                return QColor(gray, gray, gray)
        except Exception:
            pass
        return self.default_fg

    def append_ansi_text(self, textbrowser, text, default_fg=None):
        """Procesa y añade texto codificado en ANSI al QTextBrowser en la posición del cursor actual"""
        if default_fg:
            fg_color = QColor(default_fg)
        else:
            fg_color = self.default_fg

        cursor = textbrowser.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Regex para secuencias ANSI
        parts = re.split(r'(?:\x1b|\033)\[([0-9;]*)m', text)

        current_format = QTextCharFormat()
        current_format.setForeground(fg_color)

        i = 0
        while i < len(parts):
            if i % 2 == 1:
                # Secuencia de escape
                seq = parts[i]
                codes = seq.split(';') if seq else ['0']
                
                idx = 0
                while idx < len(codes):
                    code = codes[idx]
                    if not code or code == '0':
                        # Reset total
                        current_format = QTextCharFormat()
                        current_format.setForeground(fg_color)
                    elif code == '1':
                        current_format.setFontWeight(QFont.Weight.Bold)
                    elif code == '3':
                        current_format.setFontItalic(True)
                    elif code == '4':
                        current_format.setFontUnderline(True)
                    elif code in self.standard_colors:
                        current_format.setForeground(self.standard_colors[code])
                    elif code in self.standard_bg_colors:
                        current_format.setBackground(self.standard_bg_colors[code])
                    elif code == '38' and idx + 2 < len(codes) and codes[idx + 1] == '5':
                        # 256 colores FG: 38;5;N
                        current_format.setForeground(self._ansi_256_color(codes[idx + 2]))
                        idx += 2
                    elif code == '48' and idx + 2 < len(codes) and codes[idx + 1] == '5':
                        # 256 colores BG: 48;5;N
                        current_format.setBackground(self._ansi_256_color(codes[idx + 2]))
                        idx += 2
                    elif code == '38' and idx + 4 < len(codes) and codes[idx + 1] == '2':
                        # TrueColor RGB FG: 38;2;R;G;B
                        try:
                            r, g, b = int(codes[idx + 2]), int(codes[idx + 3]), int(codes[idx + 4])
                            current_format.setForeground(QColor(r, g, b))
                        except Exception:
                            pass
                        idx += 4
                    elif code == '48' and idx + 4 < len(codes) and codes[idx + 1] == '2':
                        # TrueColor RGB BG: 48;2;R;G;B
                        try:
                            r, g, b = int(codes[idx + 2]), int(codes[idx + 3]), int(codes[idx + 4])
                            current_format.setBackground(QColor(r, g, b))
                        except Exception:
                            pass
                        idx += 4
                    idx += 1
            else:
                # Texto plano
                part = parts[i]
                if part:
                    clean_part = part.replace('\r\n', '\n').replace('\r', '\n')
                    cursor.insertText(clean_part, current_format)
            i += 1

        textbrowser.setTextCursor(cursor)
        textbrowser.moveCursor(QTextCursor.MoveOperation.End)
