"""Gestión de ventanas de la sesión XFCE/X11 por identificador EWMH."""
import os
import re
from shutil import which
import subprocess
from time import sleep


def _ejecutar(programa, *argumentos):
    ejecutable = which(programa)
    if not ejecutable:
        raise RuntimeError(f"Instala {programa} para gestionar ventanas en X11.")
    try:
        return subprocess.run([ejecutable, *argumentos], capture_output=True, text=True,
                              timeout=3, check=True).stdout
    except subprocess.SubprocessError as exc:
        raise RuntimeError("El gestor de ventanas rechazó la solicitud.") from exc


def listar():
    tipo = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if tipo == "wayland" or (not tipo and os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("El control de ventanas requiere X11. Wayland necesita un adaptador de su compositor.")
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("No hay una sesión gráfica X11.")
    ventanas = []
    for linea in _ejecutar("wmctrl", "-lpx").splitlines():
        partes = linea.split(maxsplit=5)
        if len(partes) >= 5 and re.fullmatch(r"0x[0-9a-fA-F]+", partes[0]):
            identificador, _, proceso, clase, _ = partes[:5]
            titulo = partes[5] if len(partes) == 6 else clase
            ventanas.append({"id": identificador, "pid": proceso, "clase": clase, "titulo": titulo})
    return ventanas


def activa(ventanas=None):
    if ventanas is None:
        ventanas = listar()
    salida = _ejecutar("xprop", "-root", "_NET_ACTIVE_WINDOW")
    valor = re.search(r"window id # (0x[0-9a-fA-F]+)", salida)
    if valor:
        return next((v for v in ventanas if int(v["id"], 16) == int(valor[1], 16)), None)
    return None


def actuar(accion, ventana):
    def buscar():
        return next((v for v in listar() if v["id"] == ventana["id"]), None)

    presente = buscar()
    if not presente or (presente["pid"], presente["clase"]) != (ventana["pid"], ventana["clase"]):
        raise RuntimeError("La ventana seleccionada ya cambió. Vuelve a elegirla.")
    identificador = presente["id"]
    if accion == "cierra":
        _ejecutar("wmctrl", "-ic", identificador)
        for _ in range(5):
            if buscar() is None:
                return True
            sleep(.12)
        return False
    maximizada = {"_NET_WM_STATE_MAXIMIZED_VERT", "_NET_WM_STATE_MAXIMIZED_HORZ"}
    if accion == "enfoca":
        _ejecutar("wmctrl", "-ia", identificador)
    elif accion == "minimiza":
        _ejecutar("xdotool", "windowminimize", str(int(identificador, 16)))
    elif accion in {"maximiza", "restaura"}:
        if accion == "restaura":
            _ejecutar("wmctrl", "-ia", identificador)
        cambio = "add" if accion == "maximiza" else "remove"
        _ejecutar("wmctrl", "-ir", identificador, "-b", f"{cambio},maximized_vert,maximized_horz")
    else:
        raise ValueError("Acción de ventana desconocida.")

    for _ in range(5):
        if accion == "enfoca":
            enfocada = activa()
            if enfocada and enfocada["id"] == identificador:
                return True
        else:
            estado = set(re.findall(r"_NET_WM_STATE_[A-Z_]+",
                                    _ejecutar("xprop", "-id", identificador, "_NET_WM_STATE")))
            if accion == "minimiza" and "_NET_WM_STATE_HIDDEN" in estado:
                return True
            if accion == "maximiza" and maximizada <= estado:
                return True
            if accion == "restaura" and not estado.intersection(maximizada | {"_NET_WM_STATE_HIDDEN"}):
                return True
        sleep(.12)
    return False
