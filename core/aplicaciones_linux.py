"""Adaptador de la sesión gráfica Linux y sus asociaciones MIME."""
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryFile


def _gio(accion, valor=""):
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("Necesito una sesión gráfica de Linux.")
    try:
        with TemporaryFile() as salida:
            subprocess.run(
                ["/usr/bin/python3", "-I", str(Path(__file__).resolve()), accion, valor],
                stdin=subprocess.DEVNULL, stdout=salida, stderr=subprocess.DEVNULL,
                timeout=7, check=True,
            )
            salida.seek(0)
            return json.load(salida)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise RuntimeError("No pude consultar el escritorio. Comprueba que python3-gi está instalado.") from exc


def listar():
    return _gio("listar")


def abrir_documento(ruta):
    return _gio("abrir", str(ruta))


def lanzar_aplicacion(identificador):
    return _gio("lanzar", identificador)


def _ejecutar(accion, valor):
    # El Python del sistema dispone de los enlaces de GIO aunque el entorno virtual esté aislado.
    from gi.repository import Gio, GLib

    if accion == "listar":
        return sorted(({
            "nombre": app.get_display_name(),
            "id": app.get_id(),
            "formatos": sorted(app.get_supported_types() or ()),
        } for app in Gio.AppInfo.get_all() if app.should_show()),
            key=lambda app: (app["nombre"].casefold(), app["id"] or ""))

    if accion == "lanzar":
        aplicacion = next((app for app in Gio.AppInfo.get_all()
                          if app.should_show() and app.get_id() == valor), None)
        if aplicacion is None:
            return False
        try:
            return bool(aplicacion.launch([], None))
        except GLib.Error:
            return False

    archivo = Gio.File.new_for_path(valor)
    formato, _ = Gio.content_type_guess(archivo.get_basename(), None)
    aplicacion = Gio.AppInfo.get_default_for_type(formato, False)
    if aplicacion is None:
        return {"formato": formato, "aceptado": False, "aplicacion": None}
    try:
        aceptado = aplicacion.launch([archivo], None)
    except GLib.Error:
        aceptado = False
    return {"formato": formato, "aceptado": aceptado, "aplicacion": aplicacion.get_display_name()}


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3 or sys.argv[1] not in {"listar", "abrir", "lanzar"}:
        sys.exit(2)
    print(json.dumps(_ejecutar(*sys.argv[1:]), ensure_ascii=False))
