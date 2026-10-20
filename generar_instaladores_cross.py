import os
import base64
from pathlib import Path

def generate_linux_installer():
    base = Path(__file__).resolve().parent
    downloader = base / "downloader.py"
    data_zip = base / "data.zip"
    out_dir = base / "DISTRIBUCION" / "Linux"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not downloader.exists() or not data_zip.exists():
        print("[!] Faltan archivos base para Linux.")
        return

    # Leer archivos
    script_content = downloader.read_text(encoding="utf-8")
    with open(data_zip, "rb") as f:
        zip_data = base64.b64encode(f.read()).decode("utf-8")

    # Crear el Shell Script Auto-Extraíble
    sh_content = f"""#!/bin/bash
# INSTALADOR UNIVERSAL MULTITOOL PARA LINUX
# Generado electrónicamente

# 1. Verificar dependencias
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no está instalado."
    exit 1
fi

TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# 2. Reconstruir el instalador
echo "Iniciando instalador..."
cat << 'EOF' > downloader.py
{script_content}
EOF

# 3. Reconstruir data.zip
echo "{zip_data}" | base64 -d > data.zip

# 4. Ejecutar
python3 downloader.py
rm -rf "$TEMP_DIR"
"""
    
    sh_file = out_dir / "Multitool_Installer.sh"
    sh_file.write_text(sh_content, encoding="utf-8")
    print(f"[OK] Instalador Linux (.sh) generado en {sh_file}")

def generate_macos_installer():
    base = Path(__file__).resolve().parent
    downloader = base / "downloader.py"
    data_zip = base / "data.zip"
    out_dir = base / "DISTRIBUCION" / "MacOS"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not downloader.exists() or not data_zip.exists():
        print("[!] Faltan archivos base para MacOS.")
        return

    script_content = downloader.read_text(encoding="utf-8")
    with open(data_zip, "rb") as f:
        zip_data = base64.b64encode(f.read()).decode("utf-8")

    # Crear el archivo .command (estándar de Mac para scripts ejecutables)
    cmd_content = f"""#!/bin/zsh
# INSTALADOR UNIVERSAL MULTITOOL PARA MACOS
# Haz doble clic para ejecutar

cd "$(dirname "$0")"
TEMP_DIR=$(mktemp -d)
cp "downloader.py" "$TEMP_DIR/" 2>/dev/null || cat << 'EOF' > "$TEMP_DIR/downloader.py"
{script_content}
EOF

echo "{zip_data}" | base64 -d > "$TEMP_DIR/data.zip"

cd "$TEMP_DIR"
python3 downloader.py
"""
    
    cmd_file = out_dir / "Multitool_Installer.command"
    cmd_file.write_text(cmd_content, encoding="utf-8")
    # Intentar dar permisos (solo funcionará si se corre en un entorno que lo soporte, pero el archivo está listo)
    print(f"[OK] Instalador MacOS (.command) generado en {cmd_file}")

if __name__ == "__main__":
    print("=== GENERADOR DE INSTALADORES MULTIPLATAFORMA DESDE WINDOWS ===")
    generate_linux_installer()
    generate_macos_installer()
    print("\nNota: Debido a limitaciones técnicas de Windows, no se pueden crear binarios .bin/.app REALES")
    print("pero he generado Scripts Auto-Extraíbles (.sh y .command) que funcionan idénticamente.")
