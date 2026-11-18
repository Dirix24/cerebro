"""Criterio previo a acciones: explica ruta, permisos y riesgos sin ejecutar nada.

Inspirado en asistentes generalistas; no implica razonamiento autónomo del modelo.
"""
from agent.orquestador import explicar_seleccion

_ACCIONES = {
    "/crear-proyecto": ("WRITE", "Crea archivos en el espacio de trabajo.", "media"),
    "/escribir": ("WRITE", "Escribe un archivo local.", "media"),
    "/leer": ("READ", "Consulta un archivo local.", "baja"),
    "/archivos": ("READ", "Lista archivos del espacio de trabajo.", "baja"),
    "/recordar": ("WRITE", "Modifica la memoria persistente.", "media"),
    "/olvidar": ("WRITE", "Borra una entrada de memoria.", "media"),
    "/guardar-turno": ("WRITE", "Guarda un turno en el historial.", "media"),
    "/estudiar": (None, "Consulta una guía de estudio local.", "baja"),
    "/materias": (None, "Lista materias locales.", "baja"),
    "/calc": ("CALCULATE", "Calcula una expresión sin ejecutar Python arbitrario.", "baja"),
}


def evaluar_peticion(texto, permisos=None):
    """Evaluación explicable; no se concede permiso ni se ejecuta la petición."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Introduce una petición no vacía.")
    permisos = set(permisos or ())
    ruta = explicar_seleccion(texto)
    comando = texto.strip().split(None, 1)[0].lower()
    if texto.lstrip().startswith("/"):
        if comando in _ACCIONES:
            permiso, efecto, riesgo = _ACCIONES[comando]
            permitido = permiso is None or permiso in permisos
            return {"ruta": "comando", "accion": comando, "efecto": efecto,
                    "riesgo": riesgo, "permiso": permiso,
                    "puede_ejecutarse": permitido,
                    "requiere_orden_explicita": permiso == "WRITE",
                    "nota": "Evaluación previa: no se ejecutó ninguna acción."}
        return {"ruta": "comando", "accion": comando, "efecto": "No catalogado",
                "riesgo": "desconocido", "permiso": None, "puede_ejecutarse": False,
                "requiere_orden_explicita": True,
                "nota": "Comando no evaluado: consulta /ayuda."}
    return {"ruta": ruta["motor"], "accion": "consulta",
            "efecto": ruta["razon"], "riesgo": "baja",
            "permiso": None, "puede_ejecutarse": True,
            "requiere_orden_explicita": False,
            "nota": "Solo clasificación de la petición; no se verificó la respuesta."}
