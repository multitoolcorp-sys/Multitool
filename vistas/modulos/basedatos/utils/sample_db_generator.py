"""
sample_db_generator.py - Generador de la base de datos relacional de demostración
(multitool_sample.db) con llaves foráneas, tablas de ejemplo y registros iniciales.
"""


def crear_base_datos_inicial_demo(path_db: str, db_connection_cls):
    """Crea la base de datos inicial multitool_sample.db con un esquema relacional rico y llaves foráneas"""
    conn = db_connection_cls(path_db)
    if not conn.connect():
        return False

    try:
        conn.execute_query("PRAGMA foreign_keys = ON;")

        # 1. Departamentos
        conn.execute_query("""
            CREATE TABLE IF NOT EXISTS departamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                codigo TEXT UNIQUE NOT NULL,
                descripcion TEXT
            );
        """)

        # 2. Usuarios (Llave foránea -> departamentos)
        conn.execute_query("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                departamento_id INTEGER,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                rol TEXT DEFAULT 'Editor',
                activo BOOLEAN DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (departamento_id) REFERENCES departamentos(id) ON DELETE SET NULL
            );
        """)

        # 3. Proyectos (Llave foránea -> usuarios como líder)
        conn.execute_query("""
            CREATE TABLE IF NOT EXISTS proyectos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lider_id INTEGER,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                estado TEXT DEFAULT 'En Progreso',
                presupuesto REAL DEFAULT 0.0,
                fecha_inicio DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (lider_id) REFERENCES usuarios(id) ON DELETE SET NULL
            );
        """)

        # 4. Tareas (Llaves foráneas -> proyectos y usuarios)
        conn.execute_query("""
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER NOT NULL,
                asignado_a INTEGER,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                prioridad TEXT DEFAULT 'Media',
                estado TEXT DEFAULT 'Pendiente',
                fecha_limite DATE,
                FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
                FOREIGN KEY (asignado_a) REFERENCES usuarios(id) ON DELETE SET NULL
            );
        """)

        # 5. Comentarios (Llaves foráneas -> tareas y usuarios)
        conn.execute_query("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarea_id INTEGER NOT NULL,
                usuario_id INTEGER NOT NULL,
                contenido TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );
        """)

        # 6. Etiquetas
        conn.execute_query("""
            CREATE TABLE IF NOT EXISTS etiquetas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#6366F1'
            );
        """)

        # 7. Tabla Relacional Muchos-a-Muchos: Tarea_Etiquetas
        conn.execute_query("""
            CREATE TABLE IF NOT EXISTS tarea_etiquetas (
                tarea_id INTEGER NOT NULL,
                etiqueta_id INTEGER NOT NULL,
                PRIMARY KEY (tarea_id, etiqueta_id),
                FOREIGN KEY (tarea_id) REFERENCES tareas(id) ON DELETE CASCADE,
                FOREIGN KEY (etiqueta_id) REFERENCES etiquetas(id) ON DELETE CASCADE
            );
        """)

        # Poblado de datos de demostración
        conn.execute_query("""
            INSERT OR IGNORE INTO departamentos (id, nombre, codigo, descripcion) VALUES
            (1, 'Ingeniería de Software', 'ENG', 'Desarrollo de módulos y arquitectura'),
            (2, 'Diseño de Producto', 'DES', 'Interfaces modernas, estilos y UX'),
            (3, 'Control de Calidad', 'QA', 'Validación, pruebas y estabilidad');
        """)

        conn.execute_query("""
            INSERT OR IGNORE INTO usuarios (id, departamento_id, nombre, email, rol, activo) VALUES
            (1, 1, 'Admin MultiTool', 'admin@multitool.local', 'SuperAdmin', 1),
            (2, 1, 'Carlos Desarrollador', 'carlos@empresa.com', 'Desarrollador', 1),
            (3, 2, 'Lucía Diseñadora', 'lucia@estudio.io', 'Diseñadora UI', 1),
            (4, 3, 'Elena Calidad', 'elena@qa.testing', 'Tester QA', 1);
        """)

        conn.execute_query("""
            INSERT OR IGNORE INTO proyectos (id, lider_id, nombre, descripcion, estado, presupuesto, fecha_inicio) VALUES
            (1, 1, 'MultiTool Suite v2.0', 'Plataforma integrada de herramientas productivas', 'En Progreso', 12000.0, '2026-01-10'),
            (2, 3, 'Rediseño Dark Mode', 'Evolución de componentes visuales', 'Planificación', 4500.0, '2026-03-01');
        """)

        conn.execute_query("""
            INSERT OR IGNORE INTO tareas (id, proyecto_id, asignado_a, titulo, descripcion, prioridad, estado, fecha_limite) VALUES
            (1, 1, 2, 'Almacenamiento Estático de BD', 'Ruta segura y fija para bases de datos SQLite', 'Alta', 'En Progreso', '2026-09-15'),
            (2, 1, 2, 'Comandos SQL Puros', 'Interpretar CREATE DATABASE, USE, DROP y SHOW', 'Alta', 'Completada', '2026-09-10'),
            (3, 1, 3, 'Persistencia de Pestañas', 'Guardar editores y diagramas entre sesiones', 'Media', 'En Progreso', '2026-09-20'),
            (4, 2, 3, 'Relaciones ER Interactivas', 'Líneas curvas Bezier con badges para diagramas', 'Baja', 'Completada', '2026-08-30');
        """)

        conn.execute_query("""
            INSERT OR IGNORE INTO comentarios (id, tarea_id, usuario_id, contenido) VALUES
            (1, 1, 1, 'Se requiere sanitización de nombres para evitar path traversal.'),
            (2, 1, 2, 'Validación realizada exitosamente con pathlib.Path.resolve().'),
            (3, 4, 3, 'Las curvas Bezier facilitan ver las conexiones visualmente.'),
            (4, 3, 4, 'Comprobar restauración segura al reiniciar la aplicación.');
        """)

        conn.execute_query("""
            INSERT OR IGNORE INTO etiquetas (id, nombre, color) VALUES
            (1, 'Seguridad', '#EF4444'),
            (2, 'Base de Datos', '#3B82F6'),
            (3, 'Interfaz', '#10B981'),
            (4, 'Prioritario', '#F59E0B');
        """)

        conn.execute_query("""
            INSERT OR IGNORE INTO tarea_etiquetas (tarea_id, etiqueta_id) VALUES
            (1, 1),
            (1, 2),
            (2, 2),
            (3, 3),
            (4, 3);
        """)

        return True
    finally:
        conn.close()
