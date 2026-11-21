"""Estudio nativo para el núcleo de Cerebro, con un HUD inspirado en ARUS."""
from base64 import b64encode
from contextlib import suppress
from io import StringIO
import keyword
from pathlib import Path
import re
from queue import Empty, SimpleQueue
from secrets import token_hex
from threading import Lock, Thread
import tokenize
from tkinter import END, BOTH, LEFT, RIGHT, X, Y, Listbox, StringVar, Text, Tk, TclError
from tkinter import filedialog, messagebox, ttk
from urllib.parse import quote

from universe.lanzador import api, abrir, lanzar_acompanante, lanzar_terminal
from universe.mapa_studio import MapaStudio

from universe.paleta import ACENTO, ACTIVO, BORDE, EDITOR, FONDO, PANEL, SECUNDARIO, SELECCION, TEXTO


def abrir_studio(sesion, solicitud=None, inicial="proyecto"):
    try:
        app = Tk()
    except TclError as exc:
        raise RuntimeError("No pude abrir Studio. Necesitas una sesión gráfica y python3-tk.") from exc
    app.title("Cerebro Studio")
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
    entrada = StringVar()
    pendientes = SimpleQueue()
    tareas_en_curso = set()
    identificador = token_hex(12)
    presencia = Lock()
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

    def pedir(operacion, datos=None):
        return api(sesion, operacion, datos)

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
    ttk.Label(cabecera, text="Cerebro Studio", style="Titulo.TLabel").pack(side=LEFT, padx=(0, 15))
    boton(cabecera, "Chat web", lambda: abrir(sesion, "chat"), lado=RIGHT)
    boton(cabecera, "Acompañante", app.iconify, lado=RIGHT)
    boton(cabecera, "Terminal", lanzar_terminal, lado=RIGHT)
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
                 f"Entrenamientos registrados: {informe['entrenamientos_registrados']}", "",
                 *[f"{tarea['objetivo']}. {tarea['accion']}" for tarea in informe["propuestas"]]])
            messagebox.showinfo("Análisis de aprendizaje", resumen, parent=app)

        publicar(lambda: pedir("analizar-aprendizaje"), responder)

    mapa = MapaStudio(paginas, actualizar_mapa, analizar_universe)
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
    ttk.Label(archivos, text="Filtrar archivos · Ctrl+P").pack(anchor="w", pady=(0, 4))
    buscador = ttk.Entry(archivos, textvariable=filtro_archivos)
    buscador.pack(fill=X, pady=(0, 7))
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
        lista.delete(0, END)
        for nombre in inventario:
            if filtro in nombre.casefold():
                lista.insert(END, nombre)

    filtro_archivos.trace_add("write", filtrar_archivos)

    def actualizar_archivos():
        def cargar(datos):
            inventario[:] = datos["archivos"]
            filtrar_archivos()
        esperado = proyecto_activo
        publicar(lambda: proyecto("listar", esperada=esperado) if esperado else pedir("archivos"), cargar)

    def cargar_archivo(_evento=None):
        seleccionado = lista.curselection()
        if not seleccionado:
            return
        if editor.edit_modified() and not messagebox.askyesno("Cambios sin guardar", "¿Abrir otro archivo?"):
            return
        nombre = lista.get(seleccionado[0])

        abierto_en = proyecto_activo

        def copiar(datos):
            nonlocal archivo_proyecto, original_proyecto
            if proyecto_activo != abierto_en:
                return
            archivo_proyecto, original_proyecto = nombre, datos["texto"]
            ruta.set(nombre)
            vistas_editor.select(pagina_editor)
            mostrar(editor, datos["texto"])
            editor.edit_modified(False)
            programar_resaltado()

        publicar(lambda: proyecto("leer", nombre=nombre, esperada=abierto_en) if abierto_en else pedir("archivo?nombre=" + quote(nombre)), copiar)

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

    def abrir_proyecto():
        if editor.edit_modified() and not messagebox.askyesno("Cambios sin guardar", "¿Cambiar de proyecto?", parent=app):
            return
        carpeta = filedialog.askdirectory(title="Elegir carpeta de proyecto", mustexist=True, parent=app)
        if not carpeta:
            return
        if not messagebox.askyesno("Autorizar proyecto", f"¿Permitir a Cerebro inspeccionar «{carpeta}»?", parent=app):
            return

        def abierto(datos):
            nonlocal proyecto_activo, archivo_proyecto, original_proyecto
            proyecto_activo = datos["carpeta"]
            proyecto_titulo.set(Path(proyecto_activo).name)
            inventario[:] = datos["archivos"]
            filtrar_archivos()
            ruta.set("")
            archivo_proyecto = original_proyecto = None
            mostrar(editor, "")
            editor.edit_modified(False)
            cargar_propuestas([])
            cambios_aplicados.clear()
            estado.set("Proyecto abierto" + (" · inventario limitado" if datos["limitado"] else ""))

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
            lineas = [f"Revisé {datos['revisados']} archivos Python.",
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

    def probar_proyecto():
        if not proyecto_activo:
            estado.set("Abre primero una carpeta de proyecto.")
            return
        if not messagebox.askyesno("Ejecutar pruebas",
                                   f"¿Ejecutar unittest en «{proyecto_activo}»? Las pruebas ejecutan código del proyecto.",
                                   parent=app):
            return
        esperado = proyecto_activo
        vistas_editor.select(pagina_validaciones)
        mostrar(validaciones, "Ejecutando unittest…\n", anexar=True)
        publicar(lambda: proyecto("pruebas", confirmar=True, esperada=esperado), lambda dato: tareas_en_curso.add(dato["id"]))

    def enviar(texto=None):
        texto = (entrada.get() if texto is None else texto).strip()
        if not texto or chat_activo is None:
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
            estado.set("Núcleo conectado")

        publicar(lambda: pedir("chat", {"mensaje": texto, "modo": "studio", "cliente": identificador, "conversacion": activa}), respondido)

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

            publicar(consultar_chat, lambda datos: mostrar_chat(datos) if datos else None)
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
            api(sesion, "interfaz", {"id": identificador, "modo": "studio", "visible": False}, tiempo=1)
        app.after_cancel(temporizador_cola)
        app.after_cancel(temporizador_pulso)
        if resaltado_pendiente is not None:
            app.after_cancel(resaltado_pendiente)
        app.destroy()

    boton(barra_archivos, "Actualizar", actualizar_archivos)
    boton(acciones_proyecto, "Abrir proyecto", abrir_proyecto)
    boton(acciones_proyecto, "Analizar", analizar_proyecto)
    boton(acciones_proyecto, "Pruebas", probar_proyecto)
    boton(acciones_cambio, "Aplicar propuesta", aplicar_cambio, "Principal.TButton")
    elegir_cambio.bind("<<ComboboxSelected>>", mostrar_diff)
    boton(barra_editor, "Guardar · Ctrl+S", guardar, "Principal.TButton")
    boton(barra_editor, "Validar Python", revisar)
    boton(barra_chat, "Enviar", enviar, "Principal.TButton")
    boton(barra_chat, "Adjuntar", adjuntar)
    boton(barra_conversaciones, "Nuevo chat", gestionar_chat)
    boton(barra_conversaciones, "Eliminar chat", lambda: gestionar_chat(borrar=True), "Eliminar.TButton")
    def ver_chats():
        from universe.dialogo_chats import gestionar_conversaciones
        gestionar_conversaciones(app, pedir, mostrar_chat)

    boton(barra_conversaciones, "Chats", ver_chats)
    selector.bind("<<ComboboxSelected>>", seleccionar_chat)
    lista.bind("<<ListboxSelect>>", cargar_archivo)
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
    publicar(lambda: pedir("conversaciones"), mostrar_chat)
    publicar(lambda: pedir("estado"), lambda _: estado.set("Núcleo conectado"))
    informar(True)
    temporizador_cola = app.after(75, procesar)
    temporizador_pulso = app.after(2000, pulso)
    consulta.focus_set()
    app.mainloop()
