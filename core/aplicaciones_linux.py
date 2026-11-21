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


def aplicaciones_compatibles(ruta):
    return _gio("compatibles", str(ruta))


def abrir_url(url):
    return _gio("url", url)


def navegador_predeterminado():
    return _gio("navegador")


def lanzar_aplicacion(identificador):
    return _gio("lanzar", identificador)


def _datos(app):
    if app is None:
        return None
    return {
        "nombre": app.get_display_name(),
        "id": app.get_id(),
        "formatos": sorted(app.get_supported_types() or ()),
        "ejecutable": Path(app.get_executable()).name,
        "clase": (app.get_startup_wm_class() or "") if hasattr(app, "get_startup_wm_class") else "",
        "alias": list(app.get_keywords() or ()) if hasattr(app, "get_keywords") else [],
        "categorias": (app.get_categories() or "").split(";") if hasattr(app, "get_categories") else [],
    }


def _ejecutar(accion, valor):
    # El Python del sistema dispone de los enlaces de GIO aunque el entorno virtual esté aislado.
    from gi.repository import Gio, GLib

    if accion == "url":
        try:
            return bool(Gio.AppInfo.launch_default_for_uri(valor, None))
        except GLib.Error:
            return False

    if accion == "navegador":
        app = Gio.AppInfo.get_default_for_uri_scheme("https")
        if app and app.get_id() == "xfce4-web-browser.desktop":
            ruta = Path(GLib.get_user_config_dir()) / "xfce4" / "helpers.rc"
            try:
                preferido = next((linea.partition("=")[2].strip()
                                  for linea in ruta.read_text().splitlines()
                                  if linea.startswith("WebBrowser=")), "")
            except (OSError, UnicodeError):
                preferido = ""
            concreto = Gio.DesktopAppInfo.new(preferido + ".desktop") if preferido else None
            if concreto:
                app = concreto
        return _datos(app)

    if accion == "listar":
        return sorted((_datos(app) for app in Gio.AppInfo.get_all() if app.should_show()),
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
    if accion == "compatibles":
        return {"formato": formato, "aplicaciones": [app.get_display_name()
                for app in Gio.AppInfo.get_all_for_type(formato) if app.should_show()][:20]}
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

    if len(sys.argv) != 3 or sys.argv[1] not in {"listar", "abrir", "lanzar", "compatibles", "navegador", "url"}:
        sys.exit(2)
    print(json.dumps(_ejecutar(*sys.argv[1:]), ensure_ascii=False))
