"""Entradas de MX Linux para un núcleo de usuario compartido."""
import contextlib
import fcntl
from hashlib import sha256
from http.client import IncompleteRead
import json
import os
import re
from pathlib import Path
import secrets
from shutil import which
import subprocess
import sys
from threading import Event, Thread
from time import monotonic, sleep
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from webbrowser import open as abrir_web


class SoloLoopback(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


CLIENTE_LOCAL = build_opener(ProxyHandler({}), SoloLoopback())


def carpeta():
    base = Path(os.environ.get("XDG_RUNTIME_DIR") or Path.home() / ".cache")
    ruta = base / "cerebro-local"
    ruta.mkdir(mode=0o700, parents=True, exist_ok=True)
    if ruta.is_symlink() or ruta.stat().st_uid != os.getuid() or ruta.stat().st_mode & 0o077:
        raise PermissionError(f"El directorio de sesión de Cerebro debe ser privado: {ruta}")
    return ruta


def api(sesion, ruta, datos=None, tiempo=25):
    if not re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}", sesion["url"]):
        raise ValueError("Dirección de sesión inválida.")
    cuerpo = None if datos is None else json.dumps(datos, ensure_ascii=False).encode()
    solicitud = Request(sesion["url"] + "/api/" + ruta, data=cuerpo, headers={
        "Authorization": "Bearer " + sesion["token"], "Content-Type": "application/json",
    })
    try:
        with CLIENTE_LOCAL.open(solicitud, timeout=tiempo) as respuesta:
            return json.load(respuesta)
    except HTTPError as exc:
        raise RuntimeError(json.load(exc).get("error", "Cerebro devolvió un error.")) from exc
    except IncompleteRead as exc:
        raise ConnectionError("El núcleo se desconectó antes de enviar la respuesta completa.") from exc


def version_local():
    raiz = Path(__file__).resolve().parent.parent
    fuentes = sorted(raiz.glob("universe/*.py")) + sorted(raiz.glob("universe/web/*"))
    fuentes += [raiz / "chat.py", raiz / "config.py"]
    firma = sha256()
    for fuente in fuentes:
        if fuente.is_file():
            firma.update(fuente.read_bytes())
    return firma.hexdigest()


def conectar():
    ruta = carpeta()
    registro = ruta / "sesion.json"
    with (ruta / "inicio.lock").open("a") as cerrojo:
        fcntl.flock(cerrojo, fcntl.LOCK_EX)
        try:
            sesion = json.loads(registro.read_text())
            api(sesion, "interfaz", tiempo=1)
            if sesion.get("version") == version_local():
                return sesion
            api(sesion, "apagar", {}, tiempo=2)
            registro.unlink(missing_ok=True)
        except (OSError, ValueError, RuntimeError, KeyError):
            registro.unlink(missing_ok=True)
        with (ruta / "nucleo.log").open("ab") as log:
            proceso = subprocess.Popen([sys.executable, "-m", "universe.lanzador", "_nucleo"],
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       start_new_session=True)
        limite = monotonic() + 12
        while monotonic() < limite and proceso.poll() is None:
            if registro.is_file():
                return json.loads(registro.read_text())
            sleep(.08)
    raise RuntimeError(f"No arrancó el núcleo. Consulta {ruta / 'nucleo.log'}.")


def nucleo():
    from core.entorno_portatil import verificar_almacenamiento
    from main import cargar_modelo
    from universe.nucleo import Nucleo
    from universe.servidor import crear_servidor

    verificar_almacenamiento()
    modelo, meta, _ = cargar_modelo()
    internet = os.environ.get("CEREBRO_SIN_INTERNET") != "1"
    motor = Nucleo("local", modelo=modelo, meta=meta, internet=internet, investigar_auto=internet,
                   documentos_usuario=os.environ.get("CEREBRO_SIN_DOCUMENTOS") != "1")
    token = secrets.token_urlsafe(32)
    with crear_servidor(0, motor, token, permitir_cierre=True, abrir_estudio=lanzar_estudio,
                         abrir_terminal=lanzar_terminal, mostrar_acompanante=lanzar_acompanante,
                         abrir_destino=lanzar_destino, abrir_universe=lanzar_universe) as servidor:
        ruta = carpeta()
        datos = {"url": f"http://127.0.0.1:{servidor.server_port}", "token": token,
                 "version": version_local()}
        fd = os.open(ruta / "sesion.tmp", os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as archivo:
            json.dump(datos, archivo)
        (ruta / "sesion.tmp").replace(ruta / "sesion.json")
        servidor.serve_forever()


def abrir(sesion, interfaz):
    lanzar_acompanante()
    return abrir_web(f"{sesion['url']}/{interfaz}#{sesion['token']}")


def lanzar_destino(destino):
    if not _hay_escritorio():
        return False
    if destino == "youtube":
        return abrir_web("https://www.youtube.com/")
    if destino == "navegador":
        if exo := which("exo-open"):
            return _lanzar_proceso([exo, "--launch", "WebBrowser"])
        return abrir_web("about:blank")
    if destino == "steam":
        if steam := which("steam"):
            return _lanzar_proceso([steam])
        if flatpak := which("flatpak"):
            try:
                instalado = subprocess.run([flatpak, "info", "com.valvesoftware.Steam"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4).returncode == 0
            except subprocess.SubprocessError:
                instalado = False
            if instalado:
                return _lanzar_proceso([flatpak, "run", "com.valvesoftware.Steam"])
    return False


def _hay_escritorio():
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _lanzar_proceso(comando):
    with (carpeta() / "nucleo.log").open("ab") as log:
        subprocess.Popen(comando, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    return True


def lanzar_acompanante():
    if not _hay_escritorio():
        return False
    return _lanzar_proceso([sys.executable, "-m", "universe.lanzador", "_escritorio"])


def lanzar_estudio():
    if not _hay_escritorio():
        return False
    return _lanzar_proceso([sys.executable, "-m", "universe.lanzador", "studio"])


def lanzar_universe():
    if not _hay_escritorio():
        return False
    return _lanzar_proceso([sys.executable, "-m", "universe.lanzador", "universe"])


def lanzar_terminal():
    if not _hay_escritorio():
        return False
    if programa := which("xfce4-terminal"):
        prefijo = [programa, "--disable-server", "--title=Cerebro · Terminal", "--execute"]
    elif programa := which("x-terminal-emulator"):
        prefijo = [programa, "-e"]
    else:
        return False
    return _lanzar_proceso([*prefijo, sys.executable, "-m", "universe.lanzador", "terminal"])


def terminal(sesion):
    identificador = secrets.token_hex(12)
    cerrar = Event()

    def presencia(visible, enfocar=False):
        return api(sesion, "interfaz", {"id": identificador, "modo": "terminal",
                                       "visible": visible, "enfocar": enfocar}, tiempo=2)

    def renovar():
        while not cerrar.wait(2):
            with contextlib.suppress(OSError, RuntimeError):
                presencia(True)

    presencia(True, enfocar=True)
    lanzar_acompanante()
    renovador = Thread(target=renovar, daemon=True)
    renovador.start()
    acento = "\033[38;5;81m" if sys.stdout.isatty() and not os.environ.get("NO_COLOR") else ""
    fin = "\033[0m" if acento else ""
    def mostrar_historial(limite):
        for turno in api(sesion, "historial")["turnos"][-limite:]:
            print(f"{'Tú' if turno['rol'] == 'usuario' else 'Cerebro'} · {turno['texto']}")

    accesos = {
        "/studio": lanzar_estudio,
        "/web": lambda: abrir(sesion, "chat"),
    }
    fondo = "\033[48;5;233m" if acento else ""
    print(f"{fondo}{acento}  C E R E B R O  {fin}  ·  {Path.cwd()}")
    print("  /studio   /web   /historial   /nuevo-chat   /chats   /eliminar-chat   /ayuda   /salir")
    if sys.stdin.isatty():
        with contextlib.suppress(ImportError):
            __import__("readline")
    try:
        while True:
            entrada = input(f"{acento}cerebro ›{fin} ").strip()
            comando = entrada.casefold()
            if comando in {"salir", "/salir", "adiós", "adios"}:
                break
            if not entrada:
                continue
            try:
                presencia(True, enfocar=True)
                if comando == "/historial":
                    mostrar_historial(12)
                    continue
                if comando == "/nuevo-chat":
                    api(sesion, "conversaciones", {"accion": "nueva"})
                    print("Nueva conversación.")
                    continue
                if comando == "/chats":
                    chats = api(sesion, "conversaciones")["chats"]
                    for indice, chat in enumerate(chats, 1):
                        print(f"  {indice}. {chat['titulo']}")
                    if chats:
                        opcion = input("Abrir número (Enter cancela): ").strip()
                        if opcion.isascii() and opcion.isdigit() and len(opcion) <= 8 and 1 <= int(opcion) <= len(chats):
                            api(sesion, "conversaciones", {"accion": "seleccionar", "id": chats[int(opcion) - 1]["id"]})
                            mostrar_historial(12)
                    continue
                if comando == "/eliminar-chat":
                    activa = api(sesion, "conversaciones")["activa"]
                    if input("¿Eliminar la conversación actual? [s/N] ").strip().casefold() in {"s", "si", "sí"}:
                        api(sesion, "historial", {"confirmar": True, "id": activa})
                        if sys.stdout.isatty():
                            print("\033[3J\033[2J\033[H", end="")
                        print("Historial eliminado.")
                    continue
                if comando in accesos:
                    if not accesos[comando]():
                        print("No se pudo abrir la interfaz desde esta sesión.", file=sys.stderr)
                    continue
                respuesta = api(sesion, "chat", {"mensaje": entrada, "modo": "terminal", "cliente": identificador})
                print(respuesta["respuesta"])
                if respuesta.get("abrir") == "studio":
                    lanzar_estudio()
            except (OSError, RuntimeError) as exc:
                print(exc, file=sys.stderr)
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        cerrar.set()
        renovador.join(timeout=2)
        with contextlib.suppress(OSError, RuntimeError):
            presencia(False)


def escritorio(sesion):
    import queue
    import tkinter as tk
    from tkinter import messagebox

    try:
        ventana = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError("Se necesita una sesión gráfica con Tk para abrir el acompañante.") from exc
    ventana.title("Cerebro · Acompañante")
    fondo, panel, texto = "#090e18", "#121c2c", "#e8f3ff"
    ventana.configure(bg=fondo)
    ventana.resizable(False, False)
    ventana.attributes("-topmost", True)

    def ajustar_ventana(alto):
        ancho = min(380, ventana.winfo_screenwidth())
        margen = 16
        x = max(0, ventana.winfo_screenwidth() - ancho - margen)
        y = max(0, ventana.winfo_screenheight() - alto - 52)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

    def boton(padre, etiqueta, accion, color=panel):
        return tk.Button(padre, text=etiqueta, command=accion, bg=color, fg=texto,
                         activebackground="#315484", activeforeground="#ffffff",
                         disabledforeground="#7792b3", relief="flat", cursor="hand2",
                         highlightbackground=fondo, highlightcolor="#86bbff", padx=9, pady=5)

    cabecera = tk.Frame(ventana, bg=fondo)
    cabecera.pack(fill="x", padx=14, pady=(10, 0))
    tk.Label(cabecera, text="Cerebro", fg=texto, bg=fondo,
             font=("TkDefaultFont", 12, "bold")).pack(side="left")
    contenido = tk.Frame(ventana, bg=fondo)
    compacto = False

    def alternar_panel():
        nonlocal compacto
        compacto = not compacto
        if compacto:
            contenido.pack_forget()
        else:
            contenido.pack(fill="both", expand=True, padx=14, pady=(0, 12))
            if not ocupado:
                entrada.focus_set()
        boton_panel.configure(text="Abrir chat" if compacto else "Recoger")
        ajustar_ventana(161 if compacto else 432)

    boton_panel = boton(cabecera, "Recoger", alternar_panel)
    boton_panel.pack(side="right")

    from universe.orbita import Orbita
    nucleo_visual = Orbita(ventana)
    nucleo_visual.pack(fill="x")

    contenido.pack(fill="both", expand=True, padx=14, pady=(0, 12))
    ajustar_ventana(432)
    conversacion = tk.Frame(contenido, bg=panel)
    conversacion.pack(fill="both", expand=True)
    salida = tk.Text(conversacion, height=5, wrap="word", bg=panel, fg=texto, relief="flat",
                     padx=12, pady=8, highlightthickness=0, font=("TkDefaultFont", 10))
    desplazamiento = tk.Scrollbar(conversacion, command=salida.yview)
    desplazamiento.pack(side="right", fill="y")
    salida.configure(yscrollcommand=desplazamiento.set)
    salida.pack(side="left", fill="both", expand=True)
    salida.tag_configure("Tú", foreground="#a8ceff", spacing1=7)
    salida.tag_configure("Cerebro", foreground="#77d6ff", spacing1=7)
    salida.insert("end", "¿En qué te ayudo?")
    salida.configure(state="disabled")

    aviso = tk.StringVar()
    tk.Label(contenido, textvariable=aviso, fg="#aec6e5", bg=fondo, anchor="w",
             justify="left", wraplength=330).pack(fill="x")
    compositor = tk.Frame(contenido, bg=fondo)
    compositor.pack(fill="x", pady=(4, 6))
    entrada = tk.Entry(compositor, bg=panel, fg=texto, insertbackground=texto,
                       relief="flat", highlightbackground="#334e72", highlightcolor="#86bbff",
                       highlightthickness=1, font=("TkDefaultFont", 11))
    entrada.pack(side="left", fill="both", expand=True, padx=(0, 6))
    barra = tk.Frame(contenido, bg=fondo)
    barra.pack(fill="x")
    ultima_respuesta = ""
    voz_activada = False
    cancelar_audio = Event()
    microfono = tk.StringVar(value="default")
    ocupado = False
    eventos = queue.SimpleQueue()
    detenido = Event()
    identificador = secrets.token_hex(12)

    chat_activo = None

    def observar():
        while not detenido.is_set():
            try:
                eventos.put(("vista", api(sesion, "interfaz", tiempo=2)["activa"]))
                if not ocupado:
                    activa = api(sesion, "conversacion-activa", tiempo=2)["activa"]
                    if activa != chat_activo:
                        eventos.put(("conversación remota", api(sesion, "conversaciones", tiempo=2)))
            except (OSError, RuntimeError):
                registro = carpeta() / "sesion.json"
                with contextlib.suppress(OSError, ValueError):
                    nueva = json.loads(registro.read_text())
                    sesion.update(nueva)
                eventos.put(("vista", "escritorio"))
            detenido.wait(.8)

    def despachar(mensaje):
        try:
            try:
                salida = api(sesion, "chat", {"mensaje": mensaje, "modo": "escritorio", "cliente": identificador, "conversacion": chat_activo})
            except OSError:
                sesion.update(conectar())
                salida = api(sesion, "chat", {"mensaje": mensaje, "modo": "escritorio", "cliente": identificador, "conversacion": chat_activo})
            eventos.put(("respuesta", salida["respuesta"]))
            if salida.get("abrir") == "studio":
                lanzar_estudio()
        except (OSError, RuntimeError) as exc:
            eventos.put(("respuesta", str(exc)))

    def cambiar_estado(texto):
        nonlocal ocupado
        ocupado = texto != "Disponible"
        nucleo_visual.estado(texto)
        estado = "disabled" if ocupado else "normal"
        entrada.configure(state=estado)
        boton_dictar.configure(state=estado)
        boton_enviar.configure(state=estado)
        menu_acciones.entryconfigure("Elegir audio", state=estado)
        boton_borrar.configure(state=estado)
        boton_nuevo.configure(state=estado)

    def enviar(_evento=None):
        texto = entrada.get().strip()
        if texto and not ocupado and chat_activo is not None:
            entrada.delete(0, "end")
            aviso.set("")
            agregar_turno("Tú", texto)
            cambiar_estado("Procesando")
            Thread(target=despachar, args=(texto,), daemon=True).start()

    def tarea_de_voz(operacion, tipo):
        try:
            eventos.put((tipo, operacion()))
        except (OSError, RuntimeError, ValueError) as exc:
            eventos.put(("error de voz", str(exc)))

    def dictar():
        from core.local_voice import dictar as grabar
        dispositivo = microfono.get()
        aviso.set("")
        cambiar_estado("Escuchando")
        Thread(target=tarea_de_voz, args=(lambda: grabar(dispositivo=dispositivo), "dictado"),
               daemon=True).start()

    def hablar_respuesta(texto):
        from core.local_voice import leer_en_espanol
        if not texto:
            return
        cancelar_audio.clear()
        cambiar_estado("Hablando")
        Thread(target=tarea_de_voz,
               args=(lambda: leer_en_espanol(texto, cancelar_audio), "audio listo")).start()

    def alternar_voz():
        nonlocal voz_activada
        voz_activada = not voz_activada
        boton_leer.configure(text="Voz activa" if voz_activada else "Voz apagada")
        if not voz_activada:
            cancelar_audio.set()
        elif not ocupado:
            hablar_respuesta(ultima_respuesta)

    def copiar_respuesta():
        if ultima_respuesta:
            ventana.clipboard_clear()
            ventana.clipboard_append(ultima_respuesta)
            aviso.set("Respuesta copiada.")

    def audio():
        from core.local_voice import dispositivos_audio
        cambiar_estado("Detectando audio")
        Thread(target=tarea_de_voz, args=(dispositivos_audio, "dispositivos"), daemon=True).start()

    def elegir_audio(datos):
        from tkinter import ttk
        panel = tk.Toplevel(ventana)
        panel.title("Audio de Cerebro")
        panel.transient(ventana)
        cuadro = ttk.Frame(panel, padding=12)
        cuadro.pack(fill="both", expand=True)
        ttk.Label(cuadro, text="Entrada detectada · micrófono").pack(anchor="w")
        ttk.Combobox(cuadro, values=datos["entradas"], textvariable=microfono,
                     width=40, state="readonly").pack(fill="x", pady=(5, 10))
        ttk.Label(cuadro, text="Salida: predeterminada de MX Linux").pack(anchor="w")
        for dispositivo in datos["salidas"]:
            ttk.Label(cuadro, text=dispositivo, wraplength=340).pack(anchor="w")
        ttk.Button(cuadro, text="Listo", command=panel.destroy).pack(anchor="e", pady=(8, 0))

    def agregar_turno(rol, mensaje):
        salida.configure(state="normal")
        salida.insert("end", f"\n\n{rol}\n", rol)
        salida.insert("end", mensaje)
        if int(salida.index("end-1c").split(".")[0]) > 500:
            salida.delete("1.0", "101.0")
        salida.see("end")
        salida.configure(state="disabled")

    def gestionar_chat(borrar=False):
        if chat_activo is None:
            return
        if borrar and not messagebox.askyesno("Eliminar chat", "¿Eliminar la conversación actual?", parent=ventana):
            return
        cambiar_estado("Procesando")

        def operar():
            if borrar:
                api(sesion, "historial", {"confirmar": True, "id": chat_activo})
                return api(sesion, "conversaciones")
            return api(sesion, "conversaciones", {"accion": "nueva"})

        Thread(target=tarea_de_voz, args=(operar, "conversación"), daemon=True).start()

    def actualizar():
        nonlocal ultima_respuesta, chat_activo
        while not eventos.empty():
            tipo, valor = eventos.get()
            if tipo == "vista":
                if valor == "escritorio" and ventana.state() == "withdrawn":
                    ventana.deiconify()
                elif valor != "escritorio" and ventana.state() != "withdrawn":
                    ventana.withdraw()
            elif tipo == "respuesta":
                ultima_respuesta = valor
                agregar_turno("Cerebro", valor)
                cambiar_estado("Disponible")
                if voz_activada:
                    hablar_respuesta(valor)
            elif tipo in {"conversación", "conversación remota"}:
                if tipo == "conversación remota" and (ocupado or chat_activo == valor["activa"]):
                    continue
                chat_activo = valor["activa"]
                ultima_respuesta = ""
                salida.configure(state="normal")
                salida.delete("1.0", "end")
                salida.configure(state="disabled")
                cambiar_estado("Disponible")
                for turno in valor["turnos"]:
                    agregar_turno("Tú" if turno["rol"] == "usuario" else "Cerebro", turno["texto"])
                aviso.set("")
            elif tipo == "dictado":
                cambiar_estado("Disponible")
                if valor:
                    entrada.delete(0, "end")
                    entrada.insert(0, valor)
                    entrada.focus_set()
                    aviso.set("Revisa lo que has dictado y pulsa Enter para enviarlo.")
                else:
                    aviso.set("No reconocí palabras. Puedes volver a dictar o escribir tu petición.")
            elif tipo == "error de voz":
                aviso.set(valor)
                cambiar_estado("Disponible")
            elif tipo == "audio listo":
                cambiar_estado("Disponible")
            elif tipo == "dispositivos":
                cambiar_estado("Disponible")
                elegir_audio(valor)
        ventana.after(150, actualizar)

    def cerrar():
        cancelar_audio.set()
        detenido.set()
        ventana.destroy()

    boton_enviar = boton(compositor, "Enviar", enviar, "#245496")
    boton_enviar.pack(side="right")
    boton_dictar = boton(barra, "Dictar", dictar)
    boton_dictar.pack(side="left", padx=(0, 5))
    boton_leer = boton(barra, "Voz apagada", alternar_voz)
    boton_leer.pack(side="left", padx=(0, 5))
    barra_chat = tk.Frame(contenido, bg=fondo)
    barra_chat.pack(fill="x", pady=(5, 0))
    boton_nuevo = boton(barra_chat, "Nuevo chat", gestionar_chat)
    boton_nuevo.pack(side="left", padx=(0, 5))
    boton_borrar = boton(barra_chat, "Eliminar chat", lambda: gestionar_chat(borrar=True))
    boton_borrar.pack(side="left")
    entrada.bind("<Return>", enviar)

    accesos = tk.Menubutton(barra, text="Accesos ▾", bg=panel, fg=texto,
                            activebackground="#315484", activeforeground=texto,
                            takefocus=True, padx=9, pady=5)
    menu_acciones = tk.Menu(accesos, tearoff=False, bg=panel, fg=texto,
                           activebackground="#315484", activeforeground=texto)
    for nombre, accion in (("Chat web", lambda: abrir(sesion, "chat")), ("Studio", lanzar_estudio),
                           ("Terminal", lanzar_terminal), ("Universe", lanzar_universe)):
        menu_acciones.add_command(label=nombre, command=accion)
    menu_acciones.add_separator()
    menu_acciones.add_command(label="Copiar respuesta", command=copiar_respuesta)
    menu_acciones.add_command(label="Elegir audio", command=audio)
    accesos.configure(menu=menu_acciones)
    accesos.pack(side="right")
    ventana.bind("<Escape>", lambda _evento: alternar_panel() if not compacto else None)
    ventana.protocol("WM_DELETE_WINDOW", cerrar)
    Thread(target=observar, daemon=True).start()
    ventana.after(150, actualizar)
    ventana.mainloop()


def abrir_studio_local(sesion, vista="proyecto"):
    from universe.studio import abrir_studio

    directorio = carpeta()
    solicitud = directorio / "studio.mostrar"
    with (directorio / "studio.lock").open("a") as cerrojo:
        try:
            fcntl.flock(cerrojo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            temporal = directorio / f"studio.{os.getpid()}.tmp"
            temporal.write_text(vista, encoding="ascii")
            temporal.replace(solicitud)
            return
        solicitud.unlink(missing_ok=True)
        lanzar_acompanante()
        abrir_studio(sesion, solicitud=solicitud, inicial=vista)


def apagar():
    registro = carpeta() / "sesion.json"
    if registro.is_file():
        try:
            api(json.loads(registro.read_text()), "apagar", {}, tiempo=2)
        finally:
            registro.unlink(missing_ok=True)


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "terminal"
    if modo == "_nucleo":
        nucleo()
        return 0
    if modo not in {"terminal", "escritorio", "chat", "studio", "universe", "apagar", "_escritorio"}:
        print("Uso: cerebro [terminal|escritorio|chat|studio|universe|apagar]")
        return 0 if modo in {"-h", "--help"} else 2
    try:
        if modo == "apagar":
            apagar()
        elif modo == "escritorio":
            if not lanzar_acompanante():
                raise RuntimeError("Se necesita una sesión gráfica para abrir el acompañante.")
        elif modo == "_escritorio":
            with (carpeta() / "avatar.lock").open("a") as cerrojo:
                try:
                    fcntl.flock(cerrojo, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return 0
                escritorio(conectar())
        else:
            sesion = conectar()
            if modo == "terminal":
                terminal(sesion)
            elif modo in ("studio", "universe"):
                abrir_studio_local(sesion, vista="universe" if modo == "universe" else "proyecto")
            elif not abrir(sesion, modo):
                raise RuntimeError("No se pudo abrir el navegador predeterminado.")
    except (OSError, ImportError, RuntimeError, ValueError) as exc:
        print(f"Cerebro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
