import json
import datetime

class FavoritesManager:
    def __init__(self, ruta_usuario, barra_callback=None, listbox_callback=None):
        self.ruta_usuario = ruta_usuario
        self.barra_callback = barra_callback
        self.listbox_callback = listbox_callback
        self.favoritos = self.cargar_favoritos()

    def cargar_favoritos(self):
        try:
            ruta = self.ruta_usuario / "favoritos.json"
            if ruta.exists():
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except: return []

    def guardar_favoritos(self):
        try:
            ruta = self.ruta_usuario / "favoritos.json"
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(self.favoritos, f, ensure_ascii=False, indent=4)
        except: pass

    def añadir_favorito(self, nombre, url, categoria="General"):
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.favoritos.append({"nombre": nombre, "url": url, "categoria": categoria, "fecha": fecha})
        self.guardar_favoritos()
        if self.barra_callback: self.barra_callback()
        if self.listbox_callback: self.listbox_callback()

    def eliminar_favorito(self, nombre):
        self.favoritos = [f for f in self.favoritos if f["nombre"] != nombre]
        self.guardar_favoritos()
        if self.barra_callback: self.barra_callback()
        if self.listbox_callback: self.listbox_callback()

    def obtener_categorias(self):
        cats = {f.get("categoria", "General") for f in self.favoritos}
        return sorted(list(cats))

    def reasignar_categoria(self, vieja, nueva="General"):
        for f in self.favoritos:
            if f.get("categoria", "General") == vieja:
                f["categoria"] = nueva
        self.guardar_favoritos()
        if self.listbox_callback: self.listbox_callback()

