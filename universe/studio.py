"""Estudio nativo para el núcleo de Cerebro, con un HUD inspirado en ARUS."""
from base64 import b64decode, b64encode
from contextlib import suppress
from io import BytesIO, StringIO
from csv import Error as ErrorCSV
import keyword
import json
from pathlib import Path
import re
from queue import Empty, SimpleQueue
from secrets import token_hex
from threading import Lock, Thread
import tokenize
from tkinter import END, BOTH, LEFT, RIGHT, X, Y, BooleanVar, Canvas, Listbox, Menu, PhotoImage, StringVar, Text, Tk, TclError
from tkinter import filedialog, messagebox, simpledialog, ttk
from urllib.parse import quote, urlsplit

from core.escritorio_studio import archivo_soltado, intencion_archivo, intencion_carpeta
from core.visores_studio import HTML_INICIAL, html_estatico, tabla
from universe.lanzador import ErrorAPI, api, abrir, abrir_web, carpeta, lanzar_acompanante, lanzar_tactil, lanzar_terminal
from universe.mapa_studio import MapaStudio

from universe.paleta import ACENTO, ACTIVO, BORDE, EDITOR, FONDO, PANEL, SECUNDARIO, SELECCION, TEXTO


def pedir_con_reconexion(sesion, cerrojo, operacion, datos=None, tiempo=25):
    """Reconecta lecturas a la sesión publicada. Las escrituras nunca se reintentan."""
    with cerrojo:
        anterior = sesion.copy()
    try:
        return api(anterior, operacion, datos, tiempo=tiempo)
    except (OSError, ErrorAPI) as error:
        if isinstance(error, ErrorAPI) and error.codigo != 401:
            raise
        with cerrojo:
            nueva = sesion.copy()
            if nueva == anterior:
                try:
                    nueva = json.loads((carpeta() / "sesion.json").read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    raise error
                if (not isinstance(nueva, dict) or nueva == anterior
                        or not isinstance(nueva.get("url"), str) or not isinstance(nueva.get("token"), str)):
                    raise error
                api(nueva, "conversacion-activa", tiempo=2)
                sesion.update(nueva)
        if datos is not None:
            raise RuntimeError("El núcleo cambió de sesión. Comprueba el estado antes de repetir la acción.") from error
        return api(nueva, operacion, tiempo=tiempo)


def abrir_studio(sesion, solicitud=None, inicial="proyecto"):
    try:
        app = Tk()
    except TclError as exc:
        raise RuntimeError("No pude abrir Studio. Necesitas una sesión gráfica y python3-tk.") from exc
    dnd = None
    try:
        from tkinterdnd2 import DND_FILES, COPY, TkinterDnD
        TkinterDnD._require(app)
        dnd = (DND_FILES, COPY)
    except (ImportError, RuntimeError, TclError):
        pass
    app.title("Cerebro Studio")
    logo = PhotoImage(master=app, file=Path(__file__).with_name("web") / "cerebro-logo.png")
    app.iconphoto(True, logo)
    app.geometry("1120x720")
    app.minsize(720, 490)
    app.configure(bg=FONDO)
    estilo = ttk.Style(app)
    estilo.theme_use("clam")
    estilo.configure(".", background=FONDO, foreground=TEXTO, fieldbackground=PANEL,
                     bordercolor=BORDE, lightcolor=BORDE, darkcolor=BORDE, focuscolor=ACTIVO,
                     troughcolor=EDITOR, selectbackground=SELECCION, selectforeground=TEXTO)
    estilo.configure("TButton", background=PANEL, padding=(8, 5), borderwidth=1, relief="flat")
    estilo.map("TButton", background=[("active", SELECCION)])
    estilo.configure("TNotebook", background=FONDO, borderwidth=0, padding=0, tabmargins=(0, 0, 0, 3))
    estilo.configure("TNotebook.Tab", background=PANEL, borderwidth=1, padding=(12, 6), foreground=SECUNDARIO,
                     lightcolor=PANEL, darkcolor=PANEL, bordercolor=BORDE)
    estilo.map("TNotebook.Tab", background=[("selected", SELECCION), ("active", PANEL)],
               bordercolor=[("selected", ACTIVO), ("!selected", BORDE)],
               lightcolor=[("selected", SELECCION), ("!selected", PANEL)],
               darkcolor=[("selected", SELECCION), ("!selected", PANEL)],
               foreground=[("selected", ACENTO)])
    estilo.configure("Titulo.TLabel", font=("TkDefaultFont", 17, "bold"), foreground=TEXTO)
    estilo.configure("TEntry", fieldbackground=EDITOR, insertcolor=TEXTO, padding=4)
    estilo.map("TEntry", bordercolor=[("focus", ACTIVO)])
    estilo.configure("TPanedwindow", background=BORDE)
    estilo.configure("Sash", sashthickness=5, gripcount=0, background=BORDE)
    for orientacion in ("Vertical", "Horizontal"):
        barra = orientacion + ".TScrollbar"
        estilo.configure(barra, background=BORDE, troughcolor=EDITOR, bordercolor=EDITOR,
                         darkcolor=BORDE, lightcolor=BORDE, arrowcolor=SECUNDARIO, arrowsize=9,
                         borderwidth=1, gripcount=0)
        estilo.map(barra, background=[("active", SELECCION)], arrowcolor=[("active", ACENTO)])
    estilo.configure("Principal.TButton", background=ACTIVO, foreground=FONDO)
    estilo.map("Principal.TButton", background=[("active", ACENTO)])
    estilo.configure("Eliminar.TButton", foreground="#ffaab6")
    estilo.configure("Seccion.TLabel", foreground=ACENTO, font=("TkDefaultFont", 10, "bold"))
    estilo.configure("Estado.TLabel", background=PANEL, foreground=SECUNDARIO)
    estilo.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=TEXTO,
                     arrowcolor=ACENTO, bordercolor=BORDE, padding=4)
    estilo.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", TEXTO)],
               bordercolor=[("focus", ACTIVO)])
    app.option_add("*TCombobox*Listbox.background", PANEL)
    app.option_add("*TCombobox*Listbox.foreground", TEXTO)
    app.option_add("*TCombobox*Listbox.selectBackground", SELECCION)

    estado = StringVar(value="Conectando con Cerebro…")
    ruta = StringVar()
    filtro_archivos = StringVar()
    inventario = []
    entradas_archivos = []
    subcarpeta = ""
    imagen_activa = None
    solicitud_archivo = 0
    documento_activo = None
    marca_documento = None
    carpetas_disponibles = {}
    modo_tactil = BooleanVar(value=False)
    modo_edicion_tactil = False
    entrada = StringVar()
    pendientes = SimpleQueue()
    tareas_en_curso = set()
    identificador = token_hex(12)
    presencia = Lock()
    cerrojo_sesion = Lock()
    visible = True
    generacion = 0
    revision_chat = 0
    chat_activo = None
    revision_visible = None
    chats_guardados = []
    proyecto_activo = None
    proyecto_titulo = StringVar(value="Espacio de Studio")
    archivo_proyecto = None
    original_proyecto = None
    propuestas = []
    cambios_aplicados = []
    resaltado_pendiente = None
    propuesta_elegida = StringVar()

    def pedir(operacion, datos=None, tiempo=25):
        return pedir_con_reconexion(sesion, cerrojo_sesion, operacion, datos, tiempo)

    def proyecto(accion, *, esperada=None, **datos):
        return pedir("proyecto", {"cliente": identificador, "accion": accion,
                                 "carpeta_esperada": esperada, **datos})

    def publicar(trabajo, terminado=lambda _: None):
        def hacer():
            try:
                pendientes.put((terminado, trabajo(), None))
            except (OSError, ValueError, RuntimeError) as exc:
                pendientes.put((None, None, str(exc)))
        Thread(target=hacer, daemon=True).start()

    def boton(padre, nombre, accion, estilo="TButton", lado=LEFT):
        widget = ttk.Button(padre, text=nombre, command=accion, style=estilo)
        widget.pack(side=lado, padx=(0, 5), pady=3)
        return widget

    def campo_texto(padre, *, codigo=False, altura=10):
        marco = ttk.Frame(padre)
        marco.pack(fill=BOTH, expand=True)
        campo = Text(marco, bg=EDITOR if codigo else PANEL, fg=TEXTO, insertbackground=ACENTO, relief="flat",
                     padx=10, pady=9, wrap="none" if codigo else "word",
                     width=18, height=altura, highlightthickness=1, highlightbackground=BORDE,
                     highlightcolor=ACENTO, selectbackground=SELECCION,
                     font="TkFixedFont" if codigo else "TkDefaultFont")
        desplazamiento = ttk.Scrollbar(marco, command=campo.yview)
        desplazamiento.pack(side=RIGHT, fill=Y)
        campo.configure(yscrollcommand=desplazamiento.set)
        if codigo:
            horizontal = ttk.Scrollbar(marco, orient="horizontal", command=campo.xview)
            horizontal.pack(side="bottom", fill=X)
            campo.configure(xscrollcommand=horizontal.set)
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

    def ajustar_tactil(activo):
        nonlocal modo_edicion_tactil
        modo_edicion_tactil = activo
        modo_tactil.set(activo)
        estilo.configure("TButton", padding=(12, 9) if activo else (8, 5))
        estilo.configure("TNotebook.Tab", padding=(16, 11) if activo else (12, 6))
        estilo.configure("TEntry", padding=7 if activo else 4)
        for barra in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            estilo.configure(barra, arrowsize=17 if activo else 9)
        lista.configure(font=("TkDefaultFont", 12 if activo else 10))

    def cambiar_tactil():
        deseado = modo_tactil.get()
        ajustar_tactil(modo_edicion_tactil)
        publicar(lambda: proyecto("tactil", valor=deseado), lambda dato: ajustar_tactil(dato["tactil"]))

    marca = logo.subsample(4, 4)
    ttk.Label(cabecera, image=marca).pack(side=LEFT, padx=(0, 8))
    ttk.Label(cabecera, text="Cerebro Studio", style="Titulo.TLabel").pack(side=LEFT, padx=(0, 15))
    boton(cabecera, "Chat web", lambda: abrir(sesion, "chat"), lado=RIGHT)
    def abrir_acompanante():
        if lanzar_acompanante():
            app.iconify()
        else:
            estado.set("El entorno gráfico no pudo abrir el acompañante.")

    boton(cabecera, "Acompañante", abrir_acompanante, lado=RIGHT)
    boton(cabecera, "Terminal", lanzar_terminal, lado=RIGHT)
    ttk.Checkbutton(cabecera, text="Modo táctil visual", variable=modo_tactil,
                    command=cambiar_tactil).pack(side=RIGHT, padx=5)
    opciones = ttk.Menubutton(cabecera, text="Opciones")
    menu_opciones = Menu(opciones, tearoff=False)
    menu_opciones.add_command(label="Modo gestual por cámara", command=lambda: estado.set(
        "Activa la cámara desde la ventana de gestos." if lanzar_tactil()
        else "No se pudo abrir el control gestual en este escritorio."))
    opciones.configure(menu=menu_opciones)
    opciones.pack(side=RIGHT, padx=5)
    paginas = ttk.Notebook(app)
    paginas.pack(fill=BOTH, expand=True, padx=14, pady=4)
    cuerpo = ttk.Panedwindow(paginas, orient="horizontal")
    paginas.add(cuerpo, text="Proyecto")

    def actualizar_mapa():
        publicar(lambda: pedir("nodos"), mapa.actualizar)

    def analizar_universe():
        def responder(informe):
            resumen = "\n".join(
                [f"Evaluaciones: {informe['evaluaciones']}",
                 f"Correcciones pendientes: {informe['correcciones_pendientes']}",
                 f"Entrenamientos registrados: {informe['entrenamientos_registrados']}",
                 "Profesor local configurado." if informe.get("profesor_configurado")
                 else "Profesor local desactivado.", informe.get("resumen_competencias", ""), "",
                 *[f"{tarea['objetivo']}. {tarea['accion']}" for tarea in informe["propuestas"]]])
            resumen += "\nPrioridades: " + ", ".join(informe.get("prioridades_autonomas", []))
            if informe.get("estado_autonomo"):
                tarea = informe["estado_autonomo"]
                resumen += f"\nEntrenamiento: {tarea['estado']}. {tarea['detalle']}"
            if informe.get("puede_preparar_entrenamiento") and messagebox.askyesno(
                    "Análisis de aprendizaje", resumen + "\n\n¿Preparar un borrador de entrenamiento en el chat?", parent=app):
                enviar("Prepara entrenamiento autónomo")
            elif not informe.get("puede_preparar_entrenamiento"):
                messagebox.showinfo("Análisis de aprendizaje", resumen, parent=app)

        publicar(lambda: pedir("analizar-aprendizaje"), responder)

    def evaluar_universe():
        def mostrar_nota(nota):
            estado.set("Evaluación terminada.")
            messagebox.showinfo("Evaluación del alumno",
                                f"Aciertos: {nota['aciertos']} de {nota['evaluadas']}.\n{nota['aviso']}",
                                parent=app)

        estado.set("Evaluando el modelo con fichas locales…")
        publicar(lambda: pedir("evaluar-alumno"), mostrar_nota)

    mapa = MapaStudio(paginas, actualizar_mapa, analizar_universe, evaluar_universe)
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

    ttk.Label(archivos, text="EXPLORADOR", style="Seccion.TLabel").pack(anchor="w", pady=(0, 7))
    ttk.Label(archivos, textvariable=proyecto_titulo, wraplength=190).pack(anchor="w", pady=(0, 6))
    favoritas = ttk.Combobox(archivos, state="readonly")
    favoritas.pack(fill=X, pady=(0, 6))
    ttk.Label(archivos, text="Filtrar archivos · Ctrl+P").pack(anchor="w", pady=(0, 4))
    buscador = ttk.Entry(archivos, textvariable=filtro_archivos)
    buscador.pack(fill=X, pady=(0, 4))
    tipo_archivos = ttk.Combobox(archivos, state="readonly",
                                 values=("Todo", "Carpetas", "Código", "Documentos", "Imágenes"))
    tipo_archivos.current(0)
    tipo_archivos.pack(fill=X, pady=(0, 4))
    ubicacion = StringVar(value="/")
    ttk.Label(archivos, textvariable=ubicacion, wraplength=175).pack(anchor="w")
    lista = Listbox(archivos, width=19, bg=PANEL, fg=TEXTO, selectbackground=SELECCION, selectforeground=ACENTO,
                    relief="flat", highlightthickness=0, exportselection=False)
    desplazamiento_archivos = ttk.Scrollbar(archivos, command=lista.yview)
    lista.configure(yscrollcommand=desplazamiento_archivos.set)
    desplazamiento_archivos.pack(side="right", fill=Y)
    lista.pack(fill=BOTH, expand=True)
    barra_archivos = ttk.Frame(archivos)
    barra_archivos.pack(fill=X)

    vistas_editor = ttk.Notebook(codigo)
    vistas_editor.pack(fill=BOTH, expand=True)
    pagina_editor = ttk.Frame(vistas_editor, padding=6)
    pagina_validaciones = ttk.Frame(vistas_editor, padding=6)
    vistas_editor.add(pagina_editor, text="Editor")
    vistas_editor.add(pagina_validaciones, text="Validaciones")
    ttk.Entry(pagina_editor, textvariable=ruta).pack(fill=X, pady=(0, 5))
    editor = campo_texto(pagina_editor, codigo=True)
    colores_sintaxis = {"clave": "#78C4FF", "cadena": "#ADD79A", "comentario": "#8995A8", "numero": "#F3C88C"}
    for etiqueta, color in colores_sintaxis.items():
        editor.tag_configure(etiqueta, foreground=color)

    def colorear():
        nonlocal resaltado_pendiente
        resaltado_pendiente = None
        for etiqueta in colores_sintaxis:
            editor.tag_remove(etiqueta, "1.0", END)
        if not ruta.get().lower().endswith(".py"):
            return
        fuente = editor.get("1.0", "end-1c")
        tipos = {tokenize.STRING: "cadena", tokenize.NUMBER: "numero", tokenize.COMMENT: "comentario"}
        with suppress(tokenize.TokenError, IndentationError, SyntaxError):
            for token in tokenize.generate_tokens(StringIO(fuente).readline):
                etiqueta = ("clave" if token.type == tokenize.NAME and keyword.iskeyword(token.string)
                            else tipos.get(token.type))
                if etiqueta:
                    editor.tag_add(etiqueta, f"{token.start[0]}.{token.start[1]}", f"{token.end[0]}.{token.end[1]}")

    def programar_resaltado(_evento=None):
        nonlocal resaltado_pendiente
        if resaltado_pendiente is not None:
            app.after_cancel(resaltado_pendiente)
        resaltado_pendiente = app.after(130, colorear)

    editor.bind("<KeyRelease>", programar_resaltado)
    ruta.trace_add("write", lambda *_: programar_resaltado())
    barra_editor = ttk.Frame(pagina_editor)
    barra_editor.pack(fill=X)
    validaciones = campo_texto(pagina_validaciones)
    validaciones.configure(state="disabled")
    pagina_cambios = ttk.Frame(vistas_editor, padding=6)
    vistas_editor.add(pagina_cambios, text="Cambios")
    elegir_cambio = ttk.Combobox(pagina_cambios, textvariable=propuesta_elegida, state="readonly")
    elegir_cambio.pack(fill=X, pady=(0, 6))
    diff = campo_texto(pagina_cambios, codigo=True)
    diff.configure(state="disabled")
    diff.tag_configure("anadido", foreground="#ADD79A")
    diff.tag_configure("quitado", foreground="#FFADB8")
    diff.tag_configure("bloque", foreground=ACENTO)
    acciones_cambio = ttk.Frame(pagina_cambios)
    acciones_cambio.pack(fill=X)
    pagina_visor = ttk.Frame(vistas_editor, padding=6)
    pagina_resultados = ttk.Frame(vistas_editor, padding=6)
    vistas_editor.add(pagina_visor, text="Visor")
    vistas_editor.add(pagina_resultados, text="Resultados")
    imagen = ttk.Label(pagina_visor)
    acciones_visor = ttk.Frame(pagina_visor)
    acciones_visor.pack(fill=X)
    visor = campo_texto(pagina_visor, codigo=True)
    visor.tag_configure("titulo", foreground=ACENTO, font=("TkDefaultFont", 16, "bold"))
    visor.tag_configure("codigo", foreground=TEXTO, font="TkFixedFont")
    grafica = Canvas(pagina_resultados, bg=EDITOR, height=90, highlightthickness=0)
    detalles = campo_texto(pagina_resultados)
    acciones_proyecto = ttk.Frame(codigo)
    acciones_proyecto.pack(fill=X)

    ttk.Label(chat, text="CONVERSACIÓN", style="Seccion.TLabel").pack(anchor="w", pady=(0, 6))
    selector = ttk.Combobox(chat, state="readonly", width=16)
    selector.pack(fill=X, pady=(0, 3))
    barra_conversaciones = ttk.Frame(chat)
    barra_conversaciones.pack(fill=X, pady=(0, 4))
    salida = campo_texto(chat)
    salida.configure(state="disabled", spacing2=3)
    salida.tag_configure("Tú", foreground=TEXTO, font=("TkDefaultFont", 10, "bold"), spacing1=10)
    salida.tag_configure("Cerebro", foreground=ACENTO, font=("TkDefaultFont", 10, "bold"), spacing1=10)
    salida.tag_configure("mensaje", spacing3=9, lmargin1=4, lmargin2=4)

    def mostrar_mensaje(autor, texto):
        salida.configure(state="normal")
        salida.insert("end-1c", autor + "\n", autor)
        salida.insert("end-1c", texto.strip() + "\n", "mensaje")
        salida.configure(state="disabled")
        salida.see(END)

    consulta = ttk.Entry(chat, textvariable=entrada)
    consulta.pack(fill=X, pady=(6, 1))
    barra_chat = ttk.Frame(chat)
    barra_chat.pack(fill=X)
    ttk.Label(app, textvariable=estado, style="Estado.TLabel", padding=(16, 7), anchor="w").pack(fill=X)

    def filtrar_archivos(*_args):
        filtro = filtro_archivos.get().strip().casefold()
        tipo = tipo_archivos.get()
        previo = lista.get(lista.curselection()[0]) if lista.curselection() else None
        visibles = ["../"] if subcarpeta and not filtro else []
        for item in entradas_archivos:
            nombre = item["ruta"]
            es_carpeta = item["tipo"] == "carpeta"
            extension = Path(nombre).suffix.lower()
            coincide = (tipo == "Todo" or
                        (tipo == "Carpetas" and es_carpeta) or
                        (tipo == "Código" and not es_carpeta and extension in {
                            ".py", ".js", ".ts", ".css", ".html", ".rs", ".c", ".cpp", ".java", ".sh", ".sql"}) or
                        (tipo == "Documentos" and extension in {".txt", ".md", ".pdf", ".csv", ".tsv", ".docx"}) or
                        (tipo == "Imágenes" and extension in {".png", ".gif", ".jpg", ".jpeg", ".webp"}))
            padre = nombre.rpartition("/")[0]
            if coincide and (filtro in nombre.casefold() if filtro else padre == subcarpeta):
                visibles.append(nombre + ("/" if es_carpeta else ""))
        if tuple(visibles) != lista.get(0, END):
            lista.delete(0, END)
            for nombre in visibles:
                lista.insert(END, nombre)
            if previo in visibles:
                lista.selection_set(visibles.index(previo))
        ubicacion.set("/" + subcarpeta)

    filtro_archivos.trace_add("write", filtrar_archivos)
    tipo_archivos.bind("<<ComboboxSelected>>", filtrar_archivos)

    def inventariar(datos):
        inventario[:] = datos["archivos"]
        entradas_archivos[:] = datos.get("entradas", [{"ruta": n, "tipo": "archivo"} for n in inventario])
        filtrar_archivos()

    def actualizar_archivos():
        esperado = proyecto_activo

        def cargar(datos):
            if esperado == proyecto_activo:
                inventariar(datos)

        publicar(lambda: proyecto("listar", esperada=esperado) if esperado else pedir("archivos"), cargar)

    def es_seguro_salir(mensaje):
        return not editor.edit_modified() or messagebox.askyesno(
            "Cambios sin guardar", mensaje, parent=app)

    def visualizar(datos):
        nonlocal imagen_activa
        imagen.pack_forget()
        imagen.configure(image="")
        imagen_activa = None
        for hijo in acciones_visor.winfo_children():
            hijo.destroy()
        extension = datos.get("extension", "")
        nombre = datos["archivo"]
        contenido = datos.get("texto", "")
        mensaje = datos.get("aviso") or f"{nombre} · {datos['bytes']} bytes"
        if datos.get("base64") and datos.get("visor") in {"imagen", "pdf"}:
            try:
                bruto = b64decode(datos["base64"], validate=True)
                try:
                    from PIL import Image, ImageTk
                except ImportError:
                    Image = None
                if Image is not None:
                    try:
                        fuente = Image.open(BytesIO(bruto))
                    except Image.DecompressionBombError as error:
                        raise ValueError("La imagen supera el tamaño de vista previa.") from error
                    with fuente:
                        if fuente.width * fuente.height > 12_000_000:
                            raise ValueError("La imagen supera el tamaño de vista previa.")
                        fuente.thumbnail((650, 470))
                        imagen_activa = ImageTk.PhotoImage(fuente, master=app)
                else:
                    if bruto.startswith(b"\x89PNG\r\n\x1a\n") and len(bruto) >= 24:
                        ancho = int.from_bytes(bruto[16:20], "big")
                        alto = int.from_bytes(bruto[20:24], "big")
                    elif bruto.startswith((b"GIF87a", b"GIF89a")) and len(bruto) >= 10:
                        ancho = int.from_bytes(bruto[6:8], "little")
                        alto = int.from_bytes(bruto[8:10], "little")
                    else:
                        raise ValueError("Instala Pillow para previsualizar este formato.")
                    if not 0 < ancho * alto <= 12_000_000:
                        raise ValueError("La imagen supera el tamaño de vista previa.")
                    imagen_activa = PhotoImage(master=app, data=datos["base64"])
                    reduccion = max(1, (max(ancho, alto) + 649) // 650)
                    if reduccion > 1:
                        imagen_activa = imagen_activa.subsample(reduccion, reduccion)
                imagen.configure(image=imagen_activa)
                imagen.pack(side="top", before=visor.master, pady=5)
            except (OSError, ValueError, TclError) as error:
                mensaje += "\n" + str(error)
        mostrar(visor, mensaje)
        if datos.get("app_externa") and proyecto_activo:
            esperado = proyecto_activo

            def externa():
                if messagebox.askyesno("Abrir en otra aplicación", f"¿Abrir «{nombre}» en la aplicación predeterminada?", parent=app):
                    publicar(lambda: proyecto("abrir_externo", nombre=nombre, confirmar=True, esperada=esperado),
                             lambda dato: estado.set(dato["salida"]))

            boton(acciones_visor, "Abrir en aplicación local", externa)
        if (datos.get("suelto") or extension in {".html", ".md", ".csv", ".tsv", ".pdf", ".docx", ".odt"}) and "texto" in datos:
            visor.configure(state="normal")
            visor.insert(END, "\n\n")
            if extension == ".html":
                visor.insert(END, "Vista estática · sin scripts, estilos ni recursos externos\n")
                for texto, etiqueta in html_estatico(contenido):
                    visor.insert(END, texto, etiqueta)
            elif extension in {".csv", ".tsv"}:
                try:
                    for fila in tabla(contenido, extension):
                        visor.insert(END, " │ ".join(fila) + "\n")
                except ErrorCSV as error:
                    visor.insert(END, "Tabla inválida: " + str(error))
            elif extension == ".md":
                for linea in contenido.splitlines():
                    visor.insert(END, linea.lstrip("# ") + "\n" if linea.startswith("# ") or linea.startswith("## ")
                                 else linea + "\n", "titulo" if linea.startswith("#") else "")
            else:
                visor.insert(END, contenido)
            visor.configure(state="disabled")
        vistas_editor.select(pagina_visor)

    def cargar_nombre(nombre):
        nonlocal solicitud_archivo
        solicitud_archivo += 1
        solicitud = solicitud_archivo
        copia_editor = editor.get("1.0", "end-1c")
        abierto_en = proyecto_activo

        def copiar(datos):
            nonlocal archivo_proyecto, original_proyecto
            if proyecto_activo != abierto_en or solicitud != solicitud_archivo:
                return
            if editor.edit_modified() and editor.get("1.0", "end-1c") != copia_editor:
                estado.set("El editor cambió mientras se abría el archivo.")
                return
            activar_documento(abierto_en, datos) if abierto_en else desactivar_documento()
            if abierto_en and (datos.get("visor") != "texto" or datos.get("solo_lectura")):
                archivo_proyecto = original_proyecto = None
                ruta.set(nombre)
                mostrar(editor, "")
                editor.edit_modified(False)
                visualizar(datos)
            else:
                archivo_proyecto, original_proyecto = nombre, datos["texto"]
                ruta.set(nombre)
                mostrar(editor, datos["texto"])
                editor.edit_modified(False)
                programar_resaltado()
                if Path(nombre).suffix.lower() in {".html", ".md", ".csv", ".tsv"} and abierto_en:
                    visualizar(datos)
                else:
                    vistas_editor.select(pagina_editor)
            if abierto_en:
                publicar(lambda: proyecto("recordar", nombre=nombre, esperada=abierto_en))

        publicar(lambda: proyecto("inspeccionar", nombre=nombre, esperada=abierto_en)
                 if abierto_en else pedir("archivo?nombre=" + quote(nombre)), copiar)

    def cargar_archivo(_evento=None):
        nonlocal subcarpeta
        seleccionado = lista.curselection()
        if not seleccionado:
            return
        nombre = lista.get(seleccionado[0])
        if nombre.endswith("/"):
            subcarpeta = subcarpeta.rpartition("/")[0] if nombre == "../" else nombre[:-1]
            filtro_archivos.set("")
            filtrar_archivos()
            return
        if es_seguro_salir("¿Abrir otro archivo?"):
            cargar_nombre(nombre)

    def actualizar_preferencias(datos):
        carpetas_disponibles.clear()
        for item in datos["carpetas"]:
            carpetas_disponibles[item["nombre"]] = item["ruta"]
        for ruta_favorita in datos["favoritas"]:
            carpetas_disponibles["★ " + ruta_favorita] = ruta_favorita
        favoritas.configure(values=list(carpetas_disponibles))
        ajustar_tactil(datos["tactil"])

    def elegir_personal(_evento=None):
        destino = carpetas_disponibles.get(favoritas.get())
        if destino:
            abrir_proyecto(destino)

    def marcar_favorita():
        esperado = proyecto_activo
        if esperado:
            publicar(lambda: proyecto("favorita", esperada=esperado),
                     lambda _: publicar(lambda: proyecto("escritorio"), actualizar_preferencias))
        else:
            estado.set("Abre una carpeta antes de añadirla a favoritas.")

    def mostrar_gestor():
        if proyecto_activo:
            esperado, nombre = proyecto_activo, subcarpeta
            publicar(lambda: proyecto("gestor", nombre=nombre, esperada=esperado, confirmar=True),
                     lambda dato: estado.set(dato["salida"]))
        else:
            estado.set("Abre primero la carpeta que quieres mostrar en Thunar.")

    def activar_documento(esperado, datos):
        nonlocal documento_activo, marca_documento
        tipo = datos.get("visor")
        documento_activo = (esperado, datos["archivo"], tipo)
        marca_documento = datos.get("marca")
        texto = tipo in {"texto", "pdf"} and bool(datos.get("texto"))
        for indice, disponible in enumerate((texto or tipo == "imagen", texto,
                                               datos.get("extension") in {".py", ".json", ".html", ".csv", ".tsv"},
                                               texto)):
            herramientas_archivo.entryconfigure(indice, state="normal" if disponible else "disabled")

    def desactivar_documento():
        nonlocal documento_activo, marca_documento
        documento_activo = marca_documento = None
        for indice in range(4):
            herramientas_archivo.entryconfigure(indice, state="disabled")

    def actualizar_suelto():
        if documento_activo is not None and not documento_activo[0]:
            publicar(lambda: proyecto("suelto"), mostrar_suelto)
        else:
            estado.set("Selecciona de nuevo el archivo en el explorador para actualizarlo.")

    def mostrar_suelto(datos):
        activar_documento("", datos)
        visualizar(datos)

    def abrir_o_soltar(valor):
        try:
            origen = archivo_soltado(valor)
        except ValueError as error:
            estado.set(str(error))
            return
        if proyecto_activo and origen.is_relative_to(proyecto_activo):
            if es_seguro_salir("¿Abrir otro archivo?"):
                cargar_nombre(origen.relative_to(proyecto_activo).as_posix())
            return
        if messagebox.askyesno("Autorizar archivo", f"¿Leer «{origen.name}» sin copiarlo al proyecto?", parent=app):
            publicar(lambda: proyecto("abrir_suelto", ruta=str(origen), confirmar=True), mostrar_suelto)

    def elegir_archivo_suelto():
        ruta_local = filedialog.askopenfilename(title="Abrir archivo en el visor", parent=app)
        if ruta_local:
            abrir_o_soltar(ruta_local)

    def soltar(evento):
        archivos_sol = app.tk.splitlist(evento.data)
        if len(archivos_sol) != 1:
            estado.set("Arrastra un solo archivo para abrirlo.")
        else:
            abrir_o_soltar(archivos_sol[0])
        return dnd[1]

    def iniciar_arrastre(_evento):
        seleccion = lista.curselection()
        if not seleccion or not proyecto_activo:
            return ("refuse_drop", dnd[0], "")
        nombre = lista.get(seleccion[0])
        if nombre.endswith("/"):
            return ("refuse_drop", dnd[0], "")
        return (dnd[1], dnd[0], (str(Path(proyecto_activo) / nombre),))

    def herramienta_archivo(herramienta):
        if documento_activo is None:
            estado.set("Abre un archivo primero.")
            return
        esperado, nombre, visor_tipo = documento_activo
        if visor_tipo not in {"texto", "pdf"} and not (visor_tipo == "imagen" and herramienta == "analizar"):
            estado.set("El análisis y la evaluación requieren un documento con texto.")
            return

        def resultado(dato):
            if documento_activo != (esperado, nombre, visor_tipo):
                return
            grafica.pack_forget()
            vistas_editor.select(pagina_resultados)
            if "ejercicio" not in dato:
                mostrar(detalles, nombre + "\n\n" + dato["salida"])
                return
            pregunta = dato["ejercicio"]["pregunta"]
            mostrar(detalles, pregunta)
            respuesta = simpledialog.askstring("Evaluar alumno", pregunta, parent=app)
            if respuesta:
                guardar_nota = messagebox.askyesno("Guardar progreso", "¿Guardar el resultado de este ejercicio?", parent=app)
                publicar(lambda: proyecto("responder_ejercicio", respuesta=respuesta, guardar=guardar_nota),
                         lambda nota: mostrar(detalles, pregunta + "\n\n" + nota["salida"]))

        accion = "herramienta" if esperado else "herramienta_suelto"
        publicar(lambda: proyecto(accion, nombre=nombre, herramienta=herramienta, esperada=esperado), resultado)

    def abrir_pagina_web():
        valor = simpledialog.askstring("Abrir página web", "Dirección https://", parent=app)
        if not valor:
            return
        try:
            enlace = urlsplit(valor.strip())
        except ValueError:
            enlace = None
        if not enlace or enlace.scheme not in {"http", "https"} or not enlace.hostname or enlace.username or enlace.password:
            estado.set("Introduce una dirección HTTP o HTTPS válida.")
            return
        if abrir_web(valor.strip()):
            estado.set("La dirección se solicitó al navegador predeterminado.")
        else:
            estado.set("No pude abrir el navegador predeterminado.")

    def gestionar_archivo(accion, *, nombre=None, contenido=""):
        if not proyecto_activo:
            estado.set("Abre primero una carpeta de proyecto.")
            return
        seleccion = lista.curselection()
        origen = lista.get(seleccion[0]).rstrip("/") if seleccion else ""
        if accion in {"crear", "carpeta"}:
            nombre = nombre or simpledialog.askstring(
                "Nuevo archivo" if accion == "crear" else "Nueva carpeta", "Ruta relativa al proyecto",
                initialvalue=subcarpeta + "/" if subcarpeta else "", parent=app)
            if not nombre:
                return
        elif not origen or origen == "..":
            estado.set("Selecciona un archivo o carpeta.")
            return
        else:
            nombre = origen
        destino = (simpledialog.askstring("Destino", "Ruta nueva relativa al proyecto",
                                          initialvalue=nombre, parent=app)
                   if accion in {"mover", "copiar"} else None)
        if accion in {"mover", "copiar"} and (not destino or destino == nombre):
            return
        afecta = bool(archivo_proyecto and
                      (archivo_proyecto == nombre or archivo_proyecto.startswith(nombre + "/")))
        if afecta and editor.edit_modified() and accion in {"mover", "papelera"}:
            estado.set("Guarda primero los cambios del editor.")
            return
        if accion == "papelera" and not messagebox.askyesno(
                "Enviar a la papelera", f"¿Mover «{nombre}» a la papelera del proyecto?", parent=app):
            return
        esperado = proyecto_activo

        def terminado(respuesta):
            nonlocal archivo_proyecto, original_proyecto
            if esperado != proyecto_activo:
                return
            if afecta and accion in {"mover", "papelera"}:
                archivo_proyecto = original_proyecto = None
                ruta.set("")
                mostrar(editor, "")
                editor.edit_modified(False)
            estado.set("Papelera: " + respuesta["papelera"] if "papelera" in respuesta
                       else "Proyecto actualizado: " + respuesta["archivo"])
            actualizar_archivos()
            if accion == "crear" and not editor.edit_modified():
                cargar_nombre(respuesta["archivo"])

        publicar(lambda: proyecto(accion, nombre=nombre, destino=destino, texto=contenido,
                                   confirmar=True, esperada=esperado), terminado)

    def guardar():
        nombre = ruta.get().strip()
        contenido = editor.get("1.0", "end-1c")
        if not nombre:
            estado.set("Escribe una ruta para el archivo, como src/ejemplo.py.")
            return

        abierto_en = proyecto_activo
        if abierto_en:
            if nombre != archivo_proyecto or original_proyecto is None:
                estado.set("Abre primero el archivo desde el explorador.")
                return
            if not messagebox.askyesno("Guardar en el proyecto", f"¿Guardar en «{nombre}»?", parent=app):
                return
        original = original_proyecto

        def guardado(_):
            nonlocal original_proyecto
            if proyecto_activo != abierto_en:
                return
            if abierto_en:
                original_proyecto = contenido
            if editor.get("1.0", "end-1c") == contenido:
                editor.edit_modified(False)
            estado.set("Archivo guardado: " + nombre)
            actualizar_archivos()
            if abierto_en:
                def ajustar_marca(datos):
                    nonlocal marca_documento
                    if documento_activo and documento_activo[:2] == (abierto_en, nombre):
                        marca_documento = datos.get("marca")
                publicar(lambda: proyecto("estado_archivo", nombre=nombre, esperada=abierto_en), ajustar_marca)
        publicar(lambda: proyecto("guardar", nombre=nombre, texto=contenido, original=original, confirmar=True, esperada=abierto_en)
                 if abierto_en else pedir("archivo", {"nombre": nombre, "texto": contenido}), guardado)

    def revisar():
        nombre = ruta.get().strip()
        if not nombre or editor.edit_modified():
            estado.set("Guarda el archivo antes de validar su sintaxis.")
            return
        if proyecto_activo:
            esperado = proyecto_activo
            vistas_editor.select(pagina_validaciones)
            publicar(lambda: proyecto("validar", nombre=nombre, esperada=esperado),
                     lambda dato: mostrar(validaciones, dato["salida"] + "\n", anexar=True))
            return
        publicar(lambda: pedir("tarea", {"accion": "sintaxis", "nombre": nombre}),
                  lambda dato: tareas_en_curso.add(dato["id"]))
        vistas_editor.select(pagina_validaciones)
        mostrar(validaciones, "Validando «" + nombre + "»…\n", anexar=True)
        estado.set("Validación solicitada.")

    def abrir_proyecto(carpeta=None, recuperar=None):
        if not es_seguro_salir("¿Cambiar de proyecto?"):
            return
        carpeta = carpeta or filedialog.askdirectory(title="Elegir carpeta de proyecto", mustexist=True, parent=app)
        if not carpeta:
            return
        if not messagebox.askyesno("Autorizar proyecto", f"¿Permitir a Cerebro inspeccionar «{carpeta}»?", parent=app):
            return

        def abierto(datos):
            nonlocal proyecto_activo, archivo_proyecto, original_proyecto, subcarpeta
            desactivar_documento()
            proyecto_activo = datos["carpeta"]
            proyecto_titulo.set(Path(proyecto_activo).name)
            subcarpeta = ""
            filtro_archivos.set("")
            inventariar(datos)
            ruta.set("")
            archivo_proyecto = original_proyecto = None
            mostrar(editor, "")
            editor.edit_modified(False)
            cargar_propuestas([])
            cambios_aplicados.clear()
            estado.set("Proyecto abierto" + (" · inventario limitado" if datos["limitado"] else ""))
            esperado = proyecto_activo
            if recuperar and any(item["ruta"] == recuperar for item in entradas_archivos):
                cargar_nombre(recuperar)
            else:
                publicar(lambda: proyecto("recordar", esperada=esperado))

        publicar(lambda: proyecto("abrir", carpeta=carpeta, confirmar=True), abierto)

    def mostrar_diff(_evento=None):
        indice = elegir_cambio.current()
        contenido = propuestas[indice]["diff"] if indice >= 0 else ""
        mostrar(diff, contenido)
        for numero, linea in enumerate(contenido.splitlines(), 1):
            etiqueta = ({"+": "anadido", "-": "quitado", "@": "bloque"}).get(linea[:1])
            if etiqueta:
                diff.tag_add(etiqueta, f"{numero}.0", f"{numero}.end")

    def cargar_propuestas(candidatas):
        propuestas[:] = candidatas
        elegir_cambio.configure(values=[item["archivo"] for item in propuestas])
        if propuestas:
            elegir_cambio.current(0)
        else:
            propuesta_elegida.set("")
        mostrar_diff()

    def analizar_proyecto():
        if not proyecto_activo:
            estado.set("Abre primero una carpeta de proyecto.")
            return
        base = proyecto_activo

        def analizado(datos):
            if base != proyecto_activo:
                return
            lineas = [f"Revisé {datos['revisados']} archivos Python de {datos['archivos']} archivos visibles.",
                      *datos["hallazgos"], f"Propuestas verificadas por sintaxis: {len(datos['propuestas'])}."]
            if datos["limitado"]:
                lineas.append("El inventario o la revisión alcanzó el límite.")
            if datos["propuestas"]:
                lineas.append("Revisa el diff en Cambios y elige qué aplicar. Después puedes ejecutar las pruebas.")
            mostrar_mensaje("Cerebro", "\n".join(lineas))
            cargar_propuestas(datos["propuestas"])
            vistas_editor.select(pagina_cambios)
            estado.set("Inspección terminada.")

        publicar(lambda: proyecto("analizar", esperada=base), analizado)

    def aplicar_cambio():
        indice = elegir_cambio.current()
        if indice < 0:
            return
        propuesta = propuestas[indice]
        esperado = proyecto_activo
        if editor.edit_modified():
            estado.set("Guarda o descarta las ediciones abiertas antes de aplicar el diff.")
            return
        if not messagebox.askyesno("Aplicar cambio", f"¿Aplicar el diff a «{propuesta['archivo']}»?", parent=app):
            return

        def aplicado(datos):
            nonlocal archivo_proyecto, original_proyecto
            if archivo_proyecto == datos["archivo"]:
                archivo_proyecto = original_proyecto = None
            cambios_aplicados.append(propuesta)
            cargar_propuestas([item for item in propuestas if item["id"] != propuesta["id"]])
            estado.set("Cambio aplicado. Vuelve a abrir el archivo para editarlo y ejecuta las pruebas.")

        publicar(lambda: proyecto("aplicar", id=propuesta["id"], confirmar=True, esperada=esperado), aplicado)

    def revisar_decision(accion):
        indice = elegir_cambio.current()
        item = (cambios_aplicados[-1] if cambios_aplicados else None) if accion == "revertir" else (
            propuestas[indice] if indice >= 0 else None)
        if not item:
            estado.set("No hay un cambio para esa acción.")
            return
        if accion == "revertir" and editor.edit_modified():
            estado.set("Guarda las ediciones abiertas antes de revertir.")
            return
        if not messagebox.askyesno("Decidir cambio", f"¿{accion.capitalize()} el cambio de «{item['archivo']}»?", parent=app):
            return
        esperado = proyecto_activo

        def terminado(resultado):
            if esperado != proyecto_activo:
                return
            if accion == "revertir":
                cambios_aplicados.remove(item)
                if archivo_proyecto == resultado["archivo"]:
                    cargar_nombre(archivo_proyecto)
            else:
                cargar_propuestas([dato for dato in propuestas if dato["id"] != item["id"]])
            estado.set("Cambio revertido." if accion == "revertir" else "Propuesta rechazada.")

        publicar(lambda: proyecto(accion, id=item["id"], confirmar=True, esperada=esperado), terminado)

    def probar_proyecto():
        if not proyecto_activo:
            estado.set("Abre primero una carpeta de proyecto.")
            return
        if not messagebox.askyesno("Ejecutar pruebas",
                                   f"¿Ejecutar unittest en «{proyecto_activo}»? Se usa una copia de solo lectura, sin acceso a tu carpeta personal ni a Internet.",
                                   parent=app):
            return
        esperado = proyecto_activo
        vistas_editor.select(pagina_validaciones)
        mostrar(validaciones, "Ejecutando unittest…\n", anexar=True)
        publicar(lambda: proyecto("pruebas", confirmar=True, esperada=esperado), lambda dato: tareas_en_curso.add(dato["id"]))

    def presentar_resultado(dato):
        from universe.especialidades import sintetizar

        if dato.get("vista") == "robot":
            simulado = dato["robot"]
            grafica.pack_forget()
            mostrar(detalles, "Robot simulado\n\n" +
                    f"Posición: {simulado['posicion']} · Ángulo: {simulado['angulo']}°\n" +
                    ("Detenido." if simulado["parado"] else "Armado en simulación."))
            vistas_editor.select(pagina_resultados)
            return
        resultados = dato.get("especialistas", [])
        if not resultados:
            resultados = [r for exp in dato.get("experiencias", []) for r in exp["resultados"]]
        if not resultados:
            return
        simulacion = next((r["simulacion"] for r in resultados if r.get("simulacion")), None)
        grafica.pack_forget()
        grafica.delete("all")
        if simulacion:
            grafica.pack(side="top", before=detalles.master, fill=X)
            documentado = max(1, simulacion["p90_horas"], simulacion["p50_horas"])
            for y, clave, color in ((28, "p50", ACENTO), (61, "p90", "#ADD79A")):
                valor = simulacion[clave + "_horas"]
                grafica.create_text(12, y, text=clave, fill=TEXTO, anchor="w")
                grafica.create_rectangle(52, y - 8, 52 + 175 * valor / documentado, y + 8, fill=color, width=0)
                grafica.create_text(237, y, text=f"{valor:.2f} h", fill=TEXTO, anchor="w")
        bloques = []
        for resultado in resultados:
            if plan := resultado.get("plan"):
                bloques.append("Plan de trabajo\n" + "\n".join(
                    f"{paso['id']} · {paso['titulo']} · {paso.get('estado', 'previsto')}" +
                    (f" · Depende de: {', '.join(paso['depende_de'])}" if paso.get("depende_de") else "")
                    for paso in plan))
            for evidencia in resultado.get("evidencia", []):
                if evidencia["tipo"] == "fuente":
                    bloques.append(f"{evidencia['titulo']}\n{evidencia['url']}\n{evidencia.get('extracto', '')}")
        mostrar(detalles, "\n\n".join([*bloques, "Actividad y evidencias", sintetizar(resultados)]))
        if dato.get("vista") == "universe":
            paginas.select(mapa)
        else:
            vistas_editor.select(pagina_resultados)

    def previsualizar_editor():
        nombre = ruta.get()
        if not nombre or Path(nombre).suffix.lower() not in {".html", ".md", ".csv", ".tsv"}:
            estado.set("El visor del editor admite HTML estático, Markdown y tablas CSV/TSV.")
            return
        texto = editor.get("1.0", "end-1c")
        visualizar({"archivo": nombre, "extension": Path(nombre).suffix.lower(),
                    "visor": "texto", "bytes": len(texto.encode("utf-8")), "texto": texto})

    def usar_seleccion():
        if not editor.tag_ranges("sel"):
            estado.set("Selecciona código en el editor.")
            return
        fragmento = editor.get("sel.first", "sel.last")[:4000]
        pregunta = simpledialog.askstring("Consultar selección", "¿Qué quieres preguntar sobre este fragmento?",
                                           initialvalue="Explícame este fragmento", parent=app)
        if pregunta:
            esperado, nombre = proyecto_activo, archivo_proyecto
            if not esperado or not nombre:
                estado.set("Abre el código de un proyecto autorizado primero.")
                return
            mostrar_mensaje("Tú", pregunta)
            publicar(lambda: proyecto("fragmento", nombre=nombre, texto=fragmento, pregunta=pregunta,
                                       esperada=esperado), lambda dato: mostrar_mensaje("Cerebro", dato["respuesta"]))

    def enviar(texto=None):
        texto = (entrada.get() if texto is None else texto).strip()
        if not texto or chat_activo is None:
            return
        destino_personal = intencion_carpeta(texto, carpetas_disponibles)
        if destino_personal:
            entrada.set("")
            abrir_proyecto(destino_personal)
            return
        accion_contextual = intencion_archivo(texto)
        if accion_contextual and documento_activo:
            entrada.set("")
            mostrar_mensaje("Tú", texto)
            herramienta_archivo(accion_contextual)
            return
        if re.fullmatch(r"(?:cerebro[, ]+)?crea (?:una )?p[aá]gina web[.!]?", texto, re.I):
            if not proyecto_activo:
                estado.set("Abre y autoriza el proyecto donde quieres crear la página.")
                return
            destino = simpledialog.askstring("Crear página estática", "Confirma el nombre del archivo nuevo",
                                              initialvalue="index.html", parent=app)
            if destino and Path(destino).suffix.lower() == ".html":
                entrada.set("")
                mostrar_mensaje("Tú", texto)
                gestionar_archivo("crear", nombre=destino, contenido=HTML_INICIAL)
            elif destino:
                estado.set("La página requiere la extensión .html.")
            return
        normalizada = texto.casefold().strip(" .!?¿¡")
        peticion_archivo = re.fullmatch(
            r"(?:(?:cerebro|profesor)[, ]+)?(resume|analiza|explica|busca errores en|valida|eval[uú]ame sobre) "
            r"(?:esto|este documento|este archivo|este programa|este pdf|esta imagen|la selecci[oó]n)", normalizada)
        if peticion_archivo:
            accion_archivo = {"resume": "resumir", "valida": "validar"}.get(peticion_archivo[1], "analizar")
            if peticion_archivo[1].startswith("eval"):
                accion_archivo = "evaluar"
            entrada.set("")
            mostrar_mensaje("Tú", texto)
            herramienta_archivo(accion_archivo)
            return
        entrada.set("")
        mostrar_mensaje("Tú", texto)
        estado.set("Procesando…")
        if re.fullmatch(r"(?:cerebro[, ]+)?(?:analiza|revisa) (?:este |el )?proyecto"
                        r"(?: y (?:corrige|arregla) (?:sus |los )?errores)?[.!]?", texto, re.I):
            analizar_proyecto()
            return

        if re.fullmatch(r"(?:cerebro[, ]+)?abre el archivo (?:que est[aá] )?(?:seleccionado|en el explorador)[.!]?",
                        texto, re.I):
            if lista.curselection():
                cargar_archivo()
                estado.set("Abriendo el archivo seleccionado…")
            else:
                estado.set("Selecciona un archivo en el explorador.")
            return
        if re.fullmatch(r"(?:cerebro[, ]+)?corrige el error (?:que aparece )?en validaciones[.!]?", texto, re.I):
            analizar_proyecto()
            return
        if re.fullmatch(r"(?:cerebro[, ]+)?ens[eé][ñn]ame qu[eé] cambiaste[.!?]?", texto, re.I):
            if cambios_aplicados:
                mostrar_mensaje("Cerebro", "Cambios aplicados en el proyecto de esta ventana:\n" +
                                "\n".join(propuesta["diff"] for propuesta in cambios_aplicados[-3:]))
                estado.set("Mostrando los últimos cambios aplicados.")
            else:
                mostrar_mensaje("Cerebro", "Todavía no apliqué propuestas en este proyecto.")
                estado.set("Núcleo conectado")
            return

        revision = revision_chat
        activa = chat_activo

        def respondido(dato):
            nonlocal revision_visible
            if revision != revision_chat:
                return
            ya_visible = dato["revision"] == revision_visible and dato["revision"] != dato["revision_anterior"]
            if dato["revision_anterior"] == revision_visible:
                revision_visible = dato["revision"]
            if not ya_visible:
                mostrar_mensaje("Cerebro", dato["respuesta"])
            presentar_resultado(dato)
            estado.set("Núcleo conectado")

        publicar(lambda: pedir("chat", {"mensaje": texto, "modo": "studio", "cliente": identificador,
                                       "conversacion": activa}, tiempo=78), respondido)

    def mostrar_chat(datos):
        nonlocal revision_chat, chat_activo, revision_visible
        chats_guardados[:] = datos["chats"]
        if not any(chat["id"] == datos["activa"] for chat in chats_guardados):
            chats_guardados.insert(0, {"id": datos["activa"], "titulo": "Conversación actual"})
        selector.configure(values=[chat["titulo"] for chat in chats_guardados])
        selector.current(next(i for i, chat in enumerate(chats_guardados) if chat["id"] == datos["activa"]))
        version = datos["activa"], datos["revision"]
        if version == (chat_activo, revision_visible):
            return
        if datos["activa"] != chat_activo:
            revision_chat += 1
        chat_activo, revision_visible = version
        mostrar(salida, "")
        for turno in datos["turnos"]:
            mostrar_mensaje("Tú" if turno["rol"] == "usuario" else "Cerebro", turno["texto"])


    def gestionar_chat(borrar=False):
        if chat_activo is None:
            return
        if borrar and not messagebox.askyesno("Eliminar chat", "¿Eliminar la conversación actual?", parent=app):
            return
        activa = chat_activo

        def operar():
            if borrar:
                pedir("historial", {"confirmar": True, "id": activa})
                return pedir("conversaciones")
            return pedir("conversaciones", {"accion": "nueva"})

        def actualizado(datos):
            nonlocal chat_activo
            chat_activo = None
            mostrar_chat(datos)
            estado.set("Conversación eliminada." if borrar else "Nueva conversación.")

        publicar(operar, actualizado)

    def seleccionar_chat(_evento):
        indice = selector.current()
        if indice < 0:
            return
        elegida = chats_guardados[indice]["id"]
        if elegida != chat_activo:
            publicar(lambda: pedir("conversaciones", {"accion": "seleccionar", "id": elegida}), mostrar_chat)

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
                    vista = pedir("interfaz", {"id": identificador, "modo": "studio",
                                         "visible": se_ve, "enfocar": enfocar}, tiempo=2)
                if not se_ve and vista["activa"] == "escritorio":
                    lanzar_acompanante()

        publicar(enviar_presencia)

    def visibilidad(evento, mostrar):
        nonlocal visible
        if evento.widget is app:
            visible = mostrar
            informar(mostrar)


    def pulso():
        nonlocal temporizador_pulso
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
            version_visible = chat_activo, revision_visible

            def consultar_chat():
                version = pedir("conversacion-activa")
                if (version["activa"], version["revision"]) != version_visible:
                    return pedir("conversaciones")
                return None

            def sincronizado(datos):
                if datos is not None:
                    mostrar_chat(datos)
                    estado.set("Núcleo conectado")

            publicar(consultar_chat, sincronizado)
        if visible and proyecto_activo:
            actualizar_archivos()
        if visible and documento_activo is not None:
            referencia = documento_activo
            esperado, nombre, _ = referencia

            def observar_archivo():
                try:
                    return proyecto("estado_archivo" if esperado else "estado_suelto",
                                    nombre=nombre, esperada=esperado)
                except ErrorAPI:
                    return {}

            def observado(datos):
                if referencia == documento_activo and datos.get("marca") != marca_documento:
                    estado.set("El archivo cambió en disco. Vuelve a abrirlo o usa Actualizar visor.")

            publicar(observar_archivo, observado)
        if tareas_en_curso:
            def mostrar_tareas(datos):
                for tarea in datos:
                    if tarea["id"] in tareas_en_curso and tarea["estado"] in {"terminada", "error"}:
                        mostrar(validaciones, tarea["salida"] + "\n", anexar=True)
                        tareas_en_curso.remove(tarea["id"])
            publicar(lambda: pedir("tareas"), mostrar_tareas)
        temporizador_pulso = app.after(2000, pulso)

    def procesar():
        nonlocal temporizador_cola
        while True:
            try:
                terminado, datos, error = pendientes.get_nowait()
            except Empty:
                break
            if error:
                estado.set(error)
            else:
                terminado(datos)
        temporizador_cola = app.after(75, procesar)

    def cerrar():
        nonlocal generacion
        if editor.edit_modified() and not messagebox.askyesno("Cambios sin guardar", "¿Cerrar Studio?"):
            return
        generacion += 1
        with presencia, suppress(OSError, RuntimeError):
            vista = pedir("interfaz", {"id": identificador, "modo": "studio", "visible": False}, tiempo=1)
            if vista["activa"] == "escritorio":
                lanzar_acompanante()
        app.after_cancel(temporizador_cola)
        app.after_cancel(temporizador_pulso)
        if resaltado_pendiente is not None:
            app.after_cancel(resaltado_pendiente)
        app.destroy()

    boton(barra_archivos, "Actualizar", actualizar_archivos)
    menu_archivos = ttk.Menubutton(barra_archivos, text="Archivos")
    acciones_archivos = Menu(menu_archivos, tearoff=False)
    for texto_menu, accion_archivo in (("Nuevo archivo", "crear"), ("Nueva carpeta", "carpeta"),
                                        ("Mover o renombrar", "mover"), ("Copiar", "copiar"),
                                        ("Enviar a la papelera", "papelera")):
        acciones_archivos.add_command(label=texto_menu,
                                      command=lambda accion=accion_archivo: gestionar_archivo(accion))
    menu_archivos.configure(menu=acciones_archivos)
    menu_archivos.pack(side=LEFT, pady=3)
    favoritas.bind("<<ComboboxSelected>>", elegir_personal)
    herramientas_archivo = Menu(menu_archivos, tearoff=False)
    for nombre, clave in (("Analizar archivo", "analizar"), ("Resumen breve", "resumir"),
                          ("Validar archivo", "validar"), ("Evaluar alumno", "evaluar")):
        herramientas_archivo.add_command(label=nombre, state="disabled", command=lambda tipo=clave: herramienta_archivo(tipo))
    acciones_archivos.add_separator()
    acciones_archivos.add_command(label="Abrir archivo en visor", command=elegir_archivo_suelto)
    acciones_archivos.add_command(label="Actualizar visor", command=actualizar_suelto)
    acciones_archivos.add_command(label="Añadir o quitar favorita", command=marcar_favorita)
    acciones_archivos.add_cascade(label="Archivo seleccionado", menu=herramientas_archivo)
    boton(acciones_proyecto, "Abrir proyecto", abrir_proyecto)
    boton(acciones_proyecto, "Abrir en Thunar", mostrar_gestor)
    boton(acciones_proyecto, "Abrir web", abrir_pagina_web)
    if dnd:
        for superficie in (editor, visor, pagina_resultados):
            superficie.drop_target_register(dnd[0])
            superficie.dnd_bind("<<Drop>>", soltar)
        lista.drag_source_register(1, dnd[0])
        lista.dnd_bind("<<DragInitCmd>>", iniciar_arrastre)
    boton(acciones_proyecto, "Analizar", analizar_proyecto)
    boton(acciones_proyecto, "Pruebas", probar_proyecto)
    boton(acciones_cambio, "Aplicar propuesta", aplicar_cambio, "Principal.TButton")
    boton(acciones_cambio, "Rechazar", lambda: revisar_decision("rechazar"))
    boton(acciones_cambio, "Revertir último", lambda: revisar_decision("revertir"))
    elegir_cambio.bind("<<ComboboxSelected>>", mostrar_diff)
    boton(barra_editor, "Guardar · Ctrl+S", guardar, "Principal.TButton")
    boton(barra_editor, "Validar archivo", revisar)
    boton(barra_editor, "Vista previa", previsualizar_editor)
    boton(barra_editor, "Consultar selección", usar_seleccion)
    boton(barra_chat, "Enviar", enviar, "Principal.TButton")
    boton(barra_chat, "Adjuntar", adjuntar)
    boton(barra_chat, "Cancelar coordinación", lambda: publicar(
        lambda: pedir("chat", {"mensaje": "Cancela la coordinación", "modo": "studio",
                               "cliente": identificador}),
        lambda dato: estado.set(dato["respuesta"])))
    boton(barra_conversaciones, "Nuevo chat", gestionar_chat)
    boton(barra_conversaciones, "Eliminar chat", lambda: gestionar_chat(borrar=True), "Eliminar.TButton")
    def ver_chats():
        from universe.dialogo_chats import gestionar_conversaciones
        gestionar_conversaciones(app, pedir, mostrar_chat)

    boton(barra_conversaciones, "Chats", ver_chats)
    selector.bind("<<ComboboxSelected>>", seleccionar_chat)
    lista.bind("<<ListboxSelect>>", lambda evento: cargar_archivo(evento)
               if lista.curselection() and not lista.get(lista.curselection()[0]).endswith("/") else None)
    lista.bind("<Double-Button-1>", lambda evento: cargar_archivo(evento)
               if lista.curselection() and lista.get(lista.curselection()[0]).endswith("/") else None)
    lista.bind("<Return>", cargar_archivo)
    consulta.bind("<Return>", lambda _: enviar())

    def guardar_atajo(_evento):
        guardar()
        return "break"

    def buscar_atajo(_evento):
        paginas.select(cuerpo)
        buscador.focus_set()
        return "break"

    app.bind("<Control-s>", guardar_atajo)
    app.bind("<Control-p>", buscar_atajo)
    app.bind("<FocusIn>", lambda evento: informar(True) if evento.widget is app and visible else None)
    app.bind("<Map>", lambda evento: visibilidad(evento, True))
    app.bind("<Unmap>", lambda evento: visibilidad(evento, False))
    app.protocol("WM_DELETE_WINDOW", cerrar)
    if inicial == "universe":
        paginas.select(mapa)
    actualizar_archivos()

    def recordar_al_abrir(datos):
        if datos.get("carpeta") and proyecto_activo is None and inicial != "universe":
            abrir_proyecto(datos["carpeta"], datos.get("archivo"))

    publicar(lambda: proyecto("escritorio"), actualizar_preferencias)
    publicar(lambda: proyecto("recordado"), recordar_al_abrir)
    publicar(lambda: pedir("conversaciones"), mostrar_chat)
    publicar(lambda: pedir("estado"), lambda _: estado.set("Núcleo conectado"))
    informar(True)
    temporizador_cola = app.after(75, procesar)
    temporizador_pulso = app.after(2000, pulso)
    consulta.focus_set()
    app.mainloop()
