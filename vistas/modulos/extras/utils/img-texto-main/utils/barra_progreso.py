
class BarraProgresoConsola():

    def __init__(self, total):
        self._total = total
        self._completado = 10  
        self._progreso = 'Progreso'
        self._completo = 'Completo'  
        self._zoom = 0.4
        
    def dibuja_bp (self, porcentaje, decimales = 0, relleno = '█' , print_end = "\r"):
      
        self._completado = self._completado + porcentaje
        percent = ("{0:." + str(decimales) + "f}").format(self._completado)
        total_rellenedado = int(self._completado)
        barra = relleno * round(total_rellenedado * self._zoom) + '=' * (round(self._total*self._zoom) - round(total_rellenedado * self._zoom))        
        print(f'\r{self._progreso} |{barra}| {percent}% {self._completo}', end = print_end)
       
        if self._completado == self._total: 
            print()