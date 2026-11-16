"""Chat gráfico local opcional. Requiere checkpoint propio entrenado."""
import argparse
import queue
import threading
from pathlib import Path

from agent.controlled_agent import ControlledAgent
from chat import Conversacion
from core.historial_local import consultar, guardar
from main import cargar_modelo
from memory.advanced_memory import AdvancedMemoryManager

RUTA_HISTORIAL = Path(__file__).resolve().parent / "data" / "historial_cerebro.jsonl"


def crear_conversacion():
    modelo, meta, ruta = cargar_modelo()
    if modelo is None:
        raise FileNotFoundError("Falta checkpoint propio: ejecuta python3 train.py")
    return Conversacion(modelo, AdvancedMemoryManager(), ControlledAgent(),
                        info_checkpoint=meta)


def ventana(guardar_automaticamente=False):
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    root = tk.Tk()
    root.title("Cerebro · Chat local")
    root.geometry("800x600")
    mensajes = scrolledtext.ScrolledText(root, state="disabled", wrap="word")
    mensajes.pack(fill="both", expand=True, padx=12, pady=12)
    entrada = ttk.Entry(root)
    entrada.pack(fill="x", padx=12, pady=4)
    cola = queue.Queue()
    conversacion = None
    ocupado = False

    def mostrar(rol, texto):
        mensajes.configure(state="normal")
        mensajes.insert("end", f"{rol}: {texto}\n\n")
        mensajes.configure(state="disabled")
        mensajes.see("end")

    try:
        conversacion = crear_conversacion()
        mostrar("Sistema", "Modelo propio cargado. /ayuda muestra los comandos.")
    except (OSError, ValueError) as exc:
        mostrar("Sistema", str(exc))
        messagebox.showwarning("Cerebro", str(exc))

    def enviar():
        nonlocal ocupado
        texto = entrada.get().strip()
        if not texto or ocupado or conversacion is None:
            return
        entrada.delete(0, "end")
        mostrar("Tú", texto)
        ocupado = True
        boton.configure(state="disabled")

        def trabajar():
            try:
                respuesta, salir = conversacion.procesar(texto)
                if guardar_automaticamente and not texto.startswith("/"):
                    guardar(RUTA_HISTORIAL, "usuario", texto)
                    if respuesta:
                        guardar(RUTA_HISTORIAL, "cerebro", respuesta)
                cola.put((respuesta, salir, None))
            except Exception as exc:
                cola.put(("", False, str(exc)))

        threading.Thread(target=trabajar, daemon=True).start()

    def revisar():
        nonlocal ocupado
        try:
            while True:
                respuesta, salir, error = cola.get_nowait()
                mostrar("Sistema" if error else "Cerebro", error or respuesta)
                ocupado = False
                boton.configure(state="normal")
                if salir:
                    root.after(100, root.destroy)
        except queue.Empty:
            pass
        root.after(100, revisar)

    def ver_historial():
        for turno in consultar(RUTA_HISTORIAL, limite=30):
            mostrar(turno["rol"], turno["texto"])

    barra = ttk.Frame(root)
    barra.pack(fill="x", padx=12, pady=8)
    boton = ttk.Button(barra, text="Enviar", command=enviar)
    boton.pack(side="left")
    ttk.Button(barra, text="Ver historial", command=ver_historial).pack(side="left", padx=8)
    entrada.bind("<Return>", lambda _e: enviar())
    root.after(100, revisar)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="Chat gráfico de Cerebro")
    ap.add_argument("--guardar-historial", action="store_true",
                    help="guardar automáticamente los mensajes locales")
    args = ap.parse_args()
    ventana(args.guardar_historial)


if __name__ == "__main__":
    main()
