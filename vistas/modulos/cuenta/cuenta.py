import json
from pathlib import Path
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMessageBox, QLabel, QTextEdit, QDialog, QPushButton
from PyQt6.QtGui import QFont

from .submodulos.gui_user import GuiUser
from .submodulos.actividad import TabActividad
from .submodulos.privacidad import TabPrivacidad
from .submodulos.boveda import TabBoveda
from .submodulos.dispositivos import TabDispositivos
from .utils.autostart_helper import is_autostart_enabled, toggle_autostart

class TabCuenta(QWidget):
    """
    Módulo Core Cuenta: Suite completa de Perfil, Auditoría de Actividad,
    Privacidad & Auto-Bloqueo, Bóveda de Credenciales y Dispositivo.
    """
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        self.usuario = getattr(context, "usuario", None)
        self.persona = getattr(context, "persona", None)
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.colores = getattr(context.app, "COLORES", {})

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # TabWidget Principal del Módulo Cuenta
        self.tabs = QTabWidget()
        self._aplicar_estilo_tabs()

        # Carga dinámica de submódulos desde config.json
        from controlador.utils.submodule_loader import load_submodules_from_config
        module_dir = Path(__file__).resolve().parent
        self.submod_instances = load_submodules_from_config(module_dir, self.tabs, self, self.context, self.colores)

        # Fallback de seguridad si config.json no existiera
        if self.tabs.count() == 0:
            from .submodulos.gui_user import GuiUser
            self.gui_user = GuiUser(self, self.usuario, self.persona, self.ruta_usuario, self.colores, context=self.context)
            self.tabs.addTab(self.gui_user, "👤 Mi Perfil & Ajustes")
        else:
            self.gui_user = self.submod_instances.get("GuiUser") or self.submod_instances.get("guiuser")
            if not self.gui_user:
                from .submodulos.gui_user import GuiUser
                self.gui_user = GuiUser(self, self.usuario, self.persona, self.ruta_usuario, self.colores, context=self.context)

        main_lay.addWidget(self.tabs)

        # Vigilante global de inactividad del usuario (Idle Auto-Lock)
        try:
            from .utils.idle_lock_watcher import IdleLockWatcher
            self.idle_watcher = IdleLockWatcher(self.context, self.colores, self)
        except Exception as e:
            self.idle_watcher = None

        # Verificación automática de bloqueo por PIN al iniciar
        QTimer.singleShot(300, self._verificar_bloqueo_inicio)

        # Verificación automática de actualizaciones al iniciar
        QTimer.singleShot(1500, self._notificar_actualizaciones_si_existen)

    def _aplicar_estilo_tabs(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {bg_p};
            }}
            QTabBar::tab {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                color: #AAB0B8;
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
            QTabBar::tab:hover {{
                color: white;
            }}
        """)

    def actualizar_tema(self, colores):
        if isinstance(colores, dict):
            self.colores = colores
            self._aplicar_estilo_tabs()
            for instance in getattr(self, "submod_instances", {}).values():
                if hasattr(instance, "actualizar_tema") and callable(instance.actualizar_tema):
                    try:
                        instance.actualizar_tema(colores)
                    except Exception as e:
                        print(f"[WARN] Error actualizando tema en submódulo de Cuenta: {e}")

    def cargar_config(self):
        """Obtiene la configuración del usuario actual de manera segura y resiliente"""
        if hasattr(self, "gui_user") and hasattr(self.gui_user, "cargar_config"):
            try:
                cfg = self.gui_user.cargar_config()
                if cfg:
                    return cfg
            except Exception:
                pass
        cfg_path = self.ruta_usuario / "config.json"
        if cfg_path.exists():
            try:
                from controlador.auth.crypto_utils import process_config_for_load
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return process_config_for_load(json.load(f))
            except Exception:
                pass
        return {}

    def intentar_guardar(self):
        """Delega la confirmación y guardado de ajustes a gui_user"""
        if hasattr(self, "gui_user") and hasattr(self.gui_user, "intentar_guardar"):
            return self.gui_user.intentar_guardar()

    def _verificar_bloqueo_inicio(self):
        top_win = self.window()
        if hasattr(top_win, 'window'):
            top_win = top_win.window()

        if top_win and not top_win.isVisible():
            QTimer.singleShot(400, self._verificar_bloqueo_inicio)
            return

        cfg = self.cargar_config()
        pin = cfg.get("pin_lock")
        modo = cfg.get("pin_modo", "normal")
        # En modo 'siempre', se solicita la clave al iniciar la app.
        # En modo 'normal', NO se solicita al iniciar la app.
        if pin and modo == "siempre":
            from .utils.pin_lock_dialog import QuickPinLockDialog
            dlg = QuickPinLockDialog(pin, self.colores, top_win)
            dlg.exec()

    def activar_funcion_secreta_autostart(self, habilitar: bool = True):
        """Activa o desactiva la función secreta para iniciar con Windows"""
        return toggle_autostart(habilitar)

    def es_autostart_activo(self) -> bool:
        """Verifica si el inicio automático con Windows está activo"""
        return is_autostart_enabled()

    def verificar_actualizaciones_pendientes(self):
        """
        Escanea la versión local (utils/version.json) de todos los módulos
        y la compara con el catálogo oficial/web (data.json o public)
        para detectar si hay actualizaciones pendientes.
        """
        modulos_pendientes = []
        base_dir = self.ruta_usuario.parent if self.ruta_usuario.name == "cuentas" else self.ruta_usuario
        if base_dir.name == "multitool1":
            app_root = base_dir
        else:
            app_root = base_dir.parent

        candidatos_data = [
            app_root.parent / "pagina" / "api" / "data.json",
            app_root / "pagina" / "api" / "data.json",
            app_root / "data.json"
        ]
        data_json_path = next((c for c in candidatos_data if c.exists()), None)
        
        versiones_remotas = {}
        if data_json_path:
            try:
                with open(data_json_path, "r", encoding="utf-8") as f:
                    apps_data = json.load(f)
                item = next((a for a in apps_data if a.get("id") == "update-principal"), None)
                if item and "versions" in item:
                    for v in item["versions"]:
                        ver_full = v.get("version", "")
                        badge = v.get("badge", "").lower()
                        changelog = v.get("changelog", "")
                        
                        # Extraer versión limpia ej "21.1.0"
                        parts = ver_full.split()
                        ver_clean = parts[0].lstrip("v") if parts else "21.0.0"
                        
                        # Extraer nombre del módulo si aplica
                        mod_target = None
                        if "módulo:" in badge:
                            mod_target = badge.replace("módulo:", "").strip().lower()
                        elif v.get("modulo"):
                            mod_target = v.get("modulo").strip().lower()

                        if mod_target:
                            versiones_remotas[mod_target] = {
                                "version": ver_clean,
                                "changelog": changelog
                            }
            except Exception:
                pass

        mod_root = app_root / "vistas" / "modulos"
        if not mod_root.exists():
            return modulos_pendientes

        for mod_folder in mod_root.iterdir():
            if mod_folder.is_dir():
                mod_name = mod_folder.name.lower()
                vfile = mod_folder / "utils" / "version.json"
                ver_local = "21.0.0"
                if vfile.exists():
                    try:
                        with open(vfile, "r", encoding="utf-8") as f:
                            vdata = json.load(f)
                            ver_local = vdata.get("version", "21.0.0")
                    except Exception:
                        pass

                if mod_name in versiones_remotas:
                    info_remota = versiones_remotas[mod_name]
                    ver_remota = info_remota["version"]
                    if self._es_version_superior(ver_remota, ver_local):
                        modulos_pendientes.append({
                            "modulo": mod_name,
                            "version_actual": ver_local,
                            "version_nueva": ver_remota,
                            "descripcion": info_remota.get("changelog", "")
                        })

        return modulos_pendientes

    @staticmethod
    def _es_version_superior(v_remote, v_local):
        def parse_ver(v_str):
            clean = str(v_str).strip().lstrip("v")
            parts = clean.split(".")
            res = []
            for p in parts:
                try:
                    res.append(int(p))
                except ValueError:
                    res.append(0)
            while len(res) < 3:
                res.append(0)
            return tuple(res[:3])
        return parse_ver(v_remote) > parse_ver(v_local)

    def _notificar_actualizaciones_si_existen(self):
        try:
            pendientes = self.verificar_actualizaciones_pendientes()
            if pendientes:
                nombres = ", ".join([f"<b>{p['modulo'].capitalize()}</b> (v{p['version_nueva']})" for p in pendientes])
                changelogs = []
                for p in pendientes:
                    if p.get("descripcion"):
                        changelogs.append(f"📦 <b>Módulo {p['modulo'].capitalize()} (v{p['version_nueva']})</b>:<br>{p['descripcion']}")
                
                changelog_html = "<br><br>".join(changelogs) if changelogs else "Novedades y optimizaciones de seguridad y estabilidad."

                dlg = QMessageBox(self)
                dlg.setWindowTitle("🔔 Actualización Disponible - MultiTool")
                dlg.setIcon(QMessageBox.Icon.Information)
                dlg.setText(
                    f"✨ <b>¡Actualizaciones Pendientes Encontradas!</b><br><br>"
                    f"Se detectó una versión más reciente para {len(pendientes)} módulo(s):<br>"
                    f"• {nombres}<br><br>"
                    f"¿Deseas aplicar la actualización directamente en 1-Clic?"
                )
                
                btn_update_now = dlg.addButton("🚀 Actualizar Ahora (1-Clic)", QMessageBox.ButtonRole.AcceptRole)
                btn_changelog = dlg.addButton("📋 Ver Changelog", QMessageBox.ButtonRole.ActionRole)
                btn_close = dlg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
                
                dlg.exec()
                
                if dlg.clickedButton() == btn_update_now:
                    self._ir_a_tab_actualizaciones()
                elif dlg.clickedButton() == btn_changelog:
                    self._abrir_visor_changelog(changelog_html)
        except Exception as e:
            print(f"Error en notificaciones de actualización: {e}")

    def _ir_a_tab_actualizaciones(self):
        """Redirige al usuario a la pestaña de Actualizaciones en Inicio/General"""
        app = getattr(self.context, "app", None)
        if app and hasattr(app, "notebook"):
            for i in range(app.notebook.count()):
                if app.notebook.tabText(i).lower() in ["general", "inicio"]:
                    app.notebook.setCurrentIndex(i)
                    return

    def _abrir_visor_changelog(self, text_html):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
        from PyQt6.QtGui import QFont
        
        dlg = QDialog(self)
        dlg.setWindowTitle("📋 Registro de Cambios - MultiTool")
        dlg.resize(560, 420)
        dlg.setStyleSheet(f"background: {self.colores.get('bg_secundario', '#1E1E2E')}; color: white; border-radius: 10px;")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lbl_t = QLabel("📋 NOTAS DE LA VERSIÓN Y NOVEDADES")
        lbl_t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        lay.addWidget(lbl_t)

        view = QTextEdit()
        view.setReadOnly(True)
        view.setHtml(text_html)
        view.setStyleSheet(f"background: {self.colores.get('bg_terciario', '#2D2D3D')}; color: white; padding: 10px; border-radius: 6px; font-size: 12px;")
        lay.addWidget(view)

        btn_close = QPushButton("Entendido")
        btn_close.setStyleSheet(f"background: {self.colores.get('acento', '#6366F1')}; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; border: none;")
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.exec()
