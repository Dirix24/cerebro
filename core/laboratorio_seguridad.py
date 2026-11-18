"""Laboratorio defensivo local: inspección estática, sin ejecutar archivos."""
import ast
import hashlib
from pathlib import Path

_MAX = 1_000_000


def inspeccionar_archivo(ruta, raiz):
    base = Path(raiz).resolve(strict=True)
    archivo = (base / ruta).resolve(strict=True)
    if not archivo.is_relative_to(base) or not archivo.is_file():
        raise ValueError("Archivo fuera del laboratorio o no es regular.")
    if archivo.stat().st_size > _MAX:
        raise ValueError("Archivo demasiado grande para inspección.")
    contenido = archivo.read_bytes()
    resultado = {"archivo": str(archivo.relative_to(base)),
                 "bytes": len(contenido),
                 "sha256": hashlib.sha256(contenido).hexdigest(),
                 "ejecutado": False}
    if archivo.suffix.lower() == ".py":
        try:
            arbol = ast.parse(contenido.decode("utf-8"))
            resultado["python_sintaxis"] = "valida"
            resultado["funciones"] = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                                          for n in ast.walk(arbol))
            resultado["imports"] = sorted({
                a.name.split(".")[0] for n in ast.walk(arbol)
                for a in (n.names if isinstance(n, ast.Import) else
                          [ast.alias(name=n.module or "")] if isinstance(n, ast.ImportFrom) else [])
                if a.name
            })
        except (SyntaxError, UnicodeDecodeError) as exc:
            resultado["python_sintaxis"] = "error"
            resultado["detalle"] = str(exc)[:200]
    return resultado
