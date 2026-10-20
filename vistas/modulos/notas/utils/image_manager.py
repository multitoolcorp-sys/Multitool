import base64
import io
import uuid
from PIL import Image
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QCheckBox, QPushButton, QFileDialog, 
    QMessageBox, QDialogButtonBox, QFrame, QSlider, QInputDialog
)
from PyQt6.QtGui import QImage, QPixmap, QTextCursor, QTextImageFormat, QCursor, QTextFrameFormat
from PyQt6.QtCore import Qt, QUrl

class ImageManager:
    def __init__(self, editor, status_callback, imagenes_refs, imagenes_nota_data):
        self.editor = editor # QTextEdit
        self.status_callback = status_callback
        self.imagenes = imagenes_refs  # Pixmaps
        self.imagenes_nota = imagenes_nota_data # Base64 data

    def insertar_imagen(self):
        """Inserta la imagen con un tamaño estándar amigable (auto-normalización)"""
        path, _ = QFileDialog.getOpenFileName(
            self.editor, "Seleccionar Imagen", "", 
            "Imágenes (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if not path: return
        
        try:
            img_pil = Image.open(path)
            
            target_w = 400
            orig_w, orig_h = img_pil.size
            
            new_w = target_w
            new_h = int(orig_h * (target_w / orig_w))
            
            if orig_w < target_w:
                new_w, new_h = orig_w, orig_h
                
            img_res = img_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            fmt = "PNG" if img_pil.format in ["PNG", "GIF"] else "JPEG"
            img_res.save(buf, format=fmt, quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            img_id = f"img_{uuid.uuid4().hex[:8]}"
            self.imagenes_nota[img_id] = {
                "data": b64, "formato": fmt, "w": new_w, "h": new_h
            }
            
            self._insertar_en_editor(b64, new_w, new_h, img_id)
            self.status_callback("Imagen insertada (Tamaño normalizado)")
            self.sanitizar_imagenes_huerfanas()
                
        except Exception as e:
            QMessageBox.critical(self.editor, "Error", f"Error al procesar imagen: {e}")

    def insertar_desde_qimage(self, qimg):
        """Inserta una imagen obtenida desde el portapapeles o arrastrada"""
        try:
            if not qimg or qimg.isNull():
                return
            target_w = 400
            orig_w = qimg.width()
            orig_h = qimg.height()
            new_w = min(orig_w, target_w)
            new_h = int(orig_h * (new_w / orig_w)) if orig_w > 0 else 100

            scaled = qimg.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            from PyQt6.QtCore import QBuffer, QIODevice
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            scaled.save(buffer, "PNG")
            b64 = base64.b64encode(buffer.data().data()).decode('utf-8')
            buffer.close()

            img_id = f"img_{uuid.uuid4().hex[:8]}"
            self.imagenes_nota[img_id] = {
                "data": b64, "formato": "PNG", "w": new_w, "h": new_h
            }
            self._insertar_en_editor(b64, new_w, new_h, img_id)
            self.status_callback("Imagen pegada/insertada con éxito")
            self.sanitizar_imagenes_huerfanas()
        except Exception as e:
            print(f"Error al insertar QImage: {e}")

    def insertar_desde_archivo(self, path):
        """Inserta una imagen desde una ruta de archivo local"""
        if not path:
            return
        try:
            qimg = QImage(str(path))
            if not qimg.isNull():
                self.insertar_desde_qimage(qimg)
        except Exception as e:
            print(f"Error al insertar imagen desde archivo: {e}")

    def _insertar_en_editor(self, b64_data, w, h, resource_name):
        try:
            img_bytes = base64.b64decode(b64_data)
            qimg = QImage.fromData(img_bytes)
            
            if qimg.isNull():
                return

            doc = self.editor.document()
            doc.addResource(doc.ResourceType.ImageResource, QUrl(resource_name), qimg)
            
            img_fmt = QTextImageFormat()
            img_fmt.setName(resource_name)
            img_fmt.setWidth(float(w))
            img_fmt.setHeight(float(h))
            
            cursor = self.editor.textCursor()
            cursor.insertImage(img_fmt)
            
            self.editor.viewport().update()
        except Exception as e:
            print(f"Fallo al insertar recurso de imagen: {e}")

    def cargar_imagenes_desde_datos(self):
        """Restaura los recursos de imagen en el documento desde la metadata de la nota"""
        try:
            doc = self.editor.document()
            for resource_name, meta in self.imagenes_nota.items():
                if isinstance(meta, dict) and "data" in meta:
                    img_bytes = base64.b64decode(meta["data"])
                    qimg = QImage.fromData(img_bytes)
                    if not qimg.isNull():
                        doc.addResource(doc.ResourceType.ImageResource, QUrl(resource_name), qimg)
        except Exception as e:
            print(f"Error cargando imágenes desde datos: {e}")

    def cambiar_posicion_imagen(self, cursor, modo):
        """Aplica opciones estilo Word para la alineación/flotado de la imagen"""
        try:
            fmt = cursor.charFormat().toImageFormat()
            if not fmt.isValid():
                return

            if modo == "izquierda":
                fmt.setProperty(QTextImageFormat.Property.ImageQuality, 100)
            elif modo == "derecha":
                fmt.setProperty(QTextImageFormat.Property.ImageQuality, 100)
            
            cursor.mergeCharFormat(fmt)
            self.editor.viewport().update()
            self.status_callback(f"Imagen ajustada a: {modo.capitalize()}")
        except Exception as e:
            print(f"Error al cambiar posicion de imagen: {e}")

    def cambiar_tamano_dialogo(self, cursor):
        """Abre un diálogo para redimensionar la imagen seleccionada"""
        fmt = cursor.charFormat().toImageFormat()
        if not fmt.isValid():
            return

        w_actual = int(fmt.width())
        val, ok = QInputDialog.getInt(self.editor, "Cambiar Ancho de Imagen", "Ancho en píxeles (px):", w_actual, 50, 1200)
        if ok and val > 0:
            aspect = fmt.height() / max(1.0, fmt.width())
            fmt.setWidth(float(val))
            fmt.setHeight(float(val * aspect))
            cursor.mergeCharFormat(fmt)
            self.editor.viewport().update()
            self.status_callback(f"Imagen redimensionada a {val}px")

    def sanitizar_imagenes_huerfanas(self):
        try:
            html_content = self.editor.toHtml()
            ids_a_eliminar = []
            for img_id in list(self.imagenes_nota.keys()):
                if img_id not in html_content:
                    ids_a_eliminar.append(img_id)
            
            for img_id in ids_a_eliminar:
                del self.imagenes_nota[img_id]
        except Exception as e:
            print(f"Error sanitizando imágenes huérfanas: {e}")

    def eliminar_imagen_seleccionada(self):
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.removeSelectedText()
        self.sanitizar_imagenes_huerfanas()
