"""Punto de entrada único de Cerebro.

El motor NumPy no necesita PyTorch. El avanzado prepara automáticamente un
entorno aislado con dependencias, si aún no están disponibles.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv

RAIZ = Path(__file__).resolve().parent
ENTORNO = RAIZ / ".cerebro-env"


def _python_entorno():
    if os.name == "nt":
        return ENTORNO / "Scripts" / "python.exe"
    return ENTORNO / "bin" / "python"


def _ejecutar(comando):
    return subprocess.call(comando, cwd=str(RAIZ))


def _torch_disponible(python):
    return subprocess.run([str(python), "-c", "import torch"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def ejecutar_todo():
    """Chat y aprendizaje diario en paralelo; se detienen al cerrar el chat."""
    try:
        import numpy  # noqa: F401
    except ImportError:
        print("Falta NumPy: python3 -m pip install -r requirements.txt", file=sys.stderr)
        return 1
    try:
        from core.local_search import indexar
        print(f"Índice local preparado: {indexar()} documentos.", flush=True)
    except Exception as exc:
        print(f"Aviso: no se pudo actualizar el índice local: {exc}", file=sys.stderr)
    print("Cerebro completo: chat local, memoria y aprendizaje diario.", flush=True)
    print("Internet solo aporta textos; ninguna IA de terceros.", flush=True)
    aprendizaje = subprocess.Popen([sys.executable, str(RAIZ / "aprendizaje_internet.py"),
                                    "--cada-dia", "--entrenar"], cwd=str(RAIZ))
    try:
        return _ejecutar([sys.executable, str(RAIZ / "main.py")])
    finally:
        if aprendizaje.poll() is None:
            aprendizaje.terminate()
            try:
                aprendizaje.wait(timeout=5)
            except subprocess.TimeoutExpired:
                aprendizaje.kill()
                aprendizaje.wait()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cerebro: chat y entrenamiento desde un único comando")
    ap.add_argument("accion", choices=("chat", "entrenar", "generar", "herramientas", "conocimiento", "aprender", "todo"))
    ap.add_argument("--motor", choices=("original", "clasico", "avanzado"), default="original")
    ap.add_argument("--sin-instalar", action="store_true",
                    help="No descargar dependencias; útil para entornos sin Internet")
    args, resto = ap.parse_known_args(argv)
    if args.accion == "todo":
        if resto:
            ap.error("La acción todo no admite argumentos adicionales")
        return ejecutar_todo()
    if args.accion == "conocimiento":
        return _ejecutar([sys.executable, str(RAIZ / "core" / "conocimiento.py"), *resto])
    if args.accion == "aprender":
        return _ejecutar([sys.executable, str(RAIZ / "aprendizaje_internet.py"), *resto])
    if args.accion == "herramientas":
        return _ejecutar([sys.executable, str(RAIZ / "herramientas_locales.py"), *resto])
    if args.accion == "chat":
        if args.motor != "original":
            ap.error("El chat integrado actualmente utiliza el motor original; usa generar para el motor PyTorch")
        return _ejecutar([sys.executable, str(RAIZ / "main.py"), *resto])
    if args.motor == "original":
        if args.accion == "generar":
            ap.error("Para generar con el motor original usa la acción chat")
        return _ejecutar([sys.executable, str(RAIZ / "train.py"), *resto])
    python = _python_entorno()
    if not _torch_disponible(python):
        if args.sin_instalar:
            ap.error("PyTorch no está preparado. Ejecuta sin --sin-instalar para instalarlo automáticamente")
        print("Preparando el motor neuronal avanzado en .cerebro-env (solo la primera vez).", flush=True)
        print("La descarga inicial requiere Internet; no se descargan modelos preentrenados.", flush=True)
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(str(ENTORNO))
        codigo = _ejecutar([str(python), "-m", "pip", "install", "-r",
                            str(RAIZ / "requirements-avanzado.txt")])
        if codigo:
            return codigo
    if not _torch_disponible(python):
        print("No se pudo preparar PyTorch.", file=sys.stderr)
        return 1
    comando = [str(python), str(RAIZ / "cerebro_torch.py")]
    if args.accion == "generar":
        comando += ["--generar", *resto]
    else:
        if "--arquitectura" not in resto:
            comando += ["--arquitectura", "avanzada" if args.motor == "avanzado" else "clasica"]
        comando += resto
    return _ejecutar(comando)


if __name__ == "__main__":
    raise SystemExit(main())
