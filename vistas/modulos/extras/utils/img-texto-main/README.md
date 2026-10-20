# img-texto
Extractor simple del texto de una imagen, permite ejecutarse en modo consola o mediante interfaz gráfica. Cuando se ejecuta en modo consola extrae el texto a un archivo, cuando lo hace en modo gráfico puede extraer el texto de toda la imagen o bien de la parte seleccionada a un cuadro de texto, pudiéndose, asimismo, copiar, cortar, retocar y exportar a un archivo.

# Requisitos
 Python 3.

 Como motor de OCR requiere Tesseract:
 
  En linux se puede instalar con apt-get o el gestor de paquetes correspondiente, por ejemplo:
```
 sudo apt-get install tesseract-ocr
 ```
En «windows» se puede descargar desde:
 ![Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

 IMPORTANTE: Tras instalar Tesseract en «windows», es preciso meterlo en las variables de entorno.

 
 Para la interfaz gráfica se requiere «tkinter».    
 En linux se puede instalar con apt-get o el gestor de paquetes correspondiente, por ejemplo:
```
 sudo apt-get install python3-tk
 ```
En «windows» está incluido a partir de python 3.

# Instalación de dependencias
Se instalan las dependencias establecidas en el setup:
```
 pip install .    
```
# Uso
```
Uso: img_texto.py [-h] [-e ARCHIVO | -g] [--version]

img-texto 1.3.1

argumentos opcionales:
  -h, --help            muestra este mensaje de ayuda y sale
  -e ARCHIVO, --extraer ARCHIVO  Extrae el texto de la imagen
  -g, --gui             Se ejecuta el entorno gráfico
  --version             Muestra la versión del programa

```
Por ejemplo:
```
## Extraer todo el texto de un archivo de imagen
python  img_texto.py -e ./rec/prueba.png
Se ejecuta en modo consola. 

Progreso |████████████████████████████████████████| 100% Completo

El texto se ha extraído con éxito en el archivo: 231101_220117_salida.txt
```

```
## Ejecutar en modo gráfico
python  img_texto.py
o bien:
python  img_texto.py -g
```

# Ejecutables para linux ubuntu y windows

Se encuentran en la carpeta «dist».
