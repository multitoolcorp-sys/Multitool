"""
tab_analytics_notas.py - Panel de Estadísticas y Productividad de Notas
"""
import os
import json
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextDocument


class AnalyticsNotasGUI(QWidget):
    """Dashboard de estadísticas de escritura, biblioteca de notas y hábitos de productividad"""
    def __init__(self, parent=None, context=None, colores=None, **kwargs):
        super().__init__(parent)
        self.context = context
        self.colores = colores or (getattr(context, "colores", {}) if context else {})
        self.ruta_usuario = Path(getattr(context, "ruta_usuario", "."))
        self.ruta_notas = self.ruta_usuario / "notas"
        self.ruta_notas.mkdir(parents=True, exist_ok=True)

        self.init_ui()

    def init_ui(self):
        bg_p = self.colores.get('bg_principal', '#121218')
        self.setStyleSheet(f"background-color: {bg_p}; color: white;")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.lay = QVBoxLayout(self.container)
        self.lay.setContentsMargins(24, 24, 24, 24)
        self.lay.setSpacing(20)

        scroll.setWidget(self.container)
        main_lay.addWidget(scroll)

        self.actualizar_dashboard()

    def actualizar_dashboard(self):
        # Limpiar
        while self.lay.count():
            item = self.lay.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        # Calcular métricas
        archivos = list(self.ruta_notas.glob("*.txt"))
        total_notas = len(archivos)
        total_palabras = 0
        total_caracteres = 0
        notas_stats = []
        ahora = datetime.datetime.now()
        notas_esta_semana = 0
        notas_hoy = 0

        for a in archivos:
            try:
                with open(a, "r", encoding="utf-8") as f:
                    raw = f.read()
                html = ""
                try:
                    data = json.loads(raw)
                    html = data.get("html", "") if isinstance(data, dict) else raw
                except Exception:
                    html = raw

                doc = QTextDocument()
                doc.setHtml(html)
                texto = doc.toPlainText()
                palabras = len([w for w in texto.split() if w.strip()])
                caracteres = len(texto)
                total_palabras += palabras
                total_caracteres += caracteres

                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(a))
                if (ahora - mtime).days == 0 and ahora.day == mtime.day:
                    notas_hoy += 1
                if (ahora - mtime).days < 7:
                    notas_esta_semana += 1

                notas_stats.append({
                    "nombre": a.stem,
                    "palabras": palabras,
                    "caracteres": caracteres,
                    "mtime": mtime
                })
            except Exception:
                continue

        # Tags
        tags_map = {}
        ruta_tags = self.ruta_usuario / "notas_tags.json"
        if ruta_tags.exists():
            try:
                with open(ruta_tags, "r", encoding="utf-8") as f:
                    tags_map = json.load(f)
            except Exception:
                pass

        contador_tags = {}
        for tags_list in tags_map.values():
            for t in tags_list:
                contador_tags[t] = contador_tags.get(t, 0) + 1

        promedio_palabras = round(total_palabras / max(1, total_notas))
        tiempo_lectura_total = max(1, round(total_palabras / 200))

        # --- HEADER ---
        row_header = QHBoxLayout()
        lbl_tit = QLabel("📊 ANALÍTICAS Y RENDIMIENTO DE NOTAS")
        lbl_tit.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_tit.setStyleSheet(f"color: {self.colores.get('acento', '#6366F1')};")
        row_header.addWidget(lbl_tit)
        row_header.addStretch()

        btn_refresh = QPushButton("🔄 Actualizar Datos")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: {self.colores.get('acento', '#6366F1')}; color: white; border-radius: 6px;
                padding: 6px 14px; font-weight: bold; font-size: 10px; border: none;
            }}
            QPushButton:hover {{ background: {self.colores.get('acento_hover', '#818CF8')}; }}
        """)
        btn_refresh.clicked.connect(self.actualizar_dashboard)
        row_header.addWidget(btn_refresh)
        self.lay.addLayout(row_header)

        # --- 4 TARJETAS KPI RESUMEN ---
        grid_kpi = QGridLayout()
        grid_kpi.setSpacing(14)

        kpis = [
            ("📚 Total de Notas", str(total_notas), "documentos en biblioteca", "#6366F1"),
            ("✍️ Palabras Escritas", f"{total_palabras:,}", f"~{promedio_palabras} prom. por nota", "#10B981"),
            ("⏱️ Tiempo de Lectura", f"~{tiempo_lectura_total} min", "a 200 palabras/min", "#F59E0B"),
            ("🏷️ Etiquetas Únicas", str(len(contador_tags)), f"{sum(contador_tags.values())} asignaciones totales", "#EC4899")
        ]

        for idx, (titulo, valor, subtitulo, col_accent) in enumerate(kpis):
            kpi_card = QFrame()
            kpi_card.setStyleSheet(f"""
                QFrame {{
                    background: {self.colores.get('bg_secundario', '#1E1E2E')};
                    border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px;
                }}
            """)
            k_lay = QVBoxLayout(kpi_card)
            k_lay.setSpacing(4)

            lbl_kt = QLabel(titulo)
            lbl_kt.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            lbl_kt.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')};")
            k_lay.addWidget(lbl_kt)

            lbl_kv = QLabel(valor)
            lbl_kv.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
            lbl_kv.setStyleSheet(f"color: {col_accent};")
            k_lay.addWidget(lbl_kv)

            lbl_ks = QLabel(subtitulo)
            lbl_ks.setFont(QFont("Segoe UI", 8))
            lbl_ks.setStyleSheet("color: #64748B;")
            k_lay.addWidget(lbl_ks)

            grid_kpi.addWidget(kpi_card, 0, idx)

        self.lay.addLayout(grid_kpi)

        # --- SECCIÓN INTERMEDIA: ACTIVIDAD RECIENTE Y TOP ETIQUETAS ---
        row_mid = QHBoxLayout()
        row_mid.setSpacing(16)

        # Caja de Actividad
        box_act = QFrame()
        box_act.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;
            }}
        """)
        act_lay = QVBoxLayout(box_act)
        act_lay.setSpacing(10)

        lbl_atit = QLabel("📅 Ritmo de Creación y Edición")
        lbl_atit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_atit.setStyleSheet("color: white;")
        act_lay.addWidget(lbl_atit)

        for concepto, cant, col in [
            ("Notas modificadas hoy:", f"{notas_hoy} notas", "#34D399"),
            ("Notas activas esta semana:", f"{notas_esta_semana} notas", "#60A5FA"),
            ("Caracteres totales archivados:", f"{total_caracteres:,} caracteres", "#A78BFA")
        ]:
            row_item = QHBoxLayout()
            lbl_c = QLabel(concepto)
            lbl_c.setStyleSheet(f"color: {self.colores.get('fg_secundario', '#AAB0B8')}; font-size: 10px;")
            lbl_v = QLabel(cant)
            lbl_v.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 10px;")
            row_item.addWidget(lbl_c)
            row_item.addStretch()
            row_item.addWidget(lbl_v)
            act_lay.addLayout(row_item)

        act_lay.addStretch()
        row_mid.addWidget(box_act, 1)

        # Caja de Etiquetas Frecuentes
        box_tags = QFrame()
        box_tags.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;
            }}
        """)
        btags_lay = QVBoxLayout(box_tags)
        btags_lay.setSpacing(10)

        lbl_ttit = QLabel("🏷️ Etiquetas Más Utilizadas")
        lbl_ttit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_ttit.setStyleSheet("color: white;")
        btags_lay.addWidget(lbl_ttit)

        if contador_tags:
            sorted_tags = sorted(contador_tags.items(), key=lambda x: -x[1])[:5]
            max_c = max(x[1] for x in sorted_tags) if sorted_tags else 1
            for tag, count in sorted_tags:
                row_t = QHBoxLayout()
                lbl_tn = QLabel(f"#{tag}")
                lbl_tn.setStyleSheet("color: #818CF8; font-weight: bold; font-size: 10px;")
                row_t.addWidget(lbl_tn, 1)

                pbar = QProgressBar()
                pbar.setFixedHeight(8)
                pbar.setTextVisible(False)
                pbar.setRange(0, max_c)
                pbar.setValue(count)
                pbar.setStyleSheet("""
                    QProgressBar { background: rgba(255,255,255,0.06); border-radius: 4px; }
                    QProgressBar::chunk { background: #6366F1; border-radius: 4px; }
                """)
                row_t.addWidget(pbar, 2)

                lbl_tc = QLabel(f"{count} notas")
                lbl_tc.setStyleSheet("color: #64748B; font-size: 9px;")
                row_t.addWidget(lbl_tc)
                btags_lay.addLayout(row_t)
        else:
            lbl_notags = QLabel("No has asignado etiquetas a tus notas todavía.\nPuedes añadir etiquetas desde el botón '+ Tag' en Mis Notas.")
            lbl_notags.setStyleSheet("color: #64748B; font-size: 10px; font-style: italic;")
            btags_lay.addWidget(lbl_notags)

        btags_lay.addStretch()
        row_mid.addWidget(box_tags, 1)

        self.lay.addLayout(row_mid)

        # --- SECCIÓN INFERIOR: TOP NOTAS MÁS EXTENSAS ---
        box_top = QFrame()
        box_top.setStyleSheet(f"""
            QFrame {{
                background: {self.colores.get('bg_secundario', '#1E1E2E')};
                border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;
            }}
        """)
        top_lay = QVBoxLayout(box_top)
        top_lay.setSpacing(10)

        lbl_top_tit = QLabel("🏆 Notas Más Extensas de la Biblioteca")
        lbl_top_tit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_top_tit.setStyleSheet("color: white;")
        top_lay.addWidget(lbl_top_tit)

        notas_ordenadas = sorted(notas_stats, key=lambda x: -x["palabras"])[:5]
        max_palabras = notas_ordenadas[0]["palabras"] if notas_ordenadas else 1

        for idx, nota in enumerate(notas_ordenadas):
            row_n = QHBoxLayout()
            row_n.setSpacing(10)

            lbl_num = QLabel(f"#{idx+1}")
            lbl_num.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_num.setStyleSheet("color: #F59E0B; width: 20px;")
            row_n.addWidget(lbl_num)

            lbl_nom = QLabel(nota["nombre"])
            lbl_nom.setFont(QFont("Segoe UI", 10))
            lbl_nom.setStyleSheet("color: white;")
            row_n.addWidget(lbl_nom, 2)

            pb = QProgressBar()
            pb.setFixedHeight(8)
            pb.setTextVisible(False)
            pb.setRange(0, max(1, max_palabras))
            pb.setValue(nota["palabras"])
            pb.setStyleSheet("""
                QProgressBar { background: rgba(255,255,255,0.06); border-radius: 4px; }
                QProgressBar::chunk { background: #10B981; border-radius: 4px; }
            """)
            row_n.addWidget(pb, 3)

            lbl_p = QLabel(f"{nota['palabras']} palabras")
            lbl_p.setStyleSheet("color: #10B981; font-size: 10px; font-weight: bold;")
            row_n.addWidget(lbl_p)

            lbl_t_est = QLabel(f"~{max(1, round(nota['palabras']/200))} min")
            lbl_t_est.setStyleSheet("color: #64748B; font-size: 9px;")
            row_n.addWidget(lbl_t_est)

            top_lay.addLayout(row_n)

        self.lay.addWidget(box_top)
        self.lay.addStretch()
