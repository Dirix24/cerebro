"""Selector de conversaciones compartido por Studio y el acompañante."""
from tkinter import END, MULTIPLE, Listbox, StringVar, Toplevel
from tkinter import messagebox, ttk

from universe.paleta import ACENTO, FONDO, PANEL, SECUNDARIO, SELECCION, TEXTO


def gestionar_conversaciones(padre, pedir, actualizado):
    try:
        datos = pedir("conversaciones")
    except (OSError, RuntimeError, ValueError) as exc:
        messagebox.showerror("Conversaciones", str(exc), parent=padre)
        return

    ventana = Toplevel(padre, bg=FONDO)
    ventana.title("Conversaciones de Cerebro")
    ventana.transient(padre)
    ventana.minsize(320, 270)
    cuerpo = ttk.Frame(ventana, padding=14)
    cuerpo.pack(fill="both", expand=True)
    ttk.Label(cuerpo, text="Conversaciones guardadas", foreground=ACENTO).pack(anchor="w")
    resumen = StringVar(value="Selecciona uno o varios chats.")
    ttk.Label(cuerpo, textvariable=resumen, foreground=SECUNDARIO).pack(anchor="w", pady=(3, 8))
    marco = ttk.Frame(cuerpo)
    marco.pack(fill="both", expand=True)
    lista = Listbox(marco, selectmode=MULTIPLE, exportselection=False, width=36, height=8,
                    bg=PANEL, fg=TEXTO, selectbackground=SELECCION, selectforeground=TEXTO,
                    borderwidth=0, highlightthickness=0)
    barra = ttk.Scrollbar(marco, command=lista.yview)
    barra.pack(side="right", fill="y")
    lista.configure(yscrollcommand=barra.set)
    lista.pack(fill="both", expand=True)
    chats = datos["chats"]
    for chat in chats:
        lista.insert(END, ("● " if chat["id"] == datos["activa"] else "   ") + chat["titulo"])

    def ejecutar(operacion, carga):
        try:
            resultado = pedir(operacion, carga)
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("Conversaciones", str(exc), parent=ventana)
            return
        ventana.destroy()
        actualizado(resultado)

    def seleccion():
        return [chats[indice]["id"] for indice in lista.curselection()]

    def contar(_evento=None):
        cantidad = len(seleccion())
        resumen.set(f"{cantidad} de {len(chats)} seleccionados")
        abrir.configure(state="normal" if cantidad == 1 else "disabled")
        borrar.configure(state="normal" if cantidad else "disabled")

    def todo():
        if len(lista.curselection()) == len(chats):
            lista.selection_clear(0, END)
        else:
            lista.selection_set(0, END)
        contar()

    def abrir_chat():
        ids = seleccion()
        if len(ids) == 1:
            ejecutar("conversaciones", {"accion": "seleccionar", "id": ids[0]})

    def eliminar():
        ids = seleccion()
        if ids and messagebox.askyesno("Eliminar chats", f"¿Eliminar {len(ids)} conversaciones seleccionadas?", parent=ventana):
            ejecutar("borrar-conversaciones", {"confirmar": True, "ids": ids})

    acciones = ttk.Frame(cuerpo)
    acciones.pack(fill="x", pady=(8, 0))
    ttk.Button(acciones, text="Seleccionar todo", command=todo).pack(side="left")
    abrir = ttk.Button(acciones, text="Abrir", command=abrir_chat)
    abrir.pack(side="left", padx=5)
    borrar = ttk.Button(acciones, text="Eliminar", command=eliminar)
    borrar.pack(side="left")
    contar()
    lista.bind("<<ListboxSelect>>", contar)
    ventana.bind("<Escape>", lambda _: ventana.destroy())
    ventana.grab_set()
    lista.focus_set()
