import os
import sys
import urllib.request

def reporthook(count, block_size, total_size):
    if total_size > 0:
        percent = int(count * block_size * 100 / total_size)
        percent = min(percent, 100)
        sys.stdout.write(f"\rProgreso: {percent}%")
        sys.stdout.flush()

def main():
    urls = {
        "translate-en_es-1_0.argosmodel": "https://argos-net.com/v1/translate-en_es-1_0.argosmodel",
        "translate-es_en-1_9.argosmodel": "https://argos-net.com/v1/translate-es_en-1_9.argosmodel"
    }

    # Carpeta de destino
    dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vistas", "modulos", "traductor", "local_models")
    os.makedirs(dest_dir, exist_ok=True)

    print(f"Descargando modelos locales en: {dest_dir}\n")

    for filename, url in urls.items():
        dest_file = os.path.join(dest_dir, filename)
        if os.path.exists(dest_file):
            print(f"[-] {filename} ya existe en el directorio local. Omitiendo.")
            continue
        
        print(f"[+] Descargando {filename} desde:")
        print(f"    {url}")
        try:
            urllib.request.urlretrieve(url, dest_file, reporthook)
            print(f"\n[OK] {filename} descargado exitosamente.\n")
        except Exception as e:
            print(f"\n[Error] No se pudo descargar {filename}: {str(e)}\n")

    print("Proceso finalizado. Si colocas estos archivos en 'local_models', la aplicación los cargará automáticamente en modo offline.")

if __name__ == "__main__":
    main()
