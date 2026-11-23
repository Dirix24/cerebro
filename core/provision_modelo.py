"""Kit CPU local, con artefactos versionados y verificación antes de ejecutar."""
from hashlib import sha256
from pathlib import Path
import platform
from shutil import disk_usage, which
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.request import urlopen
from zipfile import ZipFile

VERSION = "b7150"
MOTOR = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/{VERSION}/llama-{VERSION}-bin-ubuntu-x64.zip",
    17_653_693, "9fcea05a47d58d8784e0bbdf771cf3f606ff07157aa3684429db1cb7404ad6d3",
)
MODELO = (
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
    491_400_032, "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db",
)


def _directorio_motor():
    return Path(sys.prefix) / f"cerebro-llama-{VERSION}"


def binario_llama():
    instalado = which("llama-server")
    if instalado:
        return instalado
    propio = _directorio_motor() / "llama-server"
    return str(propio) if sys.prefix != sys.base_prefix and propio.is_file() and not propio.is_symlink() else None


def _descargar(destino, ficha):
    url, tamano, huella = ficha
    resumen = sha256()
    total = 0
    with urlopen(url, timeout=30) as entrada, destino.open("wb") as salida:
        while bloque := entrada.read(1024 * 1024):
            total += len(bloque)
            if total > tamano:
                raise ValueError("La descarga supera el tamaño publicado.")
            resumen.update(bloque)
            salida.write(bloque)
    if total != tamano or resumen.hexdigest() != huella:
        raise ValueError("La descarga no coincide con el artefacto publicado.")


def _instalar_motor(destino):
    with TemporaryDirectory(dir=destino.parent) as temporal:
        archivo = Path(temporal) / "motor.zip"
        _descargar(archivo, MOTOR)
        carpeta = Path(temporal) / "motor"
        carpeta.mkdir()
        with ZipFile(archivo) as paquete:
            for miembro in paquete.infolist():
                ruta = Path(miembro.filename)
                if ruta.parts[:-1] != ("build", "bin"):
                    continue
                if ruta.name != "llama-server" and not ruta.name.startswith(("lib", "LICENSE")):
                    continue
                salida = carpeta / ruta.name
                salida.write_bytes(paquete.read(miembro))
                salida.chmod(0o755 if ruta.name == "llama-server" else 0o644)
        if not (carpeta / "llama-server").is_file():
            raise ValueError("El paquete verificado carece del servidor.")
        carpeta.rename(destino)


def ofrecer(raiz, confirmar):
    """Prepara el kit solo después de una autorización informada."""
    from core.configuracion_modelo_local import configurar_gguf
    from core.profesor_local import GIB, diagnostico

    entorno = diagnostico(raiz)
    if ((entorno["ram_disponible_bytes"] or 0) < 2 * GIB or entorno["disco_libre_bytes"] < GIB):
        return "Modelo conversacional: hacen falta al menos 2 GiB de RAM disponible y 1 GiB de disco."
    motor = binario_llama()
    destino_motor = _directorio_motor()
    if not motor and (sys.prefix == sys.base_prefix or platform.system() != "Linux"
                      or platform.machine() != "x86_64" or platform.libc_ver()[0] != "glibc"):
        return "Modelo conversacional: el kit CPU automático requiere Linux x86-64 con glibc."
    if not motor and disk_usage(destino_motor.parent).free < 128 * 1024**2:
        return "Modelo conversacional: hacen falta 128 MiB libres en el entorno virtual para el motor."
    carpeta = Path(raiz) / "models"
    if carpeta.is_symlink():
        raise PermissionError("La carpeta de modelos debe ser local.")
    modelo = carpeta / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    if modelo.is_symlink():
        raise PermissionError("El archivo de modelo debe ser local.")
    if motor and modelo.is_file():
        return configurar_gguf(raiz, motor, modelo)
    megas = (0 if modelo.is_file() else 491) + (0 if motor else 18)
    if not confirmar(f"¿Descargar el kit conversacional CPU ({megas} MB, requiere 1 GiB libre)?"):
        return "Modelo conversacional: descarga omitida por elección del usuario."
    if not motor:
        _instalar_motor(destino_motor)
        motor = str(destino_motor / "llama-server")
    carpeta.mkdir(parents=True, exist_ok=True)
    if not modelo.is_file():
        with NamedTemporaryFile(dir=carpeta, delete=False) as archivo:
            temporal = Path(archivo.name)
        try:
            _descargar(temporal, MODELO)
            temporal.replace(modelo)
        finally:
            temporal.unlink(missing_ok=True)
    return configurar_gguf(raiz, motor, modelo)
