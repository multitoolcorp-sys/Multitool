import threading
import tkinter.messagebox as tkmb
from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.font import Font
from tkinter.ttk import Progressbar
from PIL import Image as ImagePIL, UnidentifiedImageError
from PIL import ImageTk
from constantes import Configuracion as conf
from services.fichero_service import Fichero
from services.img_texto import ImgTexto


class Gui(Frame):

    def __init__(self, master=None):

        super().__init__(master)

        self._img_texto = ImgTexto()
        self.fichero = Fichero()
        self.coordenadas_recorte = ()
        self.x = self.y = 0
        self.start_x = None
        self.start_y = None
        self.rect = None

        self._ruta_archivo = ''
        self.master.title(conf.NOMBRE_AP)
        self.master.geometry("1200x700")

        self.addTitulo()
        self.addControles()
        self.addMenu()

        self.pack()

    def addMenu(self):
        menu = Menu(self)

        file_menu = Menu(menu, tearoff=0)
        file_menu.add_command(
            label="Abrir", command=self.seleccionar_archivo, accelerator='Ctrl+A')

        menu_interno = Menu(file_menu, tearoff=0)
        menu_interno.add_command(
            label="Extraer", command=self.hilo_extraer_texto)
        file_menu.add_command(label="Salir", command=self.quit)
        menu.add_cascade(label="Archivo", menu=file_menu)

        help_menu = Menu(menu, tearoff=0)
        help_menu.add_command(label="Acerca de...",
                              command=lambda:  tkmb.showinfo(title='Acerca de...',
                                                             message=conf.NOMBRE_AP+' ' +
                                                             conf.VERSION, icon='info', detail=conf.DESCRIPCION_AP +
                                                             '\n\n'+conf.CREDITOS+', 2023\nVillalmanzo, (España)'))
        menu.add_cascade(label="Ayuda", menu=help_menu)

        # Establece la barra de menú como la barra de menú principal
        self.master.config(menu=menu)

    def addTitulo(self):
        # Crear el frame que contiene los controles
        controles_frame = Frame(
            self, highlightbackground="white", highlightthickness=2)
        controles_frame.pack(fill=BOTH, pady=(10, 5))
        titulo = Label(controles_frame, text=conf.DESCRIPCION_AP)
        font_style = Font(family="Lucida Grande", size=20)
        titulo.config(font=font_style)

        titulo.pack(pady=5)
        descripcion = Label(controles_frame, text='Selecciona el archivo')
        descripcion.pack(pady=5)

    def addControles(self):
         # Controles de archivo:
        self.add_marco_controles_archivo()

        # Barra de progreso:
        self.add_barra_progreso()

        # Marco medio
        self.add_marco_medio()

    def add_marco_medio(self):
        self.medio_frame = Frame(self)
        self.medio_frame.pack(pady=10, padx=15, fill='both', expand=True)

        self.canvas_frame = Frame(self.medio_frame)
        self.canvas_frame.pack(side='left', fill='y', expand=True)

        # Crear un canvas para mostrar la imagen
        self.canvas = Canvas(self.canvas_frame, width=300,
                             height=600, relief='solid', bd=2,  cursor="cross")
        self.canvas.pack(side='left', fill='y', expand=True)
        # Eventos del canvas
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Se añade un área de texto para mostrar el resultado de la operación
        self.resultado = Text(self.medio_frame, width=200,
                              relief='solid', bd=2)
        self.resultado.pack(side='left', fill='both', expand=True)
        self.resultado.bind('<Button-3><ButtonRelease-3>', self.show_menu)
        self.resultado.tag_config(
            'sel', background="black", foreground="white")

    def add_barra_progreso(self):
        self.pie_frame = Frame(self)
        self.pie_frame.pack(pady=10, padx=10)

        self.progress_bar = Progressbar(
            self.pie_frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10, fill="x")
        self.label_pie = Label(self.pie_frame, text='', width=100)
        self.label_pie.pack()

    def add_marco_controles_archivo(self):
        self.archivo_frame = Frame(self)
        self.archivo_frame.pack(padx=10, pady=10)
        boton_seleccionar_archivo = Button(
            self.archivo_frame, text='Selecciona', command=self.seleccionar_archivo)
        self.label_archivo = Label(
            self.archivo_frame, text='', highlightbackground="grey", highlightthickness=2,  width=50)

        boton_seleccionar_archivo.pack(side="left", pady=10)
        self.label_archivo.pack(side="left", pady=10, fill=BOTH)
        self.boton_extraer = Button(
            self.archivo_frame, text='Extraer texto', command=self.extraer_texto)
        self.boton_extraer.pack(side='left')
        self.boton_extraer_archivo = Button(
            self.archivo_frame, text='Extraer texto a archivo', command=self.extraer_texto_archivo)
        self.boton_extraer_archivo.pack(side='left', expand=True)

    def seleccionar_todo(self):
        self.resultado.tag_add("sel", "1.0", "end")

    def show_menu(self, event):

        menu = Menu(self.resultado, tearoff=0)
        menu.add_command(label="Seleccionar todo",
                         command=self.seleccionar_todo)
        menu.add_command(
            label="Cortar", command=lambda: self.resultado.event_generate('<<Cut>>'))
        menu.add_command(
            label="Copiar", command=lambda: self.resultado.event_generate('<<Copy>>'))
        menu.add_command(
            label="Pegar", command=lambda: self.resultado.event_generate('<<Paste>>'))

        menu.post(event.x_root, event.y_root)

    def hay_archivo_seleccionado(self):
        if self._ruta_archivo == '':
            return False
        return True

    def extraer_texto(self):
        self.inicializar_controles()
        if not self.hay_archivo_seleccionado():
            self.resultado['text'] = 'No hay un archivo seleccionado'
        else:
            self.progress_bar["value"] = 10
            if self.coordenadas_recorte:
                texto = self._img_texto.extraer_parte(
                    self._ruta_archivo, self.coordenadas_recorte)
            else:
                texto = self._img_texto.extraer(self._ruta_archivo)
            self.resultado.insert('insert', texto)
            self.progress_bar["value"] = 100
            self.label_pie['text'] = 'Proceso completo'

    def extraer_texto_archivo(self):

        if not self.hay_archivo_seleccionado():
            self.label_pie['text'] = 'No hay un archivo seleccionado'
        else:
            self.progress_bar["value"] = 10
            texto = self.resultado.get('1.0', 'end')
            if not texto.strip():
                texto = self._img_texto.extraer(self._ruta_archivo)
                self.resultado.insert('insert', texto)
            dir_salida = self.fichero.obtener_directorio(conf.DIR_SALIDA)    
            text_file = dir_salida+self.fichero.marca_temporal()+'_' + \
                conf.NOMBRE_ARCHIVO_TEXTO
            self.fichero.escribir_archivo_texto(text_file, texto)
            self.progress_bar["value"] = 100
            self.label_pie['text'] = 'El archivo se ha creado en ' + \
                self.fichero.obtener_ruta_absoluta(text_file)

    def barra_progreso_callback(self, valor=10):
        # TODO: Mejorar transición..
        if self.progress_bar['value'] < 100:
            self.progress_bar['value'] += valor

    def hilo_extraer_texto(self):
        threading.Thread(target=self.extraer_texto).start()

    def seleccionar_archivo(self):
        # Muestra el diálogo de selección de archivos
        self.inicializar_controles()
        dir_ima = self.fichero.obtener_directorio(conf.DIR_IMA)
        self._ruta_archivo = askopenfilename(initialdir=dir_ima)
        self.label_archivo['text'] = self._ruta_archivo
        if self._ruta_archivo:
            try:
                imagen = ImagePIL.open(self._ruta_archivo)
                self.imagen_original_size = imagen.size
                self.image = self._img_texto.redimensionar_img(imagen)
                self.wazil, self.lard = self.image.size
                self.canvas.config(scrollregion=(0, 0, self.wazil, self.lard))
                self.tk_image = ImageTk.PhotoImage(self.image)
                self.canvas.create_image(
                    0, 0, anchor="nw", image=self.tk_image)
            except UnidentifiedImageError:
                tkmb.showinfo(title='Info...', icon='info',
                              detail='El archibo NO es una imagen')
                self.inicializar_controles()

    def inicializar_controles(self):
        self.progress_bar.stop()
        self.resultado.delete('1.0', 'end')
        self.label_pie['text'] = ''

    def on_button_press(self, event):
        if self.rect:
            self.canvas.delete(self.rect)
            self.coordenadas_recorte = ()
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.x, self.y, 1, 1, fill="", outline="red")

    def on_move_press(self, event):
        curX, curY = (event.x, event.y)
        ox, oy = self.imagen_original_size
        x, y = self.image.size
        self.coordenadas_recorte = (
            self.start_x*ox/x, self.start_y*oy/y, curX*ox/x, curY*oy/y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        pass

