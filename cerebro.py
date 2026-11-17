"""Punto de entrada único de Cerebro.

El motor NumPy no necesita PyTorch. El avanzado prepara automáticamente un
entorno aislado con dependencias, si aún no están disponibles.
"""
import argparse
import os
from pathlib import Path
import subprocess
import signal
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


def iniciar_automatico():
    """Prepara el entorno local una vez y activa los servicios compatibles."""
    try:
        import numpy  # noqa: F401
    except ImportError:
        entorno = RAIZ / ".venv"
        python = entorno / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not python.is_file():
            print("Creando entorno aislado de Cerebro...", flush=True)
            venv.EnvBuilder(with_pip=True).create(str(entorno))
        print("Instalando dependencias del motor local...", flush=True)
        codigo = _ejecutar([str(python), "-m", "pip", "install", "-r", str(RAIZ / "requirements.txt")])
        if codigo:
            return codigo
        return _ejecutar([str(python), str(RAIZ / "cerebro.py"), "todo"])
    entorno = RAIZ / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if entorno.is_file() and Path(sys.executable).resolve() != entorno.resolve():
        return _ejecutar([str(entorno), str(RAIZ / "cerebro.py"), "todo"])
    return ejecutar_todo()


def preparar_modelo_inicial():
    """El primer arranque no debe fallar si faltan pesos."""
    import config
    if Path(config.CKPT_MEJOR).is_file() or Path(config.CKPT_ULTIMO).is_file():
        return 0
    print("No hay pesos entrenados; preparando modelo inicial local...", flush=True)
    return _ejecutar([sys.executable, str(RAIZ / "train.py"), "--perfil", "pequeno", "--pasos", "200"])


def mostrar_diagnostico():
    """Estado observable sin cargar ni entrenar el modelo."""
    import json
    import config
    from core.recursos_portatil import bateria_baja
    from core.repaso_espaciado import pendientes
    datos = {
        "entrenamiento_pausado_por_bateria": bateria_baja(),
        "repasos_pendientes": len(pendientes(RAIZ / "data" / "repaso_espaciado.json", limite=10000)),
        "modelo_entrenado": Path(config.CKPT_MEJOR).is_file() or Path(config.CKPT_ULTIMO).is_file(),
        "indice_local": (RAIZ / "data" / "corpus_fts.sqlite3").is_file(),
        "historial_evolucion": (RAIZ / "data" / "aprendizaje_internet" / "evolucion.json").is_file(),
        "fuentes_wikipedia": (RAIZ / "data" / "aprendizaje_internet" / "fuentes.jsonl").is_file(),
        "nucleos_logicos": os.cpu_count(),
    }
    print(json.dumps(datos, indent=2, ensure_ascii=False))
    return 0


def ejecutar_todo():
    """Chat y aprendizaje diario en paralelo; se detienen al cerrar el chat."""
    try:
        import numpy  # noqa: F401
    except ImportError:
        print("Falta NumPy: python3 -m pip install -r requirements.txt", file=sys.stderr)
        return 1
    if preparar_modelo_inicial() != 0:
        print("No se pudo preparar el modelo inicial; revisa los datos de entrenamiento.", file=sys.stderr)
        return 1
    try:
        from core.local_search import indexar
        print(f"Índice local preparado: {indexar()} documentos.", flush=True)
    except Exception as exc:
        print(f"Aviso: no se pudo actualizar el índice local: {exc}", file=sys.stderr)
    print("Cerebro completo: chat local, memoria y aprendizaje diario.", flush=True)
    print("Internet solo aporta textos; ninguna IA de terceros.", flush=True)
    aprendizaje = subprocess.Popen([sys.executable, str(RAIZ / "aprendizaje_internet.py"),
                                    "--cada-dia", "--entrenar"], cwd=str(RAIZ),
                                    start_new_session=(os.name == "posix"))
    try:
        return _ejecutar([sys.executable, str(RAIZ / "main.py")])
    finally:
        if aprendizaje.poll() is None:
            if os.name == "posix":
                os.killpg(aprendizaje.pid, signal.SIGTERM)
            else:
                aprendizaje.terminate()
            try:
                aprendizaje.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(aprendizaje.pid, signal.SIGKILL)
                else:
                    aprendizaje.kill()
                aprendizaje.wait()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cerebro: chat y entrenamiento desde un único comando")
    ap.add_argument("accion", choices=("laboratorio", "instalar", "desinstalar", "motores", "iniciar", "diagnostico", "chat", "entrenar", "generar", "herramientas", "conocimiento", "aprender", "todo"))
    ap.add_argument("--motor", choices=("original", "clasico", "avanzado"), default="original")
    ap.add_argument("--sin-instalar", action="store_true",
                    help="No descargar dependencias; útil para entornos sin Internet")
    ap.add_argument("--avanzado", action="store_true", help="Incluir PyTorch al instalar (descarga grande)")
    ap.add_argument("--confirmar", action="store_true", help="Confirmar desinstalación de entornos")
    ap.add_argument("--borrar-datos", action="store_true", help="Solicitar también borrar datos locales")
    args, resto = ap.parse_known_args(argv)
    if args.accion == "laboratorio":
        return _ejecutar([sys.executable, str(RAIZ / "laboratorio_visual.py"), *resto])
    if args.accion == "motores":
        from core.motores import disponibles
        import json
        print(json.dumps(disponibles(), ensure_ascii=False, indent=2))
        return 0
    if args.accion == "instalar":
        from core.instalacion import instalar
        return instalar(RAIZ, avanzado=args.avanzado)
    if args.accion == "desinstalar":
        from core.instalacion import desinstalar
        if args.borrar_datos and not args.confirmar:
            ap.error("--borrar-datos requiere --confirmar")
        confirmacion_datos = ""
        if args.borrar_datos:
            confirmacion_datos = input("Para borrar recuerdos, datos y checkpoints escribe BORRAR MIS DATOS: ")
        resultado = desinstalar(RAIZ, confirmar=args.confirmar,
                               borrar_datos=args.borrar_datos, confirmacion_datos=confirmacion_datos)
        print(resultado)
        return 0
    if args.accion == "diagnostico":
        if resto:
            ap.error("La acción diagnostico no admite argumentos adicionales")
        return mostrar_diagnostico()
    if args.accion == "iniciar":
        if resto:
            ap.error("La acción iniciar no admite argumentos adicionales")
        return iniciar_automatico()
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
    python = RAIZ / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not _torch_disponible(python):
        if args.sin_instalar:
            ap.error("PyTorch no está preparado. Ejecuta sin --sin-instalar para instalarlo automáticamente")
        print("Preparando el motor neuronal avanzado en .cerebro-env (solo la primera vez).", flush=True)
        print("La descarga inicial requiere Internet; no se descargan modelos preentrenados.", flush=True)
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(str(RAIZ / ".venv"))
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
