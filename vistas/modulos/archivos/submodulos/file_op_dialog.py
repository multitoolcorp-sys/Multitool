import os
import sys
import platform
import ctypes
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QCheckBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap

# ─── NATIVE WINDOWS SHELL OPERATION (ctypes) ──────────────────────────────────
class SHFILEOPSTRUCTW(ctypes.Structure):
    if platform.system() == "Windows":
        from ctypes import wintypes
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.WORD),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

FO_MOVE   = 0x0001
FO_COPY   = 0x0002
FO_DELETE = 0x0003

FOF_ALLOWUNDO = 0x0040        # Mover a la Papelera de reciclaje / Ventana oficial de Windows
FOF_NOCONFIRMATION = 0x0010   # Opcional sin confirmación

def ejecutar_operacion_nativa_windows(accion: str, fuente: str, destino: str = None, parent_hwnd=None) -> bool:
    """
    Ejecuta operaciones de archivo (copiar, mover, eliminar) usando el shell nativo de Windows (SHFileOperationW).
    Muestra la ventana oficial de progreso de Windows, animaciones y solicitudes de permisos de administrador.
    """
    if platform.system() != "Windows":
        return False
        
    try:
        wFunc = None
        act_clean = accion.lower().strip()
        if act_clean in ["delete", "eliminar"]:
            wFunc = FO_DELETE
        elif act_clean in ["copy", "copiar"]:
            wFunc = FO_COPY
        elif act_clean in ["move", "mover", "cortar"]:
            wFunc = FO_MOVE
            
        if not wFunc:
            return False

        src_path = str(Path(fuente).resolve()) + "\0\0"
        dst_path = (str(Path(destino).resolve()) + "\0\0") if destino else None

        sf = SHFILEOPSTRUCTW()
        sf.hwnd = int(parent_hwnd) if parent_hwnd else 0
        sf.wFunc = wFunc
        sf.pFrom = src_path
        sf.pTo = dst_path
        sf.fFlags = FOF_ALLOWUNDO  # Ventana nativa + Papelera + Animaciones
        sf.fAnyOperationsAborted = False

        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(sf))
        return res == 0 and not sf.fAnyOperationsAborted
    except Exception as e:
        print(f"[WinShellOp Error]: {e}")
        return False


# ─── DIÁLOGO PYQT ESTILO WINDOWS 11 ───────────────────────────────────────────
class WinStyleFileOpDialog(QDialog):
    """
    Ventana de diálogo idéntica a la de Windows 11 para confirmación de permisos,
    progreso de copia/movimiento/eliminación con opción de omitir/continuar/cancelar.
    """
    def __init__(self, parent, titulo: str, mensaje: str, item_path: str = None, es_permiso_admin: bool = False, colores: dict = None):
        super().__init__(parent)
        self.colores = colores or {"bg_principal": "#1E1E2E", "bg_secundario": "#2A2A3C", "acento": "#6366F1"}
        self.item_path = Path(item_path) if item_path else None
        self.es_permiso_admin = es_permiso_admin
        self.respuesta = "cancel" # continue, skip, cancel
        self.hacer_para_todos = False

        self.setWindowTitle(titulo)
        self.setFixedWidth(460)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #F3F3F3;
                color: #000000;
                font-family: 'Segoe UI', sans-serif;
            }}
            QLabel {{
                color: #1F1F1F;
                background: transparent;
            }}
            QPushButton {{
                background-color: #E1E1E1;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                color: #000000;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #E5F1FB;
                border: 1px solid #0078D4;
            }}
            QPushButton#btn_continue {{
                background-color: #0078D4;
                color: white;
                border: 1px solid #005A9E;
                font-weight: bold;
            }}
            QPushButton#btn_continue:hover {{
                background-color: #106EBE;
            }}
            QProgressBar {{
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                text-align: center;
                background-color: #E6E6E6;
                height: 18px;
            }}
            QProgressBar::chunk {{
                background-color: #0078D4;
                border-radius: 3px;
            }}
            QCheckBox {{
                color: #333333;
                font-size: 12px;
            }}
        """)

        self._init_ui(titulo, mensaje)

    def _init_ui(self, titulo, mensaje):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Encabezado con Icono estilo Windows
        head_lay = QHBoxLayout()
        head_lay.setSpacing(14)

        # Icono de Reloj/Carpeta/Candado de Administrador
        lbl_icon = QLabel()
        if self.es_permiso_admin:
            lbl_icon.setText("🛡️")
            lbl_icon.setStyleSheet("font-size: 32px;")
        else:
            lbl_icon.setText("📁")
            lbl_icon.setStyleSheet("font-size: 32px;")
        head_lay.addWidget(lbl_icon, 0, Qt.AlignmentFlag.AlignTop)

        # Texto del título y descripción
        txt_lay = QVBoxLayout()
        txt_lay.setSpacing(4)
        
        lbl_sub = QLabel(mensaje)
        lbl_sub.setWordWrap(True)
        lbl_sub.setFont(QFont("Segoe UI", 10))
        txt_lay.addWidget(lbl_sub)
        
        head_lay.addLayout(txt_lay, 1)
        layout.addLayout(head_lay)

        # Detalles del Archivo / Carpeta si aplica
        if self.item_path and self.item_path.exists():
            detail_frame = QFrame()
            detail_frame.setStyleSheet("background: #EBEBEB; border-radius: 6px; border: 1px solid #E0E0E0;")
            det_lay = QHBoxLayout(detail_frame)
            det_lay.setContentsMargins(12, 10, 12, 10)
            
            lbl_item_icon = QLabel("📁" if self.item_path.is_dir() else "📄")
            lbl_item_icon.setStyleSheet("font-size: 24px;")
            det_lay.addWidget(lbl_item_icon)

            info_lay = QVBoxLayout()
            lbl_name = QLabel(self.item_path.name)
            lbl_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            info_lay.addWidget(lbl_name)

            try:
                stat = self.item_path.stat()
                import datetime
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %I:%M %p")
                lbl_meta = QLabel(f"Fecha de creación: {mtime}")
                lbl_meta.setStyleSheet("color: #666666; font-size: 11px;")
                info_lay.addWidget(lbl_meta)
            except:
                pass
                
            det_lay.addLayout(info_lay, 1)
            layout.addWidget(detail_frame)

        # Barra de progreso (para transferencias)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("")
        self.lbl_progress_status.setStyleSheet("color: #555555; font-size: 11px;")
        self.lbl_progress_status.setVisible(False)
        layout.addWidget(self.lbl_progress_status)

        # Checkbox "Hacer esto para todos los elementos actuales"
        self.chk_todos = QCheckBox("Hacer esto para todos los elementos actuales")
        layout.addWidget(self.chk_todos)

        # Botones de Acción: Continuar / Omitir / Cancelar
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        self.btn_continue = QPushButton("🛡️ Continuar" if self.es_permiso_admin else "Continuar")
        self.btn_continue.setObjectName("btn_continue")
        self.btn_continue.clicked.connect(self._on_continue)
        btn_lay.addWidget(self.btn_continue)

        self.btn_skip = QPushButton("Omitir")
        self.btn_skip.clicked.connect(self._on_skip)
        btn_lay.addWidget(self.btn_skip)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_lay.addWidget(self.btn_cancel)

        layout.addLayout(btn_lay)

    def _on_continue(self):
        self.respuesta = "continue"
        self.hacer_para_todos = self.chk_todos.isChecked()
        self.accept()

    def _on_skip(self):
        self.respuesta = "skip"
        self.hacer_para_todos = self.chk_todos.isChecked()
        self.accept()

    def _on_cancel(self):
        self.respuesta = "cancel"
        self.reject()

    def set_progress(self, percent: int, text: str):
        self.progress_bar.setVisible(True)
        self.lbl_progress_status.setVisible(True)
        self.progress_bar.setValue(percent)
        self.lbl_progress_status.setText(text)
