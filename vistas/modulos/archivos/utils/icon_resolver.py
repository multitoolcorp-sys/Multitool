import os
import platform
import mimetypes

class IconResolver:
    """Resuelve iconos (emojis) y descripciones de tipos de archivos según el sistema operativo"""
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        mimetypes.init()
        
        # Mapeo de extensiones a Emojis
        self.emojis = {
            "folder": "📁",
            "file": "📄",
            # Documentos
            ".pdf": "📕",
            ".doc": "📘", ".docx": "📘", ".odt": "📘",
            ".xls": "📗", ".xlsx": "📗", ".csv": "📗",
            ".ppt": "📙", ".pptx": "📙",
            ".txt": "📑", ".rtf": "📝", ".md": "📝",
            # Multimedia
            ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️", ".gif": "🖼️", ".bmp": "🖼️", ".svg": "🎨",
            ".mp3": "🎵", ".wav": "🎵", ".flac": "🎵", ".ogg": "🎵",
            ".mp4": "🎬", ".mkv": "🎬", ".avi": "🎬", ".mov": "🎬",
            # Web & Code
            ".html": "🌐", ".htm": "🌐", ".css": "💄", ".js": "📜",
            ".py": "🐍", ".java": "☕", ".cpp": "👾", ".c": "👾", ".cs": "🔷",
            ".php": "🐘", ".rb": "💎", ".go": "🐹", ".rs": "🦀", ".json": "📦",
            ".sql": "🗄️", ".xml": "🧬", ".sh": "📟", ".bat": "📟", ".ps1": "📟",
            # Archivos & Sistemas
            ".zip": "📦", ".rar": "📦", ".7z": "📦", ".tar": "📦", ".gz": "📦",
            ".exe": "⚙️", ".msi": "⚙️", ".dll": "🔧", ".sys": "🔧",
            ".iso": "💿", ".vmdk": "🗄️",
            ".lnk": "🔗", ".url": "🔗",
            ".ttf": "🔤", ".otf": "🔤",
            ".db": "🗄️", ".sqlite": "🗄️"
        }

    def get_emoji(self, ext, is_dir=False):
        """Retorna el emoji correspondiente a la extensión"""
        if is_dir:
            return self.emojis["folder"]
        return self.emojis.get(ext.lower(), self.emojis["file"])

    def get_system_type_name(self, path):
        """Obtiene la descripción del tipo de archivo (ej: 'Documento PDF')"""
        if self.is_windows:
            return self._get_windows_type(path)
        
        # Fallback para Linux/Mac usando mimetypes
        mime, _ = mimetypes.guess_type(path)
        if mime:
            # Ejemplo: 'application/pdf' -> 'application pdf'
            return mime.replace('/', ' ').title()
        
        return "Archivo" if os.path.isfile(path) else "Carpeta"

    def _get_windows_type(self, path):
        """Llamada a la API de Windows para obtener el nombre del tipo"""
        try:
            import ctypes
            from ctypes import wintypes
            
            class SHFILEINFO(ctypes.Structure):
                _fields_ = [
                    ("hIcon", wintypes.HANDLE),
                    ("iIcon", ctypes.c_int),
                    ("dwAttributes", wintypes.DWORD),
                    ("szDisplayName", ctypes.c_wchar * 260),
                    ("szTypeName", ctypes.c_wchar * 80)
                ]

            shell32 = ctypes.windll.shell32
            SHGFI_TYPENAME = 0x000000400
            SHGFI_USEFILEATTRIBUTES = 0x000000010
            
            shfileinfo = SHFILEINFO()
            res = shell32.SHGetFileInfoW(
                ctypes.c_wchar_p(path),
                0x80, # FILE_ATTRIBUTE_NORMAL
                ctypes.byref(shfileinfo),
                ctypes.sizeof(shfileinfo),
                SHGFI_TYPENAME | SHGFI_USEFILEATTRIBUTES
            )
            
            if res:
                return shfileinfo.szTypeName
        except:
            pass
        return None

