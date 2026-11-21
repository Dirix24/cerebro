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
    motor = Nucleo("local", modelo=modelo, meta=meta, internet=internet, investigar_auto=internet)
    token = secrets.token_urlsafe(32)
    with crear_servidor(0, motor, token, permitir_cierre=True, abrir_estudio=lanzar_estudio,
                         abrir_terminal=lanzar_terminal, mostrar_acompanante=lanzar_acompanante,
                         abrir_destino=lanzar_destino) as servidor:
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
    destinos = {"navegador": "about:blank", "youtube": "https://www.youtube.com/"}
    return bool(_hay_escritorio() and destino in destinos and abrir_web(destinos[destino]))


def _hay_escritorio():
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _lanzar_proceso(comando):
    with (carpeta() / "nucleo.log").open("ab") as log:
        subprocess.Popen(comando, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    return True


def lanzar_acompanante():
    if not _hay_escritorio():
        return False
    return _lanzar_proceso([sys.executable, "-m", "universe.lanzador", "escritorio"])


def lanzar_estudio():
    if not _hay_escritorio():
        return False
    return _lanzar_proceso([sys.executable, "-m", "universe.lanzador", "studio"])


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
    acento = "\033[38;5;79m" if sys.stdout.isatty() and not os.environ.get("NO_COLOR") else ""
    fin = "\033[0m" if acento else ""
    print(f"{acento}╭─ Cerebro · Terminal ──────────────────╮{fin}")
    print("  Programación · Revisa un archivo, pide una función o abre Studio.")
    print("  «Salir» devuelve el foco al acompañante.")
    try:
        for turno in api(sesion, "historial")["turnos"][-4:]:
            print(f"{'Tú' if turno['rol'] == 'usuario' else 'Cerebro'} · {turno['texto']}")
        while True:
            entrada = input(f"{acento}❯{fin} ").strip()
            if entrada.casefold() in {"salir", "/salir", "adiós", "adios"}:
                break
            if not entrada:
                continue
            try:
                presencia(True, enfocar=True)
                respuesta = api(sesion, "chat", {"mensaje": entrada, "modo": "terminal"})
                print(respuesta["respuesta"])
                if respuesta.get("abrir") == "studio":
                    abrir(sesion, "studio")
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

    try:
        ventana = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError("Se necesita una sesión gráfica con Tk para abrir el acompañante.") from exc
    ventana.title("Cerebro · Escritorio")
    ventana.configure(bg="#102027")
    ventana.resizable(False, False)
    ventana.attributes("-topmost", True)
    x = max(0, ventana.winfo_screenwidth() - 370)
    y = max(0, ventana.winfo_screenheight() - 398)
    ventana.geometry(f"340x367+{x}+{y}")

    from universe.orbita import Orbita
    nucleo_visual = Orbita(ventana)
    nucleo_visual.pack()

    salida = tk.Text(ventana, height=5, wrap="word", bg="#142b32", fg="#e4fffa", relief="flat",
                     padx=7, pady=4)
    salida.pack(fill="x", padx=12)
    salida.insert("1.0", "¿Qué quieres hacer? Puedes pedirme que investigue, recuerde algo o te ayude a programar.")
    salida.configure(state="disabled")
    entrada = tk.Entry(ventana, bg="#142b32", fg="#e4fffa", insertbackground="white")
    entrada.pack(fill="x", padx=12, pady=6)
    barra_voz = tk.Frame(ventana, bg="#102027")
    barra_voz.pack()
    ultima_respuesta = ""
    ocupado = False
    barra = tk.Frame(ventana, bg="#102027")
    barra.pack()
    eventos = queue.SimpleQueue()
    detenido = Event()

    def observar():
        while not detenido.is_set():
            try:
                eventos.put(("vista", api(sesion, "interfaz", tiempo=2)["activa"]))
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
                salida = api(sesion, "chat", {"mensaje": mensaje})
            except OSError:
                sesion.update(conectar())
                salida = api(sesion, "chat", {"mensaje": mensaje})
            eventos.put(("respuesta", salida["respuesta"]))
            if salida.get("abrir") == "studio":
                abrir(sesion, "studio")
        except (OSError, RuntimeError) as exc:
            eventos.put(("respuesta", str(exc)))

    def cambiar_estado(texto):
        nonlocal ocupado
        ocupado = texto != "Disponible"
        nucleo_visual.estado(texto)
        estado = "disabled" if ocupado else "normal"
        entrada.configure(state=estado)
        boton_dictar.configure(state=estado)
        boton_leer.configure(state=estado if ultima_respuesta else "disabled")

    def enviar(_evento=None):
        texto = entrada.get().strip()
        if texto and not ocupado:
            entrada.delete(0, "end")
            cambiar_estado("Procesando")
            Thread(target=despachar, args=(texto,), daemon=True).start()

    def tarea_de_voz(operacion, tipo):
        try:
            eventos.put((tipo, operacion()))
        except (OSError, RuntimeError, ValueError) as exc:
            eventos.put(("error de voz", str(exc)))

    def dictar():
        from core.local_voice import dictar as grabar
        cambiar_estado("Escuchando")
        Thread(target=tarea_de_voz, args=(grabar, "dictado"), daemon=True).start()

    def leer():
        from core.local_voice import leer_en_espanol
        texto = ultima_respuesta
        cambiar_estado("Hablando")
        Thread(target=tarea_de_voz, args=(lambda: leer_en_espanol(texto), "audio listo"), daemon=True).start()

    def mostrar_texto(texto):
        salida.configure(state="normal")
        salida.delete("1.0", "end")
        salida.insert("end", texto)
        salida.configure(state="disabled")

    def actualizar():
        nonlocal ultima_respuesta
        while not eventos.empty():
            tipo, valor = eventos.get()
            if tipo == "vista":
                if valor == "escritorio" and ventana.state() == "withdrawn":
                    ventana.deiconify()
                elif valor != "escritorio" and ventana.state() != "withdrawn":
                    ventana.withdraw()
            elif tipo == "respuesta":
                ultima_respuesta = valor
                mostrar_texto(valor)
                cambiar_estado("Disponible")
            elif tipo == "dictado":
                cambiar_estado("Disponible")
                if valor:
                    entrada.delete(0, "end")
                    entrada.insert(0, valor)
                    entrada.focus_set()
                    mostrar_texto("Revisa lo que has dictado y pulsa Enter para enviarlo.")
                else:
                    mostrar_texto("No reconocí palabras. Puedes volver a dictar o escribir tu petición.")
            elif tipo == "error de voz":
                mostrar_texto(valor)
                cambiar_estado("Disponible")
            elif tipo == "audio listo":
                cambiar_estado("Disponible")
        ventana.after(150, actualizar)

    def cerrar():
        detenido.set()
        ventana.destroy()

    boton_dictar = tk.Button(barra_voz, text="Dictar · 5 s", command=dictar, bg="#25434b",
                             fg="#e6faf5", relief="flat", padx=10, pady=4)
    boton_leer = tk.Button(barra_voz, text="Leer respuesta", command=leer, bg="#25434b",
                           fg="#e6faf5", relief="flat", padx=10, pady=4, state="disabled")
    boton_dictar.pack(side="left", padx=4, pady=(0, 4))
    boton_leer.pack(side="left", padx=4, pady=(0, 4))
    entrada.bind("<Return>", enviar)
    for nombre, accion in (("Chat web", lambda: abrir(sesion, "chat")), ("Studio", lanzar_estudio),
                           ("Terminal", lanzar_terminal), ("Universe", lambda: abrir(sesion, "universe"))):
        tk.Button(barra, text=nombre, command=accion, bg="#25434b", fg="#e6faf5",
                  activebackground="#38635f", activeforeground="#ffffff", relief="flat",
                  padx=9, pady=5, borderwidth=0).pack(side="left", padx=4)
    ventana.protocol("WM_DELETE_WINDOW", cerrar)
    Thread(target=observar, daemon=True).start()
    ventana.after(150, actualizar)
    ventana.mainloop()


def abrir_studio_local(sesion):
    from universe.studio import abrir_studio

    directorio = carpeta()
    solicitud = directorio / "studio.mostrar"
    with (directorio / "studio.lock").open("a") as cerrojo:
        try:
            fcntl.flock(cerrojo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            solicitud.touch(mode=0o600)
            return
        solicitud.unlink(missing_ok=True)
        lanzar_acompanante()
        abrir_studio(sesion, solicitud=solicitud)


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
    if modo not in {"terminal", "escritorio", "chat", "studio", "universe", "apagar"}:
        print("Uso: cerebro [terminal|escritorio|chat|studio|universe|apagar]")
        return 0 if modo in {"-h", "--help"} else 2
    try:
        if modo == "apagar":
            apagar()
        elif modo == "escritorio":
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
            elif modo == "studio":
                abrir_studio_local(sesion)
            elif not abrir(sesion, modo):
                raise RuntimeError("No se pudo abrir el navegador predeterminado.")
    except (OSError, ImportError, RuntimeError, ValueError) as exc:
        print(f"Cerebro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
