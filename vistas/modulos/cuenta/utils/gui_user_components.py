import tkinter as tk
from vistas.modulos.cuenta.utils.colores import COLORES

class UserComponentsBuilder:
    @staticmethod
    def crear_seccion_perfil(gui_instance, parent_frame, config):
        frame_perfil = tk.LabelFrame(
            parent_frame, 
            text="Perfil de Usuario", 
            font=("Arial", 12, "bold"),
            bg=COLORES["bg_secundario"],
            fg=COLORES["acento"],
            padx=20, pady=20
        )
        frame_perfil.pack(fill="x", pady=(0, 20))

        # Avatar y Nickname
        header_frame = tk.Frame(frame_perfil, bg=COLORES["bg_secundario"])
        header_frame.pack(fill="x")

        # Avatar
        gui_instance.avatar_label = tk.Label(header_frame, bg=COLORES["bg_terciario"], width=100, height=100)
        gui_instance.avatar_label.pack(side="left", padx=(0, 20))
        gui_instance.actualizar_avatar_ui()

        info_text_frame = tk.Frame(header_frame, bg=COLORES["bg_secundario"])
        info_text_frame.pack(side="left", fill="y")

        gui_instance.lbl_nick_title = tk.Label(
            info_text_frame, text=gui_instance.usuario, 
            font=("Arial", 20, "bold"), 
            bg=COLORES["bg_secundario"], fg=COLORES["fg_principal"]
        )
        gui_instance.lbl_nick_title.pack(anchor="w")

        fecha_reg = config.get("fecha_registro", "N/A")
        persona_db = config.get("persona", gui_instance.persona)

        tk.Label(
            info_text_frame, text=f"Identidad (Carpeta): {persona_db}", 
            font=("Arial", 10, "bold"), bg=COLORES["bg_secundario"], fg=COLORES["acento"]
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            info_text_frame, text=f"Registrado el: {fecha_reg}", 
            font=("Arial", 10), bg=COLORES["bg_secundario"], fg=COLORES["fg_secundario"]
        ).pack(anchor="w")
        
        # Botón cambiar avatar
        btn_avatar = tk.Button(
            frame_perfil, text="Cambiar Avatar", 
            command=gui_instance.solicitar_cambio_avatar,
            bg=COLORES["bg_terciario"], fg=COLORES["fg_principal"],
            bd=0, padx=10, pady=5, cursor="hand2"
        )
        btn_avatar.pack(anchor="w", pady=(15, 0))

    @staticmethod
    def crear_seccion_ajustes(gui_instance, parent_frame, config):
        gui_instance.frame_config = tk.LabelFrame(
            parent_frame, 
            text="Ajustes de Cuenta y Seguridad", 
            font=("Arial", 12, "bold"),
            bg=COLORES["bg_secundario"],
            fg=COLORES["acento"],
            padx=20, pady=20
        )
        gui_instance.frame_config.pack(fill="x", pady=(0, 20))

        # 1. Ajuste de Nickname (Usuario)
        tk.Label(
            gui_instance.frame_config, text="Nombre de Usuario (Login):", 
            font=("Arial", 10, "bold"), bg=COLORES["bg_secundario"], fg=COLORES["fg_principal"]
        ).pack(anchor="w", pady=(0, 5))
        
        gui_instance.ent_new_nick = tk.Entry(
            gui_instance.frame_config, 
            bg=COLORES["bg_terciario"], fg="white", 
            insertbackground="white", bd=0, font=("Arial", 12)
        )
        gui_instance.ent_new_nick.pack(fill="x", pady=(0, 15), ipady=5)
        gui_instance.ent_new_nick.insert(0, config.get("usuario", gui_instance.usuario))

        # 2. Auto-login
        gui_instance.var_login = tk.BooleanVar(value=config.get("login", False))
        chk_login = tk.Checkbutton(
            gui_instance.frame_config,
            text="Mantener sesión iniciada (Auto-login)",
            variable=gui_instance.var_login,
            font=("Arial", 11),
            bg=COLORES["bg_secundario"],
            fg=COLORES["fg_principal"],
            selectcolor=COLORES["bg_terciario"],
            activebackground=COLORES["bg_secundario"],
            activeforeground=COLORES["fg_principal"],
            cursor="hand2"
        )
        chk_login.pack(anchor="w", pady=5)
        
        tk.Label(
            gui_instance.frame_config,
            text="Protección: Se requerirá tu contraseña para confirmar los cambios.",
            font=("Arial", 9, "italic"),
            bg=COLORES["bg_secundario"],
            fg=COLORES["acento"]
        ).pack(anchor="w", pady=(10, 15))

        # 3. Confirmación por contraseña
        tk.Label(
            gui_instance.frame_config, text="Contraseña Actual:", 
            font=("Arial", 10), bg=COLORES["bg_secundario"], fg=COLORES["fg_principal"]
        ).pack(anchor="w")
        
        gui_instance.ent_pass_confirm = tk.Entry(
            gui_instance.frame_config, show="*", 
            bg=COLORES["bg_terciario"], fg="white", 
            insertbackground="white", bd=0, font=("Arial", 12)
        )
        gui_instance.ent_pass_confirm.pack(fill="x", pady=5, ipady=5)

        # Botonera
        btn_save = tk.Button(
            gui_instance.frame_config,
            text="GUARDAR CAMBIOS",
            font=("Arial", 10, "bold"),
            bg=COLORES["acento"],
            fg="white",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            command=gui_instance.intentar_guardar
        )
        btn_save.pack(anchor="e", pady=(10, 0))

    @staticmethod
    def crear_seccion_registros(gui_instance, parent_frame, config):
        frame_logs = tk.LabelFrame(
            parent_frame, 
            text="Registros de Actividad", 
            font=("Arial", 12, "bold"),
            bg=COLORES["bg_secundario"],
            fg=COLORES["acento"],
            padx=20, pady=20
        )
        frame_logs.pack(fill="x")

        tk.Label(
            frame_logs, 
            text="Historial de accesos recientes (Solo lectura):", 
            font=("Arial", 10), 
            bg=COLORES["bg_secundario"], 
            fg=COLORES["fg_secundario"]
        ).pack(anchor="w", pady=(0, 10))

        gui_instance.list_logs = tk.Text(
            frame_logs, height=8, 
            bg=COLORES["bg_terciario"], fg="white", 
            font=("Consolas", 9), bd=0, padx=10, pady=10
        )
        gui_instance.list_logs.pack(fill="x")
        
        gui_instance.list_logs.insert("end", f"[{config.get('ultimo_acceso', 'N/A')}] Login exitoso.\\n")
        gui_instance.list_logs.insert("end", f"[{config.get('fecha_registro', 'N/A')}] Cuenta creada.\\n")
        gui_instance.list_logs.config(state="disabled")

