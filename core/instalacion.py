"""Instalación y desinstalación local sin permisos de administrador.

Nunca elimina el repositorio ni datos personales automáticamente.
"""
from pathlib import Path
import shutil
import sys
import venv

ENTORNOS = (".venv", ".cerebro-env")
DATOS = ("data", "checkpoints", "learning", "memory", "universe-datos")


def instalar(raiz, avanzado=False, ejecutar=None, *, sin_red=False, ruedas=None):
    import os
    import subprocess
    opciones = []
    if ruedas is not None:
        carpeta = Path(ruedas).expanduser().resolve(strict=True)
        if not carpeta.is_dir() or not sin_red:
            raise ValueError("Indica una carpeta local de ruedas junto con --sin-red.")
        opciones = ["--find-links", carpeta.as_uri()]
    if sin_red:
        opciones += ["--no-index", "--disable-pip-version-check", "--only-binary=:all:"]
        if ejecutar is None:
            entorno_pip = {nombre: valor for nombre, valor in os.environ.items() if not nombre.startswith("PIP_")}
            entorno_pip["PIP_CONFIG_FILE"] = os.devnull

            def ejecutar(comando):
                return subprocess.call(comando, env=entorno_pip)
    raiz = Path(raiz).resolve()
    entorno = raiz / ".venv"
    python = entorno / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if entorno.is_symlink() or python.is_file() and not (entorno / "pyvenv.cfg").is_file():
        raise ValueError("La ruta .venv debe ser un entorno virtual local de Cerebro.")
    if not python.is_file():
        venv.EnvBuilder(with_pip=True, symlinks=sys.platform != "win32").create(str(entorno))
    ejecutar = ejecutar or subprocess.call
    codigo = ejecutar([str(python), "-m", "pip", "install", *opciones, "-r", str(raiz / "requirements.txt")])
    if codigo:
        return codigo
    if avanzado:
        # Optativo: PyTorch puede ser una descarga grande; no es necesario para iniciar.
        codigo = ejecutar([str(python), "-m", "pip", "install", *opciones, "-r",
                           str(raiz / "requirements-avanzado.txt")])
    return codigo


def desinstalar(raiz, confirmar=False, borrar_datos=False, confirmacion_datos=""):
    """Solo borra directorios propios dentro de la raíz; no borra el código."""
    raiz = Path(raiz).resolve()
    if not confirmar:
        return {"eliminados": [], "requiere_confirmacion": True}
    if borrar_datos and confirmacion_datos != "BORRAR MIS DATOS":
        raise ValueError("Para borrar datos escribe exactamente BORRAR MIS DATOS")
    nombres = list(ENTORNOS) + (list(DATOS) if borrar_datos else [])
    eliminados = []
    for nombre in nombres:
        destino = raiz / nombre
        if destino.is_symlink():
            raise ValueError("No se eliminan enlaces simbólicos")
        if destino.is_dir():
            shutil.rmtree(destino)
            eliminados.append(nombre)
    return {"eliminados": eliminados, "datos_conservados": not borrar_datos,
            "codigo_conservado": True}
