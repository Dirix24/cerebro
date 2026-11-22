"""Adaptador AT-SPI acotado a casillas visibles de una ventana X11."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys


def _consultar(ventana, objetivo=None):
    from core.ventanas_x11 import estado_observable

    estado_observable(ventana)
    pid = ventana["pid"]
    if not pid.isdigit() or int(pid) <= 1:
        raise RuntimeError("AT-SPI necesita una ventana con proceso identificado.")
    try:
        resultado = subprocess.run(
            ["/usr/bin/python3", "-I", str(Path(__file__).resolve())],
            input=json.dumps([int(pid), ventana["titulo"], objetivo]),
            capture_output=True, text=True, timeout=3, check=True,
        )
        dato = json.loads(resultado.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise RuntimeError("No se pudo consultar el árbol accesible de la ventana.") from exc
    if "error" in dato:
        raise RuntimeError(dato["error"])
    return dato["resultado"]


def estado(ventana):
    return _consultar(ventana)


def ejecutar(ventana, objetivo):
    return _consultar(ventana, objetivo)


def selector(objetivo):
    datos = json.loads(objetivo)
    if (not isinstance(datos, list) or len(datos) != 4 or not isinstance(datos[0], str)
            or not 0 < len(datos[0]) <= 120 or not isinstance(datos[1], str)
            or not re.fullmatch(r"[0-9a-f]{64}", datos[1])
            or any(type(v) is not bool for v in datos[2:]) or datos[2] == datos[3]):
        raise ValueError("Selector de casilla inválido.")
    return datos


def _procesar(pid, titulo, objetivo):
    import gi

    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi

    Atspi.set_timeout(650, 650)
    Atspi.init()
    escritorio = Atspi.get_desktop(0)
    ramas = []
    for indice in range(min(escritorio.get_child_count(), 96)):
        app = escritorio.get_child_at_index(indice)
        if app is None or app.get_process_id() != pid:
            continue
        for j in range(min(40, app.get_child_count())):
            hija = app.get_child_at_index(j)
            if hija and hija.get_role() == Atspi.Role.FRAME and hija.get_name() == titulo:
                ramas.append(hija)
    if len(ramas) != 1:
        raise RuntimeError("No identifiqué un marco accesible único para esa ventana.")
    controles = {}
    duplicados = set()
    cola = [ramas[0]]
    for _ in range(220):
        if not cola:
            break
        nodo = cola.pop()
        if nodo is None:
            continue
        rol = nodo.get_role()
        if rol in {Atspi.Role.PASSWORD_TEXT, Atspi.Role.DIALOG, Atspi.Role.ENTRY, Atspi.Role.TEXT}:
            continue
        if rol == Atspi.Role.CHECK_BOX:
            estados = nodo.get_state_set()
            if not estados.contains(Atspi.StateType.SHOWING) or not estados.contains(Atspi.StateType.ENABLED):
                continue
            nombre = nodo.get_name()
            if not nombre or len(nombre) > 80 or re.search(
                    r"contrase|password|token|secreto|borr|elimin|credencial|pago|autoriz|permiso", nombre, re.I):
                continue
            clave = sha256(nombre.strip().casefold().encode()).hexdigest()
            if clave in controles:
                duplicados.add(clave)
            controles[clave] = (nodo, estados.contains(Atspi.StateType.CHECKED))
        cola.extend(nodo.get_child_at_index(i) for i in range(min(nodo.get_child_count(), 40)))
    for clave in duplicados:
        controles.pop(clave, None)
    if objetivo is None:
        return {clave: marcado for clave, (_, marcado) in controles.items()}
    _, clave, antes, despues = selector(objetivo)
    if clave not in controles or controles[clave][1] != antes:
        raise RuntimeError("La casilla no es única o su estado inicial cambió.")
    nodo = controles[clave][0]
    interfaz = nodo.get_action_iface()
    if interfaz is None or interfaz.get_n_actions() != 1 or not interfaz.do_action(0):
        raise RuntimeError("La casilla no aceptó la acción accesible.")
    from time import monotonic, sleep

    limite = monotonic() + 1
    while monotonic() < limite:
        estados = nodo.get_state_set()
        if estados.contains(Atspi.StateType.SHOWING) and estados.contains(Atspi.StateType.CHECKED) == despues:
            return True
        sleep(.08)
    return False


def indicador():
    return subprocess.Popen(["/usr/bin/python3", "-I", str(Path(__file__).resolve()), "--indicador"],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _mostrar_indicador():
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    ventana = Gtk.Window(title="Cerebro está observando")
    ventana.set_keep_above(True)
    ventana.set_accept_focus(False)
    ventana.set_default_size(240, 64)
    boton = Gtk.Button(label="● Observando · Detener")
    boton.connect("clicked", Gtk.main_quit)
    ventana.connect("destroy", Gtk.main_quit)
    ventana.add(boton)
    ventana.show_all()
    Gtk.main()


if __name__ == "__main__":
    if sys.argv[1:] == ["--indicador"]:
        _mostrar_indicador()
        sys.exit(0)
    try:
        print(json.dumps({"resultado": _procesar(*json.load(sys.stdin))}))
    except Exception as exc:
        print(json.dumps({"error": str(exc) if isinstance(exc, (RuntimeError, ValueError))
                          else "AT-SPI no pudo verificar el estado solicitado."}))
