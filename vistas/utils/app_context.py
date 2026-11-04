class AppContext:
    def __init__(self, usuario, persona, ruta_usuario, config, app):
        self.usuario = usuario
        self.persona = persona
        self.ruta_usuario = ruta_usuario
        self.config = config
        self.app = app

    def abrir_en_modulo(self, modulo_nombre, submodulo_nombre=None, ruta_archivo=None):
        """Despacha una petición de apertura o envío de archivo hacia la ventana principal."""
        if hasattr(self, "app") and self.app and hasattr(self.app, "abrir_en_modulo"):
            return self.app.abrir_en_modulo(modulo_nombre, submodulo_nombre, ruta_archivo)
        return False
