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
