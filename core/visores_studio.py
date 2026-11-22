"""Vistas locales de datos. Los documentos nunca se ejecutan."""

import base64
import csv
from html.parser import HTMLParser
from io import StringIO
import os
import re
import shutil
import subprocess
from tempfile import TemporaryFile


HTML_INICIAL = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Mi proyecto</title></head>
<body><main><h1>Mi proyecto</h1><p>Edita esta página en Cerebro Studio.</p></main></body></html>
"""


class PaginaEstatica(HTMLParser):
    BLOQUES = {"h1", "h2", "h3", "p", "div", "section", "li", "br", "tr", "pre", "article"}
    INVISIBLES = {"script", "style", "iframe", "object", "template", "svg", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ocultos = []
        self.fragmentos = []
        self.etiqueta = ""

    def handle_starttag(self, tag, attrs):
        if tag in self.INVISIBLES:
            self.ocultos.append(tag)
        if self.ocultos:
            return
        if tag in self.BLOQUES:
            self.fragmentos.append(("\n", ""))
        if tag in {"h1", "h2", "h3", "pre"}:
            self.etiqueta = "titulo" if tag != "pre" else "codigo"
        if tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.fragmentos.append(("[Imagen: " + alt[:150] + "]", ""))
        elif tag == "li":
            self.fragmentos.append(("• ", ""))
        elif tag in {"td", "th"}:
            self.fragmentos.append(("  ", ""))

    def handle_endtag(self, tag):
        if self.ocultos:
            if tag == self.ocultos[-1]:
                self.ocultos.pop()
            return
        if tag in self.BLOQUES:
            self.fragmentos.append(("\n", ""))
        if tag in {"h1", "h2", "h3", "pre"}:
            self.etiqueta = ""

    def handle_data(self, data):
        if not self.ocultos:
            contenido = data if self.etiqueta == "codigo" else re.sub(r"\s+", " ", data)
            if contenido.strip() or contenido == " ":
                self.fragmentos.append((contenido, self.etiqueta))


def html_estatico(texto):
    pagina = PaginaEstatica()
    pagina.feed(texto)
    pagina.close()
    return pagina.fragmentos


def tabla(texto, extension):
    filas = []
    lector = csv.reader(StringIO(texto), delimiter="\t" if extension == ".tsv" else ",")
    for fila in lector:
        filas.append([celda[:250] for celda in fila[:24]])
        if len(filas) >= 201:
            break
    return filas


def _poppler(programa, opciones, bruto):
    ejecutable, limites = shutil.which(programa), shutil.which("prlimit")
    if not ejecutable or not limites:
        raise ValueError("Instala poppler-utils y util-linux para previsualizar PDF.")
    comando = [limites, "--as=536870912", "--cpu=4", "--fsize=2097152", "--nofile=64",
               "--", ejecutable, *opciones]
    try:
        with TemporaryFile() as salida:
            resultado = subprocess.run(comando, input=bruto, stdout=salida,
                                       stderr=subprocess.DEVNULL, timeout=6, env={**os.environ, "LC_ALL": "C"})
            if resultado.returncode:
                raise ValueError("No pude leer el PDF o se superó el límite del visor.")
            salida.seek(0)
            return salida.read(2 * 1024 * 1024)
    except subprocess.TimeoutExpired:
        raise ValueError("La vista previa del PDF agotó el tiempo.") from None


def pdf_paginas(bruto):
    ficha = _poppler("pdfinfo", ["-"], bruto)
    total = re.search(rb"^Pages:\s*([0-9]+)", ficha, re.M)
    if not total or not int(total[1]):
        raise ValueError("No pude determinar cuántas páginas contiene el PDF.")
    return int(total[1])


def pdf_texto(bruto, primera, ultima):
    return _poppler("pdftotext", ["-f", str(primera), "-l", str(ultima), "-layout", "-", "-"], bruto)


def pdf_buscar(bruto, consulta):
    consulta = consulta.strip() if isinstance(consulta, str) else ""
    if not 1 <= len(consulta) <= 160:
        raise ValueError("Escribe una búsqueda de hasta 160 caracteres.")
    total = pdf_paginas(bruto)
    limite = min(total, 50)
    texto = pdf_texto(bruto, 1, limite).decode("utf-8", "replace")
    coincidencias = []
    for numero, pagina in enumerate(texto.split("\f")[:limite], 1):
        plana = " ".join(pagina.split())
        if consulta.casefold() in plana.casefold():
            linea = next((l.strip() for l in pagina.splitlines() if consulta.casefold() in l.casefold()), "")
            coincidencias.append({"pagina": numero, "fragmento": linea[:280]})
    return {"coincidencias": coincidencias, "revisadas": limite, "paginas": total}


def pdf_vista(bruto, pagina=1, resolucion=980):
    total = pdf_paginas(bruto)
    if type(pagina) is not int or not 1 <= pagina <= total:
        raise ValueError(f"Selecciona una página entre 1 y {total}.")
    if type(resolucion) is not int or not 320 <= resolucion <= 2200:
        raise ValueError("La resolución del visor debe estar entre 320 y 2200 píxeles.")
    intervalo = ["-f", str(pagina), "-l", str(pagina)]
    texto = pdf_texto(bruto, pagina, pagina)
    vista = {"texto": texto[:256 * 1024].decode("utf-8", "replace").strip(),
             "pagina": pagina, "paginas": total, "resolucion": resolucion}
    try:
        imagen = _poppler("pdftoppm", [*intervalo, "-scale-to", str(resolucion), "-png", "-singlefile", "-"], bruto)
    except ValueError:
        vista["aviso"] = "Se muestra el texto de la página. No se pudo dibujar con esa resolución."
    else:
        if imagen.startswith(b"\x89PNG\r\n\x1a\n"):
            vista["base64"] = base64.b64encode(imagen).decode("ascii")
    return vista


def narrar(resultados):
    """Sintetiza hechos y limitaciones para el chat, sin prefijos de especialistas."""
    partes = []
    for resultado in resultados:
        if resultado.get("error"):
            partes.append(resultado["error"])
        if plan := resultado.get("plan"):
            primera = next((paso for paso in plan if paso.get("estado") == "lista"), plan[0])
            partes.append(f"Preparé un plan de {len(plan)} pasos. El siguiente paso es «{primera['titulo']}».")
        if simulacion := resultado.get("simulacion"):
            partes.append(f"La simulación estima un p50 de {simulacion['p50_horas']} h y un p90 de "
                          f"{simulacion['p90_horas']} h según las duraciones de referencia.")
        pruebas = []
        fuentes = []
        archivos = []
        cambios = []
        for item in resultado.get("evidencia", []):
            tipo = item["tipo"]
            if tipo == "fuente":
                fuentes.append(item)
            elif tipo == "analisis":
                archivos.append(item)
            elif tipo == "propuesta":
                cambios.append(item["path"])
            elif tipo in {"prueba", "prueba_registrada"}:
                pruebas.append(item)
        if fuentes:
            partes.append(f"Encontré {len(fuentes)} referencias. Puedes revisarlas en Resultados.")
        if archivos:
            errores = sum(len(a.get("errores", [])) for a in archivos)
            partes.append(f"Revisé {len(archivos)} archivos, incluido «{archivos[0]['path']}». "
                          f"El análisis registró {errores} errores sintácticos.")
        if cambios:
            partes.append("Preparé cambios pendientes de revisión para " + ", ".join(cambios) + ".")
        for prueba in pruebas:
            partes.append(f"Prueba {'registrada' if prueba['tipo'] == 'prueba_registrada' else 'ejecutada'}: "
                          f"{prueba['state']} (código {prueba['returncode']}).")
        partes.extend(resultado.get("avisos", []))
        if ejercicio := resultado.get("ejercicio"):
            partes.append(ejercicio["pregunta"] + " Puedes decir «Mi respuesta es» seguido del identificador.")
        if evaluacion := resultado.get("evaluacion"):
            partes.append(evaluacion["detalle"])
        if not any((resultado.get("error"), plan, simulacion, pruebas, fuentes, archivos, cambios,
                    resultado.get("avisos"), ejercicio, evaluacion)):
            partes.append("La consulta no devolvió resultados para mostrar.")
    return "\n\n".join(partes)
