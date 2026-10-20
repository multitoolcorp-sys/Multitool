def show_tab(app, tab):
    """Muestra la pestaña seleccionada (Login/Register) en el QTabWidget de PyQt6"""
    
    # En PyQt6, si usamos un QTabWidget como el definido en main.py,
    # simplemente cambiamos el índice actual.
    
    if hasattr(app, 'auth_tabs'):
        if tab == "login":
            app.auth_tabs.setCurrentIndex(0)
        elif tab == "register":
            app.auth_tabs.setCurrentIndex(1)
            
    # Si por algún motivo se seguían usando botones para cambiar de pestaña manualmente:
    # app.login_tab_btn y app.register_tab_btn deben ser actualizados si existen.
    # Pero con QTabWidget, el usuario puede simplemente clickear las pestañas.
