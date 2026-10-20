import sys
import io
import re
import os
import datetime
import json
import shutil
import subprocess
import tempfile
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QBuffer, QUrl
from PyQt6.QtGui import QImage, QGuiApplication, QDesktopServices


class CodeDetector:
    """Detector robusto de códigos QR y códigos de barras en QPixmap."""
    @staticmethod
    def detect(pixmap):
        results = []
        if not pixmap or pixmap.isNull():
            return results

        # 1. Intentar conversión a OpenCV BGR array si OpenCV está instalado
        cv_img = None
        try:
            qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
            width = qimage.width()
            height = qimage.height()
            ptr = qimage.bits()
            if ptr:
                ptr.setsize(height * width * 4)
                import numpy as np
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                import cv2
                cv_img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        except Exception:
            cv_img = None

        if cv_img is not None:
            try:
                import cv2
                # Detección de QR en OpenCV
                qr_detector = cv2.QRCodeDetector()
                try:
                    retval, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(cv_img)
                    if retval and decoded_info:
                        for info in decoded_info:
                            if info and info.strip():
                                is_url = bool(re.match(r'^(https?://|www\.)', info.strip(), re.IGNORECASE))
                                results.append({
                                    "type": "Código QR",
                                    "data": info.strip(),
                                    "is_url": is_url
                                })
                except Exception:
                    pass

                if not results:
                    try:
                        val, points, _ = qr_detector.detectAndDecode(cv_img)
                        if val and val.strip():
                            is_url = bool(re.match(r'^(https?://|www\.)', val.strip(), re.IGNORECASE))
                            results.append({
                                "type": "Código QR",
                                "data": val.strip(),
                                "is_url": is_url
                            })
                    except Exception:
                        pass

                # Detección de Código de Barras en OpenCV
                try:
                    if hasattr(cv2, 'barcode') and hasattr(cv2.barcode, 'BarcodeDetector'):
                        bd = cv2.barcode.BarcodeDetector()
                        retval, decoded_info, decoded_type, points = bd.detectAndDecode(cv_img)
                        if retval:
                            for info, btype in zip(decoded_info, decoded_type):
                                if info and info.strip():
                                    is_url = bool(re.match(r'^(https?://|www\.)', info.strip(), re.IGNORECASE))
                                    results.append({
                                        "type": f"Código de Barras ({btype or 'Standard'})",
                                        "data": info.strip(),
                                        "is_url": is_url
                                    })
                except Exception:
                    pass
            except Exception:
                pass

        # 2. Intentar pyzbar si está instalado
        try:
            from pyzbar.pyzbar import decode as pyzbar_decode
            from PIL import Image
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            pixmap.save(buffer, "PNG")
            pil_img = Image.open(io.BytesIO(buffer.data().data()))
            decoded_objects = pyzbar_decode(pil_img)
            for obj in decoded_objects:
                data_str = obj.data.decode("utf-8", errors="ignore").strip()
                if data_str:
                    if not any(r['data'] == data_str for r in results):
                        code_type = obj.type if hasattr(obj, 'type') else "Código"
                        is_url = bool(re.match(r'^(https?://|www\.)', data_str, re.IGNORECASE))
                        results.append({
                            "type": f"Código {code_type}",
                            "data": data_str,
                            "is_url": is_url
                        })
        except Exception:
            pass

        return results


class OcrManager:
    """Extrae texto de una imagen QPixmap usando Tesseract con pre-procesamiento, inspección de rutas y registro detallado en log_extras.json."""
    
    @staticmethod
    def log_event(action: str, details: dict):
        """Registra información de diagnóstico en log_extras.json para depuración en desarrollo y producción (.exe)."""
        try:
            log_dir = Path.home() / "Documents" / "Multitool"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "log_extras.json"
            
            data = []
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if not isinstance(data, list):
                            data = []
                except Exception:
                    data = []

            entry = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": action,
                "details": details
            }
            data.append(entry)
            
            if len(data) > 200:
                data = data[-200:]
                
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error registrando log_extras.json: {e}")

    @staticmethod
    def ensure_env_path():
        r"""Añade C:\Program Files\Tesseract-OCR\ a las Variables de Entorno de Windows si está presente."""
        tess_dir = r"C:\Program Files\Tesseract-OCR"
        added_memory = False
        added_registry = False

        if os.path.exists(tess_dir):
            cur_path = os.environ.get("PATH", "")
            if tess_dir.lower() not in cur_path.lower():
                os.environ["PATH"] = tess_dir + os.path.pathsep + cur_path
                added_memory = True
            
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
                    try:
                        val, _ = winreg.QueryValueEx(key, "PATH")
                    except FileNotFoundError:
                        val = ""
                    if tess_dir.lower() not in val.lower():
                        new_val = tess_dir + ";" + val if val else tess_dir
                        winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_val)
                        added_registry = True
                    winreg.CloseKey(key)
                except Exception as e:
                    OcrManager.log_event("ensure_env_path_registry_error", {"error": str(e)})

        OcrManager.log_event("ensure_env_path", {
            "tess_dir": tess_dir,
            "exists": os.path.exists(tess_dir),
            "added_to_memory_path": added_memory,
            "added_to_registry_path": added_registry
        })

    @staticmethod
    def _find_readme():
        exe_dir = Path(sys.executable).parent
        possible_readmes = [
            Path(__file__).resolve().parents[1] / "utils" / "img-texto-main" / "README.md",
            exe_dir / "vistas" / "modulos" / "extras" / "utils" / "img-texto-main" / "README.md",
            Path.home() / "Documents" / "Multitool" / "vistas" / "modulos" / "extras" / "utils" / "img-texto-main" / "README.md",
            Path(r"c:\Users\Yuiga_Nariyuki\Desktop\multitool\multitool1\vistas\modulos\extras\utils\img-texto-main\README.md")
        ]
        for r in possible_readmes:
            if r.exists():
                return r
        return None

    @staticmethod
    def _find_installer():
        exe_dir = Path(sys.executable).parent
        possible_installers = [
            Path(__file__).resolve().parents[1] / "utils" / "tesseract-ocr-w64-setup-5.5.3.20260724.exe",
            exe_dir / "vistas" / "modulos" / "extras" / "utils" / "tesseract-ocr-w64-setup-5.5.3.20260724.exe",
            exe_dir / "tesseract-ocr-w64-setup-5.5.3.20260724.exe",
            Path.home() / "Documents" / "Multitool" / "vistas" / "modulos" / "extras" / "utils" / "tesseract-ocr-w64-setup-5.5.3.20260724.exe",
            Path(r"c:\Users\Yuiga_Nariyuki\Desktop\multitool\multitool1\vistas\modulos\extras\utils\tesseract-ocr-w64-setup-5.5.3.20260724.exe")
        ]
        for inst in possible_installers:
            if inst.exists():
                return inst
        return None

    @staticmethod
    def _find_tesseract():
        OcrManager.ensure_env_path()
        
        exe_dir = Path(sys.executable).parent
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\tesseract\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%ProgramFiles%\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe"),
            str(exe_dir / "tesseract.exe"),
            str(exe_dir / "tesseract" / "tesseract.exe"),
            str(exe_dir / "vistas" / "modulos" / "extras" / "utils" / "tesseract" / "tesseract.exe"),
            str(Path.home() / "Documents" / "Multitool" / "vistas" / "modulos" / "extras" / "utils" / "tesseract" / "tesseract.exe"),
            str(Path.home() / "Documents" / "Multitool" / "tesseract" / "tesseract.exe"),
            str(Path.home() / "Documents" / "Multitool" / "bin" / "tesseract.exe"),
        ]
        
        evaluations = {}
        found = None
        for p in possible_paths:
            ex = os.path.exists(p)
            evaluations[p] = ex
            if ex and not found:
                found = p

        if not found:
            which_exe = shutil.which("tesseract")
            if which_exe:
                found = str(which_exe)
                evaluations["shutil.which('tesseract')"] = found

        OcrManager.log_event("find_tesseract", {
            "sys_frozen": getattr(sys, "frozen", False),
            "sys_executable": sys.executable,
            "selected_tesseract": found,
            "evaluated_paths": evaluations
        })

        return found

    @staticmethod
    def _run_tesseract_direct(tess_cmd, pixmap):
        """Ejecuta tesseract.exe directamente mediante subprocess de forma nativa sin depender de pytesseract ni PIL."""
        if not tess_cmd or not os.path.exists(tess_cmd):
            OcrManager.log_event("direct_subprocess_aborted", {"reason": "tess_cmd invalid or non-existent", "tess_cmd": tess_cmd})
            return ""

        tmp_dir = Path(tempfile.gettempdir())
        tmp_png = tmp_dir / "multitool_ocr_tmp.png"
        out_base = tmp_dir / "multitool_ocr_out"
        out_txt = tmp_dir / "multitool_ocr_out.txt"

        try:
            pixmap.save(str(tmp_png), "PNG")

            configs_to_try = [
                ["-l", "spa+eng", "--psm", "6"],
                ["-l", "spa+eng", "--psm", "3"],
                ["-l", "spa", "--psm", "6"],
                ["-l", "eng", "--psm", "6"],
                ["--psm", "6"],
                []
            ]

            creation_flags = 0x08000000 if os.name == "nt" else 0

            for cfg_args in configs_to_try:
                try:
                    if out_txt.exists():
                        out_txt.unlink()

                    cmd = [tess_cmd, str(tmp_png), str(out_base)] + cfg_args
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        creationflags=creation_flags,
                        timeout=10
                    )

                    if out_txt.exists():
                        with open(out_txt, "r", encoding="utf-8", errors="ignore") as f:
                            extracted = f.read().strip()
                        if extracted:
                            OcrManager.log_event("direct_subprocess_success", {
                                "tess_cmd": tess_cmd,
                                "config": cfg_args,
                                "text_length": len(extracted),
                                "snippet": extracted[:60]
                            })
                            return extracted
                except Exception as err_cfg:
                    OcrManager.log_event("direct_subprocess_cfg_error", {
                        "config": cfg_args, "error": str(err_cfg)
                    })

        except Exception as err_gen:
            OcrManager.log_event("direct_subprocess_general_error", {"error": str(err_gen)})
        finally:
            try:
                if tmp_png.exists(): tmp_png.unlink()
                if out_txt.exists(): out_txt.unlink()
            except Exception:
                pass

        return ""

    @staticmethod
    def extract_text(pixmap):
        if not pixmap or pixmap.isNull():
            OcrManager.log_event("extract_text_aborted", {"reason": "pixmap is null or empty"})
            return ""

        OcrManager.ensure_env_path()
        tess_cmd = OcrManager._find_tesseract()

        w_orig, h_orig = pixmap.width(), pixmap.height()

        pil_img = None
        enhanced_img = None
        try:
            from PIL import Image, ImageEnhance, ImageOps
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            pixmap.save(buffer, "PNG")
            pil_img = Image.open(io.BytesIO(buffer.data().data())).convert("RGB")

            w, h = pil_img.size
            if w < 800 or h < 600:
                scale = max(2, int(800 / max(w, 1)))
                pil_img = pil_img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)

            gray_img = ImageOps.grayscale(pil_img)
            enhancer = ImageEnhance.Contrast(gray_img)
            enhanced_img = enhancer.enhance(2.0)
        except Exception as err_prep:
            OcrManager.log_event("preprocessing_error", {"error": str(err_prep)})

        # 1. Probar pytesseract si está disponible
        errors_pytess = []
        try:
            import pytesseract
            if tess_cmd:
                pytesseract.pytesseract.tesseract_cmd = tess_cmd

            images_to_try = [("enhanced", enhanced_img), ("original", pil_img)]
            configs_to_try = ["--psm 6", "--psm 3", ""]
            langs_to_try = ["spa+eng", "spa", "eng", None]

            for img_name, img_cand in images_to_try:
                if not img_cand: continue
                for cfg in configs_to_try:
                    for lang in langs_to_try:
                        try:
                            kw = {}
                            if cfg: kw["config"] = cfg
                            if lang: kw["lang"] = lang
                            
                            text = pytesseract.image_to_string(img_cand, **kw)
                            if text and text.strip():
                                clean_text = text.strip()
                                OcrManager.log_event("extract_text_success", {
                                    "engine": "pytesseract",
                                    "tess_cmd": tess_cmd,
                                    "image_type": img_name,
                                    "config": cfg,
                                    "lang": lang,
                                    "text_length": len(clean_text),
                                    "snippet": clean_text[:60]
                                })
                                return clean_text
                        except Exception as e_run:
                            errors_pytess.append({
                                "img_type": img_name, "cfg": cfg, "lang": lang, "error": str(e_run)
                            })
        except Exception as e_tess:
            OcrManager.log_event("pytesseract_import_or_setup_error", {"error": str(e_tess)})

        OcrManager.log_event("pytesseract_attempts_failed", {
            "attempts_count": len(errors_pytess),
            "sample_errors": errors_pytess[:5]
        })

        # 2. Fallback de ejecución directa de tesseract.exe por subprocess
        if tess_cmd:
            direct_text = OcrManager._run_tesseract_direct(tess_cmd, pixmap)
            if direct_text and direct_text.strip():
                return direct_text.strip()

        # 3. Fallback EasyOCR
        try:
            import easyocr
            import numpy as np
            qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
            width = qimage.width()
            height = qimage.height()
            ptr = qimage.bits()
            if ptr:
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                reader = easyocr.Reader(['es', 'en'], gpu=False)
                res = reader.readtext(arr, detail=0)
                if res:
                    easy_text = "\n".join(res)
                    OcrManager.log_event("extract_text_success", {
                        "engine": "easyocr",
                        "text_length": len(easy_text),
                        "snippet": easy_text[:60]
                    })
                    return easy_text
        except Exception as e_easy:
            OcrManager.log_event("easyocr_failed", {"error": str(e_easy)})

        OcrManager.log_event("extract_text_no_result", {
            "orig_size": [w_orig, h_orig],
            "sys_frozen": getattr(sys, "frozen", False)
        })

        return ""


class SnipperReadingModeDialog(QDialog):
    """Ventana modal estilo Modo Lectura para extraer y copiar texto de la captura."""
    def __init__(self, text, colores, parent=None):
        super().__init__(parent)
        self.colores = colores
        self.setWindowTitle("📖 Modo Lectura - Extracción de Texto")
        self.resize(560, 460)
        self.setMinimumSize(450, 350)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build_ui(text)

    def _build_ui(self, text):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colores['bg_principal']};
                color: white;
            }}
            QLabel {{
                color: white;
                font-family: 'Outfit', 'Segoe UI', sans-serif;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Encabezado
        header = QHBoxLayout()
        icon_lbl = QLabel("📖")
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_lbl = QLabel("Modo Lectura - Texto Extraído")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        sub_lbl = QLabel("Selecciona, edita o copia el texto reconocido de la imagen recortada")
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {self.colores['fg_secundario']};")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        # Editor de texto reconocido
        self.txt_edit = QTextEdit()
        self.txt_edit.setPlainText(text)
        self.txt_edit.setPlaceholderText("No se detectó texto automático o no hay un motor OCR instalado (Tesseract/EasyOCR).\nPuedes escribir, pegar o editar texto manualmente aquí.")
        self.txt_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {self.colores['bg_secundario']};
                color: #F3F4F6;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 12px;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
                font-size: 13px;
                line-height: 1.4;
            }}
        """)
        self.txt_edit.textChanged.connect(self._update_stats)
        layout.addWidget(self.txt_edit)

        # Barra de estadísticas y acciones
        footer = QHBoxLayout()
        
        self.lbl_stats = QLabel()
        self.lbl_stats.setStyleSheet(f"color: {self.colores['fg_secundario']}; font-size: 12px;")
        self._update_stats()
        footer.addWidget(self.lbl_stats)

        footer.addStretch()

        if not text or not text.strip():
            btn_ocr_inst = QPushButton("⚡ Instalar Motor Tesseract OCR")
            btn_ocr_inst.setToolTip("Ejecutar el instalador oficial tesseract-ocr-w64-setup.exe incluido en la aplicación")
            btn_ocr_inst.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_ocr_inst.setStyleSheet("""
                QPushButton {
                    background: #D97706;
                    color: white;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 8px 14px;
                    font-size: 12px;
                    border: none;
                }
                QPushButton:hover {
                    background: #B45309;
                }
            """)
            
            def _lanzar_instalador():
                OcrManager.ensure_env_path()

                readme = OcrManager._find_readme()
                if readme and readme.exists():
                    try:
                        if platform.system() == "Windows":
                            os.startfile(str(readme))
                    except Exception:
                        pass

                inst = OcrManager._find_installer()
                if inst and inst.exists():
                    try:
                        if platform.system() == "Windows":
                            os.startfile(str(inst))
                        else:
                            subprocess.Popen([str(inst)])
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.information(
                            self,
                            "Instalador OCR - Instrucciones Importantes",
                            "Iniciando instalador oficial de Tesseract OCR.\n\n"
                            "⚠️ RECOMENDACIÓN IMPORTANTE:\n"
                            "No alteres la ruta por defecto durante la instalación:\n"
                            "C:\\Program Files\\Tesseract-OCR\\\n\n"
                            "La aplicación agregará y validará automáticamente esa ruta en las Variables de Entorno de Windows (PATH)."
                        )
                    except Exception as err:
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "Error", f"No se pudo iniciar el instalador: {err}")
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.setWindowTitle("Motor Tesseract OCR")
                    msg.setText("<b>El motor Tesseract OCR no está instalado en el sistema.</b>")
                    msg.setInformativeText(
                        "Para habilitar el reconocimiento óptico de texto:\n\n"
                        "1. Descarga el instalador para Windows desde el sitio oficial.\n"
                        "2. Instálalo en la ruta por defecto (C:\\Program Files\\Tesseract-OCR).\n"
                        "3. MultiTool detectará el motor automáticamente sin reiniciar."
                    )
                    btn_web = msg.addButton("🌐 Descargar Tesseract OCR", QMessageBox.ButtonRole.ActionRole)
                    msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
                    msg.exec()
                    if msg.clickedButton() == btn_web:
                        QDesktopServices.openUrl(QUrl("https://github.com/UB-Mannheim/tesseract/wiki"))

            btn_ocr_inst.clicked.connect(_lanzar_instalador)
            footer.addWidget(btn_ocr_inst)

        self.btn_copy_all = QPushButton("📋 Copiar Todo")
        self.btn_copy_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_all.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['acento']};
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{
                background: {self.colores['acento_hover']};
            }}
        """)
        self.btn_copy_all.clicked.connect(self._copy_all)
        footer.addWidget(self.btn_copy_all)

        btn_close = QPushButton("Cerrar")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores['bg_terciario']};
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.15);
            }}
        """)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        layout.addLayout(footer)

    def _update_stats(self):
        content = self.txt_edit.toPlainText()
        words = len(content.split()) if content.strip() else 0
        chars = len(content)
        self.lbl_stats.setText(f"📊 {words} palabras | {chars} caracteres")

    def _copy_all(self):
        content = self.txt_edit.toPlainText()
        if content:
            QGuiApplication.clipboard().setText(content)
            self.btn_copy_all.setText("✅ ¡Copiado!")
            QTimer.singleShot(1500, lambda: self.btn_copy_all.setText("📋 Copiar Todo"))
