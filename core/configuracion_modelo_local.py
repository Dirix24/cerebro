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
    datos = {"motor": "ollama", "modelo": modelo, "puerto": puerto}
    padre = Path(raiz) / "data"
    if padre.is_symlink():
        raise PermissionError("La configuración requiere un directorio de datos local.")
    padre.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=padre, delete=False) as archivo:
        temporal = Path(archivo.name)
        json.dump(datos, archivo)
    try:
        temporal.replace(padre / "modelo-local.json")
    finally:
        temporal.unlink(missing_ok=True)
    return respuesta


def preparar_instalacion(raiz, modelo=None):
    """Conserva la configuración y prueba únicamente candidatos ligeros instalados."""
    import os
    from core.motores_instalados import _modelos_ollama

    variables = ("CEREBRO_OLLAMA_MODELO", "CEREBRO_PROFESOR_PUERTO",
                 "CEREBRO_PROFESOR_MOTOR", "CEREBRO_PROFESOR_MODELO")
    if not modelo and (leer(raiz) or any(os.environ.get(v) for v in variables)):
        return "Modelo local: se conserva la configuración existente."
    puerto = int(os.environ.get("CEREBRO_OLLAMA_PUERTO", "11434"))
    if not 1024 <= puerto <= 65535:
        raise ValueError("Puerto de Ollama inválido.")
    if not modelo:
        disponibles = _modelos_ollama(puerto)
        if disponibles is None:
            return "Modelo local: Ollama no respondió. Inicia Ollama para preparar el motor."
        modelo = next((n for n in ("qwen2.5:0.5b", "qwen2.5:1.5b") if n in disponibles), None)
        if modelo is None:
            return "Modelo local: no hay un candidato ligero conocido. Usa cerebro configurar-modelo para elegir uno instalado."
    configurar(raiz, modelo, puerto)
    return f"Modelo local: {modelo} configurado después de una inferencia de prueba."


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
