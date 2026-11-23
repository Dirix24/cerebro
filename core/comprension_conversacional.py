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


def pide_dato(pregunta):
    texto = normalizar(pregunta)
    return bool(re.match(r"^(?:que (?:es|son|hace|significa|paso|ocurrio)|"
                         r"quien(?:es)?|cuando|donde|cual(?:es)?|cuanto(?:s|a|as)?|"
                         r"como (?:funciona|se|ocurrio)|por que|para que sirve|explicame|explica)\b", texto))


def consulta_referencia(pregunta):
    """Equivalencias acotadas para buscar un tema, conservando la consulta exacta aparte."""
    if concepto_definicion(pregunta):
        return pregunta
    texto = normalizar(pregunta)
    tema = re.fullmatch(r"(?:como funciona|para que sirve|explicame|explica) (.{2,100})", texto)
    if tema:
        return "¿Qué es " + tema[1] + "?"
    return pregunta


def consulta_python_literal(pregunta):
    """Resuelve len de literales sencillos, sin evaluar expresiones ni ejecutar código."""
    import ast

    solicitud = re.fullmatch(r"\s*¿?(?:qué|que)\s+(?:devuelve|retorna|da)\s+\x60?(len\(.+\))\x60?\??\s*",
                             pregunta, re.I)
    if not solicitud or len(solicitud[1]) > 256:
        return None
    try:
        nodo = ast.parse(solicitud[1], mode="eval").body
        if not isinstance(nodo, ast.Call) or nodo.keywords or len(nodo.args) != 1:
            return None
        valor = ast.literal_eval(nodo.args[0])
    except (SyntaxError, ValueError, TypeError, RecursionError):
        return None
    if type(valor) in (str, bytes, list, tuple, dict, set):
        return f"Python devuelve {len(valor)}."
    return None
