# 🛠️ MultiTool Suite

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-PyQt6-green?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![Architecture](https://img.shields.io/badge/Architecture-Modular%20MVC-orange)
![License](https://img.shields.io/badge/License-Proprietary-red)
![Version](https://img.shields.io/badge/Version-2.5%20Premium-purple)

**Una suite integral de productividad, utilidades y administración de alto rendimiento con interfaz moderna y arquitectura modular.**

[Características](#-características-principales) •
[Módulos](#-módulos-incluidos) •
[Instalación](#-instalación-y-puesta-en-marcha) •
[Arquitectura](#-estructura-del-proyecto) •
[Compilación](#-empaquetado-y-compilación) •
[Autor](#-contacto-y-créditos)

</div>

---

## 📖 Descripción General

**MultiTool** es una aplicación de escritorio diseñada para centralizar las tareas cotidianas de desarrollo, gestión de sistemas, productividad personal y entretenimiento en una única plataforma fluida, personalizable y reactiva. Desarrollada íntegramente con **Python** y **PyQt6**, ofrece una experiencia de usuario cuidada con soporte para temas dinámicos de alto contraste, widgets desacoplables en el escritorio y aceleración gráfica por hardware.

---

## ✨ Características Principales

- 🧩 **Widgets de Escritorio Desacoplables**: Ventanas flotantes ultra compactas con modo persiana y anclaje persistente al escritorio.
- 📱 **Espejo Celular (Phone Mirroring)**: Control total y transmisión a 60 FPS de smartphones Android vía USB o Wi-Fi con soporte ADB silencioso y "Modo Gamer" (UHID teclado/ratón 360°).
- 💬 **Asistente de IA Integrado**: Integración con modelos locales (Ollama) y proveedores en la nube con sanitización de datos personales (PII).
- 🌐 **Navegador Web Avanzado**: Motor WebView2 con autenticación Google OAuth (PKCE) y aislamiento de perfiles.
- 🗄️ **Gestor de Bases de Datos**: Cliente SQL multi-pestaña para MySQL/MariaDB con explorador de esquemas e historial interactivo.
- 🛡️ **Seguridad y Monitor del Sistema**: Análisis de procesos en tiempo real, escaneo de seguridad, control de inicio automático y bóveda cifrada.
- 🎨 **Theme Engine 2.0**: Personalización en tiempo real con paletas de color HSL/Hex, banner de perfil con efecto glassmorphism y presets oficiales (*Cyberpunk Neon*, *Midnight Obsidian*, *Dracula Purple*, etc.).
- 📦 **Sistema de Actualización Modular**: Detección de versiones y parches diferenciales en un clic.

---

## 🧩 Módulos Incluidos

| Módulo | Descripción |
| :--- | :--- |
| **Widgets (`vistas/modulos/widgets`)** | 12 utilidades rápidas (Notas, Terminal, Calculadora, Navegador, etc.) accesibles mediante ruleta giratoria interactiva o atajo directo `T`. |
| **Extras (`vistas/modulos/extras`)** | Espejo Android (scrcpy/ADB), herramienta de recortes Snipper con OCR en pantalla, pizarra interactiva, Soundboard, Ruleta al azar y tablero Kanban. |
| **Navegador (`vistas/modulos/navegador`)** | Navegación por pestañas basada en WebView2 con atajos rápidos y autenticación OAuth PKCE. |
| **Bases de Datos (`vistas/modulos/basedatos`)** | Conexión a bases de datos relacionales, ejecución de scripts SQL, visor de tablas y exportación de consultas. |
| **Notas y Cuaderno (`vistas/modulos/notas` / `cuaderno`)** | Editor Markdown completo con previsualización en vivo, gestión de backlinks, plantillas y tableros. |
| **Chat & IA (`vistas/modulos/chat`)** | Asistente inteligente con soporte para LLMs locales e interfaces conversacionales enriquecidas. |
| **Sistema & Seguridad (`vistas/modulos/sistema` / `seguridad`)** | Monitor de CPU/RAM, diagnósticos del SO, administrador de tareas y herramientas de diagnóstico. |
| **Tiempo & Rutinas (`vistas/modulos/tiempo`)** | Temporizador Pomodoro, cronómetro de precisión, reloj mundial y calculadora de husos horarios. |
| **Multimedia (`vistas/modulos/reproductor`)** | Reproductor de audio/video, ecualizador paramétrico, listas de reproducción y streaming de radio/TV online. |
| **Traductor (`vistas/modulos/traductor`)** | Traducción instantánea multilingüe de textos y documentos. |
| **Minijuegos (`vistas/modulos/minigames`)** | Entretenimiento integrado con Pacman, Damas, Buscaminas y Snake. |
| **Cuenta & Ajustes (`vistas/modulos/cuenta`)** | Configuración de perfil, PIN de bloqueo persistente, selector de avatar y exportación de respaldos `.mtbackup`. |

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos

- **Python 3.10 o superior** (Recomendado Python 3.12).
- Sistema Operativo: **Windows 10/11** (o distribuciones Linux compatibles con PyQt6).
- [Opcional] Herramientas Android SDK Platform-Tools (`adb`) y `scrcpy` para el submódulo de Espejo Celular.

### 1. Clonar el Repositorio

```bash
git clone https://github.com/multitoolcorp-sys/Multitool.git
cd Multitool
```

### 2. Crear y Activar un Entorno Virtual

En Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

En Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias

Instala los paquetes esenciales del proyecto:
```bash
pip install PyQt6 PyMySQL cryptography requests psutil
```

*(Adicionalmente, cada submódulo contiene su propio `requirements.txt` en caso de requerir librerías especializadas como Pillow, opencv o webview).*

### 4. Variables de Entorno (Opcional)

Si utilizas autenticación con Google OAuth en el navegador integrado, puedes definir tus credenciales en el entorno:

```powershell
$env:GOOGLE_CLIENT_ID="TU_CLIENT_ID.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET="TU_CLIENT_SECRET"
```

### 5. Iniciar la Aplicación

```bash
python main.py
```

---

## 📂 Estructura del Proyecto

```plaintext
multitool1/
├── main.py                     # Punto de entrada principal y bootstrap de Qt
├── console.py                  # Consola interactiva de diagnóstico
├── navegador.py                # Lanzador del módulo de navegación independiente
├── build.py                    # Script de compilación y empaquetado (Nuitka / PyInstaller)
├── compilar_actualizacion.py   # Generador de parches y paquetes de actualización .mtu
├── updater.py                  # Motor del actualizador automático
├── Multitool.spec              # Especificaciones de compilación PyInstaller
│
├── controlador/                # LÓGICA DE NEGOCIO Y CONTROLADORES
│   ├── auth/                   # Autenticación facial, PIN, validaciones y crypto
│   ├── commands/               # Motor de comandos de la suite
│   ├── conf/                   # Configuraciones de rutas del sistema
│   └── utils/                  # Gestor de dependencias, cargador dinámico de submódulos
│
├── vistas/                     # INTERFAZ DE USUARIO (MODERNA PYQT6)
│   ├── modulos/                # Módulos desacoplados de la suite
│   │   ├── widgets/            # Widgets desacoplables y selector de rueda
│   │   ├── extras/             # Espejo Celular, Snipper, Pizarra, Soundboard
│   │   ├── chat/               # Asistente IA conversacional
│   │   ├── navegador/          # Webview2 con soporte OAuth PKCE
│   │   ├── basedatos/          # Cliente MySQL / MariaDB
│   │   ├── notas/              # Editor Markdown y tableros
│   │   ├── cuenta/             # Perfil, Theme Engine 2.0 y Analíticas
│   │   ├── sistema/            # Monitor de hardware y diagnósticos
│   │   ├── reproductor/        # Multimedia y radio en línea
│   │   └── ...                 # Otros módulos
│   └── utils/                  # Temas, iconos, diagnósticos de inicio y bandejas
│
├── db_drivers/                 # Controladores y conectores embebidos (PyMySQL)
└── DESARROLLO/                 # Diagramas de flujo y capturas arquitectónicas
```

---

## 🔨 Empaquetado y Compilación

Para compilar un binario ejecutable autocontenido (.exe) para Windows con **Nuitka** o **PyInstaller**:

```powershell
python build.py
```

El ejecutable optimizado se generará automáticamente con todos los recursos e iconos enlazados.

---

## 🛡️ Seguridad y Privacidad

- **Cero Credenciales en Código**: Los secretos de autenticación se gestionan mediante variables de entorno del sistema o bóvedas locales cifradas.
- **Aislamiento de Datos**: Las carpetas de cuentas (`cuentas/`), historiales de portapapeles y perfiles de navegación (`browser_data/`) se mantienen excluidas del control de versiones para garantizar la privacidad del usuario.

---

## 👨‍💻 Contacto y Créditos

- **Autor:** Juan Luna ([NariyukiStudio](https://github.com/multitoolcorp-sys))
- **Organización:** [MultiTool Corp](https://github.com/multitoolcorp-sys)
- **Contacto:** [multitoolcorp@gmail.com](mailto:multitoolcorp@gmail.com)
- **Repositorio:** [github.com/multitoolcorp-sys/Multitool](https://github.com/multitoolcorp-sys/Multitool)

---

<div align="center">
Desarrollado con dedicación para una experiencia de escritorio moderna, rápida y productiva.
</div>
