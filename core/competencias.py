"""Ejercicios sintéticos, referencias independientes y progreso local del alumno."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from core.autoevaluacion import evaluar_respuesta


PRACTICA = {
    "matemáticas": ("Responde solo el número: ¿cuánto es 31 menos 17?", "14"),
    "español": ("Responde solo el plural de «luz».", "luces"),
    "programación": ("Responde solo el número que devuelve len([3, 6, 9]).", "3"),
    "razonamiento": ("Ada llegó antes que Mila, y Mila antes que Saúl. Responde solo quién llegó primero.", "Ada"),
    "herramientas": ("Elige solo una herramienta para calcular 35 por 18: navegador, calculadora o cámara.", "calculadora"),
}
RESERVADOS = {
    "matemáticas": (
        ("Responde solo el número: ¿cuánto es 42 menos 19?", "23"),
        ("Responde solo el número: ¿cuánto es siete por nueve?", "63"),
    ),
    "español": (
        ("Responde solo el plural de «raíz».", "raíces"),
        ("Responde solo el plural de «pez».", "peces"),
    ),
    "programación": (
        ("Responde solo el número que devuelve len([11, 22, 33, 44]).", "4"),
        ("Responde solo el número de elementos de range(2, 7) en Python.", "5"),
    ),
    "razonamiento": (
        ("Iria va antes que Teo y Teo antes que Lino. Responde solo quién va primero.", "Iria"),
        ("Eva va antes que Luz y Luz antes que Noa. Responde solo quién va última.", "Noa"),
    ),
    "herramientas": (
        ("Elige solo una herramienta para multiplicar 197 por 23: cámara, calculadora o editor.", "calculadora"),
        ("Elige solo una herramienta para visitar un enlace: navegador, calculadora o reloj.", "navegador"),
    ),
}


def ejercicio(materia, variante=None):
    if variante is None:
        return PRACTICA[materia]
    if type(variante) is not int or not 10 <= variante <= 99:
        raise ValueError("La variante debe ser un entero de dos cifras.")
    if materia == "matemáticas":
        return f"Responde solo el número: ¿cuánto es {variante + 80} menos 16?", str(variante + 64)
    if materia == "español":
        singular, plural = (("reloj", "relojes"), ("papel", "papeles"), ("canción", "canciones"),
                           ("mes", "meses"), ("joven", "jóvenes"))[variante % 5]
        return f"Responde solo el plural de «{singular}».", plural
    if materia == "programación":
        return (f"Responde solo el número de elementos de range({variante}, {variante + 6}) en Python.", "6")
    if materia == "razonamiento":
        nombre = ("Rosa", "Pablo", "Nuria", "Lucas", "Alicia")[variante % 5]
        return f"{nombre} entra antes que Bea y Bea antes que César. Responde solo quién entra primero.", nombre
    if materia == "herramientas":
        return (f"Elige solo una herramienta para dividir {variante} por 4: micrófono, calculadora o cámara.",
                "calculadora")
    raise ValueError("Materia desconocida.")


def huella_modelo(modelo):
    firma = sha256()
    for nombre, peso in sorted(modelo.state_dict().items()):
        firma.update(nombre.encode())
        firma.update(peso.tobytes())
    return firma.hexdigest()


def revisar(modelo, pregunta, esperada):
    from core.tokenizer import ID_EOS

    prefijo = [ID_EOS] + modelo.tokenizer.codificar(f"usuario: {pregunta}\ncerebro:")
    limite = min(32, modelo.cfg.block_size - 1)
    tokens, _ = modelo.generar_ids(prefijo[-(modelo.cfg.block_size - limite):],
                                  max_nuevos=limite, temperatura=0, parar_en=("\n",), seed=0)
    respuesta = modelo.tokenizer.decodificar(tokens).split("\n")[0].strip()
    return {"pregunta": pregunta, "esperada": esperada, "respuesta": respuesta,
            "correcta": evaluar_respuesta(respuesta, esperada)}


def evaluar(modelo):
    materias = {}
    for tema, casos in RESERVADOS.items():
        resultados = [revisar(modelo, pregunta, esperada) for pregunta, esperada in casos]
        materias[tema] = {"aciertos": sum(caso["correcta"] for caso in resultados),
                          "total": len(resultados), "resultados": resultados}
    return {"banco": 1, "fecha": datetime.now(timezone.utc).isoformat(),
            "modelo_sha256": huella_modelo(modelo), "materias": materias}


def _base(raiz):
    ruta = Path(raiz) / "data" / "competencias.sqlite3"
    if ruta.is_symlink() or ruta.parent.is_symlink():
        raise PermissionError("El registro de competencias debe ser local.")
    return ruta


def guardar(raiz, informe):
    from contextlib import closing

    ruta = _base(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ruta)) as bd, bd:
        bd.execute("CREATE TABLE IF NOT EXISTS informes (id INTEGER PRIMARY KEY, datos TEXT NOT NULL)")
        bd.execute("INSERT INTO informes (datos) VALUES (?)", (json.dumps(informe, ensure_ascii=False),))
        bd.execute("DELETE FROM informes WHERE id <= (SELECT MAX(id) - 30 FROM informes)")


def historial(raiz):
    from contextlib import closing

    ruta = _base(raiz)
    if not ruta.is_file():
        return []
    with closing(sqlite3.connect(ruta.absolute().as_uri() + "?mode=ro", uri=True)) as bd:
        if not bd.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='informes'").fetchone():
            return []
        return [json.loads(datos) for (datos,) in bd.execute("SELECT datos FROM informes ORDER BY id DESC LIMIT 30")]


def resumen(informe):
    if not informe:
        return "Aún no hay una evaluación de competencias guardada."
    lineas = []
    for tema, datos in informe["materias"].items():
        fallos = [r["esperada"] for r in datos["resultados"] if not r["correcta"]]
        linea = f"{tema.capitalize()}: {datos['aciertos']}/{datos['total']}"
        lineas.append(linea + (f" · referencias pendientes: {', '.join(fallos)}" if fallos else ""))
    if informe.get("tipo") == "candidato":
        resultado = "elegible para revisión" if informe["elegible_para_revision"] else "rechazado"
        lineas.insert(0, f"Último candidato: {resultado}.")
    return "\n".join(lineas)
