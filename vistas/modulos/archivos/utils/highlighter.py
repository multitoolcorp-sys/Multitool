import re
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt

class CodeHighlighter(QSyntaxHighlighter):
    """Resaltador de sintaxis multilingüe optimizado"""
    def __init__(self, parent, colores):
        super().__init__(parent)
        self.colores = colores
        self.rules = []

        # Formatos
        fmt_keyword = self._get_format(colores.get("acento", "#6366F1"), bold=True)
        fmt_string = self._get_format("#A6E22E")
        fmt_comment = self._get_format("#75715E", italic=True)
        fmt_number = self._get_format("#AE81FF")
        fmt_function = self._get_format("#66D9EF")
        fmt_class = self._get_format("#E6DB74", bold=True)

        # Reglas Globales (Comunes en muchos lenguajes)
        keywords = [
            "class", "def", "function", "return", "if", "else", "elif", "for", "while",
            "import", "from", "as", "class", "try", "except", "finally", "with",
            "val", "var", "let", "const", "static", "public", "private", "protected",
            "null", "None", "true", "True", "false", "False", "break", "continue"
        ]
        
        for kw in keywords:
            self.rules.append((re.compile(r'\b' + kw + r'\b'), fmt_keyword))

        self.rules.append((re.compile(r'\b\d+\b'), fmt_number))
        self.rules.append((re.compile(r'".*?"'), fmt_string))
        self.rules.append((re.compile(r"'.*?'"), fmt_string))
        self.rules.append((re.compile(r'#.*'), fmt_comment))
        self.rules.append((re.compile(r'//.*'), fmt_comment))
        self.rules.append((re.compile(r'/\*.*?\*/', re.DOTALL), fmt_comment))
        self.rules.append((re.compile(r'\b[A-Z][a-zA-Z0-9_]+\b'), fmt_class))
        self.rules.append((re.compile(r'\b[a-z_][a-zA-Z0-9_]+(?=\s*\()'), fmt_function))

    def _get_format(self, color, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold: fmt.setFontWeight(QFont.Weight.Bold)
        if italic: fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

    def actualizar_colores(self, colores):
        self.colores = colores
        fmt_keyword = self._get_format(colores.get("acento", "#6366F1"), bold=True)
        for i, (pat, fmt) in enumerate(self.rules):
            if i < 27: # Keyword rules
                self.rules[i] = (pat, fmt_keyword)
        self.rehighlight()

