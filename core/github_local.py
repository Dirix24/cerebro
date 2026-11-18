"""Consulta pública y de solo lectura de un repositorio GitHub explícito.

No usa modelos externos ni ejecuta comandos. No incluye autenticación ni
modificaciones remotas. Se necesita conexión de red al consultar.
"""
import json
import re
from urllib.request import Request, urlopen

_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")


def estado_publico(repositorio, *, abrir=urlopen):
    if not _REPO.fullmatch(repositorio) or ".." in repositorio:
        raise ValueError("Repositorio inválido; usa propietario/nombre")
    url = "https://api.github.com/repos/" + repositorio
    solicitud = Request(url, headers={"Accept": "application/vnd.github+json",
                                     "User-Agent": "Cerebro-V2-local"})
    with abrir(solicitud, timeout=8) as respuesta:
        datos = json.load(respuesta)
    return {"repositorio": datos["full_name"], "rama": datos["default_branch"],
            "privado": datos["private"], "url": datos["html_url"],
            "actualizado": datos.get("pushed_at"),
            "modo": "solo_lectura", "modelo_ia_externo": False}


def incidencias_publicas(repositorio, *, abrir=urlopen):
    """Consulta incidencias públicas sin credenciales ni escrituras."""
    if not _REPO.fullmatch(repositorio) or ".." in repositorio:
        raise ValueError("Repositorio inválido; usa propietario/nombre")
    solicitud = Request("https://api.github.com/repos/" + repositorio +
                        "/issues?state=open&per_page=20",
                        headers={"Accept": "application/vnd.github+json",
                                 "User-Agent": "Cerebro-V2-local"})
    with abrir(solicitud, timeout=8) as respuesta:
        datos = json.load(respuesta)
    return [{"numero": item["number"], "titulo": item["title"],
             "url": item["html_url"]} for item in datos
            if "pull_request" not in item]
