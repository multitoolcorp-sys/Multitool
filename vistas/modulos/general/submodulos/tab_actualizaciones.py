"""
tab_actualizaciones.py
Sub-módulo de Actualizaciones para el módulo Inicio.
Consulta la API/Catálogo web de MultiToolCorp y muestra la lista completa de actualizaciones y parches disponibles.
"""
import json
import webbrowser
import urllib.request
import urllib.error
from pathlib import Path
import sys
import ssl
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QApplication,
    QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QCursor


# ─── URL del servidor ────────────────────────────────────────────────────────
API_BASE = "https://multitool-cyan.vercel.app/api"
WEB_URL = "https://multitool-cyan.vercel.app"


# ─── Logger para Diagnóstico de Actualizaciones (update_web_log.json) ───────
def get_update_log_path() -> Path:
    """Devuelve la ruta canónica del archivo update_web_log.json"""
    try:
        submod_dir = Path(__file__).resolve().parent
        return submod_dir / "update_web_log.json"
    except Exception:
        return Path.cwd() / "update_web_log.json"

def log_debug(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = get_update_log_path()
    
    entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"last_updated": timestamp, "events": []}
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {"last_updated": timestamp, "events": []}
            except Exception:
                data = {"last_updated": timestamp, "events": []}
                
        events = data.get("events", [])
        events.append(entry)
        if len(events) > 100:
            events = events[-100:]
            
        data["last_updated"] = timestamp
        data["events"] = events
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ─── Worker thread para no bloquear la UI ───────────────────────────────────
class FetchWorker(QThread):
    data_ready   = pyqtSignal(list)   # emite lista de actualizaciones
    fetch_error  = pyqtSignal(str)    # emite mensaje de error

    def run(self):
        log_debug("=== Iniciando consulta de actualizaciones (FetchWorker) ===")
        log_debug(f"Archivo de log activo: {get_update_log_path()}")
        updates = []
        fetched = False
        errors_log = []

        # Intentar consultar servidor remoto
        urls_to_try = [
            f"{API_BASE}/apps",
            "https://multitoolcorp.vercel.app/api/apps",
            "https://multitool-kx2nkoydn-multicorp-s-projects.vercel.app/api/apps",
        ]

        # Contexto SSL desinhibido para ejecutables compilados con Nuitka en Windows
        try:
            ssl_ctx = ssl._create_unverified_context()
            log_debug("SSL Context: unverified context creado con éxito.")
        except Exception as e_ssl:
            try:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
                log_debug(f"SSL Context fallback unverified: {e_ssl}")
            except Exception as e_ssl2:
                ssl_ctx = None
                log_debug(f"SSL Context ERROR: No se pudo crear contexto SSL: {e_ssl2}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MultiToolApp/4.0",
            "Accept": "application/json"
        }

        remote_success = False
        for url in urls_to_try:
            log_debug(f"Intentando conectar a remoto: {url}")
            try:
                req = urllib.request.Request(url, headers=headers)
                kwargs = {"timeout": 8}
                if ssl_ctx:
                    kwargs["context"] = ssl_ctx

                with urllib.request.urlopen(req, **kwargs) as resp:
                    status_code = getattr(resp, 'status', 200)
                    log_debug(f"Respuesta HTTP {status_code} recibida de {url}")
                    raw = resp.read().decode("utf-8")
                    apps_data = json.loads(raw)
                    if isinstance(apps_data, list):
                        remote_success = True
                        updates = self._extract_updates(apps_data)
                        if updates:
                            fetched = True
                            log_debug(f"ÉXITO REMOTO: Se obtuvieron {len(updates)} parches desde {url}")
                            break
                        else:
                            log_debug("Respuesta JSON recibida pero no contiene parches en update-principal (Catálogo remoto vacío).")
                    else:
                        log_debug("La respuesta JSON remota no es una lista válida.")
            except Exception as e:
                err_msg = f"{url} → [{type(e).__name__}]: {e}"
                errors_log.append(err_msg)
                log_debug(f"ERROR conectando a remoto: {err_msg}")
                continue

        # Si no se obtuvieron parches del remoto, intentar buscar localmente en distintas rutas posibles
        if not fetched:
            log_debug("Buscando catálogo en fallbacks locales...")
            rutas_fallback = []
            try:
                from controlador.utils.paths import get_resource_path
                base_res = get_resource_path()
                rutas_fallback.extend([
                    base_res / "data.json",
                    base_res.parent / "pagina" / "api" / "data.json",
                    base_res / "pagina" / "api" / "data.json",
                ])
            except Exception as e_res:
                log_debug(f"Error evaluando get_resource_path: {e_res}")

            try:
                exe_dir = Path(sys.executable).resolve().parent
                rutas_fallback.extend([
                    exe_dir / "data.json",
                    exe_dir / "pagina" / "api" / "data.json",
                    exe_dir.parent / "pagina" / "api" / "data.json",
                    exe_dir.parent / "multitool" / "pagina" / "api" / "data.json",
                ])
            except Exception as e_exe:
                log_debug(f"Error evaluando rutas de exe: {e_exe}")

            try:
                cwd_dir = Path.cwd()
                rutas_fallback.extend([
                    cwd_dir / "pagina" / "api" / "data.json",
                    cwd_dir / "data.json",
                    cwd_dir.parent / "pagina" / "api" / "data.json",
                    cwd_dir.parent / "multitool" / "pagina" / "api" / "data.json",
                ])
            except Exception as e_cwd:
                log_debug(f"Error evaluando rutas CWD: {e_cwd}")

            try:
                file_dir = Path(__file__).resolve()
                for parent_dir in file_dir.parents:
                    candidate_p1 = parent_dir / "pagina" / "api" / "data.json"
                    candidate_p2 = parent_dir / "multitool" / "pagina" / "api" / "data.json"
                    candidate_p3 = parent_dir / "multitool1" / "pagina" / "api" / "data.json"
                    for c in [candidate_p1, candidate_p2, candidate_p3]:
                        if c not in rutas_fallback:
                            rutas_fallback.append(c)
            except Exception as e_file:
                log_debug(f"Error evaluando ruta __file__: {e_file}")

            for candidate in rutas_fallback:
                try:
                    log_debug(f"Comprobando fallback local: {candidate}")
                    if candidate.exists():
                        with open(candidate, "r", encoding="utf-8") as f:
                            apps_data = json.load(f)
                            updates = self._extract_updates(apps_data)
                            if updates:
                                fetched = True
                                log_debug(f"ÉXITO FALLBACK LOCAL: Se cargaron {len(updates)} parches desde {candidate}")
                                break
                    else:
                        log_debug(f"No existe fallback: {candidate}")
                except Exception as fb_e:
                    err_fb = f"Fallback {candidate.name}: [{type(fb_e).__name__}] {fb_e}"
                    errors_log.append(err_fb)
                    log_debug(f"ERROR en fallback local: {err_fb}")
                    continue

        if fetched or remote_success:
            log_debug(f"=== Proceso finalizado con ÉXITO ({len(updates)} parches disponibles) ===")
            self.data_ready.emit(updates)
        else:
            detail = "\n".join(errors_log) if errors_log else "No se encontraron parches en el servidor remoto ni en archivos locales."
            log_debug(f"=== Proceso finalizado con ERROR ===\n{detail}")
            self.fetch_error.emit(detail)

    def _extract_updates(self, apps_data: list) -> list:
        if not isinstance(apps_data, list):
            return []

        # 1. Buscar primero en update-principal
        update_app = next((a for a in apps_data if a.get("id") == "update-principal"), None)
        versions = []
        if update_app:
            versions = list(update_app.get("versions", []))

        # 2. Si update-principal no tiene versiones, recopilar de todos los ítems en apps_data
        if not versions:
            for app_item in apps_data:
                if isinstance(app_item, dict) and "versions" in app_item:
                    for v in app_item.get("versions", []):
                        if v not in versions:
                            versions.append(v)

        result = []
        for idx, v in enumerate(versions):
            url = v.get("url", "")
            if url.startswith("/"):
                url = f"{WEB_URL}{url}"

            badge = v.get("badge", "Actualización")
            version_str = v.get("version", f"v1.0.{idx}")

            result.append({
                "id": f"upd-{version_str}-{idx}",
                "version": version_str,
                "badge": badge,
                "title": f"Parche: {badge}",
                "description": v.get("changelog", "Actualización del sistema / módulos."),
                "date": v.get("releaseDate", ""),
                "size": v.get("size", ""),
                "url": url
            })
        return result


# ─── Widget principal ────────────────────────────────────────────────────────
class TabActualizaciones(QWidget):
    """
    Panel de actualizaciones del catálogo de MultiToolCorp.
    Muestra únicamente la lista de parches y versiones oficiales disponibles.
    """

    def __init__(self, parent=None, context=None, colores=None):
        super().__init__(parent)
        if isinstance(context, dict):
            self.colores = context
            self.context = colores
        elif isinstance(colores, dict):
            self.colores = colores
            self.context = context
        else:
            self.context = context
            self.colores = getattr(context, "colores", {}) if context else {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        if not isinstance(self.colores, dict):
            self.colores = {}
        self.font_family = "Segoe UI"
        self.updates_list: list = []
        self._seen_ids: set = set()

        self._cargar_ids_vistos()
        self._build_ui()
        self._fetch()

        # Auto-refresh cada 10 minutos
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._fetch)
        self._timer.start(10 * 60 * 1000)

    # ── Persistencia de actualizaciones ya vistas ─────────────────────────────
    def _path_vistos(self) -> Path:
        return Path(getattr(self.context, "ruta_usuario", ".")) / "actualizaciones_vistas.json"

    def _cargar_ids_vistos(self):
        p = self._path_vistos()
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self._seen_ids = set(json.load(f))
            except Exception:
                self._seen_ids = set()

    def _guardar_ids_vistos(self):
        try:
            with open(self._path_vistos(), "w", encoding="utf-8") as f:
                json.dump(list(self._seen_ids), f)
        except Exception:
            pass

    def _marcar_visto(self, ann_id: str):
        self._seen_ids.add(ann_id)
        self._guardar_ids_vistos()
        self._render_anuncios()

    # ── UI base ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {self.colores['bg_principal']}; }}"
        )

        self._container = QWidget()
        self._container.setStyleSheet(f"background: {self.colores['bg_principal']};")
        self._main_layout = QVBoxLayout(self._container)
        self._main_layout.setContentsMargins(40, 40, 40, 40)

        # Header
        h_title = QLabel("🔄  Lista de Actualizaciones de Módulos y Sistema actualizado")
        h_title.setFont(QFont(self.font_family, 18, QFont.Weight.Bold))
        h_title.setStyleSheet("color: white; background: transparent; border: none;")
        self._main_layout.addWidget(h_title)

        h_sub = QLabel(
            "Catálogo oficial de parches y versiones disponibles para Multitool Suite, "
            "ordenadas desde la más reciente."
        )
        h_sub.setFont(QFont(self.font_family, 10))
        h_sub.setWordWrap(True)
        h_sub.setStyleSheet(
            f"color: {self.colores.get('fg_secundario', '#9CA3AF')}; "
            "background: transparent; border: none;"
        )
        self._main_layout.addWidget(h_sub)

        # Refresh button row
        btn_row = QHBoxLayout()
        self._lbl_status = QLabel("Consultando lista de actualizaciones…")
        self._lbl_status.setFont(QFont(self.font_family, 9))
        self._lbl_status.setStyleSheet(
            f"color: {self.colores.get('fg_secundario', '#9CA3AF')}; "
            "background: transparent; border: none;"
        )
        btn_row.addWidget(self._lbl_status)
        btn_row.addStretch()

        btn_refresh = QPushButton("↻  Actualizar Lista")
        btn_refresh.setFixedSize(140, 34)
        btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_refresh.setFont(QFont(self.font_family, 9))
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05);
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {self.colores.get('acento', '#6366F1')};
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        btn_refresh.clicked.connect(self._fetch)
        btn_row.addWidget(btn_refresh)
        self._main_layout.addLayout(btn_row)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.07); border: none;")
        self._main_layout.addWidget(div)

        # Row de Filtros y Búsqueda
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        # QComboBox de filtro de categoría / módulo
        self._combo_filter = QComboBox()
        self._combo_filter.setFont(QFont(self.font_family, 9))
        self._combo_filter.setStyleSheet(f"""
            QComboBox {{
                background: rgba(255,255,255,0.06);
                color: white;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 5px 10px;
                min-width: 210px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {self.colores.get('bg_secundario', '#2D2D2D')};
                color: white;
                selection-background-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self._combo_filter.addItems([
            "🌟 Todos los parches",
            "⚙️ Sistema Base (Core)",
            "🔒 Autenticación (Auth)",
            "🔄 Generales (Multimódulo)",
            "📁 Módulo: Notas",
            "📁 Módulo: General",
            "📁 Módulo: Cuenta",
            "📁 Módulo: Calculadora",
            "📁 Módulo: Navegador",
            "📁 Módulo: Seguridad",
            "📁 Módulo: Archivos",
            "📁 Módulo: Terminal",
            "📁 Módulo: Calendario",
            "📁 Módulo: Tiempo",
            "📁 Módulo: Sistema",
            "📁 Módulo: Traductor",
            "📁 Módulo: Reproductor",
            "📁 Módulo: Grabadora",
            "📁 Módulo: Cuaderno",
            "📁 Módulo: Chat",
            "📁 Módulo: Emulador",
            "📁 Módulo: Extras",
            "📁 Módulo: Minigames",
            "📁 Módulo: Widgets",
            "📁 Módulo: Proyectos",
            "📁 Módulo: Clipboard",
        ])
        self._combo_filter.currentIndexChanged.connect(self._render_anuncios)
        filter_row.addWidget(self._combo_filter)

        # QLineEdit para búsqueda en tiempo real
        self._txt_search = QLineEdit()
        self._txt_search.setPlaceholderText("🔎 Buscar módulo o parche por nombre...")
        self._txt_search.setFont(QFont(self.font_family, 9))
        self._txt_search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.06);
                color: white;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 5px 12px;
            }}
            QLineEdit:focus {{
                border-color: {self.colores.get('acento', '#6366F1')};
            }}
        """)
        self._txt_search.textChanged.connect(self._render_anuncios)
        filter_row.addWidget(self._txt_search)

        self._main_layout.addLayout(filter_row)

        # Cards container
        self._cards_layout = QVBoxLayout()
        self._cards_layout.setSpacing(16)
        self._main_layout.addLayout(self._cards_layout)

        self._main_layout.addStretch()
        scroll.setWidget(self._container)
        outer.addWidget(scroll)

    # ── Fetch ─────────────────────────────────────────────────────────────────
    def _fetch(self):
        log_debug("UI: _fetch solicitada.")
        self._lbl_status.setText("🔄  Cargando lista de actualizaciones…")
        self._worker = FetchWorker()
        self._worker.data_ready.connect(self._on_data)
        self._worker.fetch_error.connect(self._on_error)
        self._worker.start()

    def _on_data(self, data: list):
        log_debug(f"UI: _on_data recibido con {len(data)} elementos.")
        self.updates_list = data
        ts = datetime.now().strftime("%H:%M:%S")
        count = len(data)
        new_count = sum(1 for a in data if a.get("id") not in self._seen_ids)
        if count == 0:
            self._lbl_status.setText(f"✅  Sin actualizaciones en lista  ({ts})")
        else:
            self._lbl_status.setText(
                f"✅  {count} actualización{'es' if count > 1 else ''} disponible{'s' if count > 1 else ''} "
                f"({'🔴 ' + str(new_count) + ' nueva' + ('s' if new_count > 1 else '') if new_count else 'todas vistas'})  ({ts})"
            )
        self._render_anuncios()

    def _on_error(self, error_msg: str):
        log_debug(f"UI: _on_error recibido: {error_msg}")
        ts = datetime.now().strftime("%H:%M:%S")
        self._lbl_status.setText(f"⚠️ Sin conexión ({ts})")
        self._render_sin_conexion(error_msg)

    # ── Render ────────────────────────────────────────────────────────────────
    def _clear_cards(self):
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _render_anuncios(self):
        self._clear_cards()
        if not self.updates_list:
            self._render_empty()
            return

        cat_filter = self._combo_filter.currentText() if hasattr(self, "_combo_filter") else "🌟 Todos los parches"
        query = self._txt_search.text().lower().strip() if hasattr(self, "_txt_search") else ""

        filtered = []
        for ann in self.updates_list:
            badge = (ann.get("badge") or "").lower()
            url = (ann.get("url") or "").lower()
            version = (ann.get("version") or "").lower()
            desc = (ann.get("description") or "").lower()

            # Filtro por categoría / módulo
            matches_cat = True
            if "Core" in cat_filter:
                matches_cat = "core" in badge or "/core/" in url or "sistema base" in badge
            elif "Auth" in cat_filter:
                matches_cat = "auth" in badge or "/auth/" in url or "autenticación" in badge
            elif "Generales" in cat_filter:
                matches_cat = "multimódulo" in badge or "general" in badge or "/generales/" in url
            elif "📁 Módulo:" in cat_filter:
                mod_target = cat_filter.replace("📁 Módulo:", "").strip().lower()
                matches_cat = mod_target in badge or f"/modulos/{mod_target}/" in url or f"update_{mod_target}" in url

            # Filtro por texto de búsqueda
            matches_query = True
            if query:
                matches_query = query in badge or query in url or query in version or query in desc

            if matches_cat and matches_query:
                filtered.append(ann)

        if not filtered:
            self._render_empty()
            return

        for idx, ann in enumerate(filtered):
            is_first = (idx == 0)
            self._cards_layout.addWidget(self._make_card(ann, is_first))

    def _render_empty(self):
        self._clear_cards()
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 16px;
            }
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(30, 30, 30, 30)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🎉")
        icon.setFont(QFont(self.font_family, 32))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(icon)

        lbl = QLabel("¡No hay actualizaciones en la lista!")
        lbl.setFont(QFont(self.font_family, 14, QFont.Weight.Bold))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: white; background: transparent; border: none;")
        lay.addWidget(lbl)

        sub = QLabel("No se encontraron parches publicados actualmente.")
        sub.setFont(QFont(self.font_family, 10))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color: {self.colores.get('fg_secundario', '#9CA3AF')}; "
            "background: transparent; border: none;"
        )
        lay.addWidget(sub)

        self._cards_layout.addWidget(frame)

    def _render_sin_conexion(self, error_details: str = ""):
        self._clear_cards()
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(239,68,68,0.08);
                border: 1px solid rgba(239,68,68,0.2);
                border-radius: 16px;
            }
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(24, 24, 24, 24)

        lbl = QLabel("⚠️  Sin conexión al servidor de actualizaciones")
        lbl.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #FCA5A5; background: transparent; border: none;")
        lay.addWidget(lbl)

        sub = QLabel(
            "No se pudo consultar el catálogo remoto ni cargar la lista local. "
            "Verifica tu conexión a internet e intenta nuevamente."
        )
        sub.setFont(QFont(self.font_family, 10))
        sub.setWordWrap(True)
        sub.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent; border: none;")
        lay.addWidget(sub)

        if error_details:
            err_box = QLabel(f"<b>Detalle del error técnico:</b><br>{error_details}")
            err_box.setFont(QFont(self.font_family, 9))
            err_box.setWordWrap(True)
            err_box.setStyleSheet("""
                color: #F87171;
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(239,68,68,0.3);
                border-radius: 8px;
                padding: 10px;
                margin-top: 8px;
            """)
            lay.addWidget(err_box)

        self._cards_layout.addWidget(frame)

    def _make_card(self, ann: dict, is_first: bool = False) -> QFrame:
        ann_id  = ann.get("id", "")
        is_new  = ann_id not in self._seen_ids
        badge   = ann.get("badge", "Actualización")
        version = ann.get("version", "")
        title   = ann.get("title", "")
        desc    = ann.get("description", "")
        url     = ann.get("url", "")
        date    = ann.get("date", "")
        size    = ann.get("size", "")

        acento  = self.colores.get("acento", "#6366F1")

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {"rgba(99,102,241,0.08)" if is_first else "rgba(255,255,255,0.03)"};
                border: 1px solid {"rgba(99,102,241,0.35)" if is_first else "rgba(255,255,255,0.07)"};
                border-radius: 16px;
            }}
            QFrame:hover {{
                background: rgba(99,102,241,0.12);
                border-color: rgba(99,102,241,0.5);
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(10)

        # Header row
        head = QHBoxLayout()
        head.setSpacing(10)

        ver_lbl = QLabel(version)
        ver_lbl.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        ver_lbl.setStyleSheet("color: white; background: transparent; border: none;")
        head.addWidget(ver_lbl)

        badge_lbl = QLabel(f" {badge} ")
        badge_lbl.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        badge_lbl.setStyleSheet(f"""
            color: #38BDF8;
            background: rgba(56, 189, 248, 0.15);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 5px;
            padding: 2px 6px;
        """)
        head.addWidget(badge_lbl)

        if is_first:
            first_badge = QLabel(" MÁS RECIENTE ")
            first_badge.setFont(QFont(self.font_family, 7, QFont.Weight.Bold))
            first_badge.setStyleSheet("""
                color: #0f172a;
                background: #38BDF8;
                border-radius: 5px;
                padding: 2px 6px;
                border: none;
            """)
            head.addWidget(first_badge)

        head.addStretch()

        meta_info = []
        if date:
            meta_info.append(f"Lanzado: {date}")
        if size:
            meta_info.append(f"Peso: {size}")

        if meta_info:
            date_lbl = QLabel("  ·  ".join(meta_info))
            date_lbl.setFont(QFont(self.font_family, 8))
            date_lbl.setStyleSheet(
                f"color: {self.colores.get('fg_secundario', '#9CA3AF')}; "
                "background: transparent; border: none;"
            )
            head.addWidget(date_lbl)

        lay.addLayout(head)

        # Description / Changelog
        if desc:
            lines = [l.strip() for l in desc.splitlines() if l.strip()]
            if lines:
                import re
                formatted_items = []
                for line in lines:
                    # Ignorar líneas puramente decorativas (================ o ---------------)
                    if re.match(r'^[-=]{3,}$', line):
                        continue

                    title_match = re.match(r'^\d+\.\s*(.*)', line)
                    if title_match:
                        formatted_items.append(
                            f'<p style="margin-top:12px; margin-bottom:4px; padding:6px 10px; '
                            f'background:rgba(99,102,241,0.22); border-left:4px solid #6366F1; '
                            f'border-radius:6px; font-weight:bold; font-size:12px; color:#FFFFFF;">'
                            f'{line}</p>'
                        )
                    elif line.startswith("+") or line.startswith("[+]"):
                        text = line[3:].strip() if line.startswith("[+]") else line[1:].strip()
                        formatted_items.append(
                            f'<p style="margin: 3px 0 3px 10px; line-height: 1.35;">'
                            f'<span style="color:#4ADE80; font-weight:bold;">[+]</span> '
                            f'<span style="color:#E2E8F0;">{text}</span></p>'
                        )
                    elif line.startswith("-") or line.startswith("[-]"):
                        text = line[3:].strip() if line.startswith("[-]") else line[1:].strip()
                        formatted_items.append(
                            f'<p style="margin: 3px 0 3px 10px; line-height: 1.35;">'
                            f'<span style="color:#F87171; font-weight:bold;">[-]</span> '
                            f'<span style="color:#E2E8F0;">{text}</span></p>'
                        )
                    elif any(line.startswith(prefix) for prefix in ["RESUMEN", "Fecha:", "Convención"]):
                        formatted_items.append(
                            f'<p style="margin: 3px 0; color:#A5B4FC; font-weight:bold; font-size:11px;">'
                            f'{line}</p>'
                        )
                    else:
                        formatted_items.append(
                            f'<p style="margin: 3px 0 3px 10px; line-height: 1.35;">'
                            f'<span style="color:#38BDF8;">•</span> '
                            f'<span style="color:#CBD5E1;">{line}</span></p>'
                        )
                
                changelog_html = "".join(formatted_items)
                desc_lbl = QLabel(f"<b>Detalles del Parche:</b>{changelog_html}")
                desc_lbl.setFont(QFont(self.font_family, 9))
                desc_lbl.setStyleSheet("background: transparent; border: none;")
                desc_lbl.setWordWrap(True)
                lay.addWidget(desc_lbl)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        if url:
            full_url = f"{WEB_URL}{url}" if url.startswith('/') else url

            btn_instalar = QPushButton("⚡  Instalar Parche (.mtu)")
            btn_instalar.setFixedHeight(34)
            btn_instalar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_instalar.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn_instalar.setStyleSheet("""
                QPushButton {
                    background: #10B981;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 0 16px;
                }
                QPushButton:hover {
                    background: #059669;
                }
            """)
            btn_instalar.clicked.connect(lambda checked, u=full_url, i=ann_id: self._open_url(u, i))
            btn_row.addWidget(btn_instalar)

            btn_dl = QPushButton("⬇  Descargar Parche")
            btn_dl.setFixedHeight(34)
            btn_dl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_dl.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
            btn_dl.setStyleSheet(f"""
                QPushButton {{
                    background: {acento};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 0 16px;
                }}
                QPushButton:hover {{
                    background: #818CF8;
                }}
            """)
            btn_dl.clicked.connect(lambda checked, u=full_url, i=ann_id: self._open_url(u, i))
            btn_row.addWidget(btn_dl)

        btn_web = QPushButton("🌐  Ver Catálogo Web")
        btn_web.setFixedHeight(34)
        btn_web.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_web.setFont(QFont(self.font_family, 9))
        btn_web.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
            }
        """)
        btn_web.clicked.connect(
            lambda checked, i=ann_id: self._open_url(
                WEB_URL, i
            )
        )
        btn_row.addWidget(btn_web)
        btn_row.addStretch()

        if is_new:
            btn_mark = QPushButton("✓  Marcar como visto")
            btn_mark.setFixedHeight(34)
            btn_mark.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_mark.setFont(QFont(self.font_family, 9))
            btn_mark.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: rgba(255,255,255,0.35);
                    border: 1px solid rgba(255,255,255,0.07);
                    border-radius: 8px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    color: rgba(255,255,255,0.7);
                    border-color: rgba(255,255,255,0.15);
                }
            """)
            btn_mark.clicked.connect(lambda checked, i=ann_id: self._marcar_visto(i))
            btn_row.addWidget(btn_mark)

        lay.addLayout(btn_row)
        return card

    def _open_url(self, url: str, ann_id: str = ""):
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[Actualizaciones] No se pudo abrir URL: {e}")
        if ann_id:
            self._marcar_visto(ann_id)
