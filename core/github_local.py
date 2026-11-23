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


def identificar_repositorio(valor):
    """Acepta propietario/nombre o el enlace base de GitHub."""
    from urllib.parse import urlsplit

    valor = valor.strip()
    if valor.startswith("https://"):
        url = urlsplit(valor)
        if url.netloc != "github.com" or url.query or url.fragment:
            raise ValueError("Usa un enlace base HTTPS de github.com.")
        valor = url.path.removeprefix("/").removesuffix("/").removesuffix(".git")
    if not _REPO.fullmatch(valor) or any(parte in {".", ".."} for parte in valor.split("/")):
        raise ValueError("Usa propietario/repositorio o https://github.com/propietario/repositorio.")
    return valor


def _datos_publicos(repositorio, ruta="", *, abrir=None):
    from core.fuentes_publicas import consultar_json

    repo = identificar_repositorio(repositorio)
    return consultar_json("https://api.github.com/repos/" + repo + ruta,
                          {"Accept": "application/vnd.github+json"}, abrir=abrir)


def _ruta_contenido(ruta):
    from urllib.parse import quote

    if (not re.fullmatch(r"[\w ./-]{1,240}", ruta)
            or any(parte in {"", ".", ".."} for parte in ruta.split("/"))):
        raise ValueError("Usa una ruta relativa al repositorio de GitHub.")
    return "/contents/" + quote(ruta, safe="/")


def explorar_publico(repositorio, carpeta=None, *, abrir=None):
    repo = identificar_repositorio(repositorio)
    ruta = "/contents" if carpeta is None else _ruta_contenido(carpeta)
    raiz = _datos_publicos(repo, ruta, abrir=abrir)
    if not isinstance(raiz, list):
        raise ValueError("GitHub devolvió un listado inválido.")
    elementos = sorted((item["type"], item["name"]) for item in raiz
                       if isinstance(item, dict) and item.get("type") in ("dir", "file")
                       and isinstance(item.get("name"), str))
    disponibles = ["[carpeta] " + nombre if tipo == "dir" else nombre
                   for tipo, nombre in elementos[:45]]
    return {"repo": repo, "elementos": disponibles, "omitidos": max(0, len(elementos) - len(disponibles)),
            "fuente": "https://github.com/" + repo}


def leer_publico(repositorio, archivo=None, *, abrir=None):
    import base64

    repo = identificar_repositorio(repositorio)
    ruta = "/readme" if archivo is None else _ruta_contenido(archivo)
    dato = _datos_publicos(repo, ruta, abrir=abrir)
    if (not isinstance(dato, dict) or dato.get("type") != "file"
            or dato.get("encoding") != "base64" or type(dato.get("size")) is not int
            or not 0 <= dato["size"] <= 128 * 1024 or not isinstance(dato.get("content"), str)):
        raise ValueError("Solo se admiten archivos de texto de hasta 128 KiB.")
    contenido = base64.b64decode("".join(dato["content"].split()), validate=True)
    if len(contenido) != dato["size"] or b"\0" in contenido:
        raise ValueError("El documento no es texto UTF-8 válido.")
    texto = contenido.decode("utf-8")
    fuente = dato.get("html_url")
    if not isinstance(fuente, str) or not fuente.startswith("https://github.com/" + repo + "/"):
        fuente = "https://github.com/" + repo
    return {"repo": repo, "fuente": fuente, "texto": texto}


def _referencia(valor):
    from urllib.parse import quote

    if (not isinstance(valor, str) or not re.fullmatch(r"[A-Za-z0-9_./-]{1,120}", valor)
            or ".." in valor or any(not parte or parte.startswith(".") for parte in valor.split("/"))):
        raise ValueError("Referencia Git inválida.")
    return quote(valor, safe="")


def comparar_publico(repositorio, base, destino, *, abrir=None):
    datos = _datos_publicos(repositorio, "/compare/" + _referencia(base) + "..." + _referencia(destino), abrir=abrir)
    if not isinstance(datos, dict) or datos.get("status") not in {"identical", "ahead", "behind", "diverged"}:
        raise ValueError("GitHub devolvió una comparación inválida.")
    return {"repositorio": identificar_repositorio(repositorio), "base": base, "destino": destino,
            "estado": datos["status"], "adelante": datos.get("ahead_by", 0), "atras": datos.get("behind_by", 0)}


def repositorios_cuenta():
    """Consulta la credencial gestionada por gh, sin leerla ni exportarla."""
    import os
    from shutil import which
    import subprocess

    ejecutable = which("gh")
    if not ejecutable:
        raise RuntimeError("Instala GitHub CLI y conecta tu cuenta mediante gh auth login.")
    entorno = {**os.environ, "GH_PROMPT_DISABLED": "1"}
    try:
        salida = subprocess.run([ejecutable, "api", "--hostname", "github.com",
                                  "/user/repos?per_page=20&sort=updated", "--jq", "[.[].full_name]"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 timeout=10, check=True, env=entorno)
        datos = json.loads(salida.stdout)
        if not isinstance(datos, list):
            raise ValueError("Listado inválido")
        return [identificar_repositorio(nombre) for nombre in datos[:20] if isinstance(nombre, str)]
    except (OSError, ValueError, subprocess.SubprocessError):
        raise RuntimeError("No pude consultar tu cuenta de GitHub. Comprueba gh auth status.") from None


def actividad_publica(repositorio, recurso, *, abrir=None):
    rutas = {"ramas": "branches", "commits": "commits", "issues": "issues",
             "pull requests": "pulls"}
    if recurso not in rutas:
        raise ValueError("Recurso de GitHub desconocido.")
    datos = _datos_publicos(repositorio, "/" + rutas[recurso] + "?per_page=10", abrir=abrir)
    if not isinstance(datos, list):
        raise ValueError("GitHub devolvió una lista inválida.")
    filas = []
    for objeto in datos[:10]:
        if not isinstance(objeto, dict):
            continue
        if recurso == "ramas":
            titulo = objeto.get("name")
        elif recurso == "commits":
            commit = objeto.get("commit")
            mensaje = commit.get("message") if isinstance(commit, dict) else None
            sha = objeto.get("sha")
            titulo = (sha[:8] + " · " + mensaje.split("\n", 1)[0]
                      if isinstance(sha, str) and isinstance(mensaje, str) else None)
        else:
            if recurso == "issues" and "pull_request" in objeto:
                continue
            titulo = objeto.get("title")
            numero = objeto.get("number")
            if isinstance(titulo, str) and isinstance(numero, int):
                titulo = f"#{numero} · {titulo}"
        if isinstance(titulo, str):
            filas.append(titulo[:160])
    return filas
