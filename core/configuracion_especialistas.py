"""Rutas de adaptadores locales seleccionadas durante la instalación."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import config

MODULOS = {"CAZEL": "cazel/especialista.py", "DARAS": "especialista.py"}


def _ruta():
    return Path(config.raiz_datos()) / "data" / "especialistas-locales.json"


def leer():
    ruta = _ruta()
    try:
        if ruta.is_symlink() or ruta.parent.is_symlink() or ruta.stat().st_size > 8192:
            return {}
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def obtener(clave):
    valor = os.environ.get("CEREBRO_" + clave) or leer().get(clave)
    return valor if isinstance(valor, str) and valor else None


def configurar(cazel=None, daras=None, proyecto=None):
    nuevos = {}
    for region, carpeta in (("CAZEL", cazel), ("DARAS", daras)):
        if carpeta:
            raiz = Path(carpeta).expanduser().resolve(strict=True)
            if not (raiz / MODULOS[region]).is_file():
                raise ValueError(f"No encuentro el adaptador v1 de {region} en la ruta indicada.")
            nuevos[region + "_RAIZ"] = str(raiz)
    if proyecto:
        raiz = Path(proyecto).expanduser().resolve(strict=True)
        if not raiz.is_dir() or raiz in {Path.home().resolve(), Path(raiz.anchor)}:
            raise ValueError("Selecciona una carpeta concreta de proyecto para CAZEL.")
        nuevos["CAZEL_PROYECTO"] = str(raiz)
    ruta = _ruta()
    if ruta.parent.is_symlink() or ruta.is_symlink():
        raise PermissionError("La configuración de especialistas requiere datos locales.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=ruta.parent, delete=False) as archivo:
        temporal = Path(archivo.name)
        json.dump({**leer(), **nuevos}, archivo)
    try:
        temporal.replace(ruta)
    finally:
        temporal.unlink(missing_ok=True)
