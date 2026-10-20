

from gui.gui_frame import Gui
from services.fichero_service import Fichero
from utils.espannol_string_argparse import *
import argparse
from services.img_texto import ImgTexto
from constantes import Configuracion as conf
from utils.barra_progreso import BarraProgresoConsola


class Main():

    def __init__(self):

        self._img_texto = ImgTexto()
        self.fichero = Fichero()
        parser = self._get_parser()
        self._procesar_argumentos(parser)

    # Se ejecuta con entorno gráfico
    def _ejecutar_gui(self):
        gui = Gui()
        gui.mainloop()

    # Se ejecuta en modo consola
    def _ejecutar_modo_consola(self, args):
        barra_progreso = BarraProgresoConsola(100)
        print('Se ejecuta en modo consola.', '\n')
        if args.extraer is not None:
            img_file = args.extraer
            if self.fichero.existe(img_file):
                barra_progreso.dibuja_bp(10)
                texto = self._img_texto.extraer(img_file)
                text_file = self.fichero.marca_temporal()+'_'+conf.NOMBRE_ARCHIVO_TEXTO
                self.fichero.escribir_archivo_texto(text_file, texto)
                barra_progreso.dibuja_bp(80)
                print('\nEl texto se ha extraído con éxito en el archivo:', text_file, '\n')
            else:
                print('No se encuentra el fichero de la imagen.')

    def _get_parser(self):

        parser = argparse.ArgumentParser(
            description=conf.NOMBRE_AP+" "+str(conf.VERSION))  # formatter_class=CustomHelpFormatter
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-e', '--extraer', type=str,
                           metavar=('ARCHIVO'), help='Extrae el texto de la imagen')
        group.add_argument('-g', '--gui', action='store_true',
                           help='Se ejecuta el entorno gráfico')
        parser.add_argument('--version', action='version', version='%(prog)s ' +
                            conf.VERSION, help='Muestra la versión del programa')

        return parser

    def _procesar_argumentos(self, parser):

        args = parser.parse_args()
        if args.extraer:
            self._ejecutar_modo_consola(args)
        else:
            self._ejecutar_gui()
            

if __name__ == "__main__":

    Main()
