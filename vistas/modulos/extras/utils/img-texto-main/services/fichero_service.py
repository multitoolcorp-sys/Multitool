
import os
from constantes import Configuracion as conf
from datetime import datetime

class Fichero():
    
    def leer_archivo(self, ruta_archivo):
        with open(ruta_archivo, 'rb') as archivo:
            contenido = archivo.read()
        return contenido

    def escribir_archivo(self, ruta_archivo, contenido):
        with open(ruta_archivo, 'wb') as archivo:
            archivo.write(contenido)
    
    def escribir_archivo_texto(self, ruta_archivo, contenido):       
        self.escribir_archivo(ruta_archivo, contenido.encode())

    def marca_temporal(self):
        ahora = datetime.now()
        return ahora.strftime('%y%m%d_%H%M%S')
    
    def existe(self,ruta):       
        if not os.path.isfile(ruta):
            return False       
        return True
    
    # Si no puede resolver el directorio devuelve uno por defecto
    def obtener_directorio(self, dir):
        if os.path.isdir(dir):           
            return dir        
        return conf.DIR_DOCUMENTOS + os.path.sep 
    
    def obtener_ruta_absoluta(self, dir):
        return os.path.abspath(dir)