"""Lee texto de DOCX y ODT localmente, con límites y sin abrir recursos externos."""
from io import BytesIO
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

_ESQUEMAS = {
    ".docx": ("word/document.xml", "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"),
    ".odt": ("content.xml", "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"),
}
_MAX_XML = 2 * 1024 * 1024


class _ArbolAcotado(ElementTree.TreeBuilder):
    profundidad = 0

    def start(self, tag, attrs):
        self.profundidad += 1
        if self.profundidad > 64:
            raise ValueError("El documento supera la profundidad XML admitida.")
        return super().start(tag, attrs)

    def end(self, tag):
        self.profundidad -= 1
        return super().end(tag)


def extraer_texto(bruto, extension):
    miembro, espacio = _ESQUEMAS[extension]
    try:
        with ZipFile(BytesIO(bruto)) as paquete:
            info = paquete.getinfo(miembro)
            if info.file_size > _MAX_XML:
                raise ValueError("El texto interno del documento supera 2 MiB.")
            with paquete.open(info) as archivo:
                xml = archivo.read(_MAX_XML + 1).decode("utf-8")
        if len(xml) > _MAX_XML or re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", xml, re.I):
            raise ValueError("El documento contiene XML fuera de los límites del visor.")
        raiz = ElementTree.fromstring(xml, parser=ElementTree.XMLParser(target=_ArbolAcotado()))
    except (BadZipFile, KeyError, RuntimeError, UnicodeError, ElementTree.ParseError, NotImplementedError) as error:
        raise ValueError("No se pudo extraer el texto del documento.") from error
    if extension == ".docx":
        parrafos = ("".join(texto.text or "" for texto in parrafo.iter(espacio + "t"))
                    for parrafo in raiz.iter(espacio + "p"))
    else:
        parrafos = ("".join(parrafo.itertext()) for parrafo in raiz.iter()
                    if parrafo.tag in {espacio + "p", espacio + "h"})
    return "\n".join(filter(str.strip, parrafos))[:160_000]
