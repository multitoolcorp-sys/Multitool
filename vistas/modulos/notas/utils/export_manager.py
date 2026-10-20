"""
export_manager.py - Gestor de exportación de notas a PDF, Markdown (.md) y Texto plano (.txt)
"""
import re
from html.parser import HTMLParser
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QTextDocument


class HTMLToMarkdown(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.current_tag = None
        self.in_bold = False
        self.in_italic = False
        self.in_strike = False
        self.in_underline = False
        self.in_li = False
        self.in_table = False
        self.table_row = []
        self.table_cols = 0
        self.list_level = 0
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in ("b", "strong"):
            self.result.append("**")
            self.in_bold = True
        elif tag in ("i", "em"):
            self.result.append("*")
            self.in_italic = True
        elif tag in ("s", "strike", "del"):
            self.result.append("~~")
            self.in_strike = True
        elif tag == "u":
            self.result.append("<u>")
            self.in_underline = True
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.result.append(f"\n\n{'#' * level} ")
        elif tag == "p":
            self.result.append("\n\n")
        elif tag == "br":
            self.result.append("\n")
        elif tag in ("ul", "ol"):
            self.list_level += 1
        elif tag == "li":
            self.result.append(f"\n{'  ' * (self.list_level - 1)}- ")
            self.in_li = True
        elif tag == "table":
            self.in_table = True
            self.table_row = []
            self.table_cols = 0
            self.result.append("\n\n")
        elif tag == "tr":
            self.table_row = []
        elif tag in ("td", "th"):
            pass

    def handle_endtag(self, tag):
        if tag in ("b", "strong"):
            self.result.append("**")
            self.in_bold = False
        elif tag in ("i", "em"):
            self.result.append("*")
            self.in_italic = False
        elif tag in ("s", "strike", "del"):
            self.result.append("~~")
            self.in_strike = False
        elif tag == "u":
            self.result.append("</u>")
            self.in_underline = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.result.append("\n\n")
        elif tag == "p":
            self.result.append("\n\n")
        elif tag in ("ul", "ol"):
            self.list_level = max(0, self.list_level - 1)
        elif tag == "li":
            self.in_li = False
        elif tag == "tr":
            if self.in_table:
                row_str = "| " + " | ".join(self.table_row) + " |"
                self.result.append(row_str + "\n")
                if self.table_cols == 0:
                    self.table_cols = len(self.table_row)
                    sep_str = "| " + " | ".join(["---"] * self.table_cols) + " |"
                    self.result.append(sep_str + "\n")
        elif tag == "table":
            self.in_table = False
            self.result.append("\n")

    def handle_data(self, data):
        clean_data = data.strip() if self.in_table else data
        if self.in_table and self.current_tag in ("td", "th"):
            self.table_row.append(clean_data)
        else:
            self.result.append(data)

    def get_markdown(self):
        text = "".join(self.result)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class ExportManager:
    def __init__(self, parent_widget, editor):
        self.parent = parent_widget
        self.editor = editor

    def exportar_pdf(self):
        try:
            from PyQt6.QtPrintSupport import QPrinter
        except ImportError:
            QMessageBox.warning(self.parent, "Error", "Módulo QtPrintSupport no disponible.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self.parent, "Exportar Nota a PDF", "", "Archivos PDF (*.pdf)")
        if not file_path:
            return

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            self.editor.document().print(printer)
            QMessageBox.information(self.parent, "Éxito", "Nota exportada a PDF con éxito.")
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"No se pudo exportar a PDF: {e}")

    def exportar_markdown(self):
        file_path, _ = QFileDialog.getSaveFileName(self.parent, "Exportar Nota a Markdown", "", "Archivos Markdown (*.md)")
        if not file_path:
            return

        try:
            html = self.editor.toHtml()
            parser = HTMLToMarkdown()
            parser.feed(html)
            md = parser.get_markdown()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md)
            QMessageBox.information(self.parent, "Éxito", "Nota exportada a Markdown con éxito.")
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"No se pudo exportar a Markdown: {e}")

    def exportar_txt(self):
        file_path, _ = QFileDialog.getSaveFileName(self.parent, "Exportar Nota a Texto Plano", "", "Archivos de Texto (*.txt)")
        if not file_path:
            return

        try:
            txt = self.editor.toPlainText()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(txt)
            QMessageBox.information(self.parent, "Éxito", "Nota exportada a TXT con éxito.")
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"No se pudo exportar a TXT: {e}")
