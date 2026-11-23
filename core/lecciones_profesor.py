"""Ejemplos supervisados por un modelo y comprobados con un oráculo independiente."""
from core.competencias import ejercicio

ALUMNOS = ("CEREBRO", "DARAS", "CAZEL")
MATERIAS = {"matematicas": "matemáticas", "programacion": "programación",
            "espanol": "español", "razonamiento": "razonamiento", "herramientas": "herramientas"}


def preparar(profesor, materia):
    variante = profesor.proponer_variante(materia)
    pregunta, referencia = ejercicio(materia, variante)
    respuesta = profesor.resolver_leccion(pregunta)
    if not isinstance(respuesta, str) or len(respuesta) > 60 or respuesta.strip().casefold() != referencia.casefold():
        raise ValueError("La respuesta del Profesor no coincide con la referencia independiente.")
    return {"pregunta": pregunta, "respuesta": referencia, "materia": materia,
            "origen": "PROFESOR", "verificado": True, "criterio": "competencias-v1",
            "alumnos": list(ALUMNOS)}
