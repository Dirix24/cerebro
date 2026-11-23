"""Selección persistente de un modelo instalado y comprobado en loopback."""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile


def leer(raiz):
    ruta = Path(raiz) / "data" / "modelo-local.json"
    if ruta.is_symlink() or ruta.parent.is_symlink() or not ruta.is_file() or ruta.stat().st_size > 4096:
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else None
    except (OSError, ValueError):
        return None


def configurar(raiz, modelo, puerto=11434):
    from core.motores_instalados import _modelos_ollama
    from core.profesor_local import ProfesorLocal

    motor = ProfesorLocal(puerto, ollama=modelo)
    instalados = _modelos_ollama(puerto)
    if instalados is None:
        raise ValueError("Ollama no respondió en el equipo.")
    if modelo not in instalados:
        raise ValueError("El modelo elegido no aparece entre los modelos instalados.")
    respuesta = motor.conversar("Responde a este saludo breve en español: hola.")
    _guardar(raiz, {"motor": "ollama", "modelo": modelo, "puerto": puerto})
    return respuesta


def _guardar(raiz, datos):
    padre = Path(raiz) / "data"
    if padre.is_symlink():
        raise PermissionError("La configuración requiere un directorio de datos local.")
    padre.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=padre, delete=False) as archivo:
        temporal = Path(archivo.name)
        try:
            json.dump(datos, archivo)
            archivo.close()
            temporal.replace(padre / "modelo-local.json")
        finally:
            temporal.unlink(missing_ok=True)


def preparar_instalacion(raiz, modelo=None):
    """Conserva la configuración y prueba únicamente candidatos ligeros instalados."""
    import os
    from shutil import which
    from core.motores_instalados import _modelos_ollama
    from core.profesor_local import GIB, ProfesorBajoDemanda, diagnostico

    variables = ("CEREBRO_OLLAMA_MODELO", "CEREBRO_PROFESOR_PUERTO",
                 "CEREBRO_PROFESOR_MOTOR", "CEREBRO_PROFESOR_MODELO")
    if not modelo and (leer(raiz) or any(os.environ.get(v) for v in variables)):
        return "Modelo local: se conserva la configuración existente."
    puerto = int(os.environ.get("CEREBRO_OLLAMA_PUERTO", "11434"))
    if not 1024 <= puerto <= 65535:
        raise ValueError("Puerto de Ollama inválido.")
    if modelo:
        configurar(raiz, modelo, puerto)
        return f"Modelo local: {modelo} configurado después de una inferencia de prueba."

    recursos = diagnostico(raiz)
    ram = recursos["ram_disponible_bytes"] or 0
    disponibles = _modelos_ollama(puerto) or []
    candidatos = (("qwen2.5:0.5b", 2), ("qwen2.5:1.5b", 3),
                  ("qwen2.5:3b", 5), ("qwen2.5:7b", 9))
    # En equipos con margen amplio, se puede probar primero el modelo más capaz.
    if ram >= 12 * GIB:
        candidatos = candidatos[::-1]
    for nombre, minimo in candidatos:
        if nombre not in disponibles or ram < minimo * GIB:
            continue
        try:
            configurar(raiz, nombre, puerto)
        except (RuntimeError, ValueError):
            continue
        return f"Modelo local: {nombre} configurado después de una inferencia de prueba."

    binario = which("llama-server")
    carpeta = Path(raiz) / "models"
    if binario and carpeta.is_dir() and not carpeta.is_symlink():
        modelos = []
        for ruta in carpeta.glob("*.gguf"):
            if ruta.is_file() and not ruta.is_symlink() and not ruta.name.startswith("mmproj"):
                peso = ruta.stat().st_size
                if 0 < peso <= ram - 2 * GIB:
                    modelos.append((peso, ruta))
        for _, ruta in sorted(modelos)[:3]:
            motor = ProfesorBajoDemanda(binario, ruta)
            try:
                motor.conversar("Responde a este saludo breve en español: hola.")
            except (RuntimeError, ValueError):
                continue
            finally:
                motor.cerrar()
            _guardar(raiz, {"motor": "llama.cpp", "modelo": str(ruta.resolve())})
            return f"Modelo local: {ruta.name} configurado después de una inferencia de prueba."

    return ("Modelo local: sin candidato instalado y comprobado. "
            "Usa cerebro configurar-modelo para elegir un modelo de Ollama.")


def descargar_ligero(raiz):
    """Descarga solicitada expresamente en el Ollama local ya instalado."""
    import os
    from shutil import disk_usage, which
    import subprocess
    from core.motores_instalados import _modelos_ollama

    modelo = "qwen2.5:0.5b"
    puerto = int(os.environ.get("CEREBRO_OLLAMA_PUERTO", "11434"))
    if not 1024 <= puerto <= 65535:
        raise ValueError("Puerto de Ollama inválido.")
    instalados = _modelos_ollama(puerto)
    if instalados is None:
        raise ValueError("Inicia Ollama antes de descargar un modelo.")
    if modelo not in instalados:
        binario = which("ollama")
        if not binario:
            raise ValueError("Falta el ejecutable de Ollama.")
        if disk_usage(raiz).free < 1024**3:
            raise ValueError("Deja al menos 1 GiB libre antes de descargar el modelo ligero.")
        print("Descargando Qwen2.5 0.5B (aproximadamente 400 MB) en Ollama.", flush=True)
        resultado = subprocess.run([binario, "pull", modelo], timeout=600,
                                   env={**os.environ, "OLLAMA_HOST": f"127.0.0.1:{puerto}"})
        if resultado.returncode:
            raise RuntimeError("Ollama no pudo descargar el modelo ligero.")
    return preparar_instalacion(raiz, modelo)
