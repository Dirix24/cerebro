"""Currículo sintético con referencias locales y particiones independientes."""
from dataclasses import dataclass
from hashlib import sha256
import random
import re
import unicodedata

from core.competencias import PRACTICA
from core.tokenizer import ID_EOS


ETAPAS = ("fundamentos", "compuestas", "dialogos")
_PLURALES = (
    (("luz", "luces"), ("voz", "voces"), ("cruz", "cruces"), ("nariz", "narices"),
     ("lápiz", "lápices"), ("actriz", "actrices"), ("feliz", "felices"), ("arroz", "arroces"),
     ("maíz", "maíces"), ("paz", "paces"), ("audaz", "audaces"), ("capaz", "capaces")),
    (("nuez", "nueces"), ("avestruz", "avestruces"), ("antifaz", "antifaces"),
     ("juez", "jueces"), ("tapiz", "tapices"), ("vez", "veces")),
    (("cáliz", "cálices"), ("barniz", "barnices"), ("lombriz", "lombrices"),
     ("codorniz", "codornices"), ("aprendiz", "aprendices"), ("disfraz", "disfraces")),
)
_NOMBRES = (("Ada", "Rosa", "Bea", "Luz", "Noa", "Pablo", "Inés", "Eva"),
            ("Vera", "Joel", "Sara", "Tadeo", "Alba", "Rita", "Úrsula", "Darío"),
            ("Leo", "Zoe", "Mara", "Diego", "Elsa", "Rocío", "Elías", "Clara"))
_HERRAMIENTAS = (
    ("calculadora", ("sumar dos cantidades", "calcular un descuento", "multiplicar dos cifras"),
     ("hallar un porcentaje", "resolver una cuenta"), ("obtener el total de una suma", "dividir una cantidad")),
    ("navegador", ("visitar una web", "abrir una página", "consultar una URL"),
     ("leer un sitio en internet", "visitar una dirección web"), ("ver un sitio web", "ir a una página de internet")),
    ("editor", ("modificar un texto", "corregir un archivo de notas", "escribir un párrafo"),
     ("editar un documento de texto", "cambiar un borrador"), ("reescribir una nota", "revisar un párrafo escrito")),
)


@dataclass(frozen=True)
class Caso:
    materia: str
    etapa: str
    pregunta: str
    respuesta: str
    contexto: tuple = ()

    @property
    def lineas(self):
        previas = [linea for p, r in self.contexto for linea in (f"usuario: {p}", f"cerebro: {r}")]
        return [*previas, f"usuario: {self.pregunta}", f"cerebro: {self.respuesta}"]

    @property
    def documento(self):
        return "\n".join(self.lineas)


def _caso(materia, indice, etapa, zona):
    reservado = zona > 0
    rng = random.Random(indice)
    if materia == "matemáticas":
        a = rng.randint(*((2, 23), (24, 38), (39, 55))[zona])
        b = rng.randint(1, 8)
        pregunta, respuesta = ((f"{a} + {b}", str(a + b)) if indice % 2
                               else (f"{a} - {b}", str(a - b)))
        pregunta = f"Calcula {pregunta}."
        adicional, segundo = "indica si el resultado es par o impar", "par" if int(respuesta) % 2 == 0 else "impar"
    elif materia == "español":
        palabra, respuesta = _PLURALES[zona][indice % len(_PLURALES[zona])]
        pregunta = f"Plural de {palabra}."
        adicional, segundo = "añade el singular", palabra
    elif materia == "programación":
        longitud = 2 + indice % 5
        inicio = rng.randint(*((1, 18), (20, 60), (61, 85))[zona])
        if (inicio, longitud) == (2, 5):
            inicio = 3
        if indice % 2:
            expresion = f"len(range({inicio}, {inicio + longitud}))"
        else:
            elementos = ", ".join(map(str, rng.sample(range(inicio, inicio + 20), longitud)))
            expresion = f"len([{elementos}])"
        pregunta, respuesta = f"Calcula {expresion}.", str(longitud)
        adicional, segundo = "añade el tipo del resultado en Python", "int"
    elif materia == "razonamiento":
        a, b, c = rng.sample(_NOMBRES[zona], 3)
        quien, respuesta = ("primero", a) if indice % 2 else ("último", c)
        pregunta = f"{a} antes que {b}; {b} antes que {c}. ¿Quién va {quien}?"
        adicional, segundo = "añade quién va en medio", b
    else:
        respuesta, *conjuntos = _HERRAMIENTAS[indice % len(_HERRAMIENTAS)]
        tareas = conjuntos[zona]
        tarea = tareas[(indice // len(_HERRAMIENTAS)) % len(tareas)]
        opciones = rng.sample([h[0] for h in _HERRAMIENTAS], len(_HERRAMIENTAS))
        pregunta = f"Para {tarea}, elige solo una: {', '.join(opciones)}."
        adicional, segundo = "añade cuántas opciones hay", "3"
    if etapa == "fundamentos":
        prefijo = "Respuesta breve. " if reservado else ("Resuelve. " if indice % 3 == 1 else "")
        return Caso(materia, etapa, prefijo + pregunta, respuesta)
    if etapa == "compuestas":
        conector = "Primero: " if reservado else ("Resuelve: " if indice % 3 == 1 else "")
        base = pregunta.replace("elige solo una", "elige una")
        return Caso(materia, etapa, f"{conector}{base} Luego {adicional}. Usa /.",
                    f"{respuesta} / {segundo}")
    seguimiento = "Con el valor previo" if reservado else "Con la respuesta previa"
    return Caso(materia, etapa, f"{seguimiento}, {adicional}. Usa /.",
                f"{respuesta} / {segundo}", ((pregunta, respuesta),))


def _clave(texto):
    norma = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join(re.findall(r"\w+", "".join(c for c in norma if not unicodedata.combining(c))))


def verificacion_adicional():
    """Casos fijos posteriores, sin reutilizar grupos léxicos del banco principal."""
    return {etapa: [_caso(materia, 200000 + i * 137, etapa, 2)
                    for materia in PRACTICA for i in range(6)] for etapa in ETAPAS}


def banco(semillas):
    if not isinstance(semillas, dict) or set(semillas) != set(PRACTICA):
        raise ValueError("Se necesita una lista de semillas por cada materia.")
    entrenamiento, reservado = {}, {}
    for etapa in ETAPAS:
        entrenamiento[etapa] = []
        reservado[etapa] = []
        for materia, valores in semillas.items():
            if (not isinstance(valores, list) or not 3 <= len(valores) <= 12
                    or any(type(v) is not int or not 10 <= v <= 99 for v in valores)
                    or len(set(valores)) != len(valores)):
                raise ValueError(f"Semillas inválidas para {materia}.")
            for indice in range(72):
                v = valores[indice % len(valores)]
                entrenamiento[etapa].append(_caso(materia, v + indice * 131, etapa, 0))
            for indice in range(6):
                reservado[etapa].append(_caso(materia, 100001 + indice * 137, etapa, 1))
        entrenamiento[etapa] = list(dict.fromkeys(entrenamiento[etapa]))
        reservado[etapa] = list(dict.fromkeys(reservado[etapa]))
    claves_train = {_clave("\n".join(c.lineas[:-1])) for casos in entrenamiento.values() for c in casos}
    claves_test = {_clave("\n".join(c.lineas[:-1])) for casos in reservado.values() for c in casos}
    if claves_train & claves_test:
        raise ValueError("Hay instrucciones compartidas entre entrenamiento y evaluación.")
    return entrenamiento, reservado


def prefijo(modelo, caso):
    ids = [ID_EOS]
    for linea in caso.lineas[:-1]:
        ids.extend(modelo.tokenizer.codificar(linea))
        ids.extend(modelo.tokenizer.codificar("\n"))
    ids.extend(modelo.tokenizer.codificar("cerebro:"))
    return ids


def comprobar_contexto(modelo, casos):
    longitudes = [len(prefijo(modelo, c)) + len(modelo.tokenizer.codificar(" " + c.respuesta))
                  for c in casos]
    return {"max_tokens": max(longitudes), "fuera_ventana": sum(v >= modelo.cfg.block_size for v in longitudes)}


def _canon(texto):
    # Se conservan signo, acentos y separador para calificar instrucciones estrictas.
    return " ".join(unicodedata.normalize("NFC", texto).casefold().split())


def medir(modelo, casos):
    materias = {}
    for caso in casos:
        ids = prefijo(modelo, caso)
        libres = modelo.cfg.block_size - len(ids)
        if libres < 1:
            raise ValueError("Un ejercicio excede el contexto del modelo.")
        nuevos, _ = modelo.generar_ids(ids, max_nuevos=min(16, libres), temperatura=0, penalizacion=1.0,
                                       parar_en=("\n",), seed=0)
        prediccion = modelo.tokenizer.decodificar(nuevos).split("\n")[0].strip()
        correcto = _canon(prediccion) == _canon(caso.respuesta)
        fila = materias.setdefault(caso.materia, {"aciertos": 0, "total": 0, "resultados": []})
        fila["aciertos"] += int(correcto)
        fila["total"] += 1
        fila["resultados"].append({"pregunta": caso.pregunta, "esperada": caso.respuesta,
                                  "respuesta": prediccion, "correcta": correcto})
    return materias


def huella(casos):
    return sha256("\n\n".join(c.documento for c in casos).encode()).hexdigest()
