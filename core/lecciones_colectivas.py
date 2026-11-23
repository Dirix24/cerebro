"""Contrato v1 de lecciones locales verificadas derivadas de adaptadores v1."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

VERSION = 1
MUESTRA = "def area(x, y):\n    return x * y\ndef doble(x):\n    return x + x\n"
PREGUNTA_CAZEL = "En Python: def area(x, y): return x*y; def doble(x): return x+x. ¿Cuántas funciones se definen? Responde con un número."


def muestras_cazel():
    yield MUESTRA, PREGUNTA_CAZEL, "2"
    yield ("valor = 1\ndef incompleta(\n",
           "En Python, la línea 1 es valor = 1 y la línea 2 es def incompleta(. ¿En qué línea empieza el error de sintaxis? Responde con un número.", "2")
    for cantidad in (1, 3, 4):
        lineas = [f"def paso_{i}(x): return x + {i}" for i in range(1, cantidad + 1)]
        muestra = "\n".join(lineas) + "\n"
        pregunta = "En este fragmento de Python: " + "; ".join(lineas)
        yield muestra, pregunta + ". ¿Cuántas funciones se definen? Responde con un número.", str(cantidad)


def _cazel(respuesta, variante=0):
    muestra, pregunta, referencia = list(muestras_cazel())[variante]
    evidencia = next((item for item in respuesta.get("evidencia", ())
                      if item.get("path") == "practica.py" and item.get("language") == "Python"), None)
    if not evidencia:
        return None
    try:
        arbol = ast.parse(muestra)
    except SyntaxError as fallo:
        errores = evidencia.get("errores")
        if (isinstance(errores, list) and len(errores) == 1 and isinstance(errores[0], dict)
                and errores[0].get("line") == fallo.lineno and str(fallo.lineno) == referencia):
            return pregunta, referencia, "Línea del error comprobada con el analizador Python"
        return None
    simbolos = [{"name": nodo.name, "line": nodo.lineno} for nodo in arbol.body
                if isinstance(nodo, ast.FunctionDef)]
    if evidencia.get("errores") != [] or evidencia.get("simbolos") != simbolos:
        return None
    return pregunta, referencia, "AST de la muestra pública"


def _daras(respuesta, variante=0):
    plan = respuesta.get("plan")
    if not isinstance(plan, list) or not 2 <= len(plan) <= 12:
        return None
    indices = {}
    ejercicios = []
    for numero, tarea in enumerate(plan, 1):
        if not isinstance(tarea, dict):
            return None
        ident, padres = tarea.get("id"), tarea.get("depende_de")
        if not isinstance(ident, str) or not ident or ident in indices or not isinstance(padres, list):
            return None
        if any(not isinstance(padre, str) or padre not in indices for padre in padres):
            return None
        if len(padres) == 1:
            padre = indices[padres[0]]
            ejercicios.append((f"En un plan, la tarea T{numero} depende directamente de T{padre}. "
                         f"¿Qué tarea debe terminar antes que T{numero}? Responde con su identificador.",
                         f"T{padre}", "Dependencia y orden del plan, comprobados por PROFESOR"))
        indices[ident] = numero
    return ejercicios[variante % len(ejercicios)] if ejercicios else None


TEMA_CONTRASTE = "sensor quimera"
FUENTES_CONTRASTE = (
    ("https://manual.example/spec", "Manual del sensor quimera", "El límite indicado es 60 °C."),
    ("https://ensayo.example/informe", "Ensayo del sensor quimera", "El límite indicado es 45 °C."),
)
PREGUNTA_CONTRASTE = (
    "Para un mismo sensor y las mismas condiciones, el manual indica 60 °C y el ensayo 45 °C. "
    "¿Coinciden las dos fuentes en su valor? Responde sí o no."
)


def _preparar_contraste(carpeta):
    from contextlib import closing
    import sqlite3

    with closing(sqlite3.connect(carpeta / "biblioteca.sqlite3")) as db, db:
        db.execute("""CREATE TABLE research_results (
            url TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT NOT NULL,
            extract TEXT NOT NULL, saved_at TEXT NOT NULL)""")
        db.executemany("INSERT INTO research_results VALUES (?, 'Ejercicio sintético', ?, ?, '2000-01-01')",
                       FUENTES_CONTRASTE)


def _contraste(resultado):
    evidencia = {(e.get("url"), e.get("titulo"), e.get("extracto"))
                 for e in resultado.get("evidencia", ()) if isinstance(e, dict) and e.get("tipo") == "fuente"}
    if evidencia == set(FUENTES_CONTRASTE) and resultado.get("red_autorizada") is False:
        return PREGUNTA_CONTRASTE, "no", "Dos fuentes de prueba recuperadas y valores contrastados por PROFESOR"
    return None


def recopilar(cancelacion, indice_practica=0):
    from core.configuracion_especialistas import obtener
    from universe.especialidades import _consulta

    lecciones = []
    for region, accion, evaluar in (("CAZEL", "analizar", _cazel), ("DARAS", "planificar", _daras)):
        origen = obtener(region + "_RAIZ")
        if not origen or cancelacion.is_set():
            continue
        variante = indice_practica % len(list(muestras_cazel()))
        contraste = region == "DARAS" and variante == 2
        with TemporaryDirectory(prefix="cerebro-practica-") as temporal:
            carpeta = Path(temporal)
            if region == "CAZEL":
                (carpeta / "practica.py").write_text(list(muestras_cazel())[variante][0], encoding="utf-8")
            else:
                # El adaptador DARAS v1 actual almacena SQLite junto al módulo.
                # Una copia efímera de sus puntos de entrada impide tocar sus datos.
                try:
                    for nombre in ("especialista.py", "companiona.py"):
                        fuente = Path(origen).expanduser() / nombre
                        if fuente.is_symlink() or not fuente.is_file() or fuente.stat().st_size > 1024**2:
                            raise ValueError("Módulo DARAS no disponible para la práctica.")
                        shutil.copyfile(fuente, carpeta / nombre)
                except (OSError, ValueError):
                    continue
            if contraste:
                _preparar_contraste(carpeta)
                resultado = _consulta(region, "investigar", TEMA_CONTRASTE, cancelacion=cancelacion,
                                      practica=carpeta)
            else:
                objetivo = "practica.py" if region == "CAZEL" else "Planificar un proyecto de ejemplo"
                resultado = _consulta(region, accion, objetivo, cancelacion=cancelacion, practica=carpeta)
        if resultado["estado"] == "ok":
            ejercicio = _contraste(resultado) if contraste else evaluar(resultado, variante)
            if not ejercicio:
                continue
            pregunta, respuesta, criterio = ejercicio
            lecciones.append({"version": VERSION, "especialista": region, "pregunta": pregunta,
                              "respuesta": respuesta, "criterio": criterio,
                              "evidencia_sha256": sha256(json.dumps(resultado, sort_keys=True).encode()).hexdigest()})
    return lecciones


def validar_lecciones(lecciones):
    import re

    if not isinstance(lecciones, (list, tuple)) or len(lecciones) > 2:
        raise ValueError("Se admiten hasta dos lecciones v1 por sesión.")
    vistos = set()
    for leccion in lecciones:
        if (not isinstance(leccion, dict) or type(leccion.get("version")) is not int
                or leccion["version"] != VERSION
                or set(leccion) != {"version", "especialista", "pregunta", "respuesta", "criterio", "evidencia_sha256"}
                or not all(isinstance(leccion[c], str) for c in ("especialista", "pregunta", "respuesta", "criterio", "evidencia_sha256"))
                or not re.fullmatch("[a-f0-9]{64}", leccion["evidencia_sha256"])):
            raise ValueError("Lección colectiva incompatible.")
        region = leccion["especialista"]
        pregunta = leccion["pregunta"]
        respuesta = leccion["respuesta"]
        if region == "CAZEL":
            valida = any((pregunta, respuesta) == (p, r) for _, p, r in muestras_cazel())
        elif region == "DARAS":
            dep = re.fullmatch(r"En un plan, la tarea T(\d{1,2}) depende directamente de T(\d{1,2})\. "
                               r"¿Qué tarea debe terminar antes que T\1\? Responde con su identificador\.", pregunta)
            valida = ((pregunta, respuesta) == (PREGUNTA_CONTRASTE, "no")
                      or (dep and 1 <= int(dep[2]) < int(dep[1]) <= 12 and respuesta == "T" + dep[2]))
        else:
            valida = False
        if not valida or region in vistos:
            raise ValueError("La lección no supera la comprobación de referencias.")
        vistos.add(region)
    return list(lecciones)
