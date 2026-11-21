"""Small sourced catalog, with session-only context for explicit follow-ups."""
import re

from core.respuestas_con_fuentes import normalizar


_TEMAS = {
    "japon": {
        "nombre": "Japón",
        "descripcion": "Japón es un país insular de Asia oriental. Sus cuatro islas principales son Honshū, Hokkaidō, Kyūshū y Shikoku.",
        "capital": "Tokio",
        "moneda": "el yen",
        "idioma": "el japonés",
        "ubicacion": "Asia oriental, en el océano Pacífico",
        "fuente": "https://www.exteriores.gob.es/Documents/FichasPais/JAPON_FICHA%20PAIS.pdf",
    },
    "portugal": {
        "nombre": "Portugal",
        "descripcion": "Portugal está en el sudoeste de Europa, junto al Atlántico. Incluye los archipiélagos de Azores y Madeira.",
        "capital": "Lisboa",
        "moneda": "el euro",
        "idioma": "el portugués",
        "ubicacion": "el sudoeste de Europa, junto al océano Atlántico",
        "fuente": "https://www.exteriores.gob.es/Documents/FichasPais/Portugal_FICHA%20PAIS.pdf",
    },
}
_PREGUNTA_TEMA = re.compile(r"(?:que es|que sabes de|hablame (?:de|sobre)|cuentame sobre) (.+)")
_ATRIBUTO_EXPLICITO = re.compile(r"(?:cual es )?(?:la |el )?(capital|moneda|idioma) de (.+)")
_ATRIBUTO_CONTEXTO = re.compile(r"(?:y )?(?:cual es )?su (capital|moneda|idioma)")
_UBICACION = re.compile(r"donde (?:esta|queda) (.+)")


def responder_tema(entrada, anterior):
    """Return (reply or None, topic or None) for this turn."""
    if len(entrada) > 180:
        return None, None
    pregunta = normalizar(entrada)
    atributo = "descripcion"
    if match := _ATRIBUTO_CONTEXTO.fullmatch(pregunta):
        if anterior not in _TEMAS:
            return "¿De qué país quieres saber " + {"capital": "la capital", "moneda": "la moneda",
                                                    "idioma": "el idioma"}[match[1]] + "?", None
        atributo, tema = match[1], anterior
    elif match := _ATRIBUTO_EXPLICITO.fullmatch(pregunta):
        atributo, tema = match.groups()
    elif match := _UBICACION.fullmatch(pregunta):
        atributo, tema = "ubicacion", match[1]
    elif match := _PREGUNTA_TEMA.fullmatch(pregunta):
        tema = match[1]
    else:
        return None, None
    datos = _TEMAS.get(tema)
    if not datos:
        return None, None
    valor = datos[atributo]
    nombre = datos["nombre"]
    frase = {
        "descripcion": valor,
        "capital": f"La capital de {nombre} es {valor}.",
        "moneda": f"La moneda de {nombre} es {valor}.",
        "idioma": f"El idioma principal de {nombre} es {valor}.",
        "ubicacion": f"{nombre} está en {valor}.",
    }[atributo]
    return f"{frase}\nFuente: {datos['fuente']}", tema
