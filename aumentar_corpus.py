# -*- coding: utf-8 -*-
"""
Aumento de datos del corpus de conversación (sin ninguna IA externa: solo
reglas y aleatoriedad con semilla fija, así que el resultado es reproducible).

Un corpus pequeño hace que el modelo memorice UNA sola forma de preguntar.
Este script toma los diálogos de data/corpus.txt y genera variantes:

  1. Reformulaciones de preguntas:   "¿Qué es X?" -> "Dime qué es X", ...
  2. Escritura informal:             "que es un token" (sin tildes ni signos)
  3. Prefijos naturales:             "Oye, ¿...?", "Por favor, ..."
  4. Conversaciones de varios turnos, encadenando diálogos (con saludo y
     despedida), para que el modelo aprenda el formato multi-turno.

Las respuestas NO se inventan: son siempre las del corpus original. No se
toca data/validacion.txt (esos diálogos jamás se usan para entrenar).

Uso:
    python3 aumentar_corpus.py                       # escribe data/corpus/aumentado.txt
    python3 aumentar_corpus.py --variantes 4 --cadenas 400 --semilla 1
"""

import argparse
import os
import random
import re
import sys
import unicodedata

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from core.data import documentos_desde_texto

SALIDA = os.path.join(config.CORPUS_DIR, "aumentado.txt")

PLANTILLAS_QUE_ES = [
    "¿Puedes explicarme qué es {x}?",
    "Explícame qué es {x}",
    "Dime qué es {x}",
    "¿Sabes qué es {x}?",
    "Necesito saber qué es {x}",
    "¿Me cuentas qué es {x}?",
    "Quiero entender qué es {x}",
    "Oye, ¿qué es {x}?",
    "Una duda: ¿qué es {x}?",
    "Por favor, dime qué es {x}",
    "¿Me puedes decir qué es {x}?",
]
PREFIJOS = ["Oye, ", "Por favor, ", "Una pregunta: ", "Disculpa, ", "Dime, ", "Hola, "]
SALUDOS = ["Hola", "Buenos días", "Buenas tardes", "Hola, ¿cómo estás?", "¿Qué tal?"]
DESPEDIDAS = ["Gracias", "Muchas gracias por tu ayuda", "Adiós", "Hasta luego", "Nos vemos"]


def informal(texto):
    """Como escribe la gente con prisa: minúsculas, sin tildes ni ¿?¡!"""
    t = texto.lower().replace("ñ", "\u0001")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("\u0001", "ñ")
    t = re.sub(r"[¿?¡!]", "", t)
    return re.sub(r"\s+", " ", t).strip()


_SIN_PREFIJO = ("hola", "buen", "¿qué tal", "¿que tal", "gracias", "muchas gracias",
                "adiós", "adios", "hasta", "nos vemos")


def _minuscula_inicial(q):
    if q.startswith("¿") and len(q) > 1:
        return "¿" + q[1].lower() + q[2:]
    return q[0].lower() + q[1:]


def parsear_dialogos(docs):
    """Devuelve la lista de pares (usuario, cerebro) de los documentos que
    son un diálogo de exactamente dos líneas."""
    pares = []
    for d in docs:
        lineas = d.split("\n")
        if (len(lineas) == 2 and lineas[0].startswith("usuario:")
                and lineas[1].startswith("cerebro:")):
            pares.append((lineas[0][len("usuario:"):].strip(),
                          lineas[1][len("cerebro:"):].strip()))
    return pares


def variantes_de_pregunta(pregunta, rng, cuantas):
    """Devuelve hasta `cuantas` formas distintas de plantear `pregunta`."""
    salida = []
    m = re.match(r"^¿[Qq]ué es (.+)\?$", pregunta)
    if m:
        x = m.group(1)
        opciones = [p.format(x=x) for p in PLANTILLAS_QUE_ES]
        rng.shuffle(opciones)
        salida.extend(opciones[:max(1, cuantas - 1)])
    elif "?" in pregunta and not pregunta.lower().startswith(_SIN_PREFIJO):
        minus = _minuscula_inicial(pregunta)
        opciones = [pref + minus for pref in PREFIJOS]
        rng.shuffle(opciones)
        salida.extend(opciones[:max(1, cuantas - 1)])
    salida.append(informal(pregunta))
    if m:
        salida.append(informal(rng.choice(PLANTILLAS_QUE_ES).format(x=m.group(1))))
    unicos, vistos = [], {pregunta}
    for s in salida:
        if s and s not in vistos:
            vistos.add(s)
            unicos.append(s)
    return unicos[:cuantas]


def generar(docs, variantes=3, cadenas=300, semilla=0):
    rng = random.Random(semilla)
    pares = parsear_dialogos(docs)
    if not pares:
        raise ValueError("No se encontraron diálogos 'usuario:/cerebro:' para aumentar.")
    respuesta_de = {}
    for u, c in pares:
        respuesta_de.setdefault(u, c)

    resultado = []

    # 1) variantes de cada pregunta con su misma respuesta
    for u, c in pares:
        for q in variantes_de_pregunta(u, rng, variantes):
            resultado.append(f"usuario: {q}\ncerebro: {c}")

    # 2) conversaciones de varios turnos
    saludos = [(s, respuesta_de[s]) for s in SALUDOS if s in respuesta_de]
    despedidas = [(s, respuesta_de[s]) for s in DESPEDIDAS if s in respuesta_de]
    for _ in range(cadenas):
        turnos = []
        if saludos and rng.random() < 0.5:
            turnos.append(rng.choice(saludos))
        turnos.extend(rng.sample(pares, k=rng.randint(2, 3)))
        if despedidas and rng.random() < 0.4:
            turnos.append(rng.choice(despedidas))
        lineas = []
        for u, c in turnos:
            if rng.random() < 0.35:
                alternativas = variantes_de_pregunta(u, rng, 2)
                if alternativas:
                    u = rng.choice(alternativas)
            lineas.append(f"usuario: {u}\ncerebro: {c}")
        resultado.append("\n".join(lineas))

    # Sin duplicados exactos, manteniendo el orden.
    vistos, unicos = set(), []
    for d in resultado:
        if d not in vistos:
            vistos.add(d)
            unicos.append(d)
    return unicos


def main():
    ap = argparse.ArgumentParser(description="Aumento de datos del corpus de Cerebro")
    ap.add_argument("--entrada", default=config.CORPUS_FILE, help="corpus base")
    ap.add_argument("--salida", default=SALIDA)
    ap.add_argument("--variantes", type=int, default=3, help="variantes por pregunta")
    ap.add_argument("--cadenas", type=int, default=300, help="conversaciones multi-turno")
    ap.add_argument("--semilla", type=int, default=0)
    args = ap.parse_args()

    with open(args.entrada, "r", encoding="utf-8") as f:
        docs = documentos_desde_texto(f.read())
    aumentados = generar(docs, args.variantes, args.cadenas, args.semilla)

    os.makedirs(os.path.dirname(os.path.abspath(args.salida)), exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as f:
        f.write("\n\n".join(aumentados) + "\n")
    print(f"[OK] {len(docs)} documentos base -> {len(aumentados)} documentos aumentados "
          f"en {args.salida}")


if __name__ == "__main__":
    main()
