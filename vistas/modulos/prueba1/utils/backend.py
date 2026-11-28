# -*- coding: utf-8 -*-
"""Backend y lógica de negocio del módulo prueba1."""


class Prueba1Backend:
    def procesar(self, texto: str) -> str:
        return f"Procesado: {texto}" if texto else "Listo."
