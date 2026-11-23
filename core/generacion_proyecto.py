"""Validación de propuestas de archivos devueltas por el modelo local."""
import ast
import difflib
import json
from pathlib import Path
import re

PATRON_NOMBRE = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,74}\.(py|html|css|js|ts|sql|sh|c|cpp|h|java|md|txt)$"
EXTENSIONES = (".py", ".html", ".css", ".js", ".ts", ".sql", ".sh", ".c", ".cpp", ".h", ".java", ".md", ".txt")
ESQUEMA = {"type": "object", "required": ["archivos"], "additionalProperties": False, "properties": {
    "archivos": {"type": "array", "minItems": 1, "maxItems": 6, "items": {
        "type": "object", "required": ["nombre", "texto"], "additionalProperties": False,
        "properties": {"nombre": {"type": "string", "pattern": PATRON_NOMBRE},
                       "texto": {"type": "string", "minLength": 1}}}}}}


def esquema_para(objetivo):
    from copy import deepcopy

    formato = deepcopy(ESQUEMA)
    token = r"(?<![\w/])(" + PATRON_NOMBRE[1:-1] + r")(?![\w/])"
    nombres = sorted({coincidencia[1] for coincidencia in re.finditer(token, objetivo)})
    if len(nombres) == 1:
        archivos = formato["properties"]["archivos"]
        archivos["maxItems"] = 1
        archivos["items"]["properties"]["nombre"] = {"enum": nombres}
    return formato


def validar(respuesta):
    try:
        propuesta = json.loads(respuesta)
    except (TypeError, ValueError) as exc:
        raise ValueError("El modelo no devolvió una propuesta JSON válida.") from exc
    if not isinstance(propuesta, dict) or set(propuesta) != {"archivos"}:
        raise ValueError("La propuesta del modelo tiene un formato inesperado.")
    archivos = propuesta["archivos"]
    if not isinstance(archivos, list) or not 1 <= len(archivos) <= 6:
        raise ValueError("La propuesta debe tener entre uno y seis archivos.")
    salida = {}
    for archivo in archivos:
        if not isinstance(archivo, dict) or set(archivo) != {"nombre", "texto"}:
            raise ValueError("La propuesta contiene un archivo inválido.")
        nombre, texto = archivo["nombre"], archivo["texto"]
        if (not isinstance(nombre, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", nombre)
                or Path(nombre).suffix.lower() not in EXTENSIONES
                or nombre.casefold() in (n.casefold() for n in salida)):
            raise ValueError("La propuesta contiene un nombre no permitido o repetido.")
        if not isinstance(texto, str) or not texto.strip() or "\x00" in texto:
            raise ValueError("La propuesta contiene un archivo sin texto válido.")
        if nombre.endswith(".py"):
            try:
                ast.parse(texto, filename=nombre)
            except SyntaxError as exc:
                raise ValueError(f"{nombre}: error de sintaxis en línea {exc.lineno}: {exc.msg}.") from exc
        salida[nombre] = texto if texto.endswith("\n") else texto + "\n"
    if sum(len(texto) for texto in salida.values()) > 5500:
        raise ValueError("La propuesta supera el límite de 5500 caracteres.")
    return salida


def diferencias(archivos):
    return "\n".join("".join(difflib.unified_diff([], texto.splitlines(keepends=True), "/dev/null", nombre))
                     for nombre, texto in archivos.items())
