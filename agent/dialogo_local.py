"""Intenciones breves, inspiradas en conversational_reply de Daras-IA (MIT)."""
import re
import unicodedata


def respuesta_breve(consulta):
    normal = unicodedata.normalize("NFKD", consulta.casefold())
    texto = " ".join(re.findall(r"\w+", "".join(
        letra for letra in normal if not unicodedata.combining(letra)
    )))
    if texto in {"que sabes hacer", "que puedes hacer", "en que me puedes ayudar", "ayuda"}:
        return "capacidades"
    if re.fullmatch(r"(?:tu creador es|registra a tu creador) .+", texto):
        return "creador"
    if re.match(r"^qeu es\s+\S", consulta.casefold()):
        return "aclarar_definicion"
    return None
