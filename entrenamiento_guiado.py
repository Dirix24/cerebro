"""Entrenamiento neuronal supervisado y protegido, opt-in y 100% local.

Uso: python3 entrenamiento_guiado.py --pasos 100
No descarga modelos, no ejecuta automáticamente al instalar o fusionar.
"""
import argparse
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import mkdtemp

import config
from core.entorno_portatil import preparar_almacenamiento
from core.seguridad_aprendizaje import evaluar_fijo

RAIZ = Path(__file__).resolve().parent


def decidir_aceptacion(antes, despues):
    """Solo considera candidato evaluable si reduce la pérdida fija."""
    return (antes is not None and despues is not None
            and math.isfinite(antes) and math.isfinite(despues) and despues < antes)


def entrenar_guiado(pasos, lr):
    """Entrena una copia local y conserva el candidato solo si mejora."""
    if not 1 <= pasos <= 1000:
        raise ValueError("Los pasos deben estar entre 1 y 1000")
    if not 0 < lr <= 0.001:
        raise ValueError("La tasa de aprendizaje debe estar entre 0 y 0.001")
    ultimo, mejor = Path(config.CKPT_ULTIMO), Path(config.CKPT_MEJOR)
    validacion = Path(config.VALIDACION_FILE)
    if not ultimo.is_file() or not mejor.is_file():
        raise FileNotFoundError("Se necesitan last.npz y best.npz para medir un candidato.")
    if not validacion.is_file():
        raise FileNotFoundError("Falta data/validacion.txt: no entrenamos sin validación fija.")
    base = Path(config.raiz_datos()) / "data"
    candidatos = Path(config.raiz_datos()) / "learning" / "candidatos"
    candidatos.mkdir(parents=True, exist_ok=True)
    carpeta = Path(mkdtemp(prefix="guiado-", dir=candidatos))
    conservar = False
    try:
        preparar_almacenamiento(carpeta)
        datos = carpeta / "data"
        for nombre in ("corpus.txt", "test.txt", "generalizacion.txt"):
            origen = base / nombre
            if origen.is_file():
                shutil.copy2(origen, datos / nombre)
        if (base / "corpus").is_dir():
            shutil.copytree(base / "corpus", datos / "corpus")
        validacion_copia = datos / "validacion.txt"
        shutil.copy2(validacion, validacion_copia)
        referencia = carpeta / "referencia.npz"
        shutil.copy2(mejor, referencia)
        shutil.copy2(ultimo, carpeta / "checkpoints" / "last.npz")
        shutil.copy2(referencia, carpeta / "checkpoints" / "best.npz")
        antes = evaluar_fijo(referencia, validacion_copia)
        comando = [sys.executable, str(RAIZ / "train.py"), "--resume",
                   "--pasos", str(pasos), "--lr", str(lr)]
        subprocess.run(comando, cwd=RAIZ, env={**os.environ, "CEREBRO_HOME": str(carpeta)}, check=True)
        candidato = carpeta / "checkpoints" / "best.npz"
        despues = evaluar_fijo(candidato, validacion_copia)
        print(f"Validación fija · activo: {antes} · candidato: {despues}", flush=True)
        if not decidir_aceptacion(antes, despues):
            print("Candidato descartado: no mejoró la pérdida fija.", flush=True)
            return False
        conservar = True
        print(f"Candidato conservado para revisión: {candidato}.", flush=True)
        return True
    finally:
        if not conservar:
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
