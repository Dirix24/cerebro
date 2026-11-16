"""Análisis estático de Python sin ejecutar el código inspeccionado."""
import ast


def analizar(codigo):
    if len(codigo) > 100000:
        raise ValueError("Código demasiado grande")
    arbol = ast.parse(codigo)
    funciones = [n.name for n in ast.walk(arbol) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    clases = [n.name for n in ast.walk(arbol) if isinstance(n, ast.ClassDef)]
    importaciones = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            importaciones.extend(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            importaciones.append(n.module or "")
    return {"funciones": funciones, "clases": clases, "importaciones": importaciones}
