"""Entrenamiento neuronal supervisado y protegido, opt-in y 100% local.

Uso: python3 entrenamiento_guiado.py --pasos 100
No descarga modelos, no ejecuta automáticamente al instalar o fusionar.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

import config
from core.seguridad_aprendizaje import respaldar, restaurar, evaluar_fijo

RAIZ = Path(__file__).resolve().parent


def decidir_aceptacion(antes, despues, tolerancia=0.02):
    """No aceptar pérdidas no medibles ni regresiones mayores a tolerancia."""
    if despues is None:
        return False
    if antes is None:
        return True
    return despues <= antes * (1 + tolerancia)


def entrenar_guiado(pasos, lr):
    """Continúa los pesos actuales; revierte ambos checkpoints ante fallos."""
    if not 1 <= pasos <= 1000:
        raise ValueError("Los pasos deben estar entre 1 y 1000")
    if not 0 < lr <= 0.001:
        raise ValueError("La tasa de aprendizaje debe estar entre 0 y 0.001")
    ultimo = Path(config.CKPT_ULTIMO)
    mejor = Path(config.CKPT_MEJOR)
    validacion = Path(config.VALIDACION_FILE)
    if not ultimo.is_file():
        raise FileNotFoundError("Falta checkpoints/last.npz: entrena primero el modelo original.")
    if not validacion.is_file():
        raise FileNotFoundError("Falta data/validacion.txt: no entrenamos sin validación fija.")
    # El corpus guiado se incluye automáticamente desde data/corpus/ por train.py.
    if not (RAIZ / "data/corpus/entrenamiento_guiado.txt").is_file():
        raise FileNotFoundError("Falta el currículo de entrenamiento guiado.")
    rutas = [ultimo, mejor]
    carpeta, copias = respaldar(rutas)
    try:
        antes = {ruta: evaluar_fijo(ruta, validacion) for ruta in rutas}
        comando = [sys.executable, str(RAIZ / "train.py"), "--resume",
                   "--pasos", str(pasos), "--lr", str(lr)]
        print("Validación anterior:", {p.name: v for p, v in antes.items()}, flush=True)
        subprocess.run(comando, cwd=RAIZ, check=True)
        despues = {ruta: evaluar_fijo(ruta, validacion) for ruta in rutas}
        print("Validación posterior:", {p.name: v for p, v in despues.items()}, flush=True)
        if not all(decidir_aceptacion(antes[r], despues[r]) for r in rutas):
            restaurar(copias)
            print("Entrenamiento rechazado: checkpoints restaurados.", flush=True)
            return False
        print("Entrenamiento aceptado. Los pesos se han actualizado.", flush=True)
        return True
    except BaseException:
        restaurar(copias)
        raise
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Entrenamiento guiado protegido de Cerebro")
    ap.add_argument("--pasos", type=int, default=100)
    ap.add_argument("--lr", type=float, default=0.0003)
    args = ap.parse_args()
    try:
        return 0 if entrenar_guiado(args.pasos, args.lr) else 1
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Error de entrenamiento: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
