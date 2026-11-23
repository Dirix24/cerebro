"""Copia acotada del proyecto y comando Bubblewrap para pruebas locales."""
import os
from pathlib import Path
import shutil
import stat
import subprocess
from tempfile import TemporaryDirectory

_MIB = 1024 * 1024
_OMITIR = {"__pycache__", "build", "dist", "node_modules", "venv"}
_LIMITE_TOTAL = 32 * _MIB
_LIMITE_ARCHIVO = 8 * _MIB
_LIMITE_ENTRADAS = 2048

_LIMITES_PYTHON = """
import os
import resource

for limite, valor in (
    (resource.RLIMIT_CPU, 20),
    (resource.RLIMIT_AS, 768 * 1024 * 1024),
    (resource.RLIMIT_FSIZE, 8 * 1024 * 1024),
    (resource.RLIMIT_NOFILE, 64),
    (resource.RLIMIT_NPROC, 192),
    (resource.RLIMIT_CORE, 0),
):
    resource.setrlimit(limite, (valor, valor))
    if resource.getrlimit(limite) != (valor, valor):
        raise SystemExit("No se aplicó el límite de proceso: " + str(limite))
"""

_INICIO_PYTHON = _LIMITES_PYTHON + """
import sys
import unittest

sys.path.insert(0, os.getcwd())
unittest.main(module=None, argv=["unittest", "discover", "-s", sys.argv[1]])
"""


_SONDA_BWRAP = _LIMITES_PYTHON + """
import socket

if os.getuid() == 0 or not os.statvfs("/proyecto").f_flag & os.ST_RDONLY:
    raise SystemExit("UID privilegiado o proyecto con escritura.")
if {nombre for _, nombre in socket.if_nameindex()} != {"lo"}:
    raise SystemExit("Hay interfaces de red adicionales.")
if os.path.exists("/home"):
    raise SystemExit("El perfil expone la carpeta personal.")
print("CEREBRO_AISLADO")
"""


def preparar_copia(raiz, destino):
    raiz = raiz.resolve(strict=True)
    total = entradas = 0

    def propagar(error):
        raise error

    for base, dirs, archivos, directo in os.fwalk(raiz, onerror=propagar, follow_symlinks=False):
        entradas += len(dirs) + len(archivos)
        if entradas > _LIMITE_ENTRADAS:
            raise ValueError("La copia de pruebas supera 2048 entradas.")
        base = Path(base)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in _OMITIR
                         and stat.S_ISDIR(os.stat(d, dir_fd=directo, follow_symlinks=False).st_mode))
        if not base.resolve(strict=True).is_relative_to(raiz):
            raise PermissionError("La carpeta del proyecto cambió al preparar las pruebas.")
        for archivo in archivos:
            origen = base / archivo
            if archivo.startswith(".") or origen.suffix.casefold() in {".pem", ".key", ".p12", ".pfx"}:
                continue
            info = os.stat(archivo, dir_fd=directo, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                continue
            fd = os.open(archivo, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=directo)
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


def comando_aislado(copia, *, sonda=False):
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
    arranque = ["-I", "-B", "-c", _SONDA_BWRAP] if sonda else [
        "-I", "-B", "-c", _INICIO_PYTHON, carpeta]
    return comandos + [
        "--proc", "/proc", "--dev", "/dev", "--size", str(64 * _MIB), "--tmpfs", "/tmp",
        "--ro-bind", str(copia), "/proyecto", "--remount-ro", "/", "--chdir", "/proyecto",
        "--setenv", "HOME", "/tmp", "--setenv", "TMPDIR", "/tmp",
        "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8",
        "--", "/usr/bin/python3", *arranque,
    ]


def limites_agregados(cgroup=Path("/proc/self/cgroup"), montaje=Path("/sys/fs/cgroup")):
    """Verifica la cuota efectiva del cgroup v2 que heredan Bubblewrap y sus hijos."""
    try:
        relativo = next(linea[3:].strip() for linea in cgroup.read_text().splitlines()
                        if linea.startswith("0::/"))
        ruta = (montaje / relativo.lstrip("/")).resolve()
        if not ruta.is_relative_to(montaje.resolve()):
            raise ValueError("Ruta de cgroup v2 fuera del montaje.")
        limites = {"memory.max": 768 * _MIB, "memory.swap.max": 0, "pids.max": 192}
        ausentes = []
        for nombre, maximo in limites.items():
            valor = (ruta / nombre).read_text().strip()
            if not valor.isdecimal() or int(valor) > maximo:
                ausentes.append(nombre)
        cuota, periodo = (ruta / "cpu.max").read_text().split()
        if not cuota.isdecimal() or not periodo.isdecimal() or not 0 < int(cuota) <= int(periodo):
            ausentes.append("cpu.max")
        return ausentes
    except (OSError, ValueError, StopIteration):
        return ["cgroup v2 no verificable"]


def diagnosticar():
    """Prueba el perfil real con Python de confianza y una carpeta vacía."""
    try:
        with TemporaryDirectory(prefix="cerebro-sonda-") as carpeta:
            comando = comando_aislado(Path(carpeta), sonda=True)
            resultado = subprocess.run(comando, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, timeout=4, text=True, errors="replace")
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        return False, f"Aislamiento no disponible. No se ejecutaron pruebas. {error}"
    if resultado.returncode == 0 and resultado.stdout.strip() == "CEREBRO_AISLADO":
        if faltan := limites_agregados():
            return False, ("Bubblewrap inició, pero faltan límites agregados. No se ejecutaron pruebas. "
                           + ", ".join(faltan)
                           + ". Inicia Cerebro en un ámbito cgroup v2 limitado o usa Docker rootless verificado.")
        return True, "Perfil Bubblewrap, red, montaje y límites por proceso y agregados comprobados."
    detalle = resultado.stdout.strip()[:500]
    if "uid map" in detalle and "Read-only file system" in detalle:
        motivo = "El entorno monta el mapa de usuarios como solo lectura."
    elif "namespace" in detalle or "Operation not permitted" in detalle:
        motivo = "El kernel o el entorno restringe los espacios de nombres o sus montajes."
    else:
        motivo = "El intérprete no pudo iniciar con el perfil de aislamiento."
    return False, f"Bubblewrap no pudo iniciar el aislamiento. No se ejecutó el proyecto. {motivo} {detalle}"


IMAGEN_PRUEBAS = "docker.io/library/python@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89"


_SONDA_DOCKER = """
import os
from pathlib import Path
import socket
base = Path("/sys/fs/cgroup")
assert os.getuid() == 65534
assert socket.if_nameindex() == [(1, "lo")]
assert os.statvfs("/proyecto").f_flag & os.ST_RDONLY
def comprobar(nombre, maximo):
    observado = (base / nombre).read_text().strip()
    if not observado.isdecimal() or int(observado) > maximo:
        raise SystemExit("El daemon no aplicó el límite " + nombre + ".")
comprobar("memory.max", 256 * 1024**2)
comprobar("memory.swap.max", 0)
comprobar("pids.max", 64)
cuota, periodo = (base / "cpu.max").read_text().split()
if not cuota.isdecimal() or int(cuota) > int(periodo):
    raise SystemExit("El daemon no aplicó el límite cpu.max.")
print("CEREBRO_AISLADO")
"""


def docker_local():
    """Solo un daemon rootless sobre un socket local y una imagen preinstalada."""
    import json

    ejecutable = shutil.which("docker")
    if not ejecutable or not hasattr(os, "getuid"):
        raise RuntimeError("Docker rootless requiere un cliente local en Linux.")
    sockets = [Path(f"/run/user/{os.getuid()}/docker.sock"), Path("/var/run/docker.sock")]
    if directorio := os.environ.get("XDG_RUNTIME_DIR"):
        if Path(directorio).is_absolute():
            sockets.insert(0, Path(directorio) / "docker.sock")
    for socket in sockets:
        if not socket.is_socket():
            continue
        cli = [ejecutable, "--host", "unix://" + str(socket)]
        info = subprocess.run([*cli, "info", "--format", "{{json .SecurityOptions}}"],
                              capture_output=True, text=True, timeout=4)
        if info.returncode != 0:
            continue
        opciones = json.loads(info.stdout)
        if not isinstance(opciones, list) or "name=rootless" not in opciones:
            continue
        imagen = subprocess.run([*cli, "image", "inspect", IMAGEN_PRUEBAS],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        if imagen.returncode == 0:
            return cli
    raise RuntimeError("Falta un daemon Docker rootless local con la imagen de pruebas fijada.")


def comando_docker(cli, copia, nombre, *, sonda=False):
    carpeta = "tests" if (copia / "tests").is_dir() else "."
    if any(c in str(copia) for c in (",", "\n", "\r")):
        raise ValueError("Ruta de copia incompatible con el montaje Docker.")
    argumentos = ["-c", _SONDA_DOCKER] if sonda else ["-c", _INICIO_PYTHON, carpeta]
    return [*cli, "run", "--name", nombre, "--rm", "--pull=never", "--network", "none",
            "--read-only", "--cgroupns", "private", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "64", "--memory", "256m", "--memory-swap", "256m", "--cpus", "1",
            "--user", "65534:65534", "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
            "--mount", f"type=bind,src={copia},dst=/proyecto,readonly", "--workdir", "/proyecto",
            IMAGEN_PRUEBAS, "python", "-I", "-B", *argumentos]


def limpiar_docker(cli, nombre):
    try:
        subprocess.run([*cli, "rm", "-f", nombre], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass


def perfil_pruebas():
    """Selecciona Bubblewrap o comprueba la alternativa Docker autorizada."""
    from uuid import uuid4

    funciona, aviso = diagnosticar()
    if funciona or os.environ.get("CEREBRO_PRUEBAS_DOCKER") != "1":
        return ("bubblewrap" if funciona else None), aviso, None
    nombre = "cerebro-sonda-" + uuid4().hex
    try:
        cli = docker_local()
        try:
            with TemporaryDirectory(prefix="cerebro-sonda-") as carpeta:
                copia = Path(carpeta) / "vacia"
                copia.mkdir(mode=0o755)
                copia.chmod(0o755)
                prueba = subprocess.run(comando_docker(cli, copia, nombre, sonda=True),
                                       capture_output=True, text=True, timeout=8)
        finally:
            limpiar_docker(cli, nombre)
        if prueba.returncode == 0 and prueba.stdout.strip() == "CEREBRO_AISLADO":
            return "docker", "Perfil Docker rootless local y recursos comprobados.", cli
        detalle = (prueba.stderr or prueba.stdout).strip().splitlines()
        aviso += " Docker rootless no superó la comprobación."
        if detalle:
            aviso += " " + detalle[-1][:240]
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        aviso += " " + str(error)
    return None, aviso, None
