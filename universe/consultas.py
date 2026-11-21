"""Investigación pública y análisis acotado de archivos autorizados."""
from datetime import datetime
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from zipfile import ZipFile

from core.actividad_neuronal import publicar

CANAL = "https://feeds.bbci.co.uk/mundo/rss.xml"
DOCUMENTOS = {".txt", ".md", ".csv", ".json", ".pdf", ".docx", ".vtt", ".srt", ".py"}
VIDEOS = {".mp4": "mov", ".mov": "mov", ".mkv": "matroska", ".webm": "matroska"}
PRIVADO = re.compile(r"\b(?:mi|mis|m[ií]o|m[ií]a|contrase[ñn]a|clave|archivo|documento|correo|recuerdo|tel[eé]fono)\b",
                     re.IGNORECASE)


def tema_publico(texto):
    tema = texto.strip(" ¿?¡!.,")
    if not 2 <= len(tema) <= 150 or not re.fullmatch(r"[\wáéíóúüñ -]+", tema, re.UNICODE):
        return None
    if PRIVADO.search(tema) or "/" in tema or "_" in tema or sum(c.isdigit() for c in tema) > 4:
        return None
    return tema


def _actualidad():
    with urlopen(Request(CANAL, headers={"User-Agent": "CerebroLocal/0.4"}), timeout=8) as respuesta:
        datos = respuesta.read(1_250_001)
    if len(datos) > 1_250_000 or b"<!DOCTYPE" in datos.upper():
        raise ValueError("El canal devolvió contenido no admitido.")
    articulos = []
    for item in ElementTree.fromstring(datos).findall("./channel/item"):
        enlace = item.findtext("link", "").strip()
        titulo = item.findtext("title", "").strip()
        url = urlsplit(enlace)
        if url.scheme != "https" or url.hostname not in {"www.bbc.com", "www.bbc.co.uk", "bbc.com"} or not titulo:
            continue
        try:
            fecha = parsedate_to_datetime(item.findtext("pubDate", "")).astimezone()
        except (ValueError, TypeError):
            continue
        articulos.append((fecha, titulo, enlace))
    return sorted(articulos, reverse=True)[:5]


def actualidad(habilitada):
    if not habilitada:
        return "Las consultas públicas están desactivadas en este núcleo."
    publicar("investigando", "consulta")
    try:
        articulos = _actualidad()
    except (OSError, ValueError, ElementTree.ParseError):
        publicar("error", "fallo")
        return "No pude consultar BBC Mundo en este momento."
    if not articulos:
        return "BBC Mundo no devolvió titulares con fecha."
    return "Titulares recientes de BBC Mundo\n\n" + "\n\n".join(
        f"{fecha:%d/%m/%Y %H:%M %Z} · {titulo}\n{enlace}" for fecha, titulo, enlace in articulos
    )


def desea_studio(pregunta):
    return bool(re.fullmatch(r"(?:quiero programar|abre (?:el )?estudio|abre studio)", pregunta, re.I))


def ejemplo_codigo(pregunta):
    pedido = re.fullmatch(r"(?:crea|escribe|programa)(?:me)? (?:una )?funci[oó]n (?:en )?python "
                          r"(?:para |que )?(sumar|sume|restar|reste|multiplicar|multiplique|dividir|divida)"
                          r"(?: dos n[uú]meros)?[.!]?", pregunta, re.I)
    if not pedido:
        return None
    operacion = pedido[1].casefold()[:3]
    nombre, simbolo = {"sum": ("sumar", "+"), "res": ("restar", "-"),
                       "mul": ("multiplicar", "*"), "div": ("dividir", "/")}[operacion]
    codigo = f"def {nombre}(a, b):\n"
    if simbolo == "/":
        codigo += '    if b == 0:\n        raise ValueError("No se puede dividir por cero.")\n'
    codigo += f"    return a {simbolo} b"
    publicar("creando", "herramienta")
    return codigo


def consulta_directa(nucleo, pregunta):
    actual = re.fullmatch(r"¿?(?:investiga(?: y dime)?(?: la actualidad| las noticias(?: de hoy)?)?"
                          r"|(?:dime |cu[eé]ntame )?(?:las )?noticias de hoy"
                          r"|qu[eé] (?:ha pasado|est[aá] pasando) hoy)\??", pregunta, re.I)
    if actual:
        return actualidad(nucleo.internet)
    pedido = re.fullmatch(r"investiga(?:\s+sobre)?\s*[: ]\s*(.+)", pregunta, re.I)
    if pedido:
        if not nucleo.internet:
            return "Las consultas públicas están desactivadas en este núcleo."
        tema = tema_publico(pedido[1])
        if not tema:
            return "Dime un tema público breve, como «Investiga la fotosíntesis»."
        return nucleo.chat.procesar(f"/internet {tema}")[0]
    if re.fullmatch(r"¿?qu[eé] (?:hora es|d[ií]a es hoy|fecha es hoy)\??", pregunta, re.I):
        return "Fecha y hora del equipo: " + datetime.now().astimezone().strftime("%d/%m/%Y %H:%M %Z")
    medio = re.fullmatch(r"(?:lee|resume|analiza|revisa)\s+(?:(?:el|la|este|esta)\s+)?"
                         r"(?:(?:documento|archivo|v[ií]deo|c[oó]digo)\s*:?\s+)?"
                         r"([\w ./-]+\.[a-zA-Z0-9]{2,5})", pregunta, re.I)
    if medio:
        try:
            return analizar_ruta(nucleo, medio[1].strip())
        except (ValueError, OSError, subprocess.SubprocessError, SyntaxError, ElementTree.ParseError) as exc:
            return f"No pude analizar el archivo: {exc}"
    codigo = ejemplo_codigo(pregunta)
    if codigo:
        return codigo
    if desea_studio(pregunta):
        return "Abre Cerebro Studio para editar archivos, revisar Python y ver tareas."
    return None


def alternativa_publica(nucleo, pregunta, respuesta):
    if not nucleo.investigar_auto or not respuesta.startswith((
        "No encontré una definición fiable", "No encontré una definición en mis fuentes",
        "No tengo una respuesta fiable", "¿Querías decir «qué es ",
    )):
        return respuesta
    consulta = re.fullmatch(r"¿?\s*(?:(?:qu[eé]|qeu) (?:es|son)|qui[eé]n (?:es|fue)|"
                            r"d[oó]nde queda|cu[aá]l es la capital de)\s+(.+)\??", pregunta, re.I)
    if not consulta:
        return respuesta
    tema = tema_publico(consulta[1])
    if not tema:
        return respuesta
    if re.match(r"¿?\s*cu[aá]l es la capital de", pregunta, re.I):
        tema = "capital de " + tema
    return nucleo.chat.procesar(f"/internet {tema}")[0]


def _leer_texto(ruta):
    if ruta.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("El documento supera 16 MiB.")
    if ruta.suffix.lower() == ".pdf":
        pdftotext = shutil.which("pdftotext")
        if not pdftotext:
            raise ValueError("Para leer PDF de texto, instala poppler-utils.")
        resultado = subprocess.run([pdftotext, "-f", "1", "-l", "12", "-enc", "UTF-8", str(ruta), "-"],
                                    capture_output=True, timeout=12, check=True)
        return resultado.stdout[:160000].decode("utf-8", errors="replace")
    if ruta.suffix.lower() == ".docx":
        with ZipFile(ruta) as zip_archivo:
            entrada = zip_archivo.getinfo("word/document.xml")
            if entrada.file_size > 2 * 1024 * 1024:
                raise ValueError("El documento descomprimido supera el límite.")
            cuerpo = zip_archivo.read(entrada)
        if b"<!DOCTYPE" in cuerpo.upper():
            raise ValueError("XML no admitido.")
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        return "\n".join("".join(x.text or "" for x in p.iter(ns + "t"))
                         for p in ElementTree.fromstring(cuerpo).iter(ns + "p"))
    with ruta.open("rb") as archivo:
        return archivo.read(160000).decode("utf-8", errors="replace")


def _extracto(texto):
    from core.estudio_local import resumir
    texto = " ".join(texto.split())
    if not texto:
        return "No encontré texto legible."
    return resumir(texto[:8000])


def analizar_ruta(nucleo, nombre):
    from core.analizador_codigo_local import analizar
    from zipfile import BadZipFile

    ruta = nucleo.ruta(nombre, lectura=True)
    if not ruta.is_file():
        raise ValueError("Adjunta el archivo primero o ponlo en el espacio de trabajo de Studio.")
    sufijo = ruta.suffix.lower()
    if sufijo == ".py":
        hallazgos = analizar(_leer_texto(ruta))
        publicar("razonando", "herramienta")
        return nombre + "\nAnálisis estático de Python\n" + "\n".join(
            f"{clave.capitalize()}: {', '.join(valores) or 'ninguna'}" for clave, valores in hallazgos.items()
        )
    if sufijo in VIDEOS:
        extractor = shutil.which("ffprobe")
        partes = [f"Vídeo: {nombre}"]
        if extractor:
            salida = subprocess.run([extractor, "-v", "error", "-protocol_whitelist", "file",
                "-f", VIDEOS[sufijo], "-show_entries", "format=duration:stream=codec_name,codec_type,width,height",
                "-of", "json", str(ruta)], capture_output=True, check=True, timeout=12)
            info = json.loads(salida.stdout)
            partes.append(f"Duración en segundos: {info.get('format', {}).get('duration', 'desconocida')}")
            partes.extend(f"{s.get('codec_type', '?')}: {s.get('codec_name', '?')} "
                           f"{s.get('width', '')}×{s.get('height', '')}".rstrip(" ×")
                           for s in info.get("streams", [])[:16])
        else:
            partes.append("Instala FFmpeg para ver duración, resolución y pistas.")
        for extension in (".vtt", ".srt"):
            subtitulo = nucleo.ruta(str(Path(nombre).with_suffix(extension)), lectura=True)
            if subtitulo.is_file():
                texto = re.sub(r"(?m)^(?:WEBVTT.*|\d+|[^\n]*-->[^\n]*)$", "", _leer_texto(subtitulo))
                partes.append(f"Extracto de {subtitulo.name}\n" + _extracto(texto))
                break
        else:
            partes.append("Adjunta subtítulos SRT o VTT con el mismo nombre para analizar lo dicho.")
        return "\n\n".join(partes)
    try:
        texto = _leer_texto(ruta)
    except (BadZipFile, KeyError) as exc:
        raise ValueError("El documento DOCX no es válido.") from exc
    publicar("recuperando", "herramienta")
    return nombre + "\nExtracto del texto disponible\n\n" + _extracto(texto)
