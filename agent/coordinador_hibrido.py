"""Validación de sugerencias del profesor antes del despacho de escritorio."""
import json
import re

from core.documentos_usuario import _normalizar


ACCIONES = {
    "abrir": ("Abre", ("READ",)),
    "buscar": ("Busca archivo", ("READ",)),
    "enfocar": ("Enfoca", ("READ",)),
    "cerrar": ("Cierra", ("READ", "WRITE")),
    "youtube": ("Abre YouTube", ("READ",)),
}
PREGUNTA_PLAN = re.compile(r"(?:prepara|propone|prop[oó]n) un plan de escritorio para (.+)", re.I)


def validar_plan(texto):
    try:
        datos = json.loads(texto)
    except (ValueError, TypeError) as exc:
        raise ValueError("El profesor no devolvió una lista JSON de acciones.") from exc
    if not isinstance(datos, list) or not 1 <= len(datos) <= 3:
        raise ValueError("El plan debe tener de uno a tres pasos.")
    plan = []
    for paso in datos:
        if not isinstance(paso, dict) or set(paso) != {"accion", "objetivo"}:
            raise ValueError("El paso incluye campos fuera del esquema.")
        accion, objetivo = paso["accion"], paso["objetivo"]
        if not isinstance(accion, str) or accion not in ACCIONES or not isinstance(objetivo, str):
            raise ValueError("La acción no pertenece al registro.")
        objetivo = objetivo.strip()
        normal = _normalizar(objetivo)
        if accion == "abrir" and re.fullmatch(r"(?:la pagina de )?you ?tube", normal):
            accion, objetivo = "youtube", ""
        if accion == "youtube":
            if objetivo:
                raise ValueError("YouTube usa un destino fijo.")
        elif not re.fullmatch(r"[\w .()+-]{2,70}", objetivo) or not any(c.isalnum() for c in objetivo):
            raise ValueError("El objetivo debe ser un nombre breve, sin rutas ni órdenes adicionales.")
        elif accion == "cerrar" and re.match(r"^(?:todo\b|todas\b|(?:mi |la )?sesion\b)", normal):
            raise ValueError("El plan no admite cierre general o de sesión.")
        plan.append((accion, objetivo))
    return plan


def representar(accion, objetivo):
    return (ACCIONES[accion][0] + " " + objetivo).rstrip()


def disponible(nucleo, plan):
    for accion, _ in plan:
        nucleo.exigir_permisos(*ACCIONES[accion][1])
        if accion == "youtube" and not nucleo.internet:
            raise PermissionError("Permiso de internet desactivado.")
