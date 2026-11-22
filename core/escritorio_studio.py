"""Herramientas locales de Studio para carpetas, documentos y validaciones."""

import ast
import csv
from io import StringIO
import json
import os
from pathlib import Path
import re
from shutil import which
import subprocess
from tempfile import NamedTemporaryFile
from urllib.parse import unquote, urlsplit

from core.visores_studio import html_estatico

CARPETAS_XDG = {
    "DOCUMENTS": "Documentos", "DOWNLOAD": "Descargas", "PICTURES": "Imágenes",
    "VIDEOS": "Vídeos", "MUSIC": "Música", "DESKTOP": "Escritorio",
}


def carpetas_personales(hogar=None, configuracion=None):
    hogar = Path(hogar if hogar is not None else Path.home()).resolve()
    base = Path(configuracion or os.environ.get("XDG_CONFIG_HOME") or hogar / ".config")
    ruta = base / "user-dirs.dirs"
    encontradas = {}
    if ruta.is_file():
        with ruta.open(encoding="utf-8") as archivo:
            for linea in archivo.read(16384).splitlines():
                item = re.fullmatch(r'XDG_([A-Z]+)_DIR="([^"\\`]+)"\s*', linea.strip())
                if item and item[1] in CARPETAS_XDG:
                    valor = item[2]
                    if valor.startswith("$HOME/"):
                        valor = str(hogar / valor.removeprefix("$HOME/"))
                    if "$" not in valor and Path(valor).is_absolute():
                        encontradas[item[1]] = Path(valor)
    resultados = []
    for clave, nombre in CARPETAS_XDG.items():
        ingles = "Downloads" if clave == "DOWNLOAD" else clave.title()
        candidatos = (encontradas[clave],) if clave in encontradas else (hogar / nombre, hogar / ingles)
        for candidato in candidatos:
            if candidato.is_dir() and candidato.resolve() != hogar:
                resultados.append({"nombre": nombre, "ruta": str(candidato.resolve())})
                break
    for nombre in ("Proyectos", "Projects"):
        if (hogar / nombre).is_dir():
            resultados.append({"nombre": "Proyectos", "ruta": str((hogar / nombre).resolve())})
            break
    return resultados


def archivo_soltado(valor):
    if not isinstance(valor, str) or not 1 <= len(valor) <= 4096 or "\x00" in valor:
        raise ValueError("Ruta del archivo inválida.")
    uri = urlsplit(valor)
    if uri.netloc and not uri.scheme:
        raise ValueError("Arrastra un archivo local.")
    if uri.scheme:
        if uri.scheme != "file" or uri.netloc not in ("", "localhost") or uri.query or uri.fragment:
            raise ValueError("Arrastra un archivo local.")
        valor = unquote(uri.path)
    ruta = Path(valor)
    if not ruta.is_absolute() or "\x00" in valor:
        raise ValueError("Se requiere la ruta absoluta de un archivo local.")
    return ruta


def abrir_carpeta(ruta):
    for comando in ("thunar", "Thunar", "xdg-open"):
        programa = which(comando)
        if programa:
            subprocess.Popen([programa, str(ruta)], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return "Thunar" if comando.lower() == "thunar" else "el gestor predeterminado"
    raise RuntimeError("No encontré Thunar ni un gestor predeterminado.")


def cargar_preferencias(ruta):
    if not ruta.is_file() or ruta.is_symlink():
        return {}
    try:
        with ruta.open(encoding="utf-8") as archivo:
            datos = json.loads(archivo.read(32_769))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_preferencias(ruta, preferencias):
    with NamedTemporaryFile(dir=ruta.parent, mode="w", encoding="utf-8", delete=False) as temporal:
        json.dump(preferencias, temporal, ensure_ascii=False)
    fuente = Path(temporal.name)
    try:
        fuente.replace(ruta)
    finally:
        fuente.unlink(missing_ok=True)


def _constante_json(valor):
    raise ValueError(f"Constante JSON inválida: {valor}")


def validar_archivo(texto, nombre):
    extension = Path(nombre).suffix.lower()
    if extension == ".py":
        compile(texto, nombre, "exec", dont_inherit=True)
        return "Sintaxis Python válida."
    if extension == ".json":
        try:
            json.loads(texto, parse_constant=_constante_json)
        except json.JSONDecodeError as error:
            raise ValueError(f"JSON inválido en línea {error.lineno}, columna {error.colno}: {error.msg}.") from error
        return "Documento JSON válido."
    if extension in {".csv", ".tsv"}:
        lector = csv.reader(StringIO(texto), delimiter="\t" if extension == ".tsv" else ",", strict=True)
        try:
            inicial = next(lector, None)
            if inicial is None:
                raise ValueError("La tabla está vacía.")
            columnas = len(inicial)
            total = 1
            errores = []
            for total, fila in enumerate(lector, 2):
                if len(fila) != columnas and len(errores) < 15:
                    errores.append(str(total))
            if errores:
                raise ValueError("Número de columnas irregular en filas: " + ", ".join(errores))
        except csv.Error as error:
            raise ValueError(f"Tabla inválida: {error}") from error
        return f"Tabla válida: {total} filas y {columnas} columnas."
    if extension == ".html":
        contenido = html_estatico(texto)
        if not contenido:
            raise ValueError("El visor no encontró contenido estático visible.")
        return "El visor pudo extraer contenido HTML estático. La conformidad HTML no se ha comprobado."
    raise ValueError("Este formato no tiene un validador configurado.")


def analizar_texto(archivo, texto, accion):
    extension = Path(archivo).suffix.lower()
    if extension == ".html":
        texto = "".join(t for t, _ in html_estatico(texto))
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    if not lineas:
        raise ValueError("El archivo no contiene texto utilizable.")
    datos = {"archivo": archivo, "lineas": len(lineas), "palabras": len(texto.split())}
    if accion == "validar":
        return {**datos, "salida": validar_archivo(texto, archivo)}
    if accion == "evaluar":
        from core.profesor_local import ejercicio_documento
        return {**datos, "ejercicio": ejercicio_documento(lineas)}
    if extension == ".py" and accion == "analizar":
        try:
            arbol = ast.parse(texto)
        except SyntaxError as error:
            return {**datos, "salida": f"Error de sintaxis en línea {error.lineno}: {error.msg}"}
        funciones = [n.name for n in ast.walk(arbol) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        return {**datos, "salida": "Sintaxis Python válida. Funciones detectadas: " + (", ".join(funciones[:20]) or "ninguna")}
    if accion == "resumir":
        frases = re.split(r"(?<=[.!?])\s+", " ".join(lineas))
        return {**datos, "salida": "Resumen extractivo\n\n" + " ".join(frases[:3])[:700]}
    return {**datos, "salida": f"Documento de {len(lineas)} líneas y {len(texto.split())} palabras.\n\nPrimeras líneas\n"
            + "\n".join(lineas[:8])[:1000]}


HERRAMIENTAS = {
    "gestor": {"permiso": "READ", "descripcion": "Abrir la carpeta autorizada con Thunar o el gestor predeterminado."},
    "analizar": {"permiso": "READ", "descripcion": "Inspección sintáctica o rasgos del texto extraído."},
    "resumir": {"permiso": "READ", "descripcion": "Resumen extractivo del texto del visor."},
    "validar": {"permiso": "READ", "descripcion": "Validación local de Python, JSON, tablas o contenido HTML visible.",
                "extensiones": [".py", ".json", ".csv", ".tsv", ".html"]},
    "evaluar": {"permiso": "READ", "descripcion": "Ejercicio de comprensión basado en el documento."},
}
