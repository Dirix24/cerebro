"""Descarga e inspección estática acotada de repositorios públicos."""
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from core.github_local import identificar_repositorio


def descargar(url, raiz):
    if not url.startswith("https://"):
        raise ValueError("Indica un enlace base HTTPS de GitHub.")
    repo = identificar_repositorio(url)
    deposito = raiz / "repositorios"
    if deposito.is_symlink():
        raise PermissionError("La carpeta de repositorios debe ser local.")
    deposito.mkdir(mode=0o700, exist_ok=True)
    destino = deposito / repo.replace("/", "--")
    if destino.exists() or destino.is_symlink():
        raise FileExistsError("Ya existe una descarga con ese nombre.")
    with TemporaryDirectory(dir=deposito) as temporal:
        entorno = {"PATH": os.defpath, "HOME": temporal, "XDG_CONFIG_HOME": temporal,
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
        copia = Path(temporal) / "git"

        def git(*args, timeout=5):
            try:
                return subprocess.run(
                    ["git", "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
                     "-c", "http.followRedirects=false", "-C", temporal, *args],
                    env=entorno, stdin=subprocess.DEVNULL, capture_output=True, check=True,
                    timeout=timeout,
                ).stdout
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Git superó el tiempo de espera.") from exc
            except subprocess.CalledProcessError as exc:
                raise RuntimeError("Git no pudo completar la descarga o verificar el repositorio público.") from exc

        git("clone", "--bare", "--depth=1", "--single-branch", "--no-tags",
            "--template=", "--", "https://github.com/" + repo + ".git", str(copia), timeout=45)
        commit = git("--git-dir", str(copia), "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
        arbol = git("--git-dir", str(copia), "ls-tree", "-z", "HEAD").split(b"\0")
        entradas = []
        extracto = ""
        for linea in arbol[:80]:
            metadatos, separador, nombre = linea.partition(b"\t")
            if not separador:
                continue
            modo, _, objeto = metadatos.split()
            texto = nombre.decode(errors="replace")
            entradas.append("".join(c if c.isprintable() else "?" for c in texto))
            if modo == b"100644" and re.fullmatch(r"readme(?:\.(?:md|rst|txt))?", texto, re.I):
                referencia = objeto.decode("ascii")
                tamano = int(git("--git-dir", str(copia), "cat-file", "-s", referencia))
                if tamano <= 64 * 1024:
                    contenido = git("--git-dir", str(copia), "cat-file", "blob", referencia)
                    extracto = "".join(c for c in contenido.decode(errors="replace")
                                       if c.isprintable() or c == "\n").strip()[:3000]
        # Reserva el nombre de forma exclusiva aunque lleguen dos solicitudes simultáneas.
        destino.mkdir(mode=0o700)
        try:
            copia.rename(destino / "git")
        except OSError:
            destino.rmdir()
            raise
    return {"repositorio": repo, "commit": commit, "archivos": entradas, "readme": extracto}
