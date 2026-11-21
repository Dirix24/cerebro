"""Estudio nativo para el núcleo de Cerebro, con un HUD inspirado en ARUS."""
from base64 import b64encode
from contextlib import suppress
from pathlib import Path
from queue import Empty, SimpleQueue
from secrets import token_hex
from threading import Lock, Thread
from tkinter import END, BOTH, LEFT, X, Y, Listbox, StringVar, Text, Tk, TclError
from tkinter import filedialog, messagebox, ttk
from urllib.parse import quote

from universe.lanzador import api, abrir, lanzar_acompanante, lanzar_terminal
from universe.mapa_studio import MapaStudio

FONDO = "#121920"
PANEL = "#17242e"
TEXTO = "#e9f3f6"
ACENTO = "#9fead9"


def abrir_studio(sesion, solicitud=None, inicial="proyecto"):
    try:
        app = Tk()
    except TclError as exc:
        raise RuntimeError("No pude abrir Studio. Necesitas una sesión gráfica y python3-tk.") from exc
    app.title("Cerebro Studio · Arquitectura ARUS")
    app.geometry("1120x720")
    app.minsize(720, 490)
    app.configure(bg=FONDO)
    estilo = ttk.Style(app)
    estilo.theme_use("clam")
    estilo.configure(".", background=FONDO, foreground=TEXTO, fieldbackground=PANEL)
    estilo.configure("TButton", background="#1e2e3a", foreground=TEXTO, padding=(10, 6),
                     borderwidth=0, bordercolor=FONDO, lightcolor=FONDO, darkcolor=FONDO)
    estilo.configure("TNotebook", background=FONDO, borderwidth=0)
    estilo.configure("TNotebook.Tab", background="#202d3a", foreground=TEXTO, padding=(13, 7))
    estilo.map("TNotebook.Tab", background=[("selected", "#284653")],
               foreground=[("selected", ACENTO)])
    estilo.map("TButton", background=[("active", "#263d4a")])
    estilo.configure("Titulo.TLabel", font=("TkDefaultFont", 17, "bold"), foreground=ACENTO)
    estilo.configure("TEntry", fieldbackground=PANEL, foreground=TEXTO, insertcolor=TEXTO,
                     bordercolor="#36515f", lightcolor=PANEL, darkcolor=PANEL)
    estilo.configure("TPanedwindow", background=FONDO)

    estado = StringVar(value="Conectando con Cerebro…")
    ruta = StringVar()
    entrada = StringVar()
    pendientes = SimpleQueue()
    tareas_en_curso = set()
    identificador = token_hex(12)
    presencia = Lock()
    visible = True
    generacion = 0

    def pedir(operacion, datos=None):
        return api(sesion, operacion, datos)

    def publicar(trabajo, terminado=lambda _: None):
        def hacer():
            try:
                pendientes.put((terminado, trabajo(), None))
            except (OSError, ValueError, RuntimeError) as exc:
                pendientes.put((None, None, str(exc)))
        Thread(target=hacer, daemon=True).start()

    def boton(padre, nombre, accion):
        widget = ttk.Button(padre, text=nombre, command=accion)
        widget.pack(side=LEFT, padx=(0, 6), pady=3)
        return widget

    def campo_texto(padre, *, codigo=False):
        campo = Text(padre, bg=PANEL, fg=TEXTO, insertbackground=ACENTO, relief="flat",
                     padx=10, pady=9, wrap="none" if codigo else "word",
                     font=("TkFixedFont", 11) if codigo else ("TkDefaultFont", 10))
        campo.pack(fill=BOTH, expand=True)
        return campo

    def mostrar(campo, contenido, *, anexar=False):
        campo.configure(state="normal")
        if not anexar:
            campo.delete("1.0", END)
        campo.insert(END, contenido)
        if anexar:
            campo.see(END)
        campo.configure(state="normal" if campo is editor else "disabled")

    cabecera = ttk.Frame(app, padding=(16, 12))
    cabecera.pack(fill=X)
    ttk.Label(cabecera, text="Cerebro Studio", style="Titulo.TLabel").pack(side=LEFT, padx=(0, 15))
    boton(cabecera, "Terminal", lanzar_terminal)
    boton(cabecera, "Acompañante", app.iconify)
    boton(cabecera, "Chat web", lambda: abrir(sesion, "chat"))
    paginas = ttk.Notebook(app)
    paginas.pack(fill=BOTH, expand=True, padx=14, pady=4)
    cuerpo = ttk.Panedwindow(paginas, orient="horizontal")
    paginas.add(cuerpo, text="Proyecto")

    def actualizar_mapa():
        publicar(lambda: pedir("nodos"), mapa.actualizar)

    mapa = MapaStudio(paginas, actualizar_mapa)
    paginas.add(mapa, text="Universe")

    def pagina_activa(_evento):
        if paginas.select() == str(mapa):
            actualizar_mapa()

    paginas.bind("<<NotebookTabChanged>>", pagina_activa)
    archivos = ttk.Frame(cuerpo, padding=(4, 7, 9, 4))
    codigo = ttk.Frame(cuerpo, padding=(5, 7, 9, 4))
    chat = ttk.Frame(cuerpo, padding=(5, 7, 4, 4))
    cuerpo.add(archivos, weight=1)
    cuerpo.add(codigo, weight=4)
    cuerpo.add(chat, weight=3)

    ttk.Label(archivos, text="Archivos del proyecto").pack(anchor="w", pady=(0, 7))
    lista = Listbox(archivos, width=19, bg=PANEL, fg=TEXTO, selectbackground="#346355",
                    relief="flat", highlightthickness=0, exportselection=False)
    lista.pack(fill=BOTH, expand=True)
    barra_archivos = ttk.Frame(archivos)
    barra_archivos.pack(fill=X)

    ttk.Label(codigo, text="Editor").pack(anchor="w", pady=(0, 7))
    ttk.Entry(codigo, textvariable=ruta).pack(fill=X, pady=(0, 4))
    editor = campo_texto(codigo, codigo=True)
    barra_editor = ttk.Frame(codigo)
    barra_editor.pack(fill=X)
    ttk.Label(chat, text="Conversación y análisis").pack(anchor="w", pady=(0, 7))
    salida = campo_texto(chat)
    salida.configure(state="disabled")
    consulta = ttk.Entry(chat, textvariable=entrada)
    consulta.pack(fill=X, pady=(6, 1))
    barra_chat = ttk.Frame(chat)
    barra_chat.pack(fill=X)
    ttk.Label(app, textvariable=estado, padding=(16, 7), anchor="w").pack(fill=X)

    def actualizar_archivos():
        def cargar(datos):
            lista.delete(0, END)
            for nombre in datos["archivos"]:
                lista.insert(END, nombre)
        publicar(lambda: pedir("archivos"), cargar)

    def cargar_archivo(_evento=None):
        seleccionado = lista.curselection()
        if not seleccionado:
            return
        if editor.edit_modified() and not messagebox.askyesno("Cambios sin guardar", "¿Abrir otro archivo?"):
            return
        nombre = lista.get(seleccionado[0])

        def copiar(datos):
            ruta.set(nombre)
            mostrar(editor, datos["texto"])
            editor.edit_modified(False)

        publicar(lambda: pedir("archivo?nombre=" + quote(nombre)), copiar)

    def guardar():
        nombre = ruta.get().strip()
        contenido = editor.get("1.0", "end-1c")
        if not nombre:
            estado.set("Escribe una ruta para el archivo, como src/ejemplo.py.")
            return

        def guardado(_):
            if editor.get("1.0", "end-1c") == contenido:
                editor.edit_modified(False)
            estado.set("Archivo guardado: " + nombre)
            actualizar_archivos()
        publicar(lambda: pedir("archivo", {"nombre": nombre, "texto": contenido}), guardado)

    def revisar():
        nombre = ruta.get().strip()
        if not nombre or editor.edit_modified():
            estado.set("Guarda el archivo antes de validar su sintaxis.")
            return
        publicar(lambda: pedir("tarea", {"accion": "sintaxis", "nombre": nombre}),
                  lambda dato: tareas_en_curso.add(dato["id"]))
        estado.set("Validación solicitada.")

    def enviar(texto=None):
        texto = (entrada.get() if texto is None else texto).strip()
        if not texto:
            return
        entrada.set("")
        mostrar(salida, "\nTú · " + texto + "\n", anexar=True)
        estado.set("Procesando…")

        def respondido(dato):
            mostrar(salida, "Cerebro · " + dato["respuesta"] + "\n", anexar=True)
            estado.set("Núcleo conectado")

        publicar(lambda: pedir("chat", {"mensaje": texto, "modo": "studio"}), respondido)

    def adjuntar():
        archivo = filedialog.askopenfilename(title="Seleccionar documento o vídeo")
        if not archivo:
            return
        origen = Path(archivo)

        def subir():
            with origen.open("rb") as lector:
                limite = 16 * 1024 * 1024
                datos = lector.read(limite + 1)
            if len(datos) > limite:
                raise ValueError("El adjunto supera 16 MiB.")
            return pedir("adjunto", {"nombre": origen.name, "contenido": b64encode(datos).decode()})

        def adjunto(dato):
            estado.set("Archivo adjunto: " + dato["nombre"])
            if origen.suffix.lower() not in (".srt", ".vtt"):
                enviar("Analiza " + dato["nombre"])

        publicar(subir, adjunto)

    def informar(enfocar=False):
        nonlocal generacion
        generacion += 1
        turno, se_ve = generacion, visible

        def enviar_presencia():
            with presencia:
                if turno == generacion:
                    api(sesion, "interfaz", {"id": identificador, "modo": "studio",
                                             "visible": se_ve, "enfocar": enfocar}, tiempo=2)

        publicar(enviar_presencia)

    def visibilidad(evento, mostrar):
        nonlocal visible
        if evento.widget is app:
            visible = mostrar
            informar(mostrar)
            if not mostrar:
                lanzar_acompanante()

    def pulso():
        if solicitud is not None:
            try:
                destino = solicitud.read_text(encoding="ascii")
            except FileNotFoundError:
                destino = None
            if destino is not None:
                solicitud.unlink(missing_ok=True)
                paginas.select(mapa if destino == "universe" else cuerpo)
                app.deiconify()
                app.lift()
        if visible:
            informar()
        if tareas_en_curso:
            def mostrar_tareas(datos):
                for tarea in datos:
                    if tarea["id"] in tareas_en_curso and tarea["estado"] in {"terminada", "error"}:
                        mostrar(salida, "\nValidación · " + tarea["salida"] + "\n", anexar=True)
                        tareas_en_curso.remove(tarea["id"])
            publicar(lambda: pedir("tareas"), mostrar_tareas)
        app.after(2000, pulso)

    def procesar():
        while True:
            try:
                terminado, datos, error = pendientes.get_nowait()
            except Empty:
                break
            if error:
                estado.set(error)
            else:
                terminado(datos)
        app.after(75, procesar)

    def cerrar():
        nonlocal generacion
        if editor.edit_modified() and not messagebox.askyesno("Cambios sin guardar", "¿Cerrar Studio?"):
            return
        generacion += 1
        with presencia, suppress(OSError, RuntimeError):
            api(sesion, "interfaz", {"id": identificador, "modo": "studio", "visible": False}, tiempo=1)
        app.destroy()

    boton(barra_archivos, "Actualizar", actualizar_archivos)
    boton(barra_editor, "Guardar", guardar)
    boton(barra_editor, "Validar Python", revisar)
    boton(barra_chat, "Enviar", enviar)
    boton(barra_chat, "Adjuntar", adjuntar)
    lista.bind("<<ListboxSelect>>", cargar_archivo)
    consulta.bind("<Return>", lambda _: enviar())
    app.bind("<FocusIn>", lambda evento: informar(True) if evento.widget is app and visible else None)
    app.bind("<Map>", lambda evento: visibilidad(evento, True))
    app.bind("<Unmap>", lambda evento: visibilidad(evento, False))
    app.protocol("WM_DELETE_WINDOW", cerrar)
    if inicial == "universe":
        paginas.select(mapa)
    actualizar_archivos()
    publicar(lambda: pedir("historial"), lambda datos: mostrar(salida, "\n".join(
        f"{'Tú' if turno['rol'] == 'usuario' else 'Cerebro'} · {turno['texto']}"
        for turno in datos["turnos"][-20:]
    ) + "\n", anexar=True))
    publicar(lambda: pedir("estado"), lambda _: estado.set("Núcleo conectado"))
    informar(True)
    app.after(75, procesar)
    app.after(2000, pulso)
    consulta.focus_set()
    app.mainloop()
