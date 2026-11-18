"""SpeedDeck: selección ligera y conservadora de motores.

Solo clasifica la petición; no importa ni ejecuta motores pesados.
Las escrituras requieren comandos explícitos.
"""
import re


_PATRON_BUSQUEDA = re.compile(
    r"^\s*[¿]?\s*(?:busca(?:r)?|consulta(?:r)?|investiga(?:r)?)\s+"
    r"(?:(?:en|sobre)\s+)?(?:(?:el|la|los)\s+)?"
    r"(?:corpus|biblioteca|documentos?\s+local(?:es)?|archivos?\s+local(?:es)?)\s*[: ]+",
    re.IGNORECASE,
)
_PATRON_CONOCIMIENTO = re.compile(
    r"^\s*[¿]?\s*(?:qué|que|quién|quien)\s+(?:es|fue|son)\s+.{3,}",
    re.IGNORECASE,
)


def seleccionar(texto):
    """Devuelve la ruta elegida sin activar el motor."""
    texto = texto.strip()
    if texto.startswith("/"):
        return "comando"
    if _PATRON_BUSQUEDA.match(texto):
        return "busqueda_local"
    if _PATRON_CONOCIMIENTO.match(texto):
        return "conocimiento"
    return "modelo"


def extraer_consulta_local(texto):
    """Elimina únicamente el prefijo de una petición de búsqueda reconocida."""
    coincidencia = _PATRON_BUSQUEDA.match(texto.strip())
    return texto.strip()[coincidencia.end():].strip() if coincidencia else ""


def explicar_seleccion(texto):
    """Describe la decisión de enrutamiento sin ejecutar herramientas."""
    ruta = seleccionar(texto)
    razones = {
        "comando": "Orden explícita: requiere la ejecución del comando solicitado",
        "busqueda_local": "Petición explícita de investigar o consultar documentos locales",
        "conocimiento": "Pregunta factual: buscar primero una fuente local",
        "modelo": "No se identificó herramienta determinista ni fuente específica",
    }
    return {"motor": ruta, "razon": razones[ruta],
            "requiere_confirmacion_para_escritura": ruta == "comando"}
