"""Transporte acotado para las API de investigación configuradas en código."""
import json
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOSTS = frozenset({"api.github.com", "api.search.brave.com", "es.wikipedia.org"})
MAX_BYTES = 2 * 1024 * 1024


class SinRedirecciones(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def consultar_json(url, cabeceras=None, *, abrir=None):
    destino = urlsplit(url)
    if (destino.scheme != "https" or destino.netloc not in HOSTS or destino.fragment
            or not destino.path.startswith("/")):
        raise ValueError("Destino público no admitido.")
    req = Request(url, headers={"User-Agent": "CerebroLocal/0.5",
                                "Accept": "application/json", **(cabeceras or {})})
    cliente = abrir or build_opener(SinRedirecciones()).open
    with cliente(req, timeout=8) as respuesta:
        datos = respuesta.read(MAX_BYTES + 1)
    if len(datos) > MAX_BYTES:
        raise ValueError("La respuesta pública supera 2 MiB.")
    return json.loads(datos)
