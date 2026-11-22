"""Descarga e inspección estática acotada de repositorios públicos."""
from fcntl import LOCK_EX, LOCK_NB, flock
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic

from core.github_local import identificar_repositorio


LIMITE_DISCO = 128 * 1024 * 1024


def _ocupacion(carpeta):
    total = 0
    for base, directorios, archivos in os.walk(carpeta):
        for nombre in (*directorios, *archivos):
            try:
                ficha = (Path(base) / nombre).lstat()
            except FileNotFoundError:
                continue
            total += max(ficha.st_size, ficha.st_blocks * 512)
    return total


def _git(args, entorno, comprobar, limite, timeout, *, directorio=None):
    orden = ["prlimit", f"--fsize={limite}:{limite}", "--", "git",
             "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
             "-c", "http.followRedirects=false", *args]
    comprobar()
    with subprocess.Popen(orden, env=entorno, cwd=directorio, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, start_new_session=True) as proceso:
        fin = monotonic() + timeout
        try:
            while True:
                comprobar()
                restante = fin - monotonic()
                if restante <= 0:
                    raise RuntimeError("Git superó el tiempo de espera.")
                try:
                    salida, _ = proceso.communicate(timeout=min(.1, restante))
                    break
                except subprocess.TimeoutExpired:
                    continue
            comprobar()
        except BaseException:
            try:
                os.killpg(proceso.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proceso.communicate()
            raise
        if proceso.returncode:
            raise RuntimeError("Git no pudo completar la descarga o verificar el repositorio dentro del límite.")
        return salida


def descargar(url, raiz, *, avanzar=lambda fase: None, limite=LIMITE_DISCO):
    if not url.startswith("https://"):
        raise ValueError("Indica un enlace base HTTPS de GitHub.")
    repo = identificar_repositorio(url)
    deposito = raiz / "repositorios"
    if deposito.is_symlink():
        raise PermissionError("La carpeta de repositorios debe ser local.")
    deposito.mkdir(mode=0o700, exist_ok=True)
    with (deposito / ".cerebro.lock").open("a") as bloqueo:
        try:
            flock(bloqueo, LOCK_EX | LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Ya se está descargando un repositorio en este espacio.") from exc
        return _descargar(repo, deposito, avanzar, limite)


def _descargar(repo, deposito, avanzar, limite):
    destino = deposito / repo.replace("/", "--")
    if destino.exists() or destino.is_symlink():
        raise FileExistsError("Ya existe una descarga con ese nombre.")
    if not any(linea.split(" - ", 1)[0].split()[4] == "/dev/shm"
               and linea.split(" - ", 1)[1].split()[0] == "tmpfs"
               for linea in Path("/proc/self/mountinfo").read_text().splitlines()):
        raise RuntimeError("Git necesita /dev/shm montado en tmpfs para acotar los temporales.")
    disponible = limite - _ocupacion(deposito)
    if disponible <= 0:
        raise RuntimeError("Se alcanzó el límite total de almacenamiento de repositorios.")
    with TemporaryDirectory(prefix="cerebro-git-", dir="/dev/shm") as temporal:
        entorno = {"PATH": os.defpath, "HOME": temporal, "XDG_CONFIG_HOME": temporal,
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}
        copia = Path(temporal) / "git"

        def comprobar(fase):
            avanzar(fase)
            if _ocupacion(deposito) + _ocupacion(temporal) >= limite:
                raise RuntimeError("Se alcanzó el límite total de almacenamiento de repositorios.")

        def git(*args, timeout=5, fase="verificando"):
            return _git(("-C", temporal, *args), entorno, lambda: comprobar(fase), disponible, timeout)

        git("clone", "--bare", "--depth=1", "--single-branch", "--no-tags",
            "--template=", "--", "https://github.com/" + repo + ".git", str(copia), timeout=45, fase="clonando")
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
        comprobar("publicando")
        # Reserva el nombre de forma exclusiva aunque lleguen dos solicitudes simultáneas.
        destino.mkdir(mode=0o700)
        try:
            shutil.copytree(copia, destino / "git")
            if _ocupacion(deposito) >= limite:
                raise RuntimeError("Se alcanzó el límite total de almacenamiento al publicar.")
        except (OSError, RuntimeError):
            shutil.rmtree(destino)
            raise
    return {"repositorio": repo, "commit": commit, "archivos": entradas, "readme": extracto}
