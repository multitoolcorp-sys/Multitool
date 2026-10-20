import datetime
import calendar

class CalculadoraFechasLogic:
    @staticmethod
    def calcular_diferencia(fecha1, fecha2, formato):
        """Calcula la diferencia entre dos fechas"""
        invertido = False
        if fecha2 < fecha1:
            fecha1, fecha2 = fecha2, fecha1
            invertido = True
            
        delta = fecha2 - fecha1
        dias_totales = delta.days
        
        resultado = ""
        if formato == "Días":
            resultado = f"{dias_totales} días"
        elif formato == "Semanas y días":
            semanas = dias_totales // 7
            dias_resto = dias_totales % 7
            resultado = f"{semanas} semanas y {dias_resto} días"
        elif formato == "Meses y días":
            meses, dias_resto = CalculadoraFechasLogic._obtener_meses_dias(fecha1, fecha2)
            resultado = f"{meses} meses y {dias_resto} días"
        elif formato == "Años, meses y días":
            anos, meses, dias_resto = CalculadoraFechasLogic._obtener_anos_meses_dias(fecha1, fecha2)
            partes = []
            if anos > 0: partes.append(f"{anos} año{'s' if anos > 1 else ''}")
            if meses > 0: partes.append(f"{meses} mes{'es' if meses > 1 else ''}")
            if dias_resto > 0 or not partes: partes.append(f"{dias_resto} día{'s' if dias_resto > 1 or dias_resto==0 else ''}")
            resultado = " y ".join(partes)
        elif formato == "Todo detallado":
            anos = dias_totales // 365
            semanas = (dias_totales % 365) // 7
            dias_resto = dias_totales - (anos * 365 + semanas * 7)
            horas = 24 * dias_totales
            minutos = horas * 60
            segundos = minutos * 60
            resultado = f"Diferencia total: {dias_totales} días\n• {anos} años, {semanas} semanas y {dias_resto} días\n• {horas:,} horas\n• {minutos:,} minutos\n• {segundos:,} segundos"

        return resultado, invertido

    @staticmethod
    def _obtener_meses_dias(fecha1, fecha2):
        meses = 0
        temp = fecha1
        while True:
            m = temp.month + 1 if temp.month < 12 else 1
            y = temp.year if temp.month < 12 else temp.year + 1
            dia = min(temp.day, calendar.monthrange(y, m)[1])
            sig = datetime.date(y, m, dia)
            if sig > fecha2: break
            meses += 1
            temp = sig
        return meses, (fecha2 - temp).days

    @staticmethod
    def _obtener_anos_meses_dias(fecha1, fecha2):
        anos = 0
        temp = fecha1
        while True:
            y = temp.year + 1
            dia = min(temp.day, 29 if calendar.isleap(y) and temp.month == 2 else calendar.monthrange(y, temp.month)[1])
            sig = datetime.date(y, temp.month, dia)
            if sig > fecha2: break
            anos += 1
            temp = sig
        meses, dias = CalculadoraFechasLogic._obtener_meses_dias(temp, fecha2)
        return anos, meses, dias

    @staticmethod
    def calcular_añadir_dias(fecha_base, dias, solo_laborables):
        """Añade o resta días a una fecha"""
        if solo_laborables:
            dias_contados = 0
            res = fecha_base
            while dias_contados < abs(dias):
                res += datetime.timedelta(days=1 if dias > 0 else -1)
                if res.weekday() < 5:
                    dias_contados += 1
            return res
        return fecha_base + datetime.timedelta(days=dias)

    @staticmethod
    def calcular_dias_laborables(fecha1, fecha2, inc_sab, inc_dom):
        """Calcula días laborables entre fechas"""
        if fecha2 < fecha1: fecha1, fecha2 = fecha2, fecha1
        d_lab = 0
        d_tot = (fecha2 - fecha1).days + 1
        curr = fecha1
        while curr <= fecha2:
            wd = curr.weekday()
            if wd < 5 or (wd == 5 and inc_sab) or (wd == 6 and inc_dom):
                d_lab += 1
            curr += datetime.timedelta(days=1)
        return d_lab, d_tot

