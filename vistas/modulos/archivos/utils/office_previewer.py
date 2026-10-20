import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import os

class OfficePreviewer:
    """Extrae texto de documentos de Office (Docx, Xlsx) usando librerías estándar (xml/zipfile)"""
    
    @staticmethod
    def extract_text_from_docx(file_path):
        """Extrae párrafos legibles de un archivo .docx (Word)"""
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                # El contenido principal está en word/document.xml
                content = z.read("word/document.xml")
                root = ET.fromstring(content)
                
                # Namespace de Word
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                
                paragraphs = []
                # Buscar todos los elementos de párrafo <w:p>
                for p in root.findall('.//w:p', ns):
                    texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                    if texts:
                        paragraphs.append("".join(texts))
                
                return "\n\n".join(paragraphs) if paragraphs else "[Documento sin texto legible]"
        except Exception as e:
            return f"Error al procesar Word: {e}"

    @staticmethod
    def extract_text_from_xlsx(file_path):
        """Extrae una vista textual de las primeras celdas de un archivo .xlsx (Excel)"""
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                # 1. Cargar el mapa de strings compartidos (Shared Strings)
                shared_strings = []
                if "xl/sharedStrings.xml" in z.namelist():
                    ss_content = z.read("xl/sharedStrings.xml")
                    ss_root = ET.fromstring(ss_content)
                    ns_ss = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    # Cada <t> dentro de <si> es un string
                    for si in ss_root.findall('.//ns:si', ns_ss):
                        t_parts = [t.text for t in si.findall('.//ns:t', ns_ss) if t.text]
                        shared_strings.append("".join(t_parts))

                # 2. Cargar la primera hoja (Normalmente sheet1.xml)
                sheet_content = z.read("xl/worksheets/sheet1.xml")
                sheet_root = ET.fromstring(sheet_content)
                ns_sheet = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                rows = []
                # Iterar por filas <row>
                for row in sheet_root.findall('.//ns:row', ns_sheet):
                    row_data = []
                    # Iterar por celdas <c>
                    for c in row.findall('.//ns:c', ns_sheet):
                        v = c.find('ns:v', ns_sheet)
                        if v is not None:
                            val = v.text
                            # Si p="s", es un índice en sharedStrings
                            if c.get('t') == 's':
                                try:
                                    row_data.append(shared_strings[int(val)])
                                except:
                                    row_data.append(val)
                            else:
                                row_data.append(val)
                        else:
                            row_data.append("")
                    
                    if any(row_data):
                        rows.append("\t".join(row_data))
                
                # Limitar a las primeras 100 filas para no saturar la vista
                return "\n".join(rows[:100]) if rows else "[Hoja de Excel vacía]"
        except Exception as e:
            return f"Error al procesar Excel: {e}"

    @staticmethod
    def extract_text_from_pptx(file_path):
        """Extrae texto de las diapositivas de un archivo .pptx (PowerPoint)"""
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                # Buscar archivos de diapositivas ppt/slides/slideN.xml
                slide_files = sorted([f for f in z.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")])
                
                all_text = []
                ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
                
                for i, slide_path in enumerate(slide_files):
                    content = z.read(slide_path)
                    root = ET.fromstring(content)
                    
                    slide_text = []
                    # Buscar elementos de texto <a:t>
                    for t in root.findall('.//a:t', ns):
                        if t.text:
                            slide_text.append(t.text)
                    
                    if slide_text:
                        all_text.append(f"--- Diapositiva {i+1} ---\n" + "\n".join(slide_text))
                
                return "\n\n".join(all_text) if all_text else "[Presentación sin texto legible]"
        except Exception as e:
            return f"Error al procesar PowerPoint: {e}"

