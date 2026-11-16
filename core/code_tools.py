"""Análisis de código Python sin ejecución. Todo offline."""
import ast
from pathlib import Path


def analizar_python(ruta, raiz="data/workspace", max_bytes=1_000_000):
    base = Path(raiz).resolve()
    objetivo = (base / ruta).resolve()
    if not objetivo.is_relative_to(base) or not objetivo.is_file():
        raise ValueError("Archivo inexistente o fuera del workspace")
    if objetivo.stat().st_size > max_bytes:
        raise ValueError("Archivo demasiado grande")
    fuente = objetivo.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(objetivo))
    funciones = [n.name for n in ast.walk(arbol) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    clases = [n.name for n in ast.walk(arbol) if isinstance(n, ast.ClassDef)]
    imports = [n.module or "" for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(arbol) if isinstance(n, ast.Import) for a in n.names]
    return {"lineas": len(fuente.splitlines()), "funciones": funciones,
            "clases": clases, "imports": imports}
