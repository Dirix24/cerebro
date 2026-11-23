"""Selección y vista previa de recuerdos para Studio y Acompañante."""
import json
from pathlib import Path
from tkinter import Button, END, EXTENDED, Label, Listbox, Text, Toplevel, filedialog, messagebox, simpledialog

from core.recuerdo_portable import LIMITE, crear, markdown, validar


def abrir(padre, pedir):
    def error(exc):
        messagebox.showerror("Recuerdos", str(exc), parent=padre)

    def revisar(recuerdo):
        estado = pedir("recuerdo-portable", {"recuerdo": recuerdo})
        ventana = Toplevel(padre)
        ventana.title("Vista previa del recuerdo")
        texto = Text(ventana, wrap="word", width=68, height=20)
        texto.pack(fill="both", expand=True)
        texto.insert(END, markdown(recuerdo))
        texto.configure(state="disabled")

        def guardar():
            try:
                resultado = pedir("recuerdo-portable", {"recuerdo": recuerdo, "confirmar": True})
                messagebox.showinfo("Recuerdos", f"Recuerdo {resultado['estado']}.\n"
                                    f"Lee el fragmento con /recuerdo {resultado['clave']}\n"
                                    f"Pregunta con /contexto-recuerdo {resultado['clave']} tu pregunta", parent=ventana)
                ventana.destroy()
            except (OSError, ValueError, RuntimeError) as exc:
                error(exc)

        if estado["estado"] == "nuevo":
            Button(ventana, text="Guardar en memoria", command=guardar).pack()
        else:
            Label(ventana, text=f"Estado en memoria: {estado['estado']}").pack()

    def importar():
        ruta = filedialog.askopenfilename(parent=padre, filetypes=[("Recuerdo de Cerebro", "*.json")])
        if ruta:
            try:
                origen = Path(ruta)
                if not origen.is_file():
                    raise ValueError("Selecciona un archivo regular.")
                with origen.open("rb") as archivo:
                    contenido = archivo.read(LIMITE + 1)
                if len(contenido) > LIMITE:
                    raise ValueError("El archivo supera el límite de importación.")
                revisar(validar(json.loads(contenido)))
            except (OSError, ValueError, RuntimeError, RecursionError) as exc:
                error(exc)

    try:
        datos = pedir("conversaciones")
    except (OSError, RuntimeError) as exc:
        error(exc)
        return
    ventana = Toplevel(padre)
    ventana.title("Recuerdos de la conversación")
    lista = Listbox(ventana, selectmode=EXTENDED, exportselection=False, width=68)
    lista.pack(fill="both", expand=True)
    mensajes = datos["turnos"]
    for mensaje in mensajes:
        lista.insert(END, mensaje["rol"] + " · " + " ".join(mensaje["texto"].split())[:100])

    def seleccionado():
        indices = lista.curselection()
        if not indices:
            messagebox.showinfo("Recuerdos", "Selecciona uno o varios mensajes.", parent=ventana)
            return None
        tema = simpledialog.askstring("Recuerdo", "Tema del fragmento", parent=ventana)
        if tema is None:
            return None
        return crear(tema, [mensajes[i] for i in indices], "Conversación local " + datos["activa"])

    def preparar(extension=None):
        try:
            recuerdo = seleccionado()
            if recuerdo is None:
                return
            if extension is None:
                revisar(recuerdo)
                return
            ruta = filedialog.asksaveasfilename(parent=ventana, defaultextension=extension,
                                                filetypes=[("Recuerdo de Cerebro", "*" + extension)])
            if ruta:
                contenido = json.dumps(recuerdo, ensure_ascii=False, indent=2) if extension == ".json" else markdown(recuerdo)
                Path(ruta).write_text(contenido, encoding="utf-8")
        except (OSError, ValueError, RuntimeError) as exc:
            error(exc)

    Button(ventana, text="Seleccionar mensajes visibles", command=lambda: lista.selection_set(0, END)).pack()
    Button(ventana, text="Guardar selección como recuerdo…", command=preparar).pack()
    Button(ventana, text="Exportar JSON…", command=lambda: preparar(".json")).pack()
    Button(ventana, text="Exportar Markdown…", command=lambda: preparar(".md")).pack()
    Button(ventana, text="Importar JSON…", command=importar).pack()
