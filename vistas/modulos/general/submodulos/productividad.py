import json
import shutil
try:
    import winsound
except ImportError:
    winsound = None
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QCheckBox, QProgressBar, QScrollArea, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

class ProductividadGUI(QWidget):
    """Submódulo de Productividad: Temporizador Pomodoro, Sonidos Ambientales y To-Do List"""
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
            self.colores = {}

        if not self.colores and self.context and hasattr(self.context, "app") and hasattr(self.context.app, "COLORES"):
            self.colores = self.context.app.COLORES

        if not self.colores and hasattr(parent, "colores") and isinstance(parent.colores, dict):
            self.colores = parent.colores

        self.ruta_usuario = Path(getattr(self.context, "ruta_usuario", ".")) if self.context else Path(".")
        self.dir_sonidos_personales = self.ruta_usuario / "ambiental_sounds"
        self.dir_sonidos_personales.mkdir(parents=True, exist_ok=True)

        self.font_family = "Segoe UI"

        # MultiMedia Player Setup
        self.player = None
        self.audio_output = None
        if HAS_MULTIMEDIA:
            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
            self.audio_output.setVolume(0.8)

        # Pomodoro State
        self.pomodoro_seconds = 25 * 60
        self.pomodoro_total = 25 * 60
        self.pomodoro_active = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_pomodoro)

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218') if isinstance(self.colores, dict) else '#121218'

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 8, 10, 8)
        main_lay.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {bg_p}; }}")

        content = QWidget()
        content.setStyleSheet(f"background-color: {bg_p};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # Header
        lbl_head = QLabel("⚡ CENTRO DE PRODUCTIVIDAD & ENFOQUE POMODORO")
        lbl_head.setFont(QFont(self.font_family, 13, QFont.Weight.Bold))
        lbl_head.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1') if isinstance(self.colores, dict) else '#6366F1'}; margin-bottom: 2px;")
        lay.addWidget(lbl_head)

        # Layout horizontal principal: Pomodoro a la izquierda, To-Do a la derecha
        row_main = QHBoxLayout()
        row_main.setSpacing(12)

        # ── 1. CARD TEMPORIZADOR POMODORO ─────────────────────────────
        pomo_card = QFrame()
        pomo_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colores.get('bg_secundario', '#1E1E2E') if isinstance(self.colores, dict) else '#1E1E2E'};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        pomo_lay = QVBoxLayout(pomo_card)
        pomo_lay.setContentsMargins(14, 12, 14, 12)
        pomo_lay.setSpacing(10)

        lbl_pomo_t = QLabel("⏱️ Temporizador de Enfoque Pomodoro")
        lbl_pomo_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_pomo_t.setStyleSheet("color: white;")
        pomo_lay.addWidget(lbl_pomo_t)

        # Modos de tiempo
        modes_lay = QHBoxLayout()
        btn_work = QPushButton("💻 Trabajo (25m)")
        btn_short = QPushButton("☕ Corto (5m)")
        btn_long = QPushButton("🌴 Largo (15m)")

        bg_ter = self.colores.get('bg_terciario', '#2D2D3D') if isinstance(self.colores, dict) else '#2D2D3D'
        acento = self.colores.get('acento', '#6366F1') if isinstance(self.colores, dict) else '#6366F1'

        for btn, sec in [(btn_work, 25*60), (btn_short, 5*60), (btn_long, 15*60)]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background: {bg_ter}; color: white; border-radius: 6px; padding: 6px 10px; font-size: 11px;")
            btn.clicked.connect(lambda ch, s=sec: self.set_pomodoro_mode(s))
            modes_lay.addWidget(btn)

        pomo_lay.addLayout(modes_lay)

        # Display del Reloj Pomodoro
        self.lbl_timer = QLabel("25:00")
        self.lbl_timer.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet(f"color: {acento}; margin: 8px 0;")
        pomo_lay.addWidget(self.lbl_timer)

        self.pbar_pomo = QProgressBar()
        self.pbar_pomo.setValue(100)
        self.pbar_pomo.setFixedHeight(8)
        self.pbar_pomo.setTextVisible(False)
        self.pbar_pomo.setStyleSheet(f"""
            QProgressBar {{ background: #2D2D3D; border-radius: 4px; border: none; }}
            QProgressBar::chunk {{ background-color: {acento}; border-radius: 4px; }}
        """)
        pomo_lay.addWidget(self.pbar_pomo)

        # Botones de control
        ctrl_lay = QHBoxLayout()
        self.btn_toggle_pomo = QPushButton("▶️ Iniciar Enfoque")
        self.btn_toggle_pomo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_pomo.setStyleSheet(f"background: {acento}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 14px;")
        self.btn_toggle_pomo.clicked.connect(self.toggle_pomodoro)

        btn_reset_pomo = QPushButton("🔄 Reiniciar")
        btn_reset_pomo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_pomo.setStyleSheet("background: #374151; color: white; border-radius: 6px; padding: 8px 14px;")
        btn_reset_pomo.clicked.connect(self.reset_pomodoro)

        ctrl_lay.addWidget(self.btn_toggle_pomo, 1)
        ctrl_lay.addWidget(btn_reset_pomo)
        pomo_lay.addLayout(ctrl_lay)

        # ── SONIDOS AMBIENTALES Y PERSONALIZADOS ──
        sound_box = QFrame()
        sound_box.setStyleSheet(f"background: {bg_ter}; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);")
        sound_box_lay = QVBoxLayout(sound_box)
        sound_box_lay.setContentsMargins(10, 8, 10, 8)
        sound_box_lay.setSpacing(6)

        lbl_sound_head = QLabel("🔊 Sonido Ambiental de Fondo")
        lbl_sound_head.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        lbl_sound_head.setStyleSheet("color: white;")
        sound_box_lay.addWidget(lbl_sound_head)

        sound_lay = QHBoxLayout()
        self.cb_sound = QComboBox()
        self.cb_sound.setStyleSheet("background: #1E1E2E; color: white; border-radius: 4px; padding: 5px;")
        self.cb_sound.currentIndexChanged.connect(self._on_sound_selected)
        sound_lay.addWidget(self.cb_sound, 1)

        self.btn_toggle_sound = QPushButton("▶️ Reproducir")
        self.btn_toggle_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sound.setStyleSheet(f"background: {acento}; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold;")
        self.btn_toggle_sound.clicked.connect(self.toggle_sound_playback)
        sound_lay.addWidget(self.btn_toggle_sound)

        sound_box_lay.addLayout(sound_lay)

        btn_add_custom_sound = QPushButton("➕ Agregar Sonido Personal (.MP3 / .WAV / .MP4)")
        btn_add_custom_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_custom_sound.setStyleSheet("background: rgba(255,255,255,0.05); color: #818CF8; border: 1px dashed #6366F1; border-radius: 4px; padding: 5px; font-size: 11px;")
        btn_add_custom_sound.clicked.connect(self.agregar_sonido_personal)
        sound_box_lay.addWidget(btn_add_custom_sound)

        pomo_lay.addWidget(sound_box)
        row_main.addWidget(pomo_card, 1)

        # ── 2. CARD METAS Y LISTA DE TAREAS DIARIAS (TO-DO) ───────────
        todo_card = QFrame()
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E') if isinstance(self.colores, dict) else '#1E1E2E'
        todo_card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }}
        """)
        todo_lay = QVBoxLayout(todo_card)
        todo_lay.setContentsMargins(14, 12, 14, 12)
        todo_lay.setSpacing(8)

        lbl_todo_t = QLabel("📋 Lista de Metas Diarias (To-Do & Habit Tracker)")
        lbl_todo_t.setFont(QFont(self.font_family, 11, QFont.Weight.Bold))
        lbl_todo_t.setStyleSheet("color: white;")
        todo_lay.addWidget(lbl_todo_t)

        row_input = QHBoxLayout()
        self.ent_task = QLineEdit()
        self.ent_task.setPlaceholderText("Escribe una nueva meta para hoy...")
        self.ent_task.setStyleSheet("background: #2D2D3D; color: white; padding: 6px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);")
        self.ent_task.returnPressed.connect(self.add_task)

        btn_add = QPushButton("➕ Agregar")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"background: {acento}; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px;")
        btn_add.clicked.connect(self.add_task)

        row_input.addWidget(self.ent_task, 1)
        row_input.addWidget(btn_add)
        todo_lay.addLayout(row_input)

        self.list_tasks = QListWidget()
        self.list_tasks.setStyleSheet("""
            QListWidget { background: #2D2D3D; color: white; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); padding: 4px; }
            QListWidget::item { padding: 4px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        """)
        self.list_tasks.setFixedHeight(180)
        todo_lay.addWidget(self.list_tasks)

        # Barras de progreso de tareas completadas
        self.lbl_todo_pct = QLabel("Progreso: 0% Completado")
        self.lbl_todo_pct.setFont(QFont(self.font_family, 8, QFont.Weight.Bold))
        self.lbl_todo_pct.setStyleSheet("color: #10B981;")
        todo_lay.addWidget(self.lbl_todo_pct)

        row_main.addWidget(todo_card, 1)

        lay.addLayout(row_main)

        scroll.setWidget(content)
        main_lay.addWidget(scroll)

        # Cargar lista de sonidos en el combo box
        self.cargar_lista_sonidos()
        self._load_default_tasks()

    def cargar_lista_sonidos(self):
        """Carga los sonidos por defecto y los de la carpeta personal ambiental_sounds"""
        self.cb_sound.blockSignals(True)
        self.cb_sound.clear()
        self.cb_sound.addItem("🚫 Ninguno", None)

        utils_dir = Path(__file__).parent.parent / "utils"
        rain_path = utils_dir / "Rainy Mood.wav"
        solar_path = utils_dir / "solar_music.wav"

        if rain_path.exists():
            self.cb_sound.addItem("🌧️ Lluvia de Relajación (Default)", str(rain_path.resolve()))
        if solar_path.exists():
            self.cb_sound.addItem("🌊 Océano Profundo (Default)", str(solar_path.resolve()))

        # Sonidos personales en ambiental_sounds
        if self.dir_sonidos_personales.exists():
            for f in sorted(self.dir_sonidos_personales.iterdir()):
                if f.is_file() and f.suffix.lower() in [".mp3", ".wav", ".mp4", ".aac", ".ogg", ".flac", ".m4a"]:
                    self.cb_sound.addItem(f"🎵 {f.stem} (Personal)", str(f.resolve()))

        self.cb_sound.blockSignals(False)

    def agregar_sonido_personal(self):
        """Permite al usuario seleccionar un archivo de audio para copiarlo a ambiental_sounds"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Sonido Ambiental Personal", "",
            "Archivos de Audio (*.mp3 *.wav *.mp4 *.aac *.ogg *.flac *.m4a);;Todos los archivos (*.*)"
        )
        if file_path:
            src = Path(file_path)
            dst = self.dir_sonidos_personales / src.name
            try:
                shutil.copy2(src, dst)
                self.cargar_lista_sonidos()

                # Seleccionar automáticamente el sonido recién agregado
                idx = self.cb_sound.findData(str(dst.resolve()))
                if idx != -1:
                    self.cb_sound.setCurrentIndex(idx)

                QMessageBox.information(self, "Sonido Agregado", f"¡El sonido '{src.name}' ha sido agregado a tu biblioteca personal de ambiente!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo copiar el archivo de audio:\n{e}")

    def _on_sound_selected(self, index):
        path_str = self.cb_sound.currentData()
        if not path_str:
            self.stop_sound()
        elif self.pomodoro_active or getattr(self, "_sound_manual_playing", False):
            self.play_sound(path_str)

    def toggle_sound_playback(self):
        path_str = self.cb_sound.currentData()
        if not path_str:
            QMessageBox.warning(self, "Selecciona un Sonido", "Por favor selecciona un sonido ambiental de la lista desplegable.")
            return

        if getattr(self, "_sound_manual_playing", False):
            self._sound_manual_playing = False
            self.stop_sound()
            self.btn_toggle_sound.setText("▶️ Reproducir")
        else:
            self._sound_manual_playing = True
            self.play_sound(path_str)
            self.btn_toggle_sound.setText("⏸️ Detener")

    def play_sound(self, path_str):
        if not path_str or not HAS_MULTIMEDIA or not self.player:
            return
        try:
            url = QUrl.fromLocalFile(path_str)
            self.player.setSource(url)

            # Usar constante de bucle infinito si está disponible
            if hasattr(QMediaPlayer.Loops, "Infinite"):
                self.player.setLoops(QMediaPlayer.Loops.Infinite)
            else:
                self.player.setLoops(-1)

            self.player.play()
        except Exception as e:
            print(f"[ERROR Sound] {e}")

    def stop_sound(self):
        if HAS_MULTIMEDIA and self.player:
            try:
                self.player.stop()
            except Exception:
                pass

    def set_pomodoro_mode(self, seconds):
        self.pomodoro_seconds = seconds
        self.pomodoro_total = seconds
        self.pomodoro_active = False
        self.timer.stop()
        self.stop_sound()
        self._sound_manual_playing = False
        self.btn_toggle_sound.setText("▶️ Reproducir")
        self.btn_toggle_pomo.setText("▶️ Iniciar Enfoque")
        self._render_pomodoro_display()

    def toggle_pomodoro(self):
        if self.pomodoro_active:
            self.pomodoro_active = False
            self.timer.stop()
            self.stop_sound()
            self.btn_toggle_pomo.setText("▶️ Reanudar Enfoque")
        else:
            self.pomodoro_active = True
            self.timer.start(1000)
            self.btn_toggle_pomo.setText("⏸️ Pausar")

            # Reproducir sonido ambiental si hay uno seleccionado
            sound_path = self.cb_sound.currentData()
            if sound_path:
                self.play_sound(sound_path)

    def reset_pomodoro(self):
        self.pomodoro_seconds = self.pomodoro_total
        self.pomodoro_active = False
        self.timer.stop()
        self.stop_sound()
        self._sound_manual_playing = False
        self.btn_toggle_sound.setText("▶️ Reproducir")
        self.btn_toggle_pomo.setText("▶️ Iniciar Enfoque")
        self._render_pomodoro_display()

    def _update_pomodoro(self):
        if self.pomodoro_seconds > 0:
            self.pomodoro_seconds -= 1
            self._render_pomodoro_display()
        else:
            self.timer.stop()
            self.pomodoro_active = False
            self.stop_sound()
            self.btn_toggle_pomo.setText("▶️ Iniciar Enfoque")
            try:
                winsound.Beep(1000, 500)
            except Exception:
                pass

    def _render_pomodoro_display(self):
        mins = self.pomodoro_seconds // 60
        secs = self.pomodoro_seconds % 60
        self.lbl_timer.setText(f"{mins:02d}:{secs:02d}")
        pct = int((self.pomodoro_seconds / max(1, self.pomodoro_total)) * 100)
        self.pbar_pomo.setValue(pct)

    def add_task(self):
        text = self.ent_task.text().strip()
        if text:
            item = QListWidgetItem(f"⬜ {text}")
            self.list_tasks.addItem(item)
            self.ent_task.clear()
            self.update_task_progress()

    def _load_default_tasks(self):
        defaults = []
        for t in defaults:
            self.list_tasks.addItem(QListWidgetItem(t))
        self.list_tasks.itemClicked.connect(self._toggle_task_item)
        self.update_task_progress()

    def _toggle_task_item(self, item):
        txt = item.text()
        if txt.startswith("⬜ "):
            item.setText(txt.replace("⬜ ", "✅ "))
            item.setForeground(QColor("#10B981"))
        elif txt.startswith("✅ "):
            item.setText(txt.replace("✅ ", "⬜ "))
            item.setForeground(QColor("white"))
        self.update_task_progress()

    def update_task_progress(self):
        total = self.list_tasks.count()
        if total == 0:
            self.lbl_todo_pct.setText("Progreso: 0% Completado")
            return
        done = 0
        for i in range(total):
            if self.list_tasks.item(i).text().startswith("✅ "):
                done += 1
        pct = int((done / total) * 100)
        self.lbl_todo_pct.setText(f"Progreso: {pct}% Completado ({done}/{total} tareas)")
