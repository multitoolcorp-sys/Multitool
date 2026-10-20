import psutil
import threading
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QTimer

def actualizar_procesos(tab_instance):
    """Actualiza la lista de procesos del sistema de forma asíncrona y con alto contraste."""
    tabla = tab_instance.table_procs
    filtro = tab_instance.txt_proc_search.text().lower().strip()

    def _worker():
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info
                pid = str(info['pid'])
                nombre = str(info['name'] or "Desconocido")
                usuario = str(info['username'] or "Sistema")
                cpu_val = float(info['cpu_percent'] or 0.0)
                mem_val = float(info['memory_percent'] or 0.0)
                estado = str(info['status'] or "activo")

                texto = f"{pid} {nombre} {usuario}".lower()
                if filtro and filtro not in texto:
                    continue

                procs.append({
                    "pid": pid,
                    "nombre": nombre,
                    "usuario": usuario,
                    "cpu": f"{cpu_val:.1f}%",
                    "cpu_val": cpu_val,
                    "memoria": f"{mem_val:.1f}%",
                    "mem_val": mem_val,
                    "estado": estado
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        # Ordenar por uso de memoria descendente
        procs.sort(key=lambda x: x["mem_val"], reverse=True)

        QTimer.singleShot(0, lambda: _render_procs_ui(tab_instance, procs))

    threading.Thread(target=_worker, daemon=True).start()


def _render_procs_ui(tab_instance, procs):
    tabla = tab_instance.table_procs
    tabla.setRowCount(0)
    font_family = getattr(tab_instance, "font_family", "Segoe UI")

    for p in procs:
        fila = tabla.rowCount()
        tabla.insertRow(fila)

        # 0. PID
        item_pid = QTableWidgetItem(p["pid"])
        item_pid.setFont(QFont("Consolas", 9))
        item_pid.setForeground(QColor("#AAB0B8"))
        tabla.setItem(fila, 0, item_pid)

        # 1. Nombre
        item_nombre = QTableWidgetItem(p["nombre"])
        item_nombre.setFont(QFont(font_family, 9, QFont.Weight.Bold))
        item_nombre.setForeground(QColor("#FFFFFF"))
        tabla.setItem(fila, 1, item_nombre)

        # 2. Usuario
        item_user = QTableWidgetItem(p["usuario"])
        item_user.setFont(QFont(font_family, 8))
        item_user.setForeground(QColor("#D1D5DB"))
        tabla.setItem(fila, 2, item_user)

        # 3. CPU % (Color semántico)
        item_cpu = QTableWidgetItem(p["cpu"])
        item_cpu.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        if p["cpu_val"] >= 20.0:
            item_cpu.setForeground(QColor("#F87171")) # Rojo
        elif p["cpu_val"] >= 5.0:
            item_cpu.setForeground(QColor("#FBBF24")) # Amarillo
        else:
            item_cpu.setForeground(QColor("#34D399")) # Verde
        tabla.setItem(fila, 3, item_cpu)

        # 4. Memoria %
        item_mem = QTableWidgetItem(p["memoria"])
        item_mem.setFont(QFont("Consolas", 9))
        item_mem.setForeground(QColor("#60A5FA")) # Azul claro
        tabla.setItem(fila, 4, item_mem)

        # 5. Estado
        item_estado = QTableWidgetItem(p["estado"])
        item_estado.setFont(QFont(font_family, 8))
        if p["estado"] in ("running", "activo", "active"):
            item_estado.setForeground(QColor("#34D399"))
        else:
            item_estado.setForeground(QColor("#9CA3AF"))
        tabla.setItem(fila, 5, item_estado)


def finalizar_proceso(tab_instance):
    """Termina el proceso seleccionado tras confirmación del usuario."""
    tabla = tab_instance.table_procs
    fila = tabla.currentRow()

    if fila < 0:
        QMessageBox.information(tab_instance, "Procesos", "Selecciona un proceso de la lista para terminarlo.")
        return

    pid_str = tabla.item(fila, 0).text()
    nombre_proc = tabla.item(fila, 1).text()

    resp = QMessageBox.question(
        tab_instance,
        "Confirmar Terminación",
        f"¿Estás seguro de que deseas finalizar el proceso?\n\nPID: {pid_str}\nNombre: {nombre_proc}\n\n⚠️ Datos no guardados en ese programa podrían perderse.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if resp == QMessageBox.StandardButton.Yes:
        try:
            pid = int(pid_str)
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=2)
        except psutil.TimeoutExpired:
            try:
                p.kill()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(tab_instance, "Error", f"No se pudo terminar el proceso: {e}")

        actualizar_procesos(tab_instance)
