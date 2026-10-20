import math

class CalculadoraFinancieraLogic:
    @staticmethod
    def calcular_interes_compuesto(capital, tasa_porcentaje, periodo_anos, frecuencia):
        """
        Calcula el interés compuesto.
        Retorna: (monto_final, interes_ganado, desglose_texto)
        """
        tasa = tasa_porcentaje / 100
        
        # Determinar número de periodos de capitalización por año
        n_map = {
            "Anual": 1,
            "Semestral": 2,
            "Trimestral": 4,
            "Mensual": 12,
            "Diaria": 365
        }
        n = n_map.get(frecuencia, 1)
        
        # Calcular monto final
        monto_final = capital * (1 + tasa/n)**(n*periodo_anos)
        interes_ganado = monto_final - capital
        
        resultado_txt = f"Capital inicial: {capital:.2f}\n"
        resultado_txt += f"Tasa de interés: {tasa_porcentaje:.2f}%\n"
        resultado_txt += f"Periodo: {periodo_anos} años\n"
        resultado_txt += f"Frecuencia de capitalización: {frecuencia}\n"
        resultado_txt += f"Monto final: {monto_final:.2f}\n"
        resultado_txt += f"Interés ganado: {interes_ganado:.2f}"
        
        return monto_final, interes_ganado, resultado_txt

    @staticmethod
    def calcular_amortizacion(monto, tasa_porcentaje, plazo_anos, frecuencia):
        """
        Calcula la amortización de un préstamo.
        Retorna: (cuota, total_pagado, intereses, desglose_texto)
        """
        tasa = tasa_porcentaje / 100
        
        # Determinar número de pagos
        frec_map = {
            "Anual": (1, 1),
            "Semestral": (2, 2),
            "Trimestral": (4, 4),
            "Mensual": (12, 12)
        }
        mult_pagos, div_tasa = frec_map.get(frecuencia, (12, 12))
        
        n_pagos = plazo_anos * mult_pagos
        tasa_periodo = tasa / div_tasa
        
        # Calcular cuota
        if tasa_periodo == 0:
            cuota = monto / n_pagos
        else:
            cuota = monto * (tasa_periodo * (1 + tasa_periodo)**n_pagos) / ((1 + tasa_periodo)**n_pagos - 1)
        
        # Calcular total pagado e intereses
        total_pagado = cuota * n_pagos
        intereses = total_pagado - monto
        
        resultado_txt = f"Monto del préstamo: {monto:.2f}\n"
        resultado_txt += f"Tasa de interés: {tasa_porcentaje:.2f}%\n"
        resultado_txt += f"Plazo: {plazo_anos} años\n"
        resultado_txt += f"Frecuencia de pago: {frecuencia}\n"
        resultado_txt += f"Número de pagos: {n_pagos}\n"
        resultado_txt += f"Cuota {frecuencia.lower()}: {cuota:.2f}\n"
        resultado_txt += f"Total a pagar: {total_pagado:.2f}\n"
        resultado_txt += f"Total intereses: {intereses:.2f}"
        
        return cuota, total_pagado, intereses, resultado_txt

    @staticmethod
    def calcular_valor_futuro(presente, tasa_porcentaje, periodo_anos, aportacion, frecuencia_aportacion):
        """
        Calcula el valor futuro.
        Retorna: (valor_futuro, desglose_texto)
        """
        tasa = tasa_porcentaje / 100
        
        n_map = {
            "Anual": (1, 1),
            "Semestral": (2, 2),
            "Trimestral": (4, 4),
            "Mensual": (12, 12)
        }
        n, div_tasa = n_map.get(frecuencia_aportacion, (1, 1))
        tasa_periodo = tasa / div_tasa if frecuencia_aportacion != "Anual" else tasa # This logic in original was slightly implicit but effectively: if Annual n=1, tasa_periodo=tasa.
        if frecuencia_aportacion == "Anual":
             tasa_periodo = tasa
    
        # Logic directly copied from original:
        # if frecuencia == "Anual": n=1; tasa_periodo = tasa
        # elif ... n=2; tasa_periodo = tasa/2 ...
        
        # Calcular valor futuro del capital inicial
        vf_capital = presente * (1 + tasa/n)**(n*periodo_anos)
        
        # Calcular valor futuro de las aportaciones
        if aportacion > 0:
            if tasa_periodo == 0:
                vf_aportaciones = aportacion * n * periodo_anos
            else:
                vf_aportaciones = aportacion * ((1 + tasa_periodo)**(n*periodo_anos) - 1) / tasa_periodo
        else:
            vf_aportaciones = 0
            
        valor_futuro = vf_capital + vf_aportaciones
        
        resultado_txt = f"Valor presente: {presente:.2f}\n"
        resultado_txt += f"Tasa de interés: {tasa_porcentaje:.2f}%\n"
        resultado_txt += f"Periodo: {periodo_anos} años\n"
        if aportacion > 0:
            resultado_txt += f"Aportación {frecuencia_aportacion.lower()}: {aportacion:.2f}\n"
        resultado_txt += f"Valor futuro del capital inicial: {vf_capital:.2f}\n"
        if aportacion > 0:
            resultado_txt += f"Valor futuro de las aportaciones: {vf_aportaciones:.2f}\n"
        resultado_txt += f"Valor futuro total: {valor_futuro:.2f}"
        
        return valor_futuro, resultado_txt

    @staticmethod
    def calcular_valor_presente(futuro, tasa_porcentaje, periodo_anos):
        """
        Calcula el valor presente.
        Retorna: (valor_presente, desglose_texto)
        """
        tasa = tasa_porcentaje / 100
        
        if tasa == 0:
            valor_presente = futuro
        else:
            valor_presente = futuro / (1 + tasa)**periodo_anos
            
        resultado_txt = f"Valor futuro: {futuro:.2f}\n"
        resultado_txt += f"Tasa de interés: {tasa_porcentaje:.2f}%\n"
        resultado_txt += f"Periodo: {periodo_anos} años\n"
        resultado_txt += f"Valor presente: {valor_presente:.2f}"
        
        return valor_presente, resultado_txt

    @staticmethod
    def calcular_tir(inversion, flujos):
        """
        Calcula la TIR.
        Retorna: (tir, desglose_texto)
        """
        flujo_completo = [inversion] + flujos
        
        def van(tasa):
            return sum(flujo / (1 + tasa)**(i) for i, flujo in enumerate(flujo_completo))
            
        tasa_min = -0.999
        tasa_max = 1.0
        precision = 0.0001
        max_iteraciones = 1000
        
        if van(tasa_min) * van(tasa_max) > 0:
            raise ValueError("No se puede calcular la TIR con estos flujos de caja")
            
        for _ in range(max_iteraciones):
            tasa_media = (tasa_min + tasa_max) / 2
            van_media = van(tasa_media)
            
            if abs(van_media) < precision:
                break
            
            if van_media * van(tasa_min) < 0:
                tasa_max = tasa_media
            else:
                tasa_min = tasa_media
                
        tir = tasa_media
        
        flujos_texto = ", ".join(map(str, flujos))
        resultado_txt = f"Inversión inicial: {inversion:.2f}\n"
        resultado_txt += f"Flujos de caja: {flujos_texto}\n"
        resultado_txt += f"TIR: {tir*100:.2f}%"
        
        return tir, resultado_txt

