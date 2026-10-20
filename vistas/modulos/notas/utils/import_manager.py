"""
import_manager.py - Gestor de importación de notas desde archivos externos (.md, .txt, .html)
"""
import re
import json
import datetime
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox

class ImportManager:
    def __init__(self, parent, ruta_notas, on_import_success=None):
        self.parent = parent
        self.ruta_notas = Path(ruta_notas)
        self.on_import_success = on_import_success

    def importar_archivo(self):
        """Abre diálogo para seleccionar archivos externos e importarlos como notas"""
        archivos, _ = QFileDialog.getOpenFileNames(
            self.parent,
            "Importar Notas Externas",
            "",
            "Documentos soportados (*.md *.txt *.html *.htm);;Markdown (*.md);;Texto (*.txt);;HTML (*.html *.htm);;Todos (*.*)"
        )
        if not archivos:
            return

        importadas = 0
        errores = 0

        for f_path in archivos:
            res = self.importar_archivo_individual(f_path)
            if res:
                importadas += 1
            else:
                errores += 1

        if importadas > 0:
            if self.parent:
                QMessageBox.information(
                    self.parent,
                    "Importación Exitosa",
                    f"Se importaron {importadas} nota(s) a tu biblioteca." + (f" ({errores} errores)" if errores > 0 else "")
                )
            if self.on_import_success:
                self.on_import_success()
        elif errores > 0 and self.parent:
            QMessageBox.warning(self.parent, "Error de Importación", f"No se pudieron importar los archivos seleccionados.")

    def importar_archivo_individual(self, f_path):
        """Importa un archivo individual y retorna el nombre de la nota creada o None"""
        p = Path(f_path)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                contenido = f.read()

            # Generar nombre único para la nota
            stem_limpio = re.sub(r'[\\/*?:"<>|]', "", p.stem.strip()).replace(" ", "_")
            if not stem_limpio:
                stem_limpio = "Nota_Importada"

            nombre_nota = stem_limpio
            idx = 1
            while (self.ruta_notas / f"{nombre_nota}.txt").exists():
                nombre_nota = f"{stem_limpio}_{idx}"
                idx += 1

            # Convertir contenido según formato
            suffix = p.suffix.lower()
            if suffix == ".md":
                html_content = self._markdown_a_html(contenido)
            elif suffix in [".html", ".htm"]:
                html_content = contenido
            else:  # .txt
                lineas = contenido.split("\n")
                html_content = "".join(f"<p>{l if l.strip() else '&nbsp;'}</p>" for l in lineas)

            # Guardar estructura de nota
            datos = {
                "html": html_content,
                "imagenes_metadata": {},
                "favorita": False,
                "background_color": "default"
            }

            ruta_guardado = self.ruta_notas / f"{nombre_nota}.txt"
            with open(ruta_guardado, "w", encoding="utf-8") as out:
                json.dump(datos, out, indent=4)

            return nombre_nota
        except Exception as e:
            print(f"Error importando {p.name}: {e}")
            return None

    def _markdown_a_html(self, md_text):
        """Conversor ligero de Markdown a HTML estándar"""
        # Encabezados
        html = md_text
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Negrita y cursiva
        html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'__(.*?)__', r'<b>\1</b>', html)
        html = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html)
        html = re.sub(r'_(.*?)_', r'<i>\1</i>', html)

        # Código en línea y bloques
        html = re.sub(r'```(.*?)```', r'<pre style="background:#2D2D3D; color:#A7F3D0; padding:8px; border-radius:6px;"><code>\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.*?)`', r'<code style="background:#2D2D3D; color:#A7F3D0;">\1</code>', html)

        # Líneas y saltos
        lineas = html.split("\n")
        resultado = []
        for l in lineas:
            if l.startswith("<h") or l.startswith("<pre") or l.startswith("</pre"):
                resultado.append(l)
            elif l.strip() == "---" or l.strip() == "***":
                resultado.append("<hr style='border:1px solid rgba(255,255,255,0.1);'>")
            elif l.startswith("- ") or l.startswith("* "):
                resultado.append(f"<li>{l[2:]}</li>")
            elif l.strip():
                resultado.append(f"<p>{l}</p>")
            else:
                resultado.append("<p>&nbsp;</p>")

        return "".join(resultado)
