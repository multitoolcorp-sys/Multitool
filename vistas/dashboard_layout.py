"""
dashboard_layout.py - Componentes de navegación estilo Dashboard / IDE para Multitool
Permite visualizar la suite en un diseño profesional con:
- Sidebar lateral izquierdo con módulos y lista de submódulos colapsable/expandible.
  (Clic = expandir/colapsar, Doble Clic = abrir módulo/submódulo).
- Icono oficial por módulo (emoji o imagen desde config.json).
- Barra superior de pestañas activas estilo VS Code / Antigravity IDE (con botón cerrar '✕').
- Pantalla de bienvenida / Dashboard vacío al cerrar todas las pestañas (Logo, Nombre, Atajos de teclado).
"""

import os
import json
import re
import urllib.request
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QScrollArea,
    QFrame, QLabel, QSizePolicy, QToolButton, QApplication,
    QDialog, QLineEdit, QSpinBox, QFileDialog, QMessageBox, QMenu, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QCursor







# Mapa de iconos por defecto si el módulo no define uno en config.json
ICONOS_PREDETERMINADOS = {
    "general": "🏠",
    "archivos": "📁",
    "basedatos": "🗄️",
    "base de datos": "🗄️",
    "calculadora": "🧮",
    "calendario": "📅",
    "chat": "💬",
    "clipboard": "📋",
    "cuaderno": "📓",
    "cuenta": "👤",
    "emulador": "🎮",
    "extras": "🧩",
    "grabadora": "🎙️",
    "minigames": "🕹️",
    "navegador": "🌐",
    "notas": "📝",
    "proyectos": "📊",
    "reproductor": "🎬",
    "seguridad": "🛡️",
    "sistema": "⚙️",
    "terminal": "💻",
    "tiempo": "⏰",
    "traductor": "🗣️",
    "widgets": "🪟"
}


def resolver_icono_visual(icon_val, folder_name="", modulos_dir=None, ruta_usuario=None):
    """
    Resuelve un valor de icono a:
    - ('ico', ruta_ico_valida, QIcon) si es un archivo .ico
    - ('emoji', emoji_str) si es un emoji o texto
    El icono predeterminado si no se encuentra o es inválido es '🧩'.
    """
    if not icon_val:
        return ("emoji", "🧩")

    icon_str = str(icon_val).strip()

    # Si es URL a un .ico (http o https)
    if icon_str.startswith(("http://", "https://")):
        if ".ico" in icon_str.lower():
            # Buscar si ya se descargó localmente en la carpeta del módulo
            target_dirs = []
            if ruta_usuario and folder_name:
                target_dirs.append(Path(ruta_usuario) / "modulesconf" / folder_name)
            if modulos_dir and folder_name:
                target_dirs.append(Path(modulos_dir) / folder_name)

            for td in target_dirs:
                cached_ico = td / "icon_downloaded.ico"
                if cached_ico.exists():
                    return ("ico", str(cached_ico), QIcon(str(cached_ico)))

            # Si no existe, descargar
            try:
                if target_dirs:
                    dest_dir = target_dirs[0]
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    cached_ico = dest_dir / "icon_downloaded.ico"
                    urllib.request.urlretrieve(icon_str, str(cached_ico))
                    return ("ico", str(cached_ico), QIcon(str(cached_ico)))
            except Exception:
                pass
        return ("emoji", "🧩")

    # Si termina en .ico o es archivo local .ico
    if icon_str.lower().endswith(".ico"):
        # Buscar en varias rutas candidatas
        candidates = [
            Path(icon_str),
            Path.cwd() / icon_str,
        ]
        if ruta_usuario and folder_name:
            candidates.append(Path(ruta_usuario) / "modulesconf" / folder_name / icon_str)
            candidates.append(Path(ruta_usuario) / "modulesconf" / folder_name / Path(icon_str).name)
        if modulos_dir and folder_name:
            candidates.append(Path(modulos_dir) / folder_name / icon_str)
            candidates.append(Path(modulos_dir) / folder_name / Path(icon_str).name)

        for c in candidates:
            if c.exists() and c.is_file():
                return ("ico", str(c), QIcon(str(c)))

        return ("emoji", "🧩")

    # Si es un emoji o símbolo directo (como '📊', '⚙️', etc.)
    return ("emoji", icon_str)


def obtener_icono_modulo(mod_data, modulos_dir=None, ruta_usuario=None):
    """Obtiene el icono de un módulo. Si no se encuentra, retorna el icono oficial default '🧩'."""
    raw_icon = mod_data.get("icon") or mod_data.get("icono") or ""
    mod_name_key = mod_data.get("name", "").lower()
    folder_name = mod_data.get("folder", mod_name_key)

    if not raw_icon:
        # Intentar leer desde config.json en modulesconf o en modulos_dir
        cfg_candidates = []
        if ruta_usuario:
            cfg_candidates.append(Path(ruta_usuario) / "modulesconf" / folder_name / "config.json")
        if modulos_dir:
            cfg_candidates.append(Path(modulos_dir) / folder_name / "config.json")

        for cfg_p in cfg_candidates:
            if cfg_p.exists():
                try:
                    with open(cfg_p, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        raw_icon = d.get("icon") or d.get("icono") or ""
                        if raw_icon:
                            break
                except Exception:
                    pass

    if raw_icon:
        return raw_icon
    return ICONOS_PREDETERMINADOS.get(mod_name_key, "🧩")


def extraer_submodulos_modulo(mod_name, folder_name, modulos_dir=None, ruta_usuario=None):
    """
    Extrae la lista limpia de submódulos evitando duplicar el nombre del módulo.
    Prioriza la configuración guardada del usuario en modulesconf/<folder>/config.json
    y como respaldo utiliza modulos_dir/<folder>/config.json.
    """
    subs = []
    cfg_candidates = []
    if ruta_usuario and folder_name:
        cfg_candidates.append(Path(ruta_usuario) / "modulesconf" / folder_name / "config.json")
    if modulos_dir and folder_name:
        cfg_candidates.append(Path(modulos_dir) / folder_name / "config.json")

    for cfg_file in cfg_candidates:
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    raw_subs = [s.get("name", "").strip() for s in d.get("submodulos", []) if s.get("visible", True)]
                    if len(raw_subs) > 1:
                        subs = [s for s in raw_subs if s.lower() != mod_name.lower()]
                    elif len(raw_subs) == 1 and raw_subs[0].lower() != mod_name.lower():
                        subs = raw_subs
                    if subs:
                        return subs
            except Exception:
                pass

    # 2. Si no había lista en config.json, buscar llamadas addTab en el orquestador
    if modulos_dir and folder_name:
        folder_path = Path(modulos_dir) / folder_name
        for fn in [f"{folder_name}.py", "main.py"]:
            py_f = folder_path / fn
            if py_f.exists():
                try:
                    with open(py_f, "r", encoding="utf-8") as f:
                        pattern = r'addTab\s*\([^,]+,\s*["\']([^"\']+)["\']\)'
                        matches = re.findall(pattern, f.read())
                        if matches:
                            subs = [m.strip() for m in matches]
                            break
                except Exception:
                    pass

    return subs


def obtener_metadatos_submodulos(mod_name, folder_name, modulos_dir=None, ruta_usuario=None):
    """
    Obtiene la lista detallada de submódulos (con icono, alias, posición y visibilidad)
    priorizando siempre modulesconf de la cuenta del usuario.
    """
    cfg_candidates = []
    if ruta_usuario and folder_name:
        cfg_candidates.append(Path(ruta_usuario) / "modulesconf" / folder_name / "config.json")
    if modulos_dir and folder_name:
        cfg_candidates.append(Path(modulos_dir) / folder_name / "config.json")

    for cfg_file in cfg_candidates:
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    items = []
                    for idx, s in enumerate(d.get("submodulos", [])):
                        if not s.get("visible", True):
                            continue
                        s_name = s.get("name", "").strip()
                        if not s_name or (len(d.get("submodulos", [])) > 1 and s_name.lower() == mod_name.lower()):
                            continue
                        items.append({
                            "name": s_name,
                            "alias": s.get("alias", s_name.lower().replace(" ", "_")),
                            "icon": s.get("icon") or s.get("icono") or "🧩",
                            "position": s.get("position", idx + 1),
                            "visible": s.get("visible", True)
                        })
                    if items:
                        items.sort(key=lambda x: int(x.get("position", 999)))
                        return items
            except Exception:
                pass

    simples = extraer_submodulos_modulo(mod_name, folder_name, modulos_dir, ruta_usuario)
    return [{"name": sn, "alias": sn.lower().replace(" ", "_"), "icon": "🧩", "position": i + 1, "visible": True} for i, sn in enumerate(simples)]


class JsonEditorDialog(QDialog):
    """
    Editor textual avanzado del archivo config.json del módulo.
    Permite modificar directamente el contenido JSON a gusto,
    validando la sintaxis antes de guardar.
    """
    def __init__(self, parent, cfg_file_path, colores=None):
        super().__init__(parent)
        self.cfg_file_path = Path(cfg_file_path)
        self.colores = colores or {}
        self.setWindowTitle(f"🛠️ Editor Avanzado JSON - {self.cfg_file_path.name}")
        self.resize(620, 520)
        self.init_ui()

    def init_ui(self):
        bg_pri = self.colores.get("bg_principal", "#121620")
        bg_sec = self.colores.get("bg_secundario", "#1E1E2E")
        bg_ter = self.colores.get("bg_terciario", "#2D2D3D")
        acento = self.colores.get("acento", "#34D399")
        fg_pri = self.colores.get("fg_principal", "#FFFFFF")
        fg_sec = self.colores.get("fg_secundario", "#AAB0B8")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_pri};
                color: {fg_pri};
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            QLabel {{
                color: {fg_pri};
                font-size: 12px;
            }}
            QTextEdit {{
                background-color: #0F172A;
                border: 1px solid {bg_ter};
                border-radius: 6px;
                color: #F8FAFC;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }}
            QTextEdit:focus {{
                border: 1px solid {acento};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl_info = QLabel(f"📄 Editando archivo de configuración: <b>{self.cfg_file_path.name}</b><br><span style='font-size:10px; color:{fg_sec};'>{self.cfg_file_path}</span>")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {acento}; font-size: 11px;")
        layout.addWidget(lbl_info)

        self.txt_editor = QTextEdit()
        layout.addWidget(self.txt_editor, 1)

        # Estado de validación
        self.lbl_status = QLabel("Listo.")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Botonera
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_format = QPushButton("✨ Formatear / Validar")
        btn_format.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_format.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_ter};
                color: {fg_pri};
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #374151;
                color: white;
            }}
        """)
        btn_format.clicked.connect(self._formatear_json)
        btn_box.addWidget(btn_format)

        btn_reload = QPushButton("🔄 Revertir")
        btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reload.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_ter};
                color: {fg_sec};
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
            }}
            QPushButton:hover {{
                background-color: #374151;
                color: white;
            }}
        """)
        btn_reload.clicked.connect(self._cargar_archivo)
        btn_box.addWidget(btn_reload)

        btn_box.addStretch(1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {fg_sec};
                border: 1px solid {bg_ter};
                border-radius: 6px;
                padding: 7px 16px;
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Guardar JSON")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {acento};
                color: #0A0A0F;
                border: none;
                border-radius: 6px;
                padding: 7px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #55FF55;
            }}
        """)
        btn_save.clicked.connect(self._guardar_json)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

        self._cargar_archivo()

    def _cargar_archivo(self):
        if not self.cfg_file_path.exists():
            self.txt_editor.setText("{}")
            return
        try:
            content = self.cfg_file_path.read_text(encoding="utf-8")
            d = json.loads(content)
            formatted = json.dumps(d, indent=4, ensure_ascii=False)
            self.txt_editor.setText(formatted)
            self.lbl_status.setText("✅ Archivo cargado correctamente.")
            self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")
        except Exception as e:
            self.txt_editor.setText(content)
            self.lbl_status.setText(f"⚠️ Aviso al parsear: {e}")
            self.lbl_status.setStyleSheet("color: #FBBF24; font-size: 11px;")

    def _formatear_json(self):
        raw = self.txt_editor.toPlainText().strip()
        try:
            d = json.loads(raw)
            formatted = json.dumps(d, indent=4, ensure_ascii=False)
            self.txt_editor.setText(formatted)
            self.lbl_status.setText("✅ JSON válido y formateado con éxito.")
            self.lbl_status.setStyleSheet("color: #34D399; font-size: 11px;")
            return True
        except Exception as e:
            self.lbl_status.setText(f"❌ Error de sintaxis JSON: {e}")
            self.lbl_status.setStyleSheet("color: #F87171; font-size: 11px;")
            QMessageBox.warning(self, "Error de Sintaxis JSON", f"El contenido JSON tiene errores de sintaxis:\n\n{e}")
            return False

    def _guardar_json(self):
        raw = self.txt_editor.toPlainText().strip()
        try:
            data = json.loads(raw)
        except Exception as e:
            QMessageBox.critical(
                self, "Error de Sintaxis",
                f"No se puede guardar porque el JSON no es válido:\n\n{e}\n\nPor favor corrija los errores antes de guardar."
            )
            return

        try:
            self.cfg_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cfg_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Guardado", "✅ Configuración JSON guardada con éxito.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo escribir en el archivo: {e}")


class ModuleEditDialog(QDialog):
    """
    Diálogo modal para editar Nombre, Alias, Icono (.ico, URL o emoji) y Posición
    de un módulo o submódulo con vista previa interactiva en tiempo real.
    """
    def __init__(self, parent, item_data, is_submodule=False, folder_name="", modulos_dir=None, ruta_usuario=None):
        super().__init__(parent)
        self.item_data = item_data
        self.is_submodule = is_submodule
        self.folder_name = folder_name or item_data.get("folder", "")
        self.modulos_dir = modulos_dir
        self.ruta_usuario = ruta_usuario
        self.colores = getattr(parent, "colores", {}) if parent else {}

        self.setWindowTitle("✏️ Editar Submódulo" if is_submodule else "✏️ Editar Módulo")
        self.setFixedSize(480, 480)
        self.init_ui()

    def init_ui(self):
        bg_pri = self.colores.get("bg_principal", "#121620")
        bg_sec = self.colores.get("bg_secundario", "#1E1E2E")
        bg_ter = self.colores.get("bg_terciario", "#2D2D3D")
        acento = self.colores.get("acento", "#34D399")
        fg_pri = self.colores.get("fg_principal", "#FFFFFF")
        fg_sec = self.colores.get("fg_secundario", "#AAB0B8")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_pri};
                color: {fg_pri};
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            QLabel {{
                color: {fg_pri};
                font-size: 12px;
                font-weight: 500;
            }}
            QLineEdit, QSpinBox {{
                background-color: {bg_sec};
                border: 1px solid {bg_ter};
                border-radius: 6px;
                padding: 6px 10px;
                color: {fg_pri};
                font-size: 12px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1px solid {acento};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo_tipo = "Submódulo" if self.is_submodule else "Módulo"
        lbl_head = QLabel(f"⚙️ Configuración de {titulo_tipo}: {self.item_data.get('name', '')}")
        lbl_head.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {acento}; margin-bottom: 4px;")
        layout.addWidget(lbl_head)

        # 1. Nombre
        layout.addWidget(QLabel("Nombre para mostrar:"))
        self.txt_name = QLineEdit(self.item_data.get("name", ""))
        self.txt_name.setPlaceholderText("Ej: Dashboard, MiniGames, Notas...")
        self.txt_name.textChanged.connect(self._actualizar_preview)
        layout.addWidget(self.txt_name)

        # 2. Alias
        layout.addWidget(QLabel("Alias (Acceso rápido en consola /goto):"))
        self.txt_alias = QLineEdit(self.item_data.get("alias", ""))
        self.txt_alias.setPlaceholderText("Ej: dash, calc, games (se usa en consola)...")
        layout.addWidget(self.txt_alias)

        # 3. Icono
        layout.addWidget(QLabel("Icono (Emoji directo como 📊 o ruta/URL a un archivo .ico):"))
        ico_box = QHBoxLayout()
        ico_box.setSpacing(8)
        self.txt_icon = QLineEdit(str(self.item_data.get("icon", "🧩")))
        self.txt_icon.setPlaceholderText("Emoji (ej: 📊, 🧩) o ruta/URL a archivo .ico")
        self.txt_icon.textChanged.connect(self._actualizar_preview)
        ico_box.addWidget(self.txt_icon, 1)

        btn_browse = QPushButton("Examinar .ico...")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_ter};
                color: {fg_pri};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {acento};
                color: #0A0A0F;
            }}
        """)
        btn_browse.clicked.connect(self._examinar_ico)
        ico_box.addWidget(btn_browse)
        layout.addLayout(ico_box)

        # 4. Posición
        layout.addWidget(QLabel("Posición numérica:"))
        self.spn_position = QSpinBox()
        self.spn_position.setRange(1, 999)
        self.spn_position.setValue(int(self.item_data.get("position", 1)))
        layout.addWidget(self.spn_position)

        # 5. Vista Previa en Vivo (Live Preview)
        layout.addWidget(QLabel("Vista Previa en Vivo:"))
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px dashed {bg_ter};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        prev_lay = QHBoxLayout(self.preview_frame)
        prev_lay.setContentsMargins(12, 8, 12, 8)
        prev_lay.setSpacing(10)

        self.lbl_preview_icon = QLabel("🧩")
        self.lbl_preview_icon.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        prev_lay.addWidget(self.lbl_preview_icon)

        self.lbl_preview_text = QLabel(self.item_data.get("name", ""))
        self.lbl_preview_text.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {fg_pri}; border: none; background: transparent;")
        prev_lay.addWidget(self.lbl_preview_text, 1)

        layout.addWidget(self.preview_frame)

        # Botón Opciones Avanzadas (Editar JSON directamente)
        btn_advanced = QPushButton("🛠️ Opciones Avanzadas (Editar JSON)")
        btn_advanced.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_advanced.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {acento};
                border: 1px dashed {acento};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(52, 211, 153, 0.12);
            }}
        """)
        btn_advanced.clicked.connect(self._abrir_editor_json_avanzado)
        layout.addWidget(btn_advanced)

        # 6. Botones Cancelar / Guardar
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch(1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_ter};
                color: {fg_sec};
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #374151;
                color: white;
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Guardar Cambios")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {acento};
                color: #0A0A0F;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #55FF55;
            }}
        """)
        btn_save.clicked.connect(self._guardar_cambios)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

        self._actualizar_preview()

    def _examinar_ico(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Icono (.ico exclusivamente)",
            "",
            "Archivos de Icono (*.ico)"
        )
        if file_path:
            if not file_path.lower().endswith(".ico"):
                QMessageBox.warning(
                    self, "Formato no válido",
                    "Solo se admiten archivos .ico exclusivamente. No se permiten imágenes en formato .png, .jpg, etc."
                )
                return
            self.txt_icon.setText(file_path)

    def _actualizar_preview(self):
        nombre = self.txt_name.text().strip() or "Sin Nombre"
        self.lbl_preview_text.setText(nombre)

        raw_icon = self.txt_icon.text().strip() or "🧩"
        tipo, valor, *extra = resolver_icono_visual(
            raw_icon, self.folder_name, self.modulos_dir, self.ruta_usuario
        )
        if tipo == "ico" and extra:
            qicon = extra[0]
            pix = qicon.pixmap(24, 24)
            self.lbl_preview_icon.setPixmap(pix)
            self.lbl_preview_icon.setText("")
        else:
            self.lbl_preview_icon.setPixmap(QPixmap())
            self.lbl_preview_icon.setText(valor if tipo == "emoji" else "🧩")


    def _obtener_ruta_config_json(self):
        target_dir = None
        if self.ruta_usuario and self.folder_name:
            target_dir = Path(self.ruta_usuario) / "modulesconf" / self.folder_name
        elif self.modulos_dir and self.folder_name:
            target_dir = Path(self.modulos_dir) / self.folder_name

        cfg_path = (target_dir / "config.json") if target_dir else None
        if not cfg_path or not cfg_path.exists():
            if self.modulos_dir and self.folder_name:
                orig_cfg = Path(self.modulos_dir) / self.folder_name / "config.json"
                if orig_cfg.exists():
                    if target_dir:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(orig_cfg, target_dir / "config.json")
                        cfg_path = target_dir / "config.json"
                    else:
                        cfg_path = orig_cfg
        return cfg_path

    def _abrir_editor_json_avanzado(self):
        cfg_path = self._obtener_ruta_config_json()
        if not cfg_path or not cfg_path.exists():
            QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró el archivo config.json para '{self.folder_name}'.")
            return

        dlg = JsonEditorDialog(self, cfg_path, self.colores)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Recargar datos del config.json actualizado en los campos del diálogo
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if self.is_submodule:
                    for s in data.get("submodulos", []):
                        if s.get("name", "").strip().lower() == self.item_data.get("name", "").strip().lower():
                            self.txt_name.setText(s.get("name", ""))
                            self.txt_alias.setText(s.get("alias", ""))
                            self.txt_icon.setText(str(s.get("icon", "🧩")))
                            self.spn_position.setValue(int(s.get("position", 1)))
                            break
                else:
                    self.txt_name.setText(data.get("name", ""))
                    self.txt_alias.setText(data.get("alias", ""))
                    self.txt_icon.setText(str(data.get("icon", "🧩")))
                    self.spn_position.setValue(int(data.get("position", 1)))

                self._actualizar_preview()
            except Exception as e:
                print(f"[ModuleEditDialog] Error al refrescar campos: {e}")

    def _guardar_cambios(self):
        nombre = self.txt_name.text().strip()
        alias = self.txt_alias.text().strip()
        raw_icon = self.txt_icon.text().strip() or "🧩"
        posicion = self.spn_position.value()

        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre no puede estar vacío.")

        # Si no se colocó alias, tomar el nombre por defecto como slug
        if not alias:
            alias = re.sub(r'[^\w\s-]', '', nombre).strip().lower().replace(' ', '_')

        # Validación estricta de icono
        es_url = raw_icon.startswith(("http://", "https://"))
        es_archivo = ("." in raw_icon and not es_url and len(raw_icon) > 4)

        if (es_url or es_archivo) and not raw_icon.lower().endswith(".ico"):
            QMessageBox.warning(
                self, "Icono no valido",
                "El icono solo acepta archivos con extension .ico, URLs a .ico o emojis directos (ej: emoji o .ico).\nNo se admiten archivos .png, .jpg u otros."
            )
            return

        # Determinar carpeta de destino del módulo en la cuenta del usuario
        target_dir = None
        if self.ruta_usuario and self.folder_name:
            target_dir = Path(self.ruta_usuario) / "modulesconf" / self.folder_name
        elif self.modulos_dir and self.folder_name:
            target_dir = Path(self.modulos_dir) / self.folder_name

        final_icon_val = raw_icon

        # Si es un archivo .ico o URL, copiar o descargar a la carpeta del módulo eliminando el anterior
        if target_dir and (raw_icon.lower().endswith(".ico") or es_url):
            target_dir.mkdir(parents=True, exist_ok=True)
            suffix_id = f"sub_{alias}" if self.is_submodule else "mod"
            dest_ico_name = f"icon_{suffix_id}.ico"
            dest_ico_path = target_dir / dest_ico_name

            # Eliminar icono anterior si era diferente para ahorrar espacio
            try:
                for old_f in target_dir.glob(f"icon_{suffix_id}*.ico"):
                    if old_f.exists() and old_f.resolve() != dest_ico_path.resolve():
                        old_f.unlink()
            except Exception:
                pass

            if es_url:
                try:
                    urllib.request.urlretrieve(raw_icon, str(dest_ico_path))
                    final_icon_val = dest_ico_name
                except Exception as e:
                    QMessageBox.warning(self, "Error de Descarga", f"No se pudo descargar el .ico desde la URL: {e}")
                    return
            else:
                src_ico = Path(raw_icon)
                if src_ico.exists() and src_ico.is_file():
                    try:
                        shutil.copy2(src_ico, dest_ico_path)
                        final_icon_val = dest_ico_name
                    except Exception as e:
                        print(f"[EditDialog] Error al copiar .ico: {e}")

        # Guardar en config.json
        cfg_path = (target_dir / "config.json") if target_dir else None
        if not cfg_path or not cfg_path.exists():
            if self.modulos_dir and self.folder_name:
                orig_cfg = Path(self.modulos_dir) / self.folder_name / "config.json"
                if orig_cfg.exists() and target_dir:
                    shutil.copy2(orig_cfg, cfg_path)

        if cfg_path and cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)

                if self.is_submodule:
                    subs = cfg_data.get("submodulos", [])
                    found = False
                    for s in subs:
                        if s.get("name", "").strip().lower() == self.item_data.get("name", "").strip().lower():
                            s["name"] = nombre
                            s["alias"] = alias
                            s["icon"] = final_icon_val
                            s["position"] = posicion
                            found = True
                            break
                    if not found and subs:
                        subs[0]["name"] = nombre
                        subs[0]["alias"] = alias
                        subs[0]["icon"] = final_icon_val
                        subs[0]["position"] = posicion
                    cfg_data["submodulos"] = subs
                else:
                    cfg_data["name"] = nombre
                    cfg_data["alias"] = alias
                    cfg_data["icon"] = final_icon_val
                    cfg_data["position"] = posicion

                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg_data, f, indent=4, ensure_ascii=False)

            except Exception as e:
                QMessageBox.critical(self, "Error al guardar", f"No se pudo actualizar config.json: {e}")
                return

        # Actualizar estructura en memoria
        self.item_data["name"] = nombre
        self.item_data["alias"] = alias
        self.item_data["icon"] = final_icon_val
        self.item_data["position"] = posicion

        self.accept()


class DashboardSidebar(QFrame):
    """
    Sidebar lateral izquierdo con módulos y lista de submódulos colapsable/expandible.
    - Soporta redimensión arrastrando su borde derecho (mínimo 160px para no tapar iconos).
    - Botón de colapso superior colocado arriba (ancho colapsado de 30px ultra compacto).
    - Secciones independientes y plegables: '📦 MODULES' y '🛠️ TOOLBAR'.
    - Indicador de estado por módulo: 🟢 iniciado / 🔴 en reposo.
    - Clic simple: expande o contrae la lista de submódulos.
    - Doble clic: abre la pestaña del módulo/submódulo seleccionado.
    """
    submoduleSelected = pyqtSignal(str, str, int, int) # (mod_name, sub_name, mod_idx, sub_idx)

    def __init__(self, parent=None, colores=None, modulos_dir=None):
        super().__init__(parent)
        self.main_window = parent
        self.colores = colores or {}
        self.modulos_dir = modulos_dir
        self.ruta_usuario = None
        self.modulos = []
        self._secciones_expandidas = set()
        self._mod_sub_frames = {} # mod_key -> QWidget (sub_frame)
        self._mod_header_buttons = {} # mod_key -> QPushButton (header_btn)
        self._active_mod_name = ""
        self._active_sub_name = ""
        self.is_collapsed = False
        
        # Redimensión del sidebar
        self.min_sidebar_width = 165
        self.max_sidebar_width = 450
        self.current_width = 240
        self._is_resizing = False
        self._resize_start_x = 0
        self._resize_start_w = 240

        # Estado plegable de secciones
        self._seccion_modules_visible = True
        self._seccion_toolbar_visible = True

        self._mod_sub_frames = {}
        self._mod_header_buttons = {}
        self._mod_sub_items = {}

        self.setMouseTracking(True)
        self.init_ui()

    def init_ui(self):
        self.setFixedWidth(self.current_width)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-right: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header superior del Sidebar
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(34)
        self.header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border-bottom: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
            }}
        """)
        self.h_layout = QHBoxLayout(self.header_frame)
        self.h_layout.setContentsMargins(10, 0, 4, 0)
        self.h_layout.setSpacing(4)

        self.lbl_title = QLabel("EXPLORADOR")
        self.lbl_title.setStyleSheet(f"""
            color: {self.colores.get('fg_secundario', '#AAB0B8')};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 0.5px;
            border: none;
        """)
        self.h_layout.addWidget(self.lbl_title, 1)

        # Botón colapso arriba
        self.btn_collapse = QPushButton("◀")
        self.btn_collapse.setFixedSize(22, 22)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.btn_collapse.setToolTip("Contraer / Expandir Explorador")
        self.btn_collapse.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colores.get('bg_terciario', '#2D2D3D')};
                color: white;
            }}
        """)
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        self.h_layout.addWidget(self.btn_collapse)

        self.main_layout.addWidget(self.header_frame)

        # Barra de Búsqueda / Filtro en Vivo del Explorador
        self.filter_container = QFrame()
        self.filter_container.setFixedHeight(32)
        self.filter_container.setStyleSheet("background: transparent; border: none; padding: 2px 4px;")
        f_lay = QHBoxLayout(self.filter_container)
        f_lay.setContentsMargins(4, 2, 4, 2)
        f_lay.setSpacing(4)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Filtrar módulos...")
        self.txt_filter.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colores.get('bg_principal', '#121218')};
                color: {self.colores.get('fg_principal', '#FFFFFF')};
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self.renderizar_arbol)
        self.txt_filter.textChanged.connect(lambda _: self._filter_timer.start(160))
        f_lay.addWidget(self.txt_filter, 1)

        self.btn_clear_filter = QPushButton("✕")
        self.btn_clear_filter.setFixedSize(16, 16)
        self.btn_clear_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_filter.setStyleSheet("border: none; background: transparent; color: #AAB0B8; font-size: 9px;")
        self.btn_clear_filter.clicked.connect(lambda: self.txt_filter.clear())
        f_lay.addWidget(self.btn_clear_filter)

        self.main_layout.addWidget(self.filter_container)

        # Scroll Area con la lista de módulos y submódulos
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colores.get('bg_terciario', '#3D3D3D')};
                min-height: 18px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.colores.get('acento', '#6366F1')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(2)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area, 1)

    # --- Soporte de Redimensión Manual por el Borde Derecho ---
    def mouseMoveEvent(self, event):
        if not self.is_collapsed:
            if self._is_resizing:
                delta = event.globalPosition().x() - self._resize_start_x
                new_w = max(self.min_sidebar_width, min(self.max_sidebar_width, int(self._resize_start_w + delta)))
                self.current_width = new_w
                self.setFixedWidth(new_w)
                event.accept()
                return
            else:
                if event.pos().x() >= self.width() - 6:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if not self.is_collapsed and event.button() == Qt.MouseButton.LeftButton:
            if event.pos().x() >= self.width() - 6:
                self._is_resizing = True
                self._resize_start_x = event.globalPosition().x()
                self._resize_start_w = self.width()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_resizing:
            self._is_resizing = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _get_main_window(self):
        """Obtiene de forma confiable la ventana principal MainWindow."""
        w = self.window()
        if hasattr(w, "notebook") or hasattr(w, "mostrar_log_actualizaciones"):
            return w
        if hasattr(self, "main_window") and self.main_window:
            return self.main_window
        p = self.parent()
        while p is not None:
            if hasattr(p, "notebook") or hasattr(p, "mostrar_log_actualizaciones"):
                return p
            p = p.parent()
        return None

    def _get_ruta_usuario(self):
        if self.ruta_usuario:
            return self.ruta_usuario
        mw = self._get_main_window()
        if mw:
            if hasattr(mw, "ruta_usuario"):
                return mw.ruta_usuario
            if hasattr(mw, "context") and hasattr(mw.context, "ruta_usuario"):
                return mw.context.ruta_usuario
        return None

    def toggle_collapse(self):
        """Alterna el estado colapsado. Cuando está colapsado, el botón se ubica arriba centrado."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(30) # Compacto
            self.lbl_title.hide()
            if hasattr(self, "filter_container"): self.filter_container.hide()
            self.h_layout.setContentsMargins(4, 0, 4, 0)
            self.btn_collapse.setText("▶")
            self.scroll_area.hide()
        else:
            self.setFixedWidth(self.current_width)
            self.lbl_title.show()
            if hasattr(self, "filter_container"): self.filter_container.show()
            self.h_layout.setContentsMargins(10, 0, 4, 0)
            self.btn_collapse.setText("◀")
            self.scroll_area.show()

    def set_modulos(self, modulos_cargados, active_mod_name="", active_sub_name=""):
        nuevos_modulos = [m for m in modulos_cargados if m.get("visible", True)]
        nombres_actuales = [m.get("name") for m in getattr(self, "modulos", [])]
        nombres_nuevos = [m.get("name") for m in nuevos_modulos]

        self.modulos = nuevos_modulos
        if active_mod_name:
            self._active_mod_name = active_mod_name
        if active_sub_name:
            self._active_sub_name = active_sub_name

        if nombres_actuales == nombres_nuevos and getattr(self, "_mod_sub_frames", None):
            self._actualizar_seleccion_visual()
            self._actualizar_badges()
        else:
            self.renderizar_arbol()

    def renderizar_arbol(self):
        # Limpiar widgets actuales
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._mod_sub_frames.clear()
        self._mod_header_buttons.clear()
        self._mod_sub_items.clear()

        acento = self.colores.get('acento', '#6366F1')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')
        fg_pri = self.colores.get('fg_principal', '#FFFFFF')
        fg_sec = self.colores.get('fg_secundario', '#AAB0B8')

        ruta_u = self._get_ruta_usuario()
        filtro_texto = self.txt_filter.text().strip().lower() if hasattr(self, "txt_filter") else ""

        # =====================================================================
        # SECCIÓN 1: 📦 MODULES (Plegable con un clic)
        # =====================================================================
        btn_sec_modules = QPushButton(f"{'▼' if self._seccion_modules_visible else '▶'}  📦 MODULES")
        btn_sec_modules.setFixedHeight(24)
        btn_sec_modules.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sec_modules.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                background: transparent;
                color: {fg_sec};
                border: none;
                border-radius: 4px;
                padding-left: 6px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.8px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
            }}
        """)
        def _toggle_modules_sec():
            self._seccion_modules_visible = not self._seccion_modules_visible
            self.container_modules.setVisible(self._seccion_modules_visible)
            btn_sec_modules.setText(f"{'▼' if self._seccion_modules_visible else '▶'}  📦 MODULES")
        btn_sec_modules.clicked.connect(_toggle_modules_sec)
        self.content_layout.addWidget(btn_sec_modules)

        self.container_modules = QWidget()
        self.container_modules.setStyleSheet("background: transparent;")
        lay_modules = QVBoxLayout(self.container_modules)
        lay_modules.setContentsMargins(0, 0, 0, 0)
        lay_modules.setSpacing(2)

        for mod_idx, mod in enumerate(self.modulos):
            mod_name = mod.get("name", "")
            folder_name = mod.get("folder", mod_name.lower())
            icon_str = obtener_icono_modulo(mod, self.modulos_dir, ruta_u)
            sub_items = obtener_metadatos_submodulos(mod_name, folder_name, self.modulos_dir, ruta_u)

            # Filtrar si hay búsqueda activa
            if filtro_texto:
                mod_coincide = filtro_texto in mod_name.lower() or filtro_texto in mod.get("alias", "").lower()
                subs_filtrados = [s for s in sub_items if filtro_texto in s["name"].lower() or filtro_texto in s.get("alias", "").lower()]
                if not mod_coincide and not subs_filtrados:
                    continue
                if subs_filtrados:
                    sub_items = subs_filtrados
                    self._secciones_expandidas.add(mod_name.lower())

            is_active_mod = (mod_name.lower() == self._active_mod_name.lower())
            if is_active_mod:
                self._secciones_expandidas.add(mod_name.lower())
            is_expanded = mod_name.lower() in self._secciones_expandidas

            # Círculo de estado iniciado (🟢) o reposo (🔴) y conteo de submódulos abiertos/totales (X/Y)
            is_loaded = mod.get("loaded", False)
            status_circle = "🟢" if is_loaded else "🔴"
            total_subs = max(1, len(sub_items))
            abiertos = 0
            if is_loaded:
                mw = self._get_main_window()
                if mw and hasattr(mw, "editor_tab_bar") and getattr(mw, "modo_vista", "") == "dashboard":
                    abiertos = sum(1 for t in mw.editor_tab_bar.tabs if t.get("mod_name", "").lower() == mod_name.lower())
                else:
                    cont = getattr(mw, "clases_modulos", {}).get(mod_name) if mw else None
                    if cont and hasattr(cont, "tabs") and hasattr(cont.tabs, "count"):
                        abiertos = cont.tabs.count()
                    elif cont:
                        abiertos = 1
                if abiertos > total_subs:
                    total_subs = abiertos

            status_badge = f"{status_circle} {abiertos}/{total_subs}"

            # Botón/Fila del módulo
            header_btn = QPushButton()
            header_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            header_btn.setProperty("is_nav_modulo", True)
            header_btn.setProperty("modulo_nombre", mod_name.capitalize())
            arrow = "▼" if is_expanded else "▶"

            tipo_ico, val_ico, *extra_ico = resolver_icono_visual(icon_str, folder_name, self.modulos_dir, ruta_u)
            if tipo_ico == "ico" and extra_ico:
                header_btn.setIcon(extra_ico[0])
                header_btn.setIconSize(QSize(15, 15))
                header_btn.setText(f" {arrow}   {mod_name.capitalize()}  {status_badge}")
            else:
                header_btn.setIcon(QIcon())
                header_btn.setText(f" {arrow}  {val_ico}  {mod_name.capitalize()}  {status_badge}")

            header_btn.setFixedHeight(28)

            mod_style = f"""
                QPushButton {{
                    text-align: left;
                    background-color: { 'rgba(99, 102, 241, 0.15)' if is_active_mod else 'transparent' };
                    color: { acento if is_active_mod else fg_pri };
                    border: none;
                    border-radius: 4px;
                    padding-left: 6px;
                    font-weight: 600;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {bg_ter};
                    color: white;
                }}
            """
            header_btn.setStyleSheet(mod_style)

            # Clic simple: expande/contrae
            header_btn.clicked.connect(lambda ch, mn=mod_name: self._on_mod_toggle_expand(mn))
            # Doble clic: abre módulo
            subs_names = [s["name"] for s in sub_items]
            header_btn.mouseDoubleClickEvent = lambda e, mn=mod_name, mi=mod_idx, sb=subs_names: self._on_mod_double_click(mn, mi, sb, e)

            # Clic derecho: editar módulo
            header_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            header_btn.customContextMenuRequested.connect(lambda pos, m=mod: self._mostrar_context_menu_modulo(m, pos))

            lay_modules.addWidget(header_btn)
            key_name = mod_name.lower()
            self._mod_header_buttons[key_name] = (header_btn, (tipo_ico, val_ico, *extra_ico), mod_name)
            self._mod_sub_items[key_name] = sub_items

            # Submódulos: siempre construimos el contenedor si existen sub_items para transiciones instantáneas sin parpadeo
            if sub_items:
                sub_frame = QWidget()
                sub_frame.setStyleSheet("background: transparent;")
                sub_layout = QVBoxLayout(sub_frame)
                sub_layout.setContentsMargins(18, 0, 0, 0)
                sub_layout.setSpacing(1)

                for sub_idx, sub_item in enumerate(sub_items):
                    sub_name = sub_item["name"]
                    is_active_sub = is_active_mod and (sub_name.lower() == self._active_sub_name.lower())

                    btn_sub = QPushButton()
                    btn_sub.setProperty("is_nav_submodulo", True)
                    btn_sub.setProperty("submodulo_nombre", sub_name)
                    btn_sub.setProperty("modulo_padre", mod_name.capitalize())

                    s_icon = sub_item.get("icon") or "🧩"
                    s_tipo, s_val, *s_extra = resolver_icono_visual(s_icon, folder_name, self.modulos_dir, ruta_u)
                    if s_tipo == "ico" and s_extra:
                        btn_sub.setIcon(s_extra[0])
                        btn_sub.setIconSize(QSize(13, 13))
                        btn_sub.setText(f"  {sub_name}")
                    else:
                        btn_sub.setIcon(QIcon())
                        btn_sub.setText(f"{s_val}  {sub_name}")

                    btn_sub.setFixedHeight(24)
                    btn_sub.setCursor(Qt.CursorShape.PointingHandCursor)

                    sub_style = f"""
                        QPushButton {{
                            text-align: left;
                            background-color: { acento if is_active_sub else 'transparent' };
                            color: { '#FFFFFF' if is_active_sub else fg_sec };
                            border: none;
                            border-radius: 4px;
                            padding-left: 6px;
                            font-size: 10px;
                            font-weight: { 'bold' if is_active_sub else 'normal' };
                        }}
                        QPushButton:hover {{
                            background-color: { acento if is_active_sub else 'rgba(255,255,255,0.06)' };
                            color: white;
                        }}
                    """
                    btn_sub.setStyleSheet(sub_style)

                    # Doble clic para abrir submódulo
                    btn_sub.mouseDoubleClickEvent = lambda e, mn=mod_name, sn=sub_name, mi=mod_idx, si=sub_idx: self._on_sub_double_click(mn, sn, mi, si, e)
                    # Clic simple marca selección visual
                    btn_sub.clicked.connect(lambda ch, mn=mod_name, sn=sub_name: self._on_sub_single_click(mn, sn))

                    # Clic derecho para editar submódulo
                    btn_sub.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    btn_sub.customContextMenuRequested.connect(
                        lambda pos, m=mod, sn=sub_name, si=sub_idx: self._mostrar_context_menu_submodulo(m, sn, si, pos)
                    )

                    sub_layout.addWidget(btn_sub)

                sub_frame.setVisible(is_expanded)
                self._mod_sub_frames[key_name] = sub_frame
                lay_modules.addWidget(sub_frame)

        self.container_modules.setVisible(self._seccion_modules_visible)
        self.content_layout.addWidget(self.container_modules)

        # =====================================================================
        # SECCIÓN 2: 🛠️ TOOLBAR (Plegable con un clic)
        # =====================================================================
        sep_frame = QFrame()
        sep_frame.setFixedHeight(1)
        sep_frame.setStyleSheet(f"background-color: {bg_ter}; margin-top: 8px; margin-bottom: 4px;")
        self.content_layout.addWidget(sep_frame)

        btn_sec_toolbar = QPushButton(f"{'▼' if self._seccion_toolbar_visible else '▶'}  🛠️ TOOLBAR")
        btn_sec_toolbar.setFixedHeight(24)
        btn_sec_toolbar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sec_toolbar.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                background: transparent;
                color: {fg_sec};
                border: none;
                border-radius: 4px;
                padding-left: 6px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.8px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: white;
            }}
        """)
        def _toggle_toolbar_sec():
            self._seccion_toolbar_visible = not self._seccion_toolbar_visible
            self.container_toolbar.setVisible(self._seccion_toolbar_visible)
            btn_sec_toolbar.setText(f"{'▼' if self._seccion_toolbar_visible else '▶'}  🛠️ TOOLBAR")
        btn_sec_toolbar.clicked.connect(_toggle_toolbar_sec)
        self.content_layout.addWidget(btn_sec_toolbar)

        self.container_toolbar = QWidget()
        self.container_toolbar.setStyleSheet("background: transparent;")
        lay_toolbar = QVBoxLayout(self.container_toolbar)
        lay_toolbar.setContentsMargins(0, 0, 0, 0)
        lay_toolbar.setSpacing(2)

        def _crear_btn_tb(texto, tooltip, on_click):
            b = QPushButton(texto)
            b.setFixedHeight(26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            # b.setToolTip(tooltip)
            b.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    background-color: transparent;
                    color: {fg_pri};
                    border: none;
                    border-radius: 4px;
                    padding-left: 8px;
                    font-size: 10px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {bg_ter};
                    color: white;
                }}
            """)
            b.clicked.connect(on_click)
            return b

        def _desplegar_menu_archivo():
            mw = self._get_main_window()
            m = QMenu(self)
            m.setStyleSheet(f"""
                QMenu {{
                    background-color: {bg_sec};
                    color: white;
                    border: 1px solid {bg_ter};
                    border-radius: 6px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 14px;
                    border-radius: 4px;
                }}
                QMenu::item:selected {{
                    background-color: {acento};
                    color: #0A0A0F;
                    font-weight: bold;
                }}
            """)
            act_mms = m.addAction("🖥️ Viewapp: MMS (MultiModulesStatics - Modo Clásico)")
            act_ide = m.addAction("💻 Viewapp: IDE (Modo Dashboard / Sidebar)")
            m.addSeparator()
            act_mtu = m.addAction("📦 Instalar Actualización (.mtu)...")
            act_comp = m.addAction("⚙️ Compilador de Actualizaciones...")
            m.addSeparator()
            act_salir = m.addAction("🚪 Salir de Multitool")

            res_act = m.exec(QCursor.pos())
            if not mw:
                return
            if res_act == act_mms and hasattr(mw, "_set_modo_vista"):
                mw._set_modo_vista("clasico")
            elif res_act == act_ide and hasattr(mw, "_set_modo_vista"):
                mw._set_modo_vista("dashboard")
            elif res_act == act_mtu and hasattr(mw, "instalar_actualizacion_mtu"):
                mw.instalar_actualizacion_mtu()
            elif res_act == act_comp and hasattr(mw, "abrir_compilador_actualizaciones"):
                mw.abrir_compilador_actualizaciones()
            elif res_act == act_salir and hasattr(mw, "salir_aplicacion"):
                mw.salir_aplicacion()

        btn_tb_archivo = _crear_btn_tb("📁 Archivo", "Opciones de archivo y vista", _desplegar_menu_archivo)
        lay_toolbar.addWidget(btn_tb_archivo)

        def _on_act_click():
            mw = self._get_main_window()
            if mw and hasattr(mw, "mostrar_log_actualizaciones"):
                mw.mostrar_log_actualizaciones()
        lay_toolbar.addWidget(_crear_btn_tb("📋 Actualizaciones", "Ver registro de actualizaciones", _on_act_click))

        def _on_aclara_click():
            mw = self._get_main_window()
            if mw and hasattr(mw, "mostrar_aclaraciones_sistema"):
                mw.mostrar_aclaraciones_sistema()
        lay_toolbar.addWidget(_crear_btn_tb("⚠️ Aclaraciones", "Avisos de sistema y rendimiento", _on_aclara_click))

        # Consola Dev
        mw_check = self._get_main_window()
        dev_active = getattr(mw_check, "_dev_mode_activo", False) if mw_check else False
        if dev_active:
            def _on_console_click():
                mw = self._get_main_window()
                if mw and hasattr(mw, "_toggle_console"):
                    mw._toggle_console()
            btn_tb_con = _crear_btn_tb("⚡ Consola Dev", "Terminal interactiva de comandos", _on_console_click)
            btn_tb_con.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    background-color: rgba(52, 211, 153, 0.12);
                    color: {acento};
                    border: 1px solid rgba(52, 211, 153, 0.3);
                    border-radius: 4px;
                    padding-left: 8px;
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {acento};
                    color: #0A0A0F;
                }}
            """)
            lay_toolbar.addWidget(btn_tb_con)

        def _on_reset_click():
            mw = self._get_main_window()
            if mw and hasattr(mw, "reiniciar_configuracion_modulos_zip"):
                mw.reiniciar_configuracion_modulos_zip()
        lay_toolbar.addWidget(_crear_btn_tb("🔄 Reiniciar Config (.ZIP)", "Copia de seguridad y restauración", _on_reset_click))

        def _on_about_click():
            mw = self._get_main_window()
            if mw and hasattr(mw, "mostrar_acerca_de"):
                mw.mostrar_acerca_de()
        lay_toolbar.addWidget(_crear_btn_tb("❓ Acerca de", "Información de Multitool", _on_about_click))

        self.container_toolbar.setVisible(self._seccion_toolbar_visible)
        self.content_layout.addWidget(self.container_toolbar)

    def _on_mod_toggle_expand(self, mod_name):
        key = mod_name.lower()
        if key in self._secciones_expandidas:
            self._secciones_expandidas.remove(key)
            expanded = False
        else:
            self._secciones_expandidas.add(key)
            expanded = True

        if key in self._mod_sub_frames:
            self._mod_sub_frames[key].setVisible(expanded)
        if key in self._mod_header_buttons:
            btn = self._mod_header_buttons[key][0]
            txt = btn.text()
            arrow = "▼" if expanded else "▶"
            if "▼" in txt:
                btn.setText(txt.replace("▼", arrow, 1))
            elif "▶" in txt:
                btn.setText(txt.replace("▶", arrow, 1))

    def _on_mod_double_click(self, mod_name, mod_idx, subs, event):
        first_sub = subs[0] if subs else ""
        self._active_mod_name = mod_name
        self._active_sub_name = first_sub
        key = mod_name.lower()
        self._secciones_expandidas.add(key)
        if key in self._mod_sub_frames:
            self._mod_sub_frames[key].setVisible(True)
        if key in self._mod_header_buttons:
            btn = self._mod_header_buttons[key][0]
            txt = btn.text()
            if "▶" in txt:
                btn.setText(txt.replace("▶", "▼", 1))
        self._actualizar_seleccion_visual()
        self.submoduleSelected.emit(mod_name, first_sub, mod_idx, 0)

    def _on_sub_single_click(self, mod_name, sub_name):
        self._active_mod_name = mod_name
        self._active_sub_name = sub_name
        self._actualizar_seleccion_visual()

    def _actualizar_badges(self):
        """Actualiza los badges de estado y conteo de submódulos en los botones sin redibujar."""
        mw = self._get_main_window()
        for mod in self.modulos:
            mod_name = mod.get("name", "")
            key = mod_name.lower()
            if key not in self._mod_header_buttons:
                continue
            btn, icon_data, name_raw = self._mod_header_buttons[key]
            is_loaded = mod.get("loaded", False)
            status_circle = "🟢" if is_loaded else "🔴"
            total_subs = max(1, len(self._mod_sub_items.get(key, [])))
            abiertos = 0
            if is_loaded:
                if mw and hasattr(mw, "editor_tab_bar") and getattr(mw, "modo_vista", "") == "dashboard":
                    abiertos = sum(1 for t in mw.editor_tab_bar.tabs if t.get("mod_name", "").lower() == key)
                else:
                    cont = getattr(mw, "clases_modulos", {}).get(mod_name) if mw else None
                    if cont and hasattr(cont, "tabs") and hasattr(cont.tabs, "count"):
                        abiertos = cont.tabs.count()
                    elif cont:
                        abiertos = 1
                if abiertos > total_subs:
                    total_subs = abiertos

            status_badge = f"{status_circle} {abiertos}/{total_subs}"
            arrow = "▼" if key in self._secciones_expandidas else "▶"
            tipo_ico, val_ico, *extra_ico = icon_data
            if tipo_ico == "ico" and extra_ico:
                btn.setText(f" {arrow}   {name_raw.capitalize()}  {status_badge}")
            else:
                btn.setText(f" {arrow}  {val_ico}  {name_raw.capitalize()}  {status_badge}")

    def _actualizar_seleccion_visual(self):
        """Actualiza el estilo visual de selección sin recrear todo el árbol de widgets."""
        acento = self.colores.get('acento', '#6366F1')
        fg_sec = self.colores.get('fg_secundario', '#AAB0B8')
        fg_pri = self.colores.get('fg_principal', '#FFFFFF')
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')

        for btn in self.findChildren(QPushButton):
            if btn.property("is_nav_modulo"):
                m_nom = (btn.property("modulo_nombre") or "").lower()
                is_active = (m_nom == self._active_mod_name.lower())
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        background-color: {'rgba(99, 102, 241, 0.15)' if is_active else 'transparent'};
                        color: {acento if is_active else fg_pri};
                        border: none;
                        border-radius: 4px;
                        padding-left: 6px;
                        font-weight: 600;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {bg_ter};
                        color: white;
                    }}
                """)
            elif btn.property("is_nav_submodulo"):
                s_nom = (btn.property("submodulo_nombre") or "").lower()
                m_padre = (btn.property("modulo_padre") or "").lower()
                is_active_sub = (m_padre == self._active_mod_name.lower()) and (s_nom == self._active_sub_name.lower())
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left;
                        background-color: {acento if is_active_sub else 'transparent'};
                        color: {'#FFFFFF' if is_active_sub else fg_sec};
                        border: none;
                        border-radius: 4px;
                        padding-left: 6px;
                        font-size: 10px;
                        font-weight: {'bold' if is_active_sub else 'normal'};
                    }}
                    QPushButton:hover {{
                        background-color: {acento if is_active_sub else 'rgba(255,255,255,0.06)'};
                        color: white;
                    }}
                """)

    def _on_sub_double_click(self, mod_name, sub_name, mod_idx, sub_idx, event):
        self._active_mod_name = mod_name
        self._active_sub_name = sub_name
        self._actualizar_seleccion_visual()
        self.submoduleSelected.emit(mod_name, sub_name, mod_idx, sub_idx)

    def _mostrar_context_menu_modulo(self, mod_data, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#34D399')};
                color: #0A0A0F;
                font-weight: bold;
            }}
        """)
        mod_name = mod_data.get("name", "Módulo")
        act_edit = menu.addAction(f"✏️ Editar Módulo '{mod_name}'...")
        act_refresh = menu.addAction("🔄 Recargar Árbol")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            self._abrir_editor_modulo(mod_data, is_submodule=False)
        elif chosen == act_refresh:
            self.renderizar_arbol()

    def _mostrar_context_menu_submodulo(self, mod_data, sub_name, sub_idx, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#34D399')};
                color: #0A0A0F;
                font-weight: bold;
            }}
        """)
        act_edit = menu.addAction(f"✏️ Editar Submódulo '{sub_name}'...")
        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit:
            folder_name = mod_data.get("folder", mod_data.get("name", "").lower())
            ruta_u = self._get_ruta_usuario()
            sub_items = obtener_metadatos_submodulos(mod_data.get("name", ""), folder_name, self.modulos_dir, ruta_u)
            target_sub = next((s for s in sub_items if s["name"].lower() == sub_name.lower()), None)
            if not target_sub:
                target_sub = {
                    "name": sub_name,
                    "position": sub_idx + 1,
                    "alias": sub_name.lower().replace(" ", "_"),
                    "icon": "🧩"
                }
            target_sub["folder"] = folder_name
            self._abrir_editor_modulo(target_sub, is_submodule=True, folder_name=folder_name)

    def _abrir_editor_modulo(self, item_data, is_submodule=False, folder_name=""):
        ruta_u = self._get_ruta_usuario()
        main_win = self._get_main_window()

        dlg = ModuleEditDialog(
            self, item_data, is_submodule=is_submodule,
            folder_name=folder_name or item_data.get("folder", ""),
            modulos_dir=self.modulos_dir, ruta_usuario=ruta_u
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.renderizar_arbol()
            if hasattr(main_win, "actualizar_menu_ver"):
                try:
                    main_win.actualizar_menu_ver(self.modulos)
                except Exception:
                    pass


class CommandPaletteDialog(QDialog):
    """
    Paleta de Comandos flotante estilo VS Code / Antigravity IDE (Ctrl+P / Ctrl+Shift+P).
    Permite buscar y abrir submódulos o ejecutar acciones del sistema rápidamente con el teclado.
    """
    submoduleRequested = pyqtSignal(str, str) # (mod_name, sub_name)
    actionRequested = pyqtSignal(str) # (action_name)

    def __init__(self, parent=None, colores=None, modulos_cargados=None):
        super().__init__(parent)
        self.main_win = parent
        self.colores = colores or {}
        self.modulos = modulos_cargados or []
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(560)
        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get("bg_principal", "#121218")
        bg_s = self.colores.get("bg_secundario", "#1E1E2E")
        bg_t = self.colores.get("bg_terciario", "#2D2D3D")
        acento = self.colores.get("acento", "#6366F1")
        fg_p = self.colores.get("fg_principal", "#FFFFFF")
        fg_s = self.colores.get("fg_secundario", "#AAB0B8")

        main_box = QVBoxLayout(self)
        main_box.setContentsMargins(8, 8, 8, 8)

        self.container_frame = QFrame(self)
        self.container_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_s};
                border: 1px solid {acento};
                border-radius: 8px;
            }}
        """)
        c_layout = QVBoxLayout(self.container_frame)
        c_layout.setContentsMargins(10, 10, 10, 10)
        c_layout.setSpacing(8)

        # Campo de entrada con icono de búsqueda
        search_box = QHBoxLayout()
        search_box.setSpacing(6)
        
        lbl_icon = QLabel("🔍")
        lbl_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        search_box.addWidget(lbl_icon)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Escribe para buscar submódulos o comandos... (Ctrl+P / Esc para cerrar)")
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_p};
                color: {fg_p};
                border: 1px solid {bg_t};
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QLineEdit:focus {{
                border: 1px solid {acento};
            }}
        """)
        self.txt_search.textChanged.connect(self._filtrar_opciones)
        search_box.addWidget(self.txt_search, 1)
        c_layout.addLayout(search_box)

        # Lista de resultados
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem
        self.list_results = QListWidget()
        self.list_results.setMaximumHeight(280)
        self.list_results.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_p};
                border: 1px solid {bg_t};
                border-radius: 6px;
                color: {fg_p};
                font-size: 11px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-radius: 4px;
                margin: 1px 0px;
            }}
            QListWidget::item:hover {{
                background-color: {bg_t};
                color: white;
            }}
            QListWidget::item:selected {{
                background-color: {acento};
                color: white;
                font-weight: bold;
            }}
        """)
        self.list_results.itemActivated.connect(self._ejecutar_seleccionado)
        c_layout.addWidget(self.list_results)

        # Footer con atajos de ayuda
        lbl_help = QLabel("↑/↓: Navegar  |  Enter: Seleccionar  |  Esc: Cerrar")
        lbl_help.setStyleSheet(f"color: {fg_s}; font-size: 9px; background: transparent; border: none; padding-left: 2px;")
        c_layout.addWidget(lbl_help)

        main_box.addWidget(self.container_frame)

    def show_centered(self):
        """Muestra la paleta centrada en la parte superior de la ventana principal."""
        if self.main_win:
            geo = self.main_win.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + 70 # 70px desde la parte superior
            self.move(x, y)
        self._cargar_catalogo()
        self._filtrar_opciones("")
        self.show()
        self.txt_search.setFocus()
        self.txt_search.selectAll()

    def _cargar_catalogo(self):
        self.catalogo = []
        # 1. Comandos globales
        self.catalogo.append({"tipo": "cmd", "id": "toggle_view", "title": "🖥️ Cambiar Vista: MMS (Clásico) ⟷ IDE (Dashboard)", "desc": "Alterna la interfaz"})
        self.catalogo.append({"tipo": "cmd", "id": "fullscreen", "title": "⛶ Alternar Pantalla Completa (F11)", "desc": "Maximiza el área de trabajo"})
        self.catalogo.append({"tipo": "cmd", "id": "console", "title": "⚡ Abrir / Alternar Consola Dev (F12)", "desc": "Terminal de comandos"})
        self.catalogo.append({"tipo": "cmd", "id": "ram_clean", "title": "🧹 Liberar Memoria RAM (Garbage Collector)", "desc": "Optimiza el consumo"})
        self.catalogo.append({"tipo": "cmd", "id": "updates", "title": "📋 Ver Registro de Actualizaciones", "desc": "Historial de versiones"})
        self.catalogo.append({"tipo": "cmd", "id": "modules_mgr", "title": "⚙️ Gestionar Módulos...", "desc": "Organizar visibilidad y orden"})
        self.catalogo.append({"tipo": "cmd", "id": "close_tab", "title": "✕ Cerrar Pestaña Actual", "desc": "Cierra la pestaña en foco"})

        # 2. Submódulos de cada módulo
        from controlador.utils.paths import get_resource_path
        mod_dir = get_resource_path() / "vistas" / "modulos"
        ruta_u = getattr(self.main_win, "ruta_usuario", None)

        for mod in self.modulos:
            if not mod.get("visible", True):
                continue
            m_name = mod.get("name", "")
            f_name = mod.get("folder", m_name.lower())
            subs = obtener_metadatos_submodulos(m_name, f_name, mod_dir, ruta_u)
            m_icon = obtener_icono_modulo(mod, mod_dir, ruta_u)
            for s in subs:
                s_name = s.get("name", "")
                s_icon = s.get("icon") or m_icon or "🧩"
                self.catalogo.append({
                    "tipo": "sub",
                    "mod_name": m_name,
                    "sub_name": s_name,
                    "icon": s_icon,
                    "title": f"{s_icon}  {m_name.capitalize()} › {s_name}",
                    "desc": f"Abrir submódulo de {m_name.capitalize()}"
                })

    def _filtrar_opciones(self, texto):
        from PyQt6.QtWidgets import QListWidgetItem
        self.list_results.clear()
        q = texto.strip().lower()

        for item in getattr(self, "catalogo", []):
            title = item.get("title", "")
            desc = item.get("desc", "")
            if not q or q in title.lower() or q in desc.lower():
                list_item = QListWidgetItem(title)
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                self.list_results.addItem(list_item)

        if self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            curr = self.list_results.currentRow()
            count = self.list_results.count()
            if count > 0:
                if key == Qt.Key.Key_Down:
                    self.list_results.setCurrentRow((curr + 1) % count)
                else:
                    self.list_results.setCurrentRow((curr - 1 + count) % count)
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._ejecutar_seleccionado(self.list_results.currentItem())
            event.accept()
        else:
            super().keyPressEvent(event)

    def _ejecutar_seleccionado(self, item):
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        self.close()
        if not data:
            return

        if data.get("tipo") == "sub":
            self.submoduleRequested.emit(data["mod_name"], data["sub_name"])
        elif data.get("tipo") == "cmd":
            cmd_id = data.get("id")
            mw = self.main_win
            if not mw:
                return
            if cmd_id == "toggle_view" and hasattr(mw, "toggle_modo_vista"):
                mw.toggle_modo_vista()
            elif cmd_id == "fullscreen" and hasattr(mw, "toggle_pantalla_completa"):
                mw.toggle_pantalla_completa()
            elif cmd_id == "console" and hasattr(mw, "_toggle_console"):
                mw._toggle_console()
            elif cmd_id == "ram_clean":
                import gc
                gc.collect()
                if hasattr(mw, "set_status"):
                    mw.set_status("✅ Memoria RAM liberada y optimizada.")
            elif cmd_id == "updates" and hasattr(mw, "mostrar_log_actualizaciones"):
                mw.mostrar_log_actualizaciones()
            elif cmd_id == "modules_mgr" and hasattr(mw, "abrir_gestor_modulos"):
                mw.abrir_gestor_modulos()
            elif cmd_id == "close_tab" and hasattr(mw, "editor_tab_bar"):
                if mw.editor_tab_bar.current_index >= 0:
                    mw.editor_tab_bar.close_tab(mw.editor_tab_bar.current_index)




class DashboardEmptyView(QWidget):
    """
    Vista de bienvenida cuando se cierran todas las pestañas en Modo Dashboard (estilo VS Code / Antigravity).
    Muestra el logo de la aplicación, el nombre y las combinaciones de teclas para navegar y abrir módulos.
    """
    def __init__(self, parent=None, colores=None, app_name="Multitool"):
        super().__init__(parent)
        self.colores = colores or {}
        self.app_name = app_name
        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        acento = self.colores.get('acento', '#6366F1')
        fg_pri = self.colores.get('fg_principal', '#FFFFFF')
        fg_sec = self.colores.get('fg_secundario', '#AAB0B8')

        self.setStyleSheet(f"background-color: {bg_p};")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        # Logo / Icono central
        lbl_logo = QLabel("🛠️")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("font-size: 56px; background: transparent; border: none;")
        lay.addWidget(lbl_logo)

        # Nombre de la App
        lbl_title = QLabel(self.app_name)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {fg_pri}; background: transparent; border: none;")
        lay.addWidget(lbl_title)

        lbl_sub = QLabel("Entorno de Trabajo Modular & Automatización")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {fg_sec}; background: transparent; border: none;")
        lay.addWidget(lbl_sub)

        # Panel de atajos de teclado estilo editor
        box_shortcuts = QFrame()
        box_shortcuts.setFixedWidth(460)
        box_shortcuts.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        bs_layout = QVBoxLayout(box_shortcuts)
        bs_layout.setSpacing(8)

        shortcuts = [
            ("Doble clic en el explorador", "Abrir cualquier módulo o submódulo"),
            ("Ctrl + T", "Buscador de comandos / Abrir módulo rápido"),
            ("Ctrl + <Número> (Enter)", "Abrir módulo por número de lista (ej: Ctrl+1, Ctrl+10)"),
            ("F1 / F12", "Abrir Consola Interactiva CLI"),
            ("F11", "Alternar Pantalla Completa")
        ]

        for key, desc in shortcuts:
            row = QHBoxLayout()
            lbl_k = QLabel(key)
            lbl_k.setStyleSheet(f"background-color: {self.colores.get('bg_terciario', '#2D2D3D')}; color: {acento}; font-family: Consolas; font-weight: bold; font-size: 11px; padding: 3px 8px; border-radius: 4px;")
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet(f"color: {fg_sec}; font-size: 11px; background: transparent; border: none;")
            row.addWidget(lbl_k)
            row.addSpacing(10)
            row.addWidget(lbl_d, 1)
            bs_layout.addLayout(row)

        lay.addWidget(box_shortcuts)


class FloatingModuleWindow(QDialog):
    """Ventana flotante independiente para trabajar con un módulo o submódulo en monitores secundarios."""
    def __init__(self, parent_main, mod_name, sub_name, display_title, colores=None):
        super().__init__(None) # Ventana nativa de nivel superior
        self.parent_main = parent_main
        self.mod_name = mod_name
        self.sub_name = sub_name
        self.colores = colores or {}
        self.widget_hosted = None
        self.original_parent = None
        self.original_layout = None
        
        self.setWindowTitle(f"{display_title} - MultiTool [Flotante]")
        self.resize(920, 620)
        self.init_ui(display_title)

    def init_ui(self, display_title):
        bg = self.colores.get("bg_principal", "#121218")
        bg_s = self.colores.get("bg_secundario", "#1E1E2E")
        acento = self.colores.get("acento", "#6366F1")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header con botón de reacoplamiento
        header = QFrame(self)
        header.setFixedHeight(34)
        header.setStyleSheet(f"background-color: {bg_s}; border-bottom: 1px solid rgba(255,255,255,0.08);")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(12, 0, 12, 0)
        
        lbl = QLabel(f"🖥️ {display_title}")
        lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        h_lay.addWidget(lbl)
        h_lay.addStretch()
        
        btn_dock = QPushButton("⬇️ Reacoplar a MultiTool")
        btn_dock.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dock.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(99, 102, 241, 0.15);
                color: {acento};
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {acento};
                color: white;
            }}
        """)
        btn_dock.clicked.connect(self.reacoplar)
        h_lay.addWidget(btn_dock)
        layout.addWidget(header)
        
        self.content_container = QWidget(self)
        self.content_container.setStyleSheet(f"background-color: {bg};")
        self.c_layout = QVBoxLayout(self.content_container)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_container, 1)

    def set_content_widget(self, widget):
        self.widget_hosted = widget
        self.original_parent = widget.parent()
        self.c_layout.addWidget(widget)

    def reacoplar(self):
        if hasattr(self, "widget_hosted") and self.widget_hosted:
            if self.original_parent and hasattr(self.original_parent, "layout") and self.original_parent.layout():
                self.original_parent.layout().addWidget(self.widget_hosted)
        if self.parent_main and hasattr(self.parent_main, "abrir_en_modulo"):
            self.parent_main.abrir_en_modulo(self.mod_name, self.sub_name)
        self.close()

    def closeEvent(self, event):
        self.reacoplar()
        super().closeEvent(event)


class DashboardTabBar(QFrame):
    """
    Barra superior de pestañas activas estilo VS Code / Antigravity IDE.
    - Soporte completo para Fijar Pestañas (Pin Tabs).
    - Menú contextual: Fijar/Desfijar, Cerrar, Cerrar demás, Cerrar a la derecha.
    - Arrastre interactivo horizontal para reordenar.
    - Scrollbar horizontal delgado y scroll con rueda del ratón.
    - Tamaño ultra compacto para maximizar el área de trabajo.
    """
    tabSelected = pyqtSignal(int)
    tabClosed = pyqtSignal(int)
    tabMoved = pyqtSignal(int, int) # (from_idx, to_idx)

    def __init__(self, parent=None, colores=None):
        super().__init__(parent)
        self.colores = colores or {}
        self.tabs = [] # Lista de dicts con metadata de pestañas
        self.current_index = -1
        self.setFixedHeight(24) # Tamaño compacto al 50%
        self.setAcceptDrops(True)
        
        self.init_ui()

    def init_ui(self):
        acento = self.colores.get('acento', '#6366F1')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_ter = self.colores.get('bg_terciario', '#2D2D3D')

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border-bottom: 1px solid {bg_ter};
            }}
        """)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 3px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {bg_ter};
                min-width: 14px;
                border-radius: 1px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {acento};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

        self.tab_container = QWidget()
        self.tab_container.setStyleSheet("background: transparent;")
        self.tab_layout = QHBoxLayout(self.tab_container)
        self.tab_layout.setContentsMargins(2, 1, 2, 0)
        self.tab_layout.setSpacing(2)
        self.tab_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.scroll_area.setWidget(self.tab_container)
        self.main_layout.addWidget(self.scroll_area)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            hbar = self.scroll_area.horizontalScrollBar()
            hbar.setValue(hbar.value() - delta)
            event.accept()
        else:
            super().wheelEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                f_path = urls[0].toLocalFile()
                pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                target_tab = None
                child = self.childAt(pos)
                while child and child != self:
                    for t in self.tabs:
                        if t.get("frame") == child or t.get("btn_tab") == child:
                            target_tab = t
                            break
                    if target_tab:
                        break
                    child = child.parent()

                if not target_tab and 0 <= self.current_index < len(self.tabs):
                    target_tab = self.tabs[self.current_index]

                if target_tab:
                    mw = getattr(self, "parent", None)
                    if not mw or not hasattr(mw, "abrir_en_modulo"):
                        mw = self.window()
                    if mw and hasattr(mw, "abrir_en_modulo"):
                        mw.abrir_en_modulo(target_tab["mod_name"], target_tab["sub_name"], ruta_archivo=f_path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def add_tab(self, mod_name, sub_name, display_title, make_active=True):
        key = (mod_name.lower(), sub_name.lower() if sub_name else "")
        for idx, t in enumerate(self.tabs):
            if t["key"] == key:
                if make_active:
                    self.set_current_index(idx)
                return idx

        tab_idx = len(self.tabs)
        tab_widget = QFrame()
        tab_widget.setFixedHeight(20)
        tab_widget.setCursor(Qt.CursorShape.PointingHandCursor)

        t_layout = QHBoxLayout(tab_widget)
        t_layout.setContentsMargins(6, 0, 4, 0)
        t_layout.setSpacing(4)

        lbl = QLabel(display_title)
        lbl.setStyleSheet("background: transparent; font-size: 9px; font-weight: 600; border: none; padding: 0px; margin: 0px;")
        t_layout.addWidget(lbl)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(12, 12)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                border: none;
                border-radius: 6px;
                font-size: 8px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.25);
                color: #EF4444;
            }}
        """)
        t_layout.addWidget(btn_close)

        tab_info = {
            "key": key,
            "title": display_title,
            "widget": tab_widget,
            "lbl": lbl,
            "btn_close": btn_close,
            "mod_name": mod_name,
            "sub_name": sub_name,
            "pinned": False
        }
        self.tabs.append(tab_info)
        self.tab_layout.addWidget(tab_widget)

        self._configurar_eventos_tab(tab_info)

        if make_active:
            self.set_current_index(tab_idx)
        else:
            self._update_styles()

        return tab_idx

    def _configurar_eventos_tab(self, tab_info):
        widget = tab_info["widget"]
        btn_close = tab_info["btn_close"]

        def _on_press(event):
            if event.button() == Qt.MouseButton.LeftButton:
                widget._drag_start_x = event.globalPosition().x()
                current_i = self._get_tab_index(tab_info)
                if current_i >= 0 and current_i != self.current_index:
                    self.set_current_index(current_i)

        def _on_move(event):
            if event.buttons() & Qt.MouseButton.LeftButton and not tab_info.get("pinned", False):
                start_x = getattr(widget, "_drag_start_x", None)
                if start_x is not None:
                    curr_x = event.globalPosition().x()
                    delta_x = curr_x - start_x
                    curr_i = self._get_tab_index(tab_info)
                    if curr_i >= 0:
                        # Si es arrastrada sobre otra no-fijada
                        if delta_x > 25 and curr_i < len(self.tabs) - 1:
                            widget._drag_start_x = curr_x
                            self.mover_tab(curr_i, curr_i + 1)
                        elif delta_x < -25 and curr_i > 0:
                            # Prevenir mover antes de pestañas fijadas si esta no lo está
                            prev_is_pinned = self.tabs[curr_i - 1].get("pinned", False)
                            if not prev_is_pinned:
                                widget._drag_start_x = curr_x
                                self.mover_tab(curr_i, curr_i - 1)

        def _on_release(event):
            widget._drag_start_x = None

        widget.mousePressEvent = _on_press
        widget.mouseMoveEvent = _on_move
        widget.mouseReleaseEvent = _on_release

        # Menú contextual de clic derecho (Fijar / Cerrar / Cerrar demás)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(lambda pos, t=tab_info: self._mostrar_context_menu_tab(t, pos))

        try:
            btn_close.clicked.disconnect()
        except Exception:
            pass
        btn_close.clicked.connect(lambda: self.close_tab(self._get_tab_index(tab_info)))

    def _mostrar_context_menu_tab(self, tab_info, pos):
        curr_i = self._get_tab_index(tab_info)
        if curr_i < 0:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: white;
                border: 1px solid {self.colores.get('bg_terciario', '#2D2D3D')};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 14px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.colores.get('acento', '#6366F1')};
                color: white;
                font-weight: bold;
            }}
            QMenu::item:disabled {{
                color: #555566;
            }}
        """)

        is_pinned = tab_info.get("pinned", False)
        act_pin = menu.addAction("📌 Desfijar Pestaña" if is_pinned else "📌 Fijar Pestaña")
        act_popout = menu.addAction("🖥️ Desacoplar a ventana flotante")
        menu.addSeparator()
        act_close = menu.addAction("✕ Cerrar Pestaña")
        act_close.setEnabled(not is_pinned)
        act_close_others = menu.addAction("✕ Cerrar las demás pestañas")
        act_close_right = menu.addAction("✕ Cerrar pestañas a la derecha")

        chosen = menu.exec(QCursor.pos())
        if chosen == act_pin:
            self.toggle_pin_tab(curr_i)
        elif chosen == act_popout:
            self.desacoplar_pestana(curr_i)
        elif chosen == act_close:
            self.close_tab(curr_i)
        elif chosen == act_close_others:
            self.close_other_tabs(curr_i)
        elif chosen == act_close_right:
            self.close_tabs_to_right(curr_i)

    def desacoplar_pestana(self, idx):
        """Desacopla la pestaña a una ventana flotante independiente."""
        if idx < 0 or idx >= len(self.tabs):
            return
        tab_info = self.tabs[idx]
        mod_name = tab_info["mod_name"]
        sub_name = tab_info["sub_name"]
        display_title = tab_info.get("title", f"{mod_name} › {sub_name}")
        
        mw = getattr(self, "main_win", None) or self.window()
        cont = getattr(mw, "clases_modulos", {}).get(mod_name) if mw else None
        target_widget = None
        if cont and hasattr(cont, "tabs") and isinstance(cont.tabs, QWidget):
            for i in range(cont.tabs.count()):
                if cont.tabs.tabText(i).strip().lower() == sub_name.strip().lower():
                    target_widget = cont.tabs.widget(i)
                    break
        elif cont:
            target_widget = cont

        if target_widget and mw:
            float_win = FloatingModuleWindow(mw, mod_name, sub_name, display_title, self.colores)
            float_win.set_content_widget(target_widget)
            float_win.show()
            self.close_tab(idx)

    def toggle_pin_tab(self, idx):
        if 0 <= idx < len(self.tabs):
            tab = self.tabs[idx]
            new_state = not tab.get("pinned", False)
            tab["pinned"] = new_state

            # Si se fija, mover al inicio de las fijadas
            if new_state:
                # Contar fijadas existentes
                pinned_count = sum(1 for t in self.tabs if t.get("pinned", False)) - 1
                if idx != pinned_count:
                    self.mover_tab(idx, pinned_count)
            self._update_styles()

    def close_other_tabs(self, keep_idx):
        if 0 <= keep_idx < len(self.tabs):
            keep_tab = self.tabs[keep_idx]
            to_remove = [i for i, t in enumerate(self.tabs) if i != keep_idx and not t.get("pinned", False)]
            for i in reversed(to_remove):
                self.close_tab(i)

    def close_tabs_to_right(self, from_idx):
        if 0 <= from_idx < len(self.tabs):
            to_remove = [i for i in range(from_idx + 1, len(self.tabs)) if not self.tabs[i].get("pinned", False)]
            for i in reversed(to_remove):
                self.close_tab(i)

    def _get_tab_index(self, tab_info):
        try:
            return self.tabs.index(tab_info)
        except ValueError:
            return -1

    def mover_tab(self, from_idx, to_idx):
        if from_idx < 0 or to_idx < 0 or from_idx >= len(self.tabs) or to_idx >= len(self.tabs) or from_idx == to_idx:
            return

        item = self.tabs.pop(from_idx)
        self.tabs.insert(to_idx, item)

        self.tab_layout.removeWidget(item["widget"])
        self.tab_layout.insertWidget(to_idx, item["widget"])

        if self.current_index == from_idx:
            self.current_index = to_idx
        elif from_idx < self.current_index <= to_idx:
            self.current_index -= 1
        elif to_idx <= self.current_index < from_idx:
            self.current_index += 1

        self._update_styles()
        self.tabMoved.emit(from_idx, to_idx)

    def set_current_index(self, idx):
        if 0 <= idx < len(self.tabs):
            self.current_index = idx
            self._update_styles()
            self.tabSelected.emit(idx)
            self.scroll_area.ensureWidgetVisible(self.tabs[idx]["widget"])

    def close_tab(self, idx):
        if 0 <= idx < len(self.tabs):
            # No permitir cerrar si está fijada
            if self.tabs[idx].get("pinned", False):
                return

            item = self.tabs.pop(idx)
            item["widget"].deleteLater()

            self.tabClosed.emit(idx)

            if len(self.tabs) > 0:
                new_idx = min(idx, len(self.tabs) - 1)
                self.set_current_index(new_idx)
            else:
                self.current_index = -1
                self.tabSelected.emit(-1)

    def _update_styles(self):
        acento = self.colores.get('acento', '#6366F1')
        bg_pri = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        fg_pri = self.colores.get('fg_principal', '#FFFFFF')
        fg_sec = self.colores.get('fg_secundario', '#AAB0B8')

        for idx, t in enumerate(self.tabs):
            is_active = (idx == self.current_index)
            is_pinned = t.get("pinned", False)
            w = t["widget"]
            lbl = t["lbl"]
            btn_close = t["btn_close"]

            # Si está fijada, ocultar botón cerrar y mostrar icono 📌
            if is_pinned:
                btn_close.hide()
                clean_title = t["title"].replace("📌 ", "")
                lbl.setText(f"📌 {clean_title}")
            else:
                btn_close.show()
                clean_title = t["title"].replace("📌 ", "")
                lbl.setText(clean_title)

            if is_active:
                w.setStyleSheet(f"""
                    QFrame {{
                        background-color: {bg_pri};
                        border-top: 2px solid {acento};
                        border-left: 1px solid rgba(255,255,255,0.06);
                        border-right: 1px solid rgba(255,255,255,0.06);
                        border-bottom: none;
                        border-top-left-radius: 3px;
                        border-top-right-radius: 3px;
                    }}
                """)
                lbl.setStyleSheet(f"color: {fg_pri}; font-weight: bold; font-size: 9px; background: transparent; padding: 0px;")
            else:
                w.setStyleSheet(f"""
                    QFrame {{
                        background-color: {bg_sec};
                        border-top: 2px solid transparent;
                        border-left: 1px solid transparent;
                        border-right: 1px solid transparent;
                        border-bottom: 1px solid rgba(255,255,255,0.05);
                        border-radius: 0px;
                    }}
                    QFrame:hover {{
                        background-color: rgba(255,255,255,0.04);
                    }}
                """)
                lbl.setStyleSheet(f"color: {fg_sec}; font-weight: normal; font-size: 9px; background: transparent; padding: 0px;")

