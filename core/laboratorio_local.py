"""Registro de experimentos y métricas, no ejecuta entrenamiento."""
import json
from pathlib import Path


def registrar(ruta, nombre, parametros, metricas):
    if not nombre or len(nombre) > 100:
        raise ValueError("Nombre de experimento inválido")
    for valores in (parametros, metricas):
        if not isinstance(valores, dict):
            raise ValueError("Parámetros y métricas deben ser diccionarios")
    entrada = {"nombre": nombre, "parametros": parametros, "metricas": metricas}
    texto = json.dumps(entrada, ensure_ascii=False, allow_nan=False)
    if len(texto) > 10000:
        raise ValueError("Experimento demasiado grande")
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as archivo:
        archivo.write(texto + "\n")
    return entrada


def historial(ruta, limite=100):
    archivo = Path(ruta)
    if not archivo.exists():
        return []
    return [json.loads(linea) for linea in archivo.read_text(encoding="utf-8").splitlines()[-limite:]]
