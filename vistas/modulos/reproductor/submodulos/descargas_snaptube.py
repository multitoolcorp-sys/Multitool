import os
import re
import html
import platform
import urllib.request
import urllib.parse
import json
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QScrollArea, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QPixmap, QImage
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

import yt_dlp

try:
    from ..utils.reproductor_logger import ReproductorLogger
except Exception:
    class ReproductorLogger:
        @staticmethod
        def log(n, m): pass
        @staticmethod
        def info(m): pass
        @staticmethod
        def warning(m): pass
        @staticmethod
        def error(m): pass

class DescargasSnaptubeSubmodule(QWidget):
    """Submódulo 2: Buscador & Descargador de Contenido Online (Snaptube MP3 / MP4 + Reproductor de Audio Streaming)"""
    dw_progreso_signal = pyqtSignal(int, str)
    dw_fin_signal = pyqtSignal(str, str)
    busqueda_fin_signal = pyqtSignal(list)
    reproducir_stream_signal = pyqtSignal(str, str)
    reproducir_video_stream_signal = pyqtSignal(str, str)

    def __init__(self, parent, context, manager, colores, callbacks=None):
        super().__init__(parent)
        self.context = context
        self.player_manager = manager
        self.colores = colores
        self.callbacks = callbacks or {}
        self.font_family = "Segoe UI" if platform.system() == "Windows" else "Inter"
        self.net_manager = QNetworkAccessManager(self)

        self.dw_progreso_signal.connect(self._on_dw_progreso)
        self.dw_fin_signal.connect(self._on_dw_fin)
        self.busqueda_fin_signal.connect(self._on_busqueda_fin)
        self.reproducir_stream_signal.connect(self._on_reproducir_stream)
        self.reproducir_video_stream_signal.connect(self._on_reproducir_video_stream)

        self.inicializar_ui()

    def inicializar_ui(self):
        bg_main = self.colores.get('bg_principal', '#121218')
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')

        self.setStyleSheet(f"background-color: {bg_main}; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        hdr = QHBoxLayout()
        lbl_title = QLabel("🔍 BUSCADOR, ESCUCHAR AUDIO & DESCARGADOR (SNAPTUBE MP3 / MP4)")
        lbl_title.setFont(QFont(self.font_family, 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; background: transparent;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()

        layout.addLayout(hdr)

        # Barra de búsqueda
        search_f = QFrame()
        search_f.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }}
        """)
        search_lay = QHBoxLayout(search_f)
        search_lay.setContentsMargins(10, 8, 10, 8)
        search_lay.setSpacing(10)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Escribe el nombre de la canción o vídeo (ej: Linkin Park, Queen, Michael Jackson, Bad Bunny)...")
        self.inp_search.setFont(QFont(self.font_family, 10))
        self.inp_search.setStyleSheet(f"background: {bg_terc}; border-radius: 8px; padding: 8px 12px; color: white; border: none;")
        self.inp_search.returnPressed.connect(self._buscar_online)
        search_lay.addWidget(self.inp_search, 1)

        btn_search = QPushButton("🔍 Buscar")
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        btn_search.setStyleSheet(f"background: {acento}; border-radius: 8px; color: white; padding: 8px 18px; border: none;")
        btn_search.clicked.connect(self._buscar_online)
        search_lay.addWidget(btn_search)

        layout.addWidget(search_f)

        # Barra de Progreso de Descarga / Carga
        self.pbar_frame = QFrame()
        self.pbar_frame.setStyleSheet(f"background: {bg_sec}; border-radius: 8px; padding: 8px;")
        self.pbar_frame.hide()
        p_lay = QVBoxLayout(self.pbar_frame)
        self.lbl_dw_status = QLabel("Procesando...")
        self.lbl_dw_status.setFont(QFont(self.font_family, 8))
        self.lbl_dw_status.setStyleSheet("color: white; background: transparent;")
        p_lay.addWidget(self.lbl_dw_status)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{ background: {bg_terc}; border-radius: 4px; text-align: center; color: transparent; }}
            QProgressBar::chunk {{ background: {acento}; border-radius: 4px; }}
        """)
        p_lay.addWidget(self.pbar)
        layout.addWidget(self.pbar_frame)

        # Resultados de búsqueda en rejilla/lista scrollable con FONDO OSCURO GARANTIZADO
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {bg_main}; border: none; }}
            QScrollBar:vertical {{ background: {bg_sec}; width: 10px; border-radius: 5px; }}
            QScrollBar::handle:vertical {{ background: {bg_terc}; border-radius: 5px; }}
        """)

        self.content = QWidget()
        self.content.setStyleSheet(f"background-color: {bg_main}; color: white;")
        self.res_lay = QVBoxLayout(self.content)
        self.res_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.res_lay.setSpacing(10)
        self.scroll.setWidget(self.content)

        layout.addWidget(self.scroll, 1)

    def _buscar_online(self):
        query = self.inp_search.text().strip()
        if not query:
            return

        self._limpiar_resultados()
        lbl_loading = QLabel(f"🔍 Buscando '{query}' en línea...")
        lbl_loading.setFont(QFont(self.font_family, 10))
        lbl_loading.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent;")
        self.res_lay.addWidget(lbl_loading)

        def run():
            items = self._hacer_busqueda_scraping(query)
            if not items:
                items = self._hacer_busqueda_ytdlp(query)
            self.busqueda_fin_signal.emit(items)

        threading.Thread(target=run, daemon=True).start()

    def _hacer_busqueda_scraping(self, query, limit=7):
        try:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=6) as response:
                html_code = response.read().decode('utf-8')
                match = re.search(r'var ytInitialData = ({.*?});</script>', html_code)
                if not match:
                    match = re.search(r'window\["ytInitialData"\] = ({.*?});</script>', html_code)
                    
                if match:
                    data = json.loads(match.group(1))
                    results = []
                    contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
                    for item in contents:
                        if 'videoRenderer' in item:
                            vr = item['videoRenderer']
                            vid_id = vr.get('videoId')
                            title = vr.get('title', {}).get('runs', [{}])[0].get('text', 'Vídeo')
                            thumb = vr.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url', '')
                            dur = vr.get('lengthText', {}).get('simpleText', '00:00')
                            if vid_id:
                                results.append({
                                    "id": vid_id,
                                    "title": html.unescape(title),
                                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                                    "thumb": thumb,
                                    "duration": dur
                                })
                            if len(results) >= limit:
                                break
                    return results
        except Exception:
            pass
        return []

    def _hacer_busqueda_ytdlp(self, query):
        try:
            ydl_opts = {'quiet': True, 'extract_flat': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res = ydl.extract_info(f"ytsearch7:{query}", download=False)
                items = []
                for entry in res.get('entries', []):
                    items.append({
                        "title": entry.get("title", "Vídeo"),
                        "id": entry.get("id", ""),
                        "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        "thumb": entry.get("thumbnail", ""),
                        "duration": "00:00"
                    })
                return items
        except Exception:
            return []

    def _on_busqueda_fin(self, items):
        self._limpiar_resultados()
        if not items:
            lbl_no = QLabel("No se encontraron resultados de búsqueda. Verifica tu conexión.")
            lbl_no.setStyleSheet("color: #F87171; background: transparent;")
            self.res_lay.addWidget(lbl_no)
            return

        for item in items:
            self._agregar_tarjeta_resultado(item)

    def _limpiar_resultados(self):
        while self.res_lay.count():
            item = self.res_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _agregar_tarjeta_resultado(self, item):
        bg_sec = self.colores.get('bg_secundario', '#1E1E2E')
        bg_terc = self.colores.get('bg_terciario', '#2D2D3D')
        acento = self.colores.get('acento', '#6366F1')
        exito = self.colores.get('exito', '#34D399')

        card = QFrame()
        card.setFixedHeight(110)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_sec};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }}
            QFrame:hover {{
                border: 1px solid {acento};
            }}
        """)
        l = QHBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(12)

        lbl_thumb = QLabel("🖼️")
        lbl_thumb.setFixedSize(120, 80)
        lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_thumb.setStyleSheet("background-color: black; border-radius: 6px; color: white;")
        l.addWidget(lbl_thumb)

        if item.get("thumb"):
            req = QNetworkRequest(QUrl(item["thumb"]))
            reply = self.net_manager.get(req)
            reply.finished.connect(lambda: self._on_thumb_ready(reply, lbl_thumb))

        info = QVBoxLayout()
        t = QLabel(item.get("title", ""))
        t.setFont(QFont(self.font_family, 9, QFont.Weight.Bold))
        t.setStyleSheet("color: white; background: transparent;")
        t.setWordWrap(True)
        info.addWidget(t)

        lbl_dur = QLabel(f"⏱️ Duración: {item.get('duration', '00:00')}")
        lbl_dur.setFont(QFont(self.font_family, 8))
        lbl_dur.setStyleSheet("color: rgba(255,255,255,0.6); background: transparent;")
        info.addWidget(lbl_dur)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        # Botón para Reproducir Audio Streaming directo con línea de tiempo
        btn_stream = QPushButton("▶ Escuchar Audio")
        btn_stream.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_stream.setStyleSheet(f"background: {exito}; border-radius: 6px; font-size: 11px; padding: 6px 12px; color: black; font-weight: bold; border: none;")
        btn_stream.clicked.connect(lambda: self._reproducir_audio_stream(item["url"], item["title"]))
        btn_box.addWidget(btn_stream)

        # Botón para Reproducir Vídeo Completo directo en pantalla
        btn_video = QPushButton("🎬 Ver Vídeo")
        btn_video.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_video.setStyleSheet(f"background: {acento}; border-radius: 6px; font-size: 11px; padding: 6px 12px; color: white; font-weight: bold; border: none;")
        btn_video.clicked.connect(lambda: self._reproducir_video_stream(item["url"], item["title"]))
        btn_box.addWidget(btn_video)

        btn_mp3 = QPushButton("🎵 MP3")
        btn_mp3.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_mp3.setStyleSheet(f"background: {bg_terc}; border-radius: 6px; font-size: 11px; padding: 6px 12px; color: white; border: none;")
        btn_mp3.clicked.connect(lambda: self._descargar_media(item["url"], item["title"], True))
        btn_box.addWidget(btn_mp3)

        btn_mp4 = QPushButton("🎬 MP4")
        btn_mp4.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_mp4.setStyleSheet(f"background: {bg_terc}; border-radius: 6px; font-size: 11px; padding: 6px 12px; color: white; border: none;")
        btn_mp4.clicked.connect(lambda: self._descargar_media(item["url"], item["title"], False))
        btn_box.addWidget(btn_mp4)

        info.addLayout(btn_box)
        l.addLayout(info, 1)

        self.res_lay.addWidget(card)

    def _reproducir_audio_stream(self, video_url, title):
        ReproductorLogger.info(f"Snaptube: Solicitud de streaming audio para: '{title}' ({video_url})")

        self.pbar_frame.show()
        self.lbl_dw_status.setText(f"Obteniendo enlace de audio para '{title}'...")
        self.pbar.setValue(30)

        def run():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'bestaudio/best',
                    'js_runtimes': {'node': {}}
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    stream_url = info.get('url')
                    if stream_url:
                        ReproductorLogger.info(f"Snaptube: Enlace extraído con éxito para '{title}' | URL: {stream_url[:80]}...")
                        self.dw_progreso_signal.emit(100, "¡Enlace obtenido! Conectando al reproductor...")
                        self.reproducir_stream_signal.emit(stream_url, title)
                    else:
                        fail_msg = f"No se pudo extraer la URL del stream para '{title}'"
                        ReproductorLogger.error(f"Snaptube: {fail_msg}")
                        self.dw_progreso_signal.emit(0, "❌ No se pudo extraer el enlace de audio.")
            except Exception as e:
                err_msg = f"Error extrayendo stream: {e}"
                ReproductorLogger.error(f"Snaptube: {err_msg}")
                self.dw_progreso_signal.emit(0, f"❌ Error al obtener stream: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _on_reproducir_stream(self, stream_url, title):
        self.pbar_frame.hide()
        ReproductorLogger.info(f"Snaptube: Conectando stream a 'Reproductor ARK' para: '{title}'")
        if "reproducir_directo" in self.callbacks:
            self.callbacks["reproducir_directo"](stream_url, titulo_radio=title, es_video=False)

    def _reproducir_video_stream(self, video_url, title):
        ReproductorLogger.info(f"Snaptube: Solicitud de streaming vídeo para: '{title}' ({video_url})")

        self.pbar_frame.show()
        self.lbl_dw_status.setText(f"Obteniendo enlace de vídeo en alta definición para '{title}'...")
        self.pbar.setValue(30)

        def run():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best[vcodec!=none][acodec!=none]/22/18/best',
                    'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}},
                    'js_runtimes': {'node': {}}
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    stream_url = None
                    formats = info.get('formats', [])
                    # Priorizar formatos combinados que tienen vídeo y audio sincronizados
                    combos = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url')]
                    if combos:
                        combos.sort(key=lambda x: x.get('height') or 0, reverse=True)
                        stream_url = combos[0]['url']
                    else:
                        stream_url = info.get('url')

                    if stream_url:
                        ReproductorLogger.info(f"Snaptube: Enlace de vídeo obtenido con éxito para '{title}' | URL: {stream_url[:80]}...")
                        self.dw_progreso_signal.emit(100, "¡Enlace de vídeo obtenido! Conectando al reproductor...")
                        self.reproducir_video_stream_signal.emit(stream_url, title)
                    else:
                        fail_msg = f"No se pudo extraer la URL del vídeo para '{title}'"
                        ReproductorLogger.error(f"Snaptube: {fail_msg}")
                        self.dw_progreso_signal.emit(0, "❌ No se pudo extraer el enlace de vídeo.")
            except Exception as e:
                err_msg = f"Error extrayendo vídeo: {e}"
                ReproductorLogger.error(f"Snaptube: {err_msg}")
                self.dw_progreso_signal.emit(0, f"❌ Error al obtener vídeo: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _on_reproducir_video_stream(self, stream_url, title):
        self.pbar_frame.hide()
        ReproductorLogger.info(f"Snaptube: Conectando vídeo completo a 'Reproductor ARK' para: '{title}'")
        if "reproducir_directo" in self.callbacks:
            self.callbacks["reproducir_directo"](stream_url, titulo_radio=title, es_video=True)


    def _descargar_media(self, url, title, solo_audio):
        if self.context and hasattr(self.context, 'ruta_usuario') and self.context.ruta_usuario:
            base_dw = Path(self.context.ruta_usuario) / "descargas"
        else:
            base_dw = Path.home() / "Downloads"

        sub_name = "musicas" if solo_audio else "videos"
        dest_folder = base_dw / sub_name
        dest_folder.mkdir(parents=True, exist_ok=True)

        self.pbar_frame.show()
        self.lbl_dw_status.setText(f"Iniciando descarga de: {title} ({'MP3' if solo_audio else 'MP4'})")
        self.pbar.setValue(10)

        def progress_hook(d):
            if d.get('status') == 'downloading':
                try:
                    p = d.get('_percent_str', '50%').replace('%', '').strip()
                    self.dw_progreso_signal.emit(int(float(p)), f"Descargando: {d.get('_eta_str', '')}")
                except Exception:
                    pass
            elif d.get('status') == 'finished':
                self.dw_progreso_signal.emit(100, "Procesando archivo final...")

        def run():
            try:
                import shutil
                import sys

                archivos_antes = set(dest_folder.glob("*"))

                ffmpeg_exe = shutil.which("ffmpeg")
                if not ffmpeg_exe:
                    try:
                        from controlador.utils.paths import get_resource_path
                        candidatos_ffmpeg = [
                            get_resource_path() / "ffmpeg.exe",
                            get_resource_path() / "bin" / "ffmpeg.exe",
                            Path(sys.executable).parent / "ffmpeg.exe",
                            Path(sys.executable).parent / "bin" / "ffmpeg.exe"
                        ]
                        for cf in candidatos_ffmpeg:
                            if cf.exists():
                                ffmpeg_exe = str(cf)
                                break
                    except Exception:
                        pass

                out_tmpl = str(dest_folder / "%(title)s.%(ext)s")

                ydl_opts = {
                    'outtmpl': out_tmpl,
                    'progress_hooks': [progress_hook],
                    'quiet': True,
                    'noplaylist': True,
                    'ignoreerrors': False
                }

                if ffmpeg_exe:
                    ydl_opts['ffmpeg_location'] = ffmpeg_exe
                    if solo_audio:
                        ydl_opts['format'] = 'bestaudio/best'
                        ydl_opts['postprocessors'] = [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }]
                    else:
                        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    if solo_audio:
                        ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
                    else:
                        ydl_opts['format'] = 'best[ext=mp4]/best'

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                archivos_despues = set(dest_folder.glob("*"))
                nuevos = archivos_despues - archivos_antes
                if nuevos:
                    nombre_archivo = list(nuevos)[0].name
                    self.dw_progreso_signal.emit(100, f"¡Descarga completada: {nombre_archivo}!")
                    self.dw_fin_signal.emit(title, str(dest_folder))
                else:
                    # Si ya existía o se sobreescribió
                    self.dw_progreso_signal.emit(100, "¡Descarga completada con éxito!")
                    self.dw_fin_signal.emit(title, str(dest_folder))
            except Exception as e:
                self.dw_progreso_signal.emit(0, f"❌ Error en la descarga: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _on_dw_progreso(self, pct, status):
        self.pbar.setValue(pct)
        self.lbl_dw_status.setText(status)

    def _on_dw_fin(self, title, folder):
        QMessageBox.information(self, "Descarga Finalizada", f"¡'{title}' fue guardado con éxito en:\n{folder}")

    def _on_thumb_ready(self, reply, label):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            img = QImage()
            img.loadFromData(reply.readAll())
            pix = QPixmap.fromImage(img).scaled(120, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(pix)
        reply.deleteLater()

    def actualizar_tema(self, colores):
        self.colores = colores
