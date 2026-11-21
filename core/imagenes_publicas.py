"""Descarga JPEG de un catálogo pequeño de fuentes públicas verificadas."""
from dataclasses import dataclass
from io import BytesIO
from urllib.request import Request, build_opener

from core.fuentes_publicas import MAX_BYTES, SinRedirecciones


@dataclass(frozen=True)
class ImagenPublica:
    pagina: str
    archivo: str
    nombre: str
    credito: str


CATALOGO = {
    "tierra": ImagenPublica(
        pagina="https://svs.gsfc.nasa.gov/30002/",
        archivo="https://svs.gsfc.nasa.gov/vis/a030000/a030000/a030002/npp-cropped_print.jpg",
        nombre="tierra-blue-marble-nasa.jpg",
        credito="NASA/NOAA/GSFC/Suomi NPP/VIIRS/Norman Kuring",
    ),
}


def descargar(imagen, *, abrir=None):
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise RuntimeError("Falta Pillow para verificar imágenes descargadas.") from exc

    req = Request(imagen.archivo, headers={"Accept": "image/jpeg", "User-Agent": "CerebroLocal/0.5"})
    cliente = abrir or build_opener(SinRedirecciones()).open
    with cliente(req, timeout=8) as respuesta:
        if respuesta.headers.get_content_type() != "image/jpeg":
            raise ValueError("La fuente devolvió un tipo diferente de JPEG.")
        datos = respuesta.read(MAX_BYTES + 1)
    if not datos or len(datos) > MAX_BYTES:
        raise ValueError("La descarga está vacía o supera 2 MiB.")
    try:
        with Image.open(BytesIO(datos), formats=("JPEG",)) as jpeg:
            ancho, alto = jpeg.size
            if ancho * alto > 4_000_000:
                raise ValueError("La imagen supera el límite de cuatro megapíxeles.")
            jpeg.load()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("El JPEG recibido no se pudo decodificar.") from exc
    return datos, ancho, alto
