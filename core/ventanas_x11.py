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
                              timeout=3, check=True, env={**os.environ, "LC_ALL": "C"}).stdout
    except (OSError, subprocess.SubprocessError) as exc:
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


def admite_cierre_general(ventana):
    """La lista EWMH también contiene ventanas especiales del escritorio."""
    if not ventana["pid"].isdigit() or int(ventana["pid"]) <= 1:
        return False
    propiedades = _ejecutar("xprop", "-id", ventana["id"],
                            "_NET_WM_WINDOW_TYPE", "WM_TRANSIENT_FOR")
    tipo = re.search(r"^_NET_WM_WINDOW_TYPE\(ATOM\) = (.+)$", propiedades, re.M)
    transitoria = re.search(r"^WM_TRANSIENT_FOR\(WINDOW\):", propiedades, re.M)
    return bool(tipo and tipo[1].strip() == "_NET_WM_WINDOW_TYPE_NORMAL" and not transitoria)


def activa(ventanas=None):
    if ventanas is None:
        ventanas = listar()
    salida = _ejecutar("xprop", "-root", "_NET_ACTIVE_WINDOW")
    valor = re.search(r"window id # (0x[0-9a-fA-F]+)", salida)
    if valor:
        return next((v for v in ventanas if int(v["id"], 16) == int(valor[1], 16)), None)
    return None


def clase_activa():
    """Lee solo WM_CLASS de la ventana enfocada, sin consultar títulos."""
    tipo = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if not os.environ.get("DISPLAY") or tipo == "wayland" or (not tipo and os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("Los hábitos de ventanas requieren una sesión X11.")
    salida = _ejecutar("xprop", "-root", "_NET_ACTIVE_WINDOW")
    valor = re.search(r"window id # (0x[0-9a-fA-F]+)", salida)
    if not valor or int(valor[1], 16) == 0:
        return None
    propiedad = _ejecutar("xprop", "-id", valor[1], "WM_CLASS")
    clase = re.fullmatch(r'WM_CLASS\(STRING\) = "[^"]*", "([a-zA-Z0-9_-]{1,40})"\s*', propiedad)
    return clase[1].casefold() if clase else None


def _geometria(identificador):
    informe = _ejecutar("xwininfo", "-id", identificador)
    valores = []
    for clave in ("Absolute upper-left X", "Absolute upper-left Y", "Width", "Height"):
        dato = re.search(rf"^\s*{clave}:\s*(-?\d+)$", informe, re.M)
        if not dato:
            raise RuntimeError("X11 no devolvió la geometría de la ventana.")
        valores.append(int(dato[1]))
    propiedad = _ejecutar("xprop", "-id", identificador, "_NET_FRAME_EXTENTS")
    marco = re.search(r"= (\d+), (\d+), (\d+), (\d+)", propiedad)
    bordes = tuple(map(int, marco.groups())) if marco else (0, 0, 0, 0)
    return tuple(valores), bordes


def _area_trabajo(geometria):
    propiedades = _ejecutar("xprop", "-root", "_NET_CURRENT_DESKTOP", "_NET_WORKAREA")
    escritorio = re.search(r"_NET_CURRENT_DESKTOP.+?= (\d+)", propiedades)
    areas = re.search(r"_NET_WORKAREA.+?= ([\d, -]+)", propiedades)
    if not escritorio or not areas:
        raise RuntimeError("El gestor de ventanas no informó del área de trabajo.")
    inicio = 4 * int(escritorio[1])
    coordenadas = [int(dato) for dato in re.findall(r"-?\d+", areas[1])]
    if len(coordenadas) < inicio + 4:
        raise RuntimeError("No identifiqué el área de trabajo de este escritorio.")
    x, y, ancho, alto = coordenadas[inicio:inicio + 4]
    gx, gy, gw, gh = geometria
    monitores = _ejecutar("xrandr", "--listactivemonitors")
    for w, h, mx, my in re.findall(r"(\d+)/\d+x(\d+)/\d+(\+?-?\d+)(\+?-?\d+)", monitores):
        w, h, mx, my = map(lambda valor: int(valor.removeprefix("+")), (w, h, mx, my))
        if mx <= gx + gw / 2 < mx + w and my <= gy + gh / 2 < my + h:
            izquierda, arriba = max(x, mx), max(y, my)
            return izquierda, arriba, min(x + ancho, mx + w) - izquierda, min(y + alto, my + h) - arriba
    raise RuntimeError("No pude identificar el monitor donde se encuentra la ventana.")


def _colocar(identificador, lado, area=None):
    if area is None:
        geometria, _ = _geometria(identificador)
        area = _area_trabajo(geometria)
    x, y, ancho, alto = area
    _ejecutar("wmctrl", "-ia", identificador)
    _ejecutar("wmctrl", "-ir", identificador, "-b", "remove,maximized_vert,maximized_horz")
    mitad = ancho // 2
    if lado == "derecha":
        x += mitad
        mitad = ancho - mitad
    for _ in range(5):
        _, (izq, der, arriba, abajo) = _geometria(identificador)
        medida = (x, y, mitad - izq - der, alto - arriba - abajo)
        if min(medida[2:]) <= 0:
            raise RuntimeError("El área disponible es demasiado pequeña para colocar la ventana.")
        _ejecutar("wmctrl", "-ir", identificador, "-e", "0," + ",".join(map(str, medida)))
        sleep(.12)
        actual, bordes = _geometria(identificador)
        marco = (actual[0] - bordes[0], actual[1] - bordes[2], actual[2], actual[3])
        if all(abs(real - esperado) <= 4 for real, esperado in zip(marco, medida)):
            return True
    return False


def _vigente(ventana, ventanas):
    for actual in ventanas:
        if all(actual[campo] == ventana[campo] for campo in ("id", "pid", "clase")):
            return actual
    raise RuntimeError("La ventana seleccionada ya cambió. Vuelve a elegirla.")


def colocar_juntas(izquierda, derecha):
    if izquierda["id"] == derecha["id"]:
        raise ValueError("Elige dos ventanas distintas.")
    ventanas = listar()
    izquierda = _vigente(izquierda, ventanas)
    derecha = _vigente(derecha, ventanas)
    geometria, _ = _geometria(izquierda["id"])
    area = _area_trabajo(geometria)
    resultados = []
    for lado, ventana in (("izquierda", izquierda), ("derecha", derecha)):
        try:
            _vigente(ventana, listar())
            resultados.append(_colocar(ventana["id"], lado, area))
        except RuntimeError:
            resultados.append(False)
    return tuple(resultados)


def actuar(accion, ventana):
    presente = _vigente(ventana, listar())

    def buscar():
        return next((v for v in listar() if v["id"] == ventana["id"]), None)

    identificador = presente["id"]
    if accion in {"izquierda", "derecha"}:
        return _colocar(identificador, accion)
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


def estado_observable(ventana):
    """Lee solo los atributos de estado de la ventana previamente autorizada."""
    salida = _ejecutar("xprop", "-id", ventana["id"], "WM_CLASS", "_NET_WM_PID", "_NET_WM_STATE")
    clase = re.search(r'^WM_CLASS\(STRING\) = "([^"]+)", "([^"]+)"', salida, re.M)
    pid = re.search(r"^_NET_WM_PID\(CARDINAL\) = (\d+)", salida, re.M)
    if not clase or ".".join(clase.groups()) != ventana["clase"] or (
            ventana["pid"] not in {"0", pid[1] if pid else ""}):
        raise RuntimeError("La ventana autorizada cambió o dejó de estar disponible.")
    estado = set(re.findall(r"_NET_WM_STATE_[A-Z_]+", salida))
    enfocada = activa([ventana]) is not None
    return ("_NET_WM_STATE_HIDDEN" in estado,
            {"_NET_WM_STATE_MAXIMIZED_VERT", "_NET_WM_STATE_MAXIMIZED_HORZ"} <= estado,
            enfocada)
