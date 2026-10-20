from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
from PyQt6.QtCore import Qt

class FormatManager:
    def __init__(self, editor, colores, status_callback=None, stats_callback=None):
        self.editor = editor
        self.colores = colores
        self.status_callback = status_callback
        self.stats_callback = stats_callback

    def aplicar_formato(self, tipo):
        """Aplica formato visual preservando otros atributos (tamaño, color, etc)"""
        cursor = self.editor.textCursor()
        current_fmt = cursor.charFormat()
        new_fmt = QTextCharFormat()
        
        if tipo == "negrita":
            is_bold = current_fmt.fontWeight() == QFont.Weight.Bold
            new_fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        elif tipo == "cursiva":
            new_fmt.setFontItalic(not current_fmt.fontItalic())
        elif tipo == "subrayado":
            new_fmt.setFontUnderline(not current_fmt.fontUnderline())
        elif tipo == "tachado":
            new_fmt.setFontStrikeOut(not current_fmt.fontStrikeOut())
            
        cursor.mergeCharFormat(new_fmt)
        self.editor.mergeCurrentCharFormat(new_fmt)
        
        if self.stats_callback:
            self.stats_callback()

    def actualizar_estado_botones(self, pos, btns_info):
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        
        for info in btns_info:
            btn = info["btn"]
            tipo = info["tipo"]
            
            activo = False
            if tipo == "negrita": activo = fmt.fontWeight() == QFont.Weight.Bold
            elif tipo == "cursiva": activo = fmt.fontItalic()
            elif tipo == "subrayado": activo = fmt.fontUnderline()
            elif tipo == "tachado": activo = fmt.fontStrikeOut()
            
            acento = self.colores.get('acento', '#6366F1') if isinstance(self.colores, dict) else '#6366F1'
            if activo:
                btn.setStyleSheet(f"background: {acento}; color: white; border-radius: 6px; border: none;")
            else:
                btn.setStyleSheet("background: rgba(0,0,0,0.2); color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")

    def insertar_vineta(self, tipo):
        """Inserta viñeta amigable a la selección multi-línea o en la posición del cursor"""
        vinetas = {
            "punto": "• ",
            "circulo": "◦ ",
            "cuadrado": "▪ ",
            "flecha": "➢ ",
            "check": "✓ ",
            "numero": "1. ",
            "checkbox": "☐ "
        }
        simbolo = vinetas.get(tipo, "• ")
        cursor = self.editor.textCursor()

        if tipo == "checkbox" and not cursor.hasSelection():
            if hasattr(self.editor, "alternar_checkbox_linea_actual") and self.editor.alternar_checkbox_linea_actual():
                return
            cursor.insertText(simbolo)
            return

        if cursor.hasSelection():
            # Aplicar viñeta al inicio de cada línea seleccionada
            sel_text = cursor.selectedText()
            lines = sel_text.split('\u2029') # Sep de párrafos en Qt
            if len(lines) <= 1:
                lines = sel_text.split('\n')

            new_lines = []
            for idx, line in enumerate(lines):
                if line.strip():
                    if tipo == "numero":
                        prefix = f"{idx + 1}. "
                    elif tipo == "checkbox":
                        if line.startswith("☐ "):
                            prefix = "☑ "
                            line = line[2:]
                        elif line.startswith("☑ "):
                            prefix = "☐ "
                            line = line[2:]
                        else:
                            prefix = "☐ "
                    else:
                        prefix = simbolo
                    # Evitar duplicar viñetas si ya las tiene
                    clean_line = line
                    for s in vinetas.values():
                        if clean_line.startswith(s):
                            clean_line = clean_line[len(s):]
                    new_lines.append(f"{prefix}{clean_line}")
                else:
                    new_lines.append(line)

            cursor.insertText("\n".join(new_lines))
        else:
            cursor.insertText(simbolo)

    def cambiar_tamano(self, size):
        """Aplica un tamaño de fuente específico y mantiene el estado para seguir escribiendo"""
        try:
            sz = float(size)
            if sz > 0:
                fmt = QTextCharFormat()
                fmt.setFontPointSize(sz)
                cursor = self.editor.textCursor()
                cursor.mergeCharFormat(fmt)
                self.editor.mergeCurrentCharFormat(fmt)
        except Exception:
            pass

    def cambiar_color_texto(self, color_hex):
        """Aplica un color al texto seleccionado"""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color_hex))
        cursor = self.editor.textCursor()
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def cambiar_color_fondo(self, color_hex):
        """Aplica resaltador (background) ajustando el contraste del texto para legibilidad"""
        qcol = QColor(color_hex)
        fmt = QTextCharFormat()
        fmt.setBackground(qcol)
        
        # Calcular luminancia para decidir el color de letra
        luminance = (qcol.red() * 0.299 + qcol.green() * 0.587 + qcol.blue() * 0.114)
        if luminance > 128:
            fmt.setForeground(QColor("#1E293B")) # Texto oscuro si el resaltador es claro
        else:
            fmt.setForeground(QColor("#FFFFFF")) # Texto claro si el resaltador es oscuro

        cursor = self.editor.textCursor()
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def cambiar_familia_fuente(self, nombre_fuente):
        """Aplica una familia tipográfica específica al texto seleccionado"""
        try:
            fmt = QTextCharFormat()
            fmt.setFontFamilies([str(nombre_fuente)])
            cursor = self.editor.textCursor()
            cursor.mergeCharFormat(fmt)
            self.editor.mergeCurrentCharFormat(fmt)
        except Exception:
            pass

    def limpiar_formato(self):
        """Restaura el formato del texto seleccionado a estilo neutro sin negrita, cursiva o colores"""
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal)
        fmt.setFontItalic(False)
        fmt.setFontUnderline(False)
        fmt.setFontStrikeOut(False)
        fmt.setForeground(QColor("#E0E0E0"))
        fmt.setBackground(QColor(Qt.GlobalColor.transparent))
        fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignNormal)
        cursor = self.editor.textCursor()
        cursor.setCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def aplicar_superindice(self):
        """Aplica o remueve superíndice X²"""
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        new_fmt = QTextCharFormat()
        if fmt.verticalAlignment() == QTextCharFormat.VerticalAlignment.AlignSuperScript:
            new_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignNormal)
        else:
            new_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSuperScript)
        cursor.mergeCharFormat(new_fmt)
        self.editor.mergeCurrentCharFormat(new_fmt)

    def aplicar_subindice(self):
        """Aplica o remueve subíndice X₂"""
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        new_fmt = QTextCharFormat()
        if fmt.verticalAlignment() == QTextCharFormat.VerticalAlignment.AlignSubScript:
            new_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignNormal)
        else:
            new_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSubScript)
        cursor.mergeCharFormat(new_fmt)
        self.editor.mergeCurrentCharFormat(new_fmt)

    def insertar_bloque_codigo(self):
        """Aplica estilo de bloque de código (Consolas, fondo oscuro)"""
        fmt = QTextCharFormat()
        fmt.setFontFamily("Consolas")
        fmt.setFontPointSize(11)
        fmt.setBackground(QColor("#2D2D3D"))
        fmt.setForeground(QColor("#A7F3D0"))
        cursor = self.editor.textCursor()
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def aplicar_encabezado(self, tipo):
        """Aplica estilos de encabezados profesionales (H1, H2, H3, Cita, Párrafo)"""
        try:
            tipo_str = str(tipo).strip().lower()
            cursor = self.editor.textCursor()
            fmt = QTextCharFormat()
            if tipo_str in ("h1", "título 1", "titulo 1"):
                fmt.setFontPointSize(20)
                fmt.setFontWeight(QFont.Weight.Bold)
                fmt.setForeground(QColor("#FFFFFF"))
            elif tipo_str in ("h2", "título 2", "titulo 2"):
                fmt.setFontPointSize(16)
                fmt.setFontWeight(QFont.Weight.Bold)
                fmt.setForeground(QColor("#818CF8"))
            elif tipo_str in ("h3", "título 3", "titulo 3"):
                fmt.setFontPointSize(14)
                fmt.setFontWeight(QFont.Weight.Bold)
                fmt.setForeground(QColor("#C7D2FE"))
            elif tipo_str in ("quote", "cita"):
                fmt.setFontPointSize(11)
                fmt.setFontItalic(True)
                fmt.setForeground(QColor("#9CA3AF"))
            else: # Párrafo Normal
                fmt.setFontPointSize(12)
                fmt.setFontWeight(QFont.Weight.Normal)
                fmt.setFontItalic(False)
                fmt.setForeground(QColor("#E0E0E0"))

            # Si no hay texto seleccionado, aplicar a todo el bloque actual
            if not cursor.hasSelection():
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.mergeCharFormat(fmt)
            self.editor.mergeCurrentCharFormat(fmt)
            if self.stats_callback:
                self.stats_callback()
        except Exception:
            pass

    def insertar_separador(self):
        """Inserta una línea divisoria horizontal elegante y segura"""
        cursor = self.editor.textCursor()
        cursor.insertText("\n────────────────────────────────────────\n")

    def insertar_checklist(self):
        """Inserta una casilla interactiva de lista de tareas"""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            sel_text = cursor.selectedText()
            lines = sel_text.split('\u2029')
            if len(lines) <= 1:
                lines = sel_text.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith("☐ "):
                    new_lines.append("☑ " + line[2:])
                elif line.startswith("☑ "):
                    new_lines.append(line[2:])
                elif line.strip():
                    new_lines.append("☐ " + line)
                else:
                    new_lines.append(line)
            cursor.insertText("\n".join(new_lines))
        else:
            cursor.insertText("☐ ")

    def insertar_enlace(self, texto, url):
        """Inserta un hipervínculo en el cursor"""
        if not url:
            return
        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("mailto:"):
            url = f"https://{url}"
        label = texto if texto else url
        cursor = self.editor.textCursor()
        cursor.insertHtml(f"<a href='{url}' style='color: #6366F1; text-decoration: underline;'>{label}</a> ")

    def obtener_formatos_activos(self):
        """Retorna el estado de los formatos en la posición actual del cursor de forma 100% segura"""
        try:
            cursor = self.editor.textCursor()
            fmt = cursor.charFormat()
            align = self.editor.alignment()
            font = fmt.font()
            fam = font.family() if font else "Segoe UI"
            sz = str(int(fmt.fontPointSize())) if fmt.fontPointSize() > 0 else "12"
            return {
                "negrita": fmt.fontWeight() == QFont.Weight.Bold,
                "cursiva": fmt.fontItalic(),
                "subrayado": fmt.fontUnderline(),
                "tachado": fmt.fontStrikeOut(),
                "fuente": fam,
                "tamano": sz,
                "alineacion": align
            }
        except Exception:
            return {
                "negrita": False,
                "cursiva": False,
                "subrayado": False,
                "tachado": False,
                "fuente": "Segoe UI",
                "tamano": "12",
                "alineacion": Qt.AlignmentFlag.AlignLeft
            }

    def deshacer(self):
        self.editor.undo()

    def rehacer(self):
        self.editor.redo()
