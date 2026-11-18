"""Consolidación conservadora: elimina solo duplicados exactos, nunca conocimientos únicos.

No toca checkpoints ni pesos del modelo. Copia primero los duplicados a un
archivo de respaldo local, para permitir su recuperación manual.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _normalizar(valor):
    return " ".join(str(valor).casefold().split())


def _prioridad(clave, dato):
    try:
        importancia = float(dato.get("importancia", 1))
    except (ValueError, TypeError):
        importancia = 1
    # Conserva primero la memoria más importante; desempata por antigüedad.
    return (-importancia, str(dato.get("fecha", "")), str(clave))


def plan_duplicados(memoria, umbral=500):
    """Devuelve claves redundantes; nunca descarta hechos diferentes."""
    if not isinstance(memoria, dict) or len(memoria) <= umbral:
        return []
    grupos = {}
    for clave, dato in memoria.items():
        if not isinstance(dato, dict):
            continue
        valor = _normalizar(dato.get("valor", ""))
        categoria = _normalizar(dato.get("categoria", "general"))
        if not valor:
            continue
        # Claves distintas pueden tener significados distintos aunque su valor coincida.
        # Solo unificar variantes de escritura de la MISMA clave.
        clave_normalizada = _normalizar(clave)
        grupos.setdefault((clave_normalizada, valor, categoria), []).append(clave)
    sobrantes = []
    for claves in grupos.values():
        if len(claves) > 1:
            orden = sorted(claves, key=lambda k: _prioridad(k, memoria[k]))
            sobrantes.extend(orden[1:])
    return sobrantes


def consolidar(memoria, archivo_memoria, umbral=500):
    """Archiva duplicados antes de retirarlos. Devuelve número retirado.

    Si falla el respaldo, no modifica la memoria. Nunca borra recuerdos
    únicos, explícitos de contenido distinto ni archivos de entrenamiento.
    """
    claves = plan_duplicados(memoria, umbral)
    if not claves:
        return 0
    ruta = Path(str(archivo_memoria) + ".duplicados.jsonl")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Crear un respaldo íntegro de los duplicados; sin red ni envío externo.
    registro = {"fecha": datetime.now(timezone.utc).isoformat(),
                "duplicados": {k: memoria[k] for k in claves}}
    contenido = (json.dumps(registro, ensure_ascii=False) + "\n").encode("utf-8")
    # Solo anexar; escritura íntegra en una operación. Nunca elimina el respaldo.
    fd = os.open(str(ruta), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    try:
        escritos = os.write(fd, contenido)
        if escritos != len(contenido):
            raise OSError("Respaldo incompleto")
        os.fsync(fd)
    finally:
        os.close(fd)
    for clave in claves:
        memoria.pop(clave, None)
    return len(claves)
