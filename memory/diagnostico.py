"""Diagnóstico local y recuperación explícita de recuerdos archivados.

No abre conexiones ni modifica memoria salvo que el usuario solicite restaurar.
"""
import json
from pathlib import Path

from memory.consolidacion import plan_duplicados


def informe(memoria, archivo):
    memoria = memoria if isinstance(memoria, dict) else {}
    ruta = Path(archivo)
    respaldo = Path(str(archivo) + ".duplicados.jsonl")
    return {
        "recuerdos_activos": len(memoria),
        "duplicados_consolidables": len(plan_duplicados(memoria)),
        "bytes_memoria": ruta.stat().st_size if ruta.is_file() else 0,
        "bytes_respaldo": respaldo.stat().st_size if respaldo.is_file() else 0,
        "respaldo_existe": respaldo.is_file(),
    }


def listar_archivados(archivo, limite=30):
    """Solo metadatos; no imprime contenido privado."""
    ruta = Path(str(archivo) + ".duplicados.jsonl")
    if not ruta.is_file():
        return []
    resultado = {}
    with ruta.open("rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        f.seek(max(0, tam - 2_000_000))
        if tam > 2_000_000:
            f.readline()
        for linea in f:
            try:
                lote = json.loads(linea)
                if isinstance(lote, dict) and isinstance(lote.get("duplicados"), dict):
                    for clave, dato in lote["duplicados"].items():
                        if isinstance(dato, dict):
                            resultado[clave] = dato
            except (UnicodeError, ValueError, TypeError):
                continue
    cantidad = max(0, min(100, int(limite)))
    return list(resultado)[-cantidad:] if cantidad else []


def restaurar(gestor, clave, confirmado=False):
    """Recupera la versión archivada sin sobrescribir recuerdos existentes."""
    if not confirmado:
        raise PermissionError("Se requiere confirmación explícita")
    if clave in gestor.long_term_memory:
        return False
    ruta = Path(str(gestor.filepath) + ".duplicados.jsonl")
    if not ruta.is_file():
        return False
    encontrado = None
    # El archivo es local; lectura limitada a 2 MB más recientes.
    with ruta.open("rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        f.seek(max(0, tam - 2_000_000))
        if tam > 2_000_000:
            f.readline()
        for linea in f:
            try:
                lote = json.loads(linea)
                if isinstance(lote, dict) and isinstance(lote.get("duplicados"), dict):
                    candidato = lote["duplicados"].get(clave)
                    if isinstance(candidato, dict):
                        encontrado = candidato
            except (UnicodeError, ValueError, TypeError):
                continue
    if encontrado is None:
        return False
    gestor.long_term_memory[clave] = encontrado
    try:
        gestor.persistir()
    except Exception:
        gestor.long_term_memory.pop(clave, None)
        raise
    return True
