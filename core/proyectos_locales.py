"""Creador conservador de proyectos Python, sin ejecutar código generado."""
import re
from pathlib import Path

import config

NOMBRE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")
PLANTILLAS = {
    "cli": {
        "README.md": "# {nombre}\n\nProyecto de línea de comandos en Python.\n\nEjecutar: `python main.py`\nProbar: `python -m unittest discover -s tests`\n",
        "main.py": '"""Aplicación CLI."""\n\ndef main():\n    print("Hola desde {nombre}")\n\n\nif __name__ == "__main__":\n    main()\n',
        "tests/test_main.py": 'import unittest\nfrom main import main\n\n\nclass TestMain(unittest.TestCase):\n    def test_main_existe(self):\n        self.assertTrue(callable(main))\n',
        ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
    },
    "biblioteca": {
        "README.md": "# {nombre}\n\nBiblioteca Python sin dependencias externas.\n\nPruebas: `python -m unittest discover -s tests`\n",
        "src/__init__.py": "",
        "src/operaciones.py": '"""Operaciones iniciales."""\n\ndef sumar(a, b):\n    return a + b\n',
        "tests/test_operaciones.py": 'import unittest\nfrom src.operaciones import sumar\n\n\nclass TestOperaciones(unittest.TestCase):\n    def test_suma(self):\n        self.assertEqual(sumar(2, 3), 5)\n',
        ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
    },
}


def crear_proyecto(nombre, tipo="cli", raiz=None):
    """Crea una plantilla nueva, sin sobrescribir proyectos ni seguir symlinks."""
    if not NOMBRE.fullmatch(nombre):
        raise ValueError("Nombre inválido: usa letras, números, guiones y guion bajo (máx. 50).")
    if tipo not in PLANTILLAS:
        raise ValueError("Tipo desconocido. Disponibles: " + ", ".join(PLANTILLAS))
    base = Path(raiz or config.WORKSPACE_DIR).resolve()
    base.mkdir(parents=True, exist_ok=True)
    destino = base / nombre
    # mkdir sin exist_ok evita sobrescritura, incluso de enlaces simbólicos.
    destino.mkdir()
    archivos = []
    for relativo, contenido in PLANTILLAS[tipo].items():
        archivo = destino / relativo
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido.replace("{nombre}", nombre), encoding="utf-8")
        archivos.append(relativo)
    return {"ruta": str(destino), "archivos": archivos, "tipo": tipo}
