"""Enrutador de motores especializados: decisión explicable, sin ejecución.

Los motores de cámara/voz/internet siguen desactivados hasta integrar hardware
y obtener permiso explícito. El núcleo NumPy no cambia de arquitectura aquí.
"""
import re

_REGLAS = (
    ("ciberseguridad", re.compile(r"\b(ciberseguridad|seguridad informática|vulnerabilidad|sha256|malware|auditoría defensiva)\b", re.I)),
    ("documentos", re.compile(r"\b(pdf|documento|informe)\b", re.I)),
    ("proyectos", re.compile(r"\b(programar|programación|proyecto|código|python|aplicación)\b", re.I)),
    ("analisis_codigo", re.compile(r"\b(analiza(?:r)? código|revisa(?:r)? código|errores de sintaxis)\b", re.I)),
)


def proponer_motor(peticion):
    """Solo recomienda; nunca convierte lenguaje libre en escritura/ejecución."""
    if not isinstance(peticion, str) or not peticion.strip():
        raise ValueError("Petición vacía.")
    if peticion.lstrip().startswith("/"):
        return {"motor": "comando", "requiere_comando_explicito": False,
                "motivo": "La petición ya usa un comando explícito."}
    for nombre, patron in _REGLAS:
        if patron.search(peticion):
            return {"motor": nombre, "requiere_comando_explicito": True,
                    "motivo": "Se detectó una materia especializada; no se ejecutó nada."}
    return {"motor": "nucleo", "requiere_comando_explicito": False,
            "motivo": "Consulta general; usar fuentes locales antes de generar."}
