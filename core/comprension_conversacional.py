"""Normalización conservadora de preguntas informativas."""
import re

from core.respuestas_con_fuentes import concepto_definicion, normalizar


def preparar(pregunta):
    texto = normalizar(pregunta)
    # Conserva la consulta original cuando ya está bien segmentada.
    if re.match(r"^ques (?:el|la|un|una|los|las) \S", texto):
        return "¿Qué es " + texto.removeprefix("ques ") + "?", None
    if texto.startswith("ques "):
        return pregunta, "¿Qué quieres decir con «" + texto.removeprefix("ques ")[:60] + "»?"
    fusion = re.fullmatch(r"que es([a-zñ]{3,})", texto)
    if fusion and not texto.startswith("que est"):
        return "¿Qué es " + fusion[1] + "?", None
    return pregunta, None


def pide_explicacion(pregunta):
    texto = normalizar(pregunta)
    return bool(concepto_definicion(texto) or re.match(r"^(?:explicame|cuentame|por que|como funciona|como se|cual es la diferencia|que diferencia hay) ", texto))


def pide_seguimiento(pregunta):
    texto = normalizar(pregunta)
    return bool(re.match(r"^(?:y (?:como|por que|para que|cuando|que)\b|"
                         r"(?:dame|ponme|muestrame) (?:otro|un) ejemplo\b|"
                         r"(?:explicalo|explicamelo|resumelo|resumemelo) (?:mejor|mas facil|de nuevo|en pocas palabras)\b)", texto))


def intencion_comun(texto):
    """Corrige vocabulario de la interfaz, sin reescribir nombres de archivos."""
    if not re.match(r"^(?:quiero |abre |abreme |crea |hazme )", texto):
        return texto
    palabras = {"aser": "hacer", "pajina": "pagina", "pograma": "programa"}
    return " ".join(palabras.get(palabra, palabra) for palabra in texto.split())



def conserva_contexto(respuesta, referencia):
    """Descarta reformulaciones vacías cuando existe una ficha local de respaldo."""
    principal = set(palabra for palabra in normalizar(referencia).split() if len(palabra) >= 5)
    salida = set(normalizar(respuesta).split())
    return len(principal & salida) >= 2
