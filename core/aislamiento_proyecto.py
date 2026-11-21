"""Copia acotada del proyecto y comando Bubblewrap para pruebas locales."""
import os
from pathlib import Path
import shutil
import stat

_MIB = 1024 * 1024
_OMITIR = {"__pycache__", "build", "dist", "node_modules", "venv"}
_LIMITE_TOTAL = 32 * _MIB
_LIMITE_ARCHIVO = 8 * _MIB
_LIMITE_ENTRADAS = 2048

_INICIO_PYTHON = """
import os
import resource
import sys
import unittest

for limite, valor in (
    (resource.RLIMIT_CPU, 20),
    (resource.RLIMIT_AS, 768 * 1024 * 1024),
    (resource.RLIMIT_FSIZE, 8 * 1024 * 1024),
    (resource.RLIMIT_NOFILE, 64),
    (resource.RLIMIT_NPROC, 192),
    (resource.RLIMIT_CORE, 0),
):
    resource.setrlimit(limite, (valor, valor))

sys.path.insert(0, os.getcwd())
unittest.main(module=None, argv=["unittest", "discover", "-s", sys.argv[1]])
"""


def preparar_copia(raiz, destino):
    raiz = raiz.resolve(strict=True)
    total = entradas = 0

    def propagar(error):
        raise error

    for base, dirs, archivos in os.walk(raiz, onerror=propagar):
        entradas += len(dirs) + len(archivos)
        if entradas > _LIMITE_ENTRADAS:
            raise ValueError("La copia de pruebas supera 2048 entradas.")
        base = Path(base)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in _OMITIR
                         and not (base / d).is_symlink())
        if not base.resolve(strict=True).is_relative_to(raiz):
            raise PermissionError("La carpeta del proyecto cambió al preparar las pruebas.")
        for archivo in archivos:
            origen = base / archivo
            if (archivo.startswith(".") or origen.is_symlink()
                    or origen.suffix.casefold() in {".pem", ".key", ".p12", ".pfx"}):
                continue
            info = origen.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                continue
            fd = os.open(origen, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as lector:
                info = os.fstat(lector.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    continue
                limite = min(_LIMITE_ARCHIVO, _LIMITE_TOTAL - total)
                if info.st_size > limite:
                    raise ValueError("La copia supera 8 MiB por archivo o 32 MiB en total.")
                datos = lector.read(limite + 1)
                if len(datos) > limite:
                    raise ValueError("La copia supera 8 MiB por archivo o 32 MiB en total.")
            total += len(datos)
            salida = destino / origen.relative_to(raiz)
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(datos)


def comando_aislado(copia):
    bwrap = shutil.which("bwrap")
    if not bwrap or not Path("/usr/bin/python3").is_file():
        raise RuntimeError("Las pruebas requieren Bubblewrap y /usr/bin/python3. No se ejecutaron.")
    comandos = [
        bwrap, "--unshare-all", "--unshare-user", "--disable-userns", "--die-with-parent",
        "--new-session", "--clearenv", "--cap-drop", "ALL",
        "--ro-bind", "/usr/bin", "/usr/bin", "--ro-bind", "/usr/lib", "/usr/lib",
    ]
    if Path("/usr/lib64").is_dir():
        comandos += ["--ro-bind", "/usr/lib64", "/usr/lib64"]
    if Path("/usr/libexec").is_dir():
        comandos += ["--ro-bind", "/usr/libexec", "/usr/libexec"]
    for biblioteca in ("lib", "lib64", "bin"):
        ruta = Path("/") / biblioteca
        if ruta.is_symlink():
            comandos += ["--symlink", os.readlink(ruta), str(ruta)]
        elif ruta.is_dir():
            comandos += ["--ro-bind", str(ruta), str(ruta)]
    if Path("/etc/ld.so.cache").is_file():
        comandos += ["--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache"]
    carpeta = "tests" if (copia / "tests").is_dir() else "."
    return comandos + [
        "--proc", "/proc", "--dev", "/dev", "--size", str(64 * _MIB), "--tmpfs", "/tmp",
        "--ro-bind", str(copia), "/proyecto", "--remount-ro", "/", "--chdir", "/proyecto",
        "--setenv", "HOME", "/tmp", "--setenv", "TMPDIR", "/tmp",
        "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8",
        "--", "/usr/bin/python3", "-I", "-B", "-c", _INICIO_PYTHON, carpeta,
    ]
