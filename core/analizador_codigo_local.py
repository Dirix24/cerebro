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


def consultar(entrada):
    """Detecta código Python reconocible o un bloque Markdown declarado."""
    import re

    bloque = re.fullmatch(r"```(python|py)\s*\n([\s\S]+?)\n?```", entrada, re.I)
    if bloque:
        codigo = bloque[2]
    elif re.match(r"(?:async\s+def|def|class|from|import)\s+\w|[a-zA-Z_]\w*\s*=(?!=)|print\s*\(", entrada):
        codigo = entrada
    else:
        return None
    try:
        informe = analizar(codigo)
    except SyntaxError as error:
        return f"Sintaxis Python: línea {error.lineno}, columna {error.offset or 1}. {error.msg}."
    except ValueError as error:
        return str(error)
    partes = ["Sintaxis Python válida."]
    for clave, etiqueta in (("funciones", "Funciones"), ("clases", "Clases"), ("importaciones", "Importaciones")):
        if informe[clave]:
            partes.append(f"{etiqueta}: {', '.join(informe[clave][:15])}.")
    return " ".join(partes) + " Inspección estática. Para comprobar el comportamiento, ejecuta pruebas autorizadas del proyecto."
