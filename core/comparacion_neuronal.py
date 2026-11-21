"""Bancos inéditos y lotes documentales compartidos entre arquitecturas."""
from hashlib import sha256
import random
from statistics import median
from time import perf_counter
import unicodedata

import numpy as np

from core import curriculo
from core.data import construir_stream
from core.tokenizer import ID_PAD


def banco_nuevo():
    casos = []
    datos = {
        "matemáticas": [(f"Saldo inicial {a}; cargo {b}; abono {c}. Escribe el saldo final.",
                         str(a - b + c)) for a, b, c in
                        ((47, 15, 9), (63, 26, 8), (75, 28, 11), (52, 38, 7),
                         (81, 47, 16), (96, 39, 12), (70, 23, 9), (59, 18, 13))],
        "español": [(f"Completa con el femenino singular: esta persona es {m}. Escribe solo la palabra.",
                     f) for m, f in (("actor", "actriz"), ("autor", "autora"), ("duque", "duquesa"),
                     ("emperador", "emperatriz"), ("rey", "reina"), ("poeta", "poetisa"),
                     ("alcalde", "alcaldesa"), ("príncipe", "princesa"))],
        "razonamiento": [(f"En un cajón hay una {a} y un {b}; saco la {a}. Di qué queda.",
                          b) for a, b in (("llave", "anillo"), ("tiza", "dado"), ("vela", "botón"),
                          ("goma", "lápiz"), ("piedra", "imán"), ("cinta", "tornillo"),
                          ("cuchara", "vaso"), ("taza", "plato"))],
        "programación": [(f"Lista Python: {a}. Se quita su primer elemento. ¿Cuántos quedan?",
                           str(len(a) - 1)) for a in ([81, 24], [79, 22, 88], [31, 49, 28, 77],
                           [19, 35, 49], [28, 47, 81, 59, 13], [73, 49], [72, 84, 63, 93],
                           [51, 29, 38, 77, 62, 95])],
        "herramientas": [(f"Elige el instrumento que usarías y escribe solo su nombre. Caso: {p}.",
                         r) for p, r in (("obtener el IVA de una compra", "calculadora"),
                         ("arreglar una falta en un borrador", "editor"),
                         ("leer una dirección de un sitio", "navegador"),
                         ("tengo que sumar los importes de cinco facturas", "calculadora"),
                         ("modificar dos frases de un archivo", "editor"),
                         ("consultar una página de ayuda de la web", "navegador"),
                         ("quiero convertir el descuento en un importe numérico", "calculadora"),
                         ("quiero corregir la redacción de un TXT", "editor"))],
    }
    for materia, filas in datos.items():
        casos.extend(curriculo.Caso(materia, "estructura_nueva", p, r) for p, r in filas)
    return casos


def dialogos_largos(prueba):
    palabras = ("rojo", "azul", "verde", "negro")
    asuntos = (("un mapa de montañas", "las horas de viaje", "la luz al final del día"),
               ("el jardín del museo", "el horario de visitas", "el camino junto al río"))
    casos = []
    for indice in range(8 if prueba else 32):
        a, b, c = asuntos[int(prueba)]
        interlocucion = (
            ("La clave de esta ronda es {clave}.", "De acuerdo."),
            (f"Hablemos de {a} y de {b}.", "Lo vemos después."),
            (f"Deja pendiente {c}. Nota {indice + (80 if prueba else 1)}.", "Por supuesto."),
        )
        seleccion = (palabras[indice % 4], palabras[(indice + 1) % 4]) if prueba else (palabras[indice % 4],)
        for clave in seleccion:
            contexto = ((interlocucion[0][0].format(clave=clave), interlocucion[0][1]), *interlocucion[1:])
            pregunta = ("Di solo el color indicado al inicio." if prueba
                        else "¿Qué color nombré al principio? Di solo el color.")
            casos.append(curriculo.Caso("razonamiento", "dialogo_largo", pregunta, clave, contexto))
    return casos


def clave_entrada(caso):
    return curriculo._clave("\n".join(
        [s for p, r in caso.contexto for s in (p, r)] + [caso.pregunta]))


def verificar_particiones(entrenamiento, *bancos):
    vistos = {clave_entrada(c) for c in entrenamiento}
    if len(vistos) != len(entrenamiento):
        raise ValueError("Hay entradas duplicadas en el entrenamiento.")
    for banco in bancos:
        claves = [clave_entrada(c) for c in banco]
        if len(claves) != len(set(claves)) or vistos.intersection(claves):
            raise ValueError("Los bancos contienen entradas duplicadas o compartidas.")
        vistos.update(claves)


def medir(modelo, casos, limite=None):
    materias = {}
    latencias = []
    for caso in casos:
        ids = curriculo.prefijo(modelo, caso)
        ventana = min(modelo.cfg.block_size, limite or modelo.cfg.block_size) - 12
        conserva = len(ids) <= ventana
        inicio = perf_counter()
        nuevos, _ = modelo.generar_ids(ids[-ventana:], max_nuevos=12, temperatura=0,
                                       penalizacion=1.0, parar_en=("\n",), seed=0)
        latencias.append(perf_counter() - inicio)
        salida = modelo.tokenizer.decodificar(nuevos).split("\n")[0].strip()
        exacto = unicodedata.normalize("NFC", salida) == caso.respuesta
        exito = curriculo._canon(salida.rstrip(".!?")) == curriculo._canon(caso.respuesta)
        fila = materias.setdefault(caso.materia, {"exactos": 0, "exitos": 0, "total": 0,
                                                   "contextos_completos": 0, "resultados": []})
        fila["exactos"] += int(exacto)
        fila["exitos"] += int(exito)
        fila["total"] += 1
        fila["contextos_completos"] += int(conserva)
        fila["resultados"].append({"salida": salida, "esperada": caso.respuesta, "exacto": exacto,
                                    "exito": exito, "tokens_entrada": len(ids)})
    return {"materias": materias, "latencia_mediana_ms": 1000 * median(latencias)}


class Lotes:
    """Una pareja de documentos prefijada por paso. Conserva solo el turno final en diálogos largos."""
    def __init__(self, parejas, tokenizador, contexto, dialogos):
        self.parejas = iter(parejas)
        self.T = contexto
        self.contexto = contexto
        self.documentos = {}
        self.mascara = sha256()
        self.objetivos = 0
        for d in {d for pareja in parejas for d in pareja}:
            stream = construir_stream([d], tokenizador)
            mask = stream.mask[1:].copy()
            if d in dialogos:
                ultimo_turno = tokenizador.codificar(d.splitlines()[-1])
                mask[:-len(ultimo_turno) - 1] = False
            x, y = stream.ids[:-1], np.where(mask, stream.ids[1:], -1)
            limite = contexto if d in dialogos else min(contexto, 112)
            self.documentos[d] = x[-limite:], y[-limite:]

    def siguiente(self):
        pareja = next(self.parejas)
        originales = [self.documentos[d] for d in pareja]
        filas = [(x[-self.contexto:], y[-self.contexto:]) for x, y in originales]
        ancho = max(map(lambda fila: len(fila[0]), filas))
        xs, ys = [], []
        for x, y in filas:
            xs.append(np.pad(x, (0, ancho - len(x)), constant_values=ID_PAD))
            ys.append(np.pad(y, (0, ancho - len(y)), constant_values=-1))
            objetivos = y[y >= 0]
            self.objetivos += len(objetivos)
            self.mascara.update(objetivos.astype("<i8").tobytes())
        return np.asarray(xs), np.asarray(ys)


def planificar(antiguos, nuevos, pasos, semilla, estrategia):
    rng = random.Random(semilla)
    if estrategia == "solo_nuevos":
        return [tuple(rng.choices(nuevos, k=2)) for _ in range(pasos)]
    # Se recorre un orden barajado antes de volver a repetir un ejemplo antiguo.
    repaso = rng.sample(antiguos, len(antiguos))
    return [(rng.choice(nuevos), repaso[i % len(repaso)]) for i in range(pasos)]
