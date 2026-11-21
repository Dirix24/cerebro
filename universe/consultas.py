"""Investigación pública y análisis acotado de archivos autorizados."""
from datetime import datetime
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.error import HTTPError
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
    return bool(re.fullmatch(r"(?:quiero programar|abre (?:el )?estudio|abre studio)", pregunta.strip(" ¿?!."), re.I))


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


def deduccion_en_frase(nucleo, pregunta):
    persona = r"([\w-]+(?: [\w-]+){0,4})"
    clase = r"([\w-]+(?: [\w-]+){0,4}?)"
    articulo = r"(?:(?:un|una|el|la) )?"
    premisas = re.fullmatch(
        rf"si {persona} es {articulo}{clase} y (?:todo|toda) {clase} es {articulo}{clase},"
        rf"\s*¿?{persona} es {articulo}{clase}\??", pregunta, re.I
    )
    if not premisas:
        return None
    individuo, categoria, origen, destino, consulta, objetivo = premisas.groups()
    if individuo.casefold() != consulta.casefold():
        return f"Las premisas hablan de {individuo}. No hay una premisa sobre {consulta}."
    return nucleo.chat.procesar(f"/deducir {individuo} es {categoria}; {origen} implica {destino} ? {objetivo}")[0]


def investigacion_externa(nucleo, pregunta):
    comando, _, argumentos = pregunta.partition(" ")
    comando = comando.casefold()
    repo = re.fullmatch(r"(?:explora|inspecciona|analiza|investiga|revisa) "
                        r"(?:(?:el )?repositorio )?(https://github\.com/[^\s]+|[\w.-]+/[\w.-]+)",
                        pregunta, re.I)
    if repo:
        comando, argumentos = "/github-explorar", repo[1]
    web = re.fullmatch(r"(?:busca|investiga) en la web\s+(.+)", pregunta, re.I)
    if web:
        comando, argumentos = "/web", web[1]
    clave = os.environ.get("CEREBRO_BRAVE_API_KEY")
    if clave and (web_general := re.fullmatch(r"(?:busca|consulta) en internet\s+(.+)", pregunta, re.I)):
        comando, argumentos = "/web", web_general[1]
    if comando not in ("/github-explorar", "/github-leer", "/web"):
        return None
    if not nucleo.internet:
        raise PermissionError("Las consultas públicas están desactivadas en este núcleo.")
    publicar("investigando", "consulta")
    try:
        if comando == "/web":
            from core.busqueda_web import buscar
            tema = tema_publico(argumentos)
            if not tema:
                return "Escribe un tema público breve, como «Busca en la web editores para MX Linux»."
            resultados = buscar(tema, clave)
            if not resultados:
                return "No encontré referencias web para ese tema."
            return "Resultados de búsqueda web (Brave Search)\n\n" + "\n\n".join(
                "\n".join(parte for parte in (titulo, extracto, enlace) if parte)
                for titulo, extracto, enlace in resultados
            )
        from core.github_local import explorar_publico, leer_publico
        repositorio, separador, ruta = argumentos.partition("||")
        ruta = ruta.strip() if separador else None
        if separador and not ruta:
            return f"Uso: {comando} propietario/repositorio || ruta/relativa"
        if comando == "/github-explorar":
            datos = explorar_publico(repositorio, ruta)
            lugar = datos["repo"] + (f" · {ruta}" if ruta else "")
            filas = ["Estructura de " + lugar, *datos["elementos"]]
            if datos["omitidos"]:
                filas.append(f"{datos['omitidos']} entradas adicionales.")
            filas.append("Fuente: " + datos["fuente"])
            return "\n".join(filas)
        datos = leer_publico(repositorio, ruta)
        extracto = datos["texto"][:3800]
        if len(extracto) < len(datos["texto"]):
            extracto += "\n[Extracto recortado]"
        return (f"Texto público de {datos['repo']}\n\n{extracto}\n\n"
                f"Fuente: {datos['fuente']}")
    except HTTPError as exc:
        publicar("error", "fallo")
        if exc.code in (403, 429):
            return "El servicio público limitó o rechazó la consulta. Prueba más tarde."
        if exc.code == 404:
            return "No encontré ese recurso público o no está disponible."
        return f"El servicio público devolvió HTTP {exc.code}."
    except (OSError, ValueError) as exc:
        publicar("error", "fallo")
        return str(exc) if isinstance(exc, ValueError) else "No pude conectar con la fuente pública."


def consulta_directa(nucleo, pregunta, modo=None):
    investigacion = investigacion_externa(nucleo, pregunta)
    if investigacion is not None:
        return investigacion
    explicacion = re.fullmatch(r"¿?(?:expl[ií]ca(?:me|lo)?|res[uú]me(?:lo)?|qu[eé] dice)"
                              r"(?: (?:m[aá]s|esto|eso|el (?:archivo|documento|v[ií]deo)|qu[eé] dice))?[?.]?",
                              pregunta, re.I)
    if explicacion:
        if not nucleo.archivo_en_contexto:
            return "Adjunta un archivo o pídeme que lo revise primero."
        try:
            return analizar_ruta(nucleo, nucleo.archivo_en_contexto, explicar=True)
        except (OSError, ValueError, SyntaxError, subprocess.SubprocessError, ElementTree.ParseError) as exc:
            return f"No pude explicar el archivo: {exc}"
    if modo in ("terminal", "studio") and re.fullmatch(r"¿?(?:qu[eé] sabes hacer|ayuda para programar)\??", pregunta, re.I):
        return ("Puedo generar funciones sencillas de Python, inspeccionar funciones e importaciones de tus archivos "
                "y comprobar su sintaxis en Studio. Prueba «Revisa src/ejemplo.py» o "
                "«Escribe una función en Python para sumar dos números».")
    if re.fullmatch(r"(?:guarda|recuerda) (?:lo aprendido|un resumen) (?:de este archivo|del archivo)", pregunta, re.I):
        if "WRITE" not in nucleo.agente.permisos_concedidos:
            raise PermissionError("Falta el permiso de escritura para guardar en memoria.")
        nombre = nucleo.archivo_en_contexto
        if not nombre:
            return "Primero adjunta un archivo y deja que lo analice."
        try:
            resumen = analizar_ruta(nucleo, nombre, explicar=True)
            clave = "archivo_" + Path(nombre).name
            cantidad = nucleo.memoria.importar_recuerdos({clave: resumen[:3600]})
        except (OSError, ValueError, SyntaxError, subprocess.SubprocessError, ElementTree.ParseError) as exc:
            return f"No pude guardar ese análisis: {exc}"
        if cantidad:
            publicar("aprendido", "memoria")
            return f"Guardé el análisis como recuerdo «{clave}»."
        return f"El análisis ya estaba guardado como «{clave}»."
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
            nombre = medio[1].strip()
            respuesta = analizar_ruta(nucleo, nombre)
            nucleo.archivo_en_contexto = nombre
            return respuesta
        except (ValueError, OSError, subprocess.SubprocessError, SyntaxError, ElementTree.ParseError) as exc:
            return f"No pude analizar el archivo: {exc}"
    razonamiento = deduccion_en_frase(nucleo, pregunta)
    if razonamiento:
        return razonamiento
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


def analizar_ruta(nucleo, nombre, *, explicar=False):
    from core.analizador_codigo_local import analizar
    from zipfile import BadZipFile

    ruta = nucleo.ruta(nombre, lectura=True)
    if not ruta.is_file():
        raise ValueError("Adjunta el archivo primero o ponlo en el espacio de trabajo de Studio.")
    sufijo = ruta.suffix.lower()
    if sufijo == ".py":
        hallazgos = analizar(_leer_texto(ruta))
        publicar("razonando", "herramienta")
        informe = "\n".join(f"{clave.capitalize()}: {', '.join(valores) or 'ninguna'}"
                            for clave, valores in hallazgos.items())
        if explicar:
            from ast import AsyncFunctionDef, ClassDef, FunctionDef, get_docstring, parse
            arbol = parse(_leer_texto(ruta))
            anotaciones = [f"{nodo.name}: {doc.splitlines()[0][:180]}"
                          for nodo in arbol.body if isinstance(nodo, (FunctionDef, AsyncFunctionDef, ClassDef))
                          and (doc := get_docstring(nodo))]
            if anotaciones:
                informe += "\n\nDescripción declarada en el código\n" + "\n".join(anotaciones[:8])
            else:
                informe += "\n\nPuedo identificar la estructura del programa. No hay descripciones en sus funciones o clases."
        return nombre + "\nAnálisis estático de Python\n" + informe
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
    if explicar:
        from core.estudio_local import palabras_clave, resumir
        palabras = palabras_clave(texto[:8000], limite=6)
        puntos = resumir(" ".join(texto[:8000].split()), max_frases=4)
        return (f"Qué dice {nombre}\n\nPasajes principales\n{puntos or 'No hay texto legible.'}"
                + ("\n\nTemas del archivo: " + ", ".join(palabras) if palabras else ""))
    return nombre + "\nExtracto del texto disponible\n\n" + _extracto(texto)
