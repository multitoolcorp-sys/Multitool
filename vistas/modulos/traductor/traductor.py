import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMessageBox, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from .submodulos.traductor_texto import TraductorTextoSubmodule
from .submodulos.traductor_documentos import TraductorDocumentosSubmodule
from .submodulos.diccionario_glosario import DiccionarioGlosarioSubmodule
from .submodulos.historial_favoritos import HistorialFavoritosSubmodule
from .submodulos.modo_conversacion import ModoConversacionSubmodule
from .utils.translator_manager import TranslatorManager


class TabTraductor(QWidget):
    """Módulo Principal de Traducción estructurado en Submódulos independientes"""
    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        self.context = context
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"

        default_colores = {
            "bg_principal": "#121218", "bg_secundario": "#1E1E2E", "bg_terciario": "#2D2D3D",
            "fg_principal": "#E2E2E2", "fg_secundario": "#AAB0B8", "acento": "#6366F1",
            "acento_hover": "#818CF8", "exito": "#34D399", "error": "#F87171", "advertencia": "#FBBF24"
        }
        passed_colores = colores or getattr(context, "colores", None) or getattr(getattr(context, "app", None), "COLORES", None) or {}
        self.colores = {**default_colores, **(passed_colores if isinstance(passed_colores, dict) else {})}

        # Callbacks para los submódulos
        self.callbacks = {
            "traducir": self.traducir,
            "detectar": self.detectar,
            "intercambiar": self.intercambiar,
            "limpiar": self.limpiar,
            "copiar": self.copiar,
            "guardar_favorito": self.guardar_favorito,
            "pronunciar_original": self.pronunciar_original,
            "pronunciar_traducido": self.pronunciar_traducido,
            "cargar_al_editor": self.cargar_al_editor
        }

        # Manager
        self.manager = TranslatorManager(context=self.context)
        self.manager.traduccion_completada.connect(self._on_traduccion_exito)
        self.manager.error_ocurrido.connect(self._on_error)
        self.manager.deteccion_completada.connect(self._on_deteccion_exito)
        self.manager.argos_status.connect(self._on_argos_status)

        self.inicializar_ui()

    def inicializar_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # TabWidget Principal de Submódulos
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont(self.font_family, 9))
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores['bg_principal']};
            }}
            QTabBar::tab {{
                background: {self.colores['bg_secundario']};
                color: #AAB0B8;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores['acento']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        # Submódulos dinámicos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        extra_kwargs = {
            "callbacks": self.callbacks,
            "manager": self.manager
        }
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores, extra_kwargs)

        if self.tabs.count() == 0:
            self.submod_texto = TraductorTextoSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_conversacion = ModoConversacionSubmodule(self, self.context, self.manager, self.colores)
            self.submod_documentos = TraductorDocumentosSubmodule(self, self.context, self.manager, self.colores)
            self.submod_diccionario = DiccionarioGlosarioSubmodule(self, self.context, self.manager, self.colores)
            self.submod_historial = HistorialFavoritosSubmodule(self, self.context, self.manager, self.colores, self.callbacks)

            self.tabs.addTab(self.submod_texto, "🔤 Texto & Voz")
            self.tabs.addTab(self.submod_conversacion, "🗣️ Conversación")
            self.tabs.addTab(self.submod_documentos, "📄 Documentos")
            self.tabs.addTab(self.submod_diccionario, "📖 Diccionario")
            self.tabs.addTab(self.submod_historial, "⭐ Historial & Favoritos")
        else:
            self.submod_texto = self.submod_instances.get("TraductorTextoSubmodule") or self.submod_instances.get("traductortextosubmodule")
            if not self.submod_texto:
                self.submod_texto = TraductorTextoSubmodule(self, self.context, self.manager, self.colores, self.callbacks)
            self.submod_conversacion = self.submod_instances.get("ModoConversacionSubmodule") or self.submod_instances.get("modoconversacionsubmodule")
            if not self.submod_conversacion:
                self.submod_conversacion = ModoConversacionSubmodule(self, self.context, self.manager, self.colores)
            self.submod_documentos = self.submod_instances.get("TraductorDocumentosSubmodule")
            self.submod_diccionario = self.submod_instances.get("DiccionarioGlosarioSubmodule")
            self.submod_historial = self.submod_instances.get("HistorialFavoritosSubmodule")

        self.gui = self.submod_texto # Alias de compatibilidad
        main_lay.addWidget(self.tabs)

        # Cargar idiomas en los combos
        if self.submod_texto and hasattr(self.submod_texto, "actualizar_idiomas"):
            self.submod_texto.actualizar_idiomas(
                self.manager.obtener_lista_formatada(incluir_auto=True),
                self.manager.obtener_lista_formatada(incluir_auto=False)
            )

        # Conectar selector de modo (Online / Offline)
        if self.submod_texto and hasattr(self.submod_texto, "combo_modo"):
            self.submod_texto.combo_modo.currentIndexChanged.connect(self._on_modo_cambiado)

    def _get_codigo(self, seleccion: str) -> str:
        if "(" in seleccion and ")" in seleccion:
            return seleccion.rsplit("(", 1)[1].rstrip(")")
        return "auto"

    def traducir(self):
        texto = self.submod_texto.panel_original.text().strip()
        if not texto:
            return
        origen = self._get_codigo(self.submod_texto.combo_origen.currentText())
        destino = self._get_codigo(self.submod_texto.combo_destino.currentText())
        self.submod_texto.lbl_estado.setText("Traduciendo...")
        self.manager.traducir(texto, origen, destino)

    def detectar(self):
        texto = self.submod_texto.panel_original.text().strip()
        if not texto:
            return
        self.submod_texto.lbl_estado.setText("Detectando idioma...")
        self.manager.detectar_idioma(texto)

    def intercambiar(self):
        idx_orig = self.submod_texto.combo_origen.currentIndex()
        txt_orig_name = self.submod_texto.combo_origen.currentText()
        if "(auto)" in txt_orig_name:
            return

        txt_dest = self.submod_texto.combo_destino.currentText()
        for i in range(self.submod_texto.combo_origen.count()):
            if self.submod_texto.combo_origen.itemText(i) == txt_dest:
                self.submod_texto.combo_origen.setCurrentIndex(i)
                break

        for i in range(self.submod_texto.combo_destino.count()):
            if self.submod_texto.combo_destino.itemText(i) == txt_orig_name:
                self.submod_texto.combo_destino.setCurrentIndex(i)
                break

        # Intercambiar textos
        t_orig = self.submod_texto.panel_original.text()
        t_trad = self.submod_texto.panel_traducido.text()
        self.submod_texto.panel_original.set_text(t_trad)
        self.submod_texto.panel_traducido.set_text(t_orig)

    def limpiar(self):
        self.submod_texto.panel_original.clear()
        self.submod_texto.panel_traducido.clear()
        self.submod_texto.lbl_estado.setText("Listo.")

    def copiar(self):
        txt = self.submod_texto.panel_traducido.text().strip()
        if txt:
            QApplication.clipboard().setText(txt)
            self.submod_texto.lbl_estado.setText("📋 ¡Copiado al portapapeles!")

    def guardar_favorito(self):
        orig = self.submod_texto.panel_original.text().strip()
        trad = self.submod_texto.panel_traducido.text().strip()
        if orig and trad:
            origen = self._get_codigo(self.submod_texto.combo_origen.currentText())
            destino = self._get_codigo(self.submod_texto.combo_destino.currentText())
            self.submod_historial.agregar_favorito(orig, trad, origen, destino)
            self.submod_texto.lbl_estado.setText("⭐ ¡Guardado en favoritos!")

    def pronunciar_original(self):
        txt = self.submod_texto.panel_original.text().strip()
        if txt:
            lang = self._get_codigo(self.submod_texto.combo_origen.currentText())
            if lang == "auto": lang = "es"
            self.manager.pronunciar(txt, lang)

    def pronunciar_traducido(self):
        txt = self.submod_texto.panel_traducido.text().strip()
        if txt:
            lang = self._get_codigo(self.submod_texto.combo_destino.currentText())
            self.manager.pronunciar(txt, lang)

    def cargar_al_editor(self, orig, trad):
        self.submod_texto.panel_original.set_text(orig)
        self.submod_texto.panel_traducido.set_text(trad)
        self.tabs.setCurrentIndex(0) # Cambiar a la pestaña de Texto

    def _on_modo_cambiado(self, idx):
        offline = (idx == 1)
        self.manager.set_modo_offline(offline)

    def _on_traduccion_exito(self, d):
        self.submod_texto.panel_traducido.set_text(d["text"])
        self.submod_texto.lbl_estado.setText("✅ Traducción completada.")
        
        # Registrar en Historial
        orig = self.submod_texto.panel_original.text().strip()
        origen = self._get_codigo(self.submod_texto.combo_origen.currentText())
        destino = self._get_codigo(self.submod_texto.combo_destino.currentText())
        if orig and d["text"]:
            self.submod_historial.agregar_historial(orig, d["text"], origen, destino)

        if d.get("dict"):
            self.submod_diccionario.set_diccionario_texto(d["dict"])

    def _on_error(self, err):
        self.submod_texto.lbl_estado.setText(f"❌ {err}")

    def _on_deteccion_exito(self, lang_code):
        for i in range(self.submod_texto.combo_origen.count()):
            if f"({lang_code})" in self.submod_texto.combo_origen.itemText(i):
                self.submod_texto.combo_origen.setCurrentIndex(i)
                break
        self.submod_texto.lbl_estado.setText(f"🔍 Idioma detectado: {lang_code}")

    def _on_argos_status(self, msg):
        self.submod_texto.lbl_estado.setText(msg)

    def actualizar_tema(self, colores: dict):
        """Actualiza la paleta de colores del módulo principal y propaga a todos los submódulos."""
        if not colores or not isinstance(colores, dict):
            return
        self.colores.update(colores)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {self.colores.get('bg_principal', '#121218')};
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: {self.colores.get('fg_secundario', '#AAB0B8')};
                padding: 10px 18px;
                font-weight: bold;
                font-size: 11px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.colores.get('acento', '#6366F1')};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255,255,255,0.08);
                color: white;
            }}
        """)

        for submod in [
            getattr(self, "submod_texto", None),
            getattr(self, "submod_conversacion", None),
            getattr(self, "submod_documentos", None),
            getattr(self, "submod_diccionario", None),
            getattr(self, "submod_historial", None)
        ]:
            if submod and hasattr(submod, "actualizar_tema"):
                try:
                    submod.actualizar_tema(self.colores)
                except Exception:
                    pass

    def cleanup(self):
        """Libera recursos y detiene procesos secundarios de todos los submódulos."""
        for submod in [
            getattr(self, "submod_texto", None),
            getattr(self, "submod_conversacion", None),
            getattr(self, "submod_documentos", None),
            getattr(self, "submod_diccionario", None),
            getattr(self, "submod_historial", None)
        ]:
            if submod and hasattr(submod, "cleanup"):
                try:
                    submod.cleanup()
                except Exception:
                    pass

        if self.manager and hasattr(self.manager, "cleanup"):
            try:
                self.manager.cleanup()
            except Exception:
                pass

