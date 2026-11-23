"""Respuestas factuales conservadoras a partir de fichas y corpus local.

Sin red, sin IA externa y sin inventar información. No confunde similitud con verdad.
"""
import re
import unicodedata

ALIAS = {"ia": "inteligencia artificial", "i a": "inteligencia artificial"}
DEFINICIONES_BASE = {
    "portatil": "Un portátil es un ordenador compacto que puedes transportar. "
                 "Normalmente incluye una batería, una pantalla y un teclado.",
    "fotosintesis": "La fotosíntesis es el proceso por el que las plantas usan luz, agua y dióxido de carbono "
                     "para producir azúcares y liberar oxígeno.",
}

VACIAS = {"que", "es", "son", "un", "una", "el", "la", "los", "las", "de", "del", "en", "por"}


def normalizar(texto):
    texto = texto.casefold().replace("ñ", "\ufff0")
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto)
                    if not unicodedata.combining(c)).replace("\ufff0", "ñ")
    return " ".join(re.findall(r"\w+", texto))


def concepto_definicion(pregunta):
    m = re.fullmatch(r"\s*¿?\s*(?:qué|que)\s+(?:es|son)\s+(.+?)\s*\??\s*",
                     pregunta, re.IGNORECASE)
    if not m:
        return None
    concepto = normalizar(m.group(1))
    concepto = re.sub(r"^(?:un|una|el|la|los|las)\s+", "", concepto)
    return ALIAS.get(concepto, concepto)


def _extraer_respuesta(documento, concepto):
    """Solo acepta un par de pregunta-respuesta sobre el concepto consultado."""
    patron = re.compile(r"usuario:\s*(.*?)\s*\n\s*cerebro:\s*(.*?)(?=\n\s*usuario:|\Z)",
                        re.IGNORECASE | re.DOTALL)
    for pregunta, respuesta in patron.findall(documento):
        if concepto_definicion(pregunta) == concepto:
            respuesta = respuesta.strip()
            if respuesta and len(respuesta) <= 1200:
                return respuesta
    return None


def responder_definicion(pregunta, buscador=None, buscar_hechos=None):
    """Devuelve respuesta y fuente, o None si falta evidencia local."""
    concepto = concepto_definicion(pregunta)
    if not concepto:
        return None
    if buscar_hechos is None:
        from core.conocimiento import respuesta_exacta
        buscar_hechos = respuesta_exacta
    variantes = [f"¿Qué es {concepto}?", f"¿Qué es un {concepto}?",
                 f"¿Qué es una {concepto}?", f"¿Qué son {concepto}?"]
    for variante in variantes:
        dato = buscar_hechos(variante)
        if dato:
            return dato["respuesta"][:1200], dato["fuente"]
    if buscador is None:
        from core.local_search import buscar
        buscador = buscar
    # Una coincidencia de palabras no es suficiente: verificar la pregunta del documento.
    for texto, origen in buscador(concepto, limite=10):
        respuesta = _extraer_respuesta(texto, concepto)
        if respuesta:
            return respuesta, origen
    if concepto in DEFINICIONES_BASE:
        return DEFINICIONES_BASE[concepto], "Glosario local de Cerebro"
    return None



def respuesta_clara(texto, max_caracteres=430):
    """Extrae hasta dos frases completas; nunca corta a mitad de palabra."""
    limpio = re.sub(r"[\u200b-\u200f\ufeff]", "", texto)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    # Los textos enciclopédicos suelen incluir marcas de referencias invisibles.
    limpio = re.sub(r"\[\d+\]", "", limpio)
    frases = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])", limpio)
    salida = []
    for frase in frases:
        frase = frase.strip()
        if not frase:
            continue
        candidato = " ".join(salida + [frase])
        if len(candidato) > max_caracteres:
            break
        salida.append(frase)
        if len(salida) == 2:
            break
    if salida:
        return " ".join(salida)
    # Si una frase supera el límite, buscar un cierre natural antes del límite.
    trozo = limpio[:max_caracteres]
    cierre = max(trozo.rfind("."), trozo.rfind(";"), trozo.rfind(","))
    if cierre >= 80:
        return trozo[:cierre].rstrip(",; ") + "."
    corte = trozo.rfind(" ")
    return (trozo[:corte] if corte > 40 else trozo).rstrip(" ,;:") + "…"


def consultar_internet_si_falta(pregunta, obtener=None, guardar=None):
    """Consulta pública solo para definiciones sin evidencia; sin enviar memoria ni historial."""
    concepto = concepto_definicion(pregunta)
    if not concepto or len(concepto) > 100:
        return None
    if obtener is None:
        from aprendizaje_internet import obtener_tema
        obtener = obtener_tema
    if guardar is None:
        from core.conocimiento import guardar as guardar_ficha
        guardar = guardar_ficha
    from urllib.error import HTTPError, URLError
    import ssl
    try:
        pagina = obtener(concepto)
        if not pagina:
            return None
        # No almacenar como conocimiento una página cuyo título no corresponde.
        if normalizar(pagina["titulo"]) != normalizar(concepto):
            return None
        respuesta = pagina["texto"]
        fuente = pagina["url"]
        guardar(f"¿Qué es {concepto}?", respuesta, fuente)
        return respuesta, fuente
    except (HTTPError, URLError, OSError, TimeoutError, ssl.SSLError, ValueError, KeyError):
        return None


def seleccion_publica(tema, paginas):
    """Acepta un título inequívoco, incluso con una errata menor, con su extracto."""
    from difflib import SequenceMatcher
    from urllib.parse import urlsplit

    clave = normalizar(tema)
    exactas, cercanas = [], []
    for pagina in paginas:
        titulo = pagina.get("title")
        texto = pagina.get("extract")
        url = pagina.get("fullurl")
        if not all(isinstance(campo, str) and campo.strip() for campo in (titulo, texto, url)):
            continue
        enlace = urlsplit(url)
        if (enlace.scheme != "https" or enlace.netloc != "es.wikipedia.org"
                or not enlace.path.startswith("/wiki/") or "disambiguation" in pagina.get("pageprops", {})):
            continue
        candidato = normalizar(titulo)
        if clave == candidato:
            exactas.append((texto, url))
        elif (len(clave) >= 7 and len(clave.split()) == len(candidato.split())
              and SequenceMatcher(None, clave, candidato, autojunk=False).ratio() >= .90):
            cercanas.append((texto, url))
    opciones = exactas or cercanas
    if len(opciones) == 1:
        texto, url = opciones[0]
        return respuesta_clara(texto), url
    return None


def buscar_definicion_publica(tema):
    from urllib.parse import urlencode

    from core.fuentes_publicas import consultar_json

    parametros = {"action": "query", "generator": "search", "gsrsearch": tema,
                  "gsrnamespace": 0, "gsrlimit": 4, "prop": "extracts|info|pageprops",
                  "explaintext": 1, "exintro": 1, "exchars": 900, "inprop": "url",
                  "ppprop": "disambiguation", "format": "json", "formatversion": 2}
    try:
        datos = consultar_json("https://es.wikipedia.org/w/api.php?" + urlencode(parametros))
        return seleccion_publica(tema, datos.get("query", {}).get("pages", []))
    except (OSError, ValueError, AttributeError, TypeError):
        return None
