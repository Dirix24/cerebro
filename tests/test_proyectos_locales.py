"""Creación de proyectos: confinamiento, no sobrescritura y sintaxis."""
import ast
from pathlib import Path

import pytest

from core.proyectos_locales import crear_proyecto


@pytest.mark.parametrize("tipo", ["cli", "biblioteca"])
def test_crear_proyecto_python_valido(tmp_path, tipo):
    resultado = crear_proyecto("mi_proyecto", tipo, raiz=tmp_path)
    carpeta = Path(resultado["ruta"])
    assert carpeta.parent == tmp_path
    for relativo in resultado["archivos"]:
        archivo = carpeta / relativo
        assert archivo.is_file()
        if archivo.suffix == ".py":
            ast.parse(archivo.read_text(encoding="utf-8"))


@pytest.mark.parametrize("nombre", ["../escape", "..", "a/b", "x y", ""])
def test_rechaza_rutas_inseguras(tmp_path, nombre):
    with pytest.raises(ValueError):
        crear_proyecto(nombre, raiz=tmp_path)


def test_no_sobrescribe_proyecto_existente(tmp_path):
    crear_proyecto("demo", raiz=tmp_path)
    archivo = tmp_path / "demo" / "main.py"
    archivo.write_text("personalizado", encoding="utf-8")
    with pytest.raises(FileExistsError):
        crear_proyecto("demo", raiz=tmp_path)
    assert archivo.read_text(encoding="utf-8") == "personalizado"


def test_rechaza_enlace_simbolico(tmp_path):
    destino = tmp_path / "otro"
    destino.mkdir()
    (tmp_path / "demo").symlink_to(destino, target_is_directory=True)
    with pytest.raises(FileExistsError):
        crear_proyecto("demo", raiz=tmp_path)
