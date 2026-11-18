"""Generación de PDF de texto en el espacio de trabajo, sin contenido remoto."""
from pathlib import Path
import re

import config

_NOMBRE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")


def crear_pdf(nombre, texto, raiz=None):
    if not _NOMBRE.fullmatch(nombre):
        raise ValueError("Nombre inválido.")
    if not texto.strip() or len(texto) > 20000:
        raise ValueError("El texto debe tener entre 1 y 20000 caracteres.")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from xml.sax.saxutils import escape
    except ImportError as exc:
        raise RuntimeError("Instala reportlab para crear PDF: pip install reportlab") from exc
    base = Path(raiz or config.WORKSPACE_DIR).resolve()
    base.mkdir(parents=True, exist_ok=True)
    destino = base / (nombre + ".pdf")
    # Evitar sobrescribir documentos existentes.
    with destino.open("xb") as archivo:
        try:
            doc = SimpleDocTemplate(archivo, pagesize=A4)
            estilo = getSampleStyleSheet()["BodyText"]
            elementos = []
            for linea in texto.splitlines() or [texto]:
                elementos.append(Paragraph(escape(linea) or " ", estilo))
                elementos.append(Spacer(1, 6))
            doc.build(elementos)
        except Exception:
            destino.unlink(missing_ok=True)
            raise
    return str(destino)
