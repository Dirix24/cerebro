"""Interpretación de órdenes dirigidas al escritorio y selección de candidatos."""
from difflib import SequenceMatcher
import re

from core.documentos_usuario import _normalizar


_CONTROLES = (
    ("enfoca", r"(?:enfoca(?:me)?|cambia a|activa) (.+)"),
    ("enfoca", r"pon (.+) (?:delante|al frente)"),
    ("cierra", r"cierra (.+)"),
    ("minimiza", r"minimiza (.+)"),
    ("maximiza", r"maximiza (.+)"),
    ("restaura", r"restaura (.+)"),
)
_LISTAR = r"(?:muestra(?:me)?|lista|enumera) (?:todas )?(?:las )?ventanas(?: abiertas)?"


def interpretar(texto):
    if re.fullmatch(_LISTAR, texto):
        return "lista", ""
    texto = re.sub(r" (?:por favor|otra vez|de nuevo)$", "", texto)
    for accion, patron in _CONTROLES:
        coincidencia = re.fullmatch(patron, texto)
        if coincidencia and 2 <= len(coincidencia[1]) <= 100:
            nombre = re.sub(r"^(?:la ventana de|el programa|la aplicacion) ", "", coincidencia[1])
            return accion, nombre
    return None


def etiquetas(app):
    identificador = app.get("id") or ""
    corto = identificador.removesuffix(".desktop").rsplit(".", 1)[-1]
    return [app["nombre"], corto, app.get("ejecutable", ""), app.get("clase", "")]


def buscar(nombre, opciones, claves, *, aproximada=False):
    nombre = re.sub(r"^(?:el|la|los|las) ", "", nombre)
    candidatos = [(opcion, [_normalizar(valor) for valor in claves(opcion) if valor])
                  for opcion in opciones]
    exactas = [opcion for opcion, valores in candidatos if nombre in valores]
    if exactas:
        return exactas
    patron = re.compile(rf"(?<!\w){re.escape(nombre)}(?!\w)")
    parciales = [opcion for opcion, valores in candidatos if any(patron.search(valor) for valor in valores)]
    if parciales or not aproximada or len(nombre) < 4:
        return parciales
    return [opcion for opcion, valores in candidatos if any(
        SequenceMatcher(None, nombre, valor, autojunk=False).ratio() >= .78 for valor in valores)]
