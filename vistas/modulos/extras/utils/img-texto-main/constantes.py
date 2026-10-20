import os

class Configuracion:

    __slots__ = ()
    NOMBRE_AP = 'img-texto'
    DESCRIPCION_AP = ' Extractor simple del texto de una imagen'
    VERSION = '1.3.0'
    CREDITOS = 'César Medina'
    
   
    
    # Directorio de la aplicación
    DIR_APP = os.path.dirname(os.path.abspath(__file__))  
    DIR_DOCUMENTOS = os.path.expanduser("~") 
    DIR_IMA = 'rec'+os.path.sep  
    DIR_SALIDA = 'salida'+os.path.sep  
    DIR_TXT = DIR_IMA
    NOMBRE_ARCHIVO_TEXTO = 'salida.txt'   
    
    # PID
    PID_FILE =  DIR_APP+os.path.sep+'pid.pid'
   
   
   
  
   
    
    
