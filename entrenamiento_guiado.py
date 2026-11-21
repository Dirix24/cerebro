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


def acierto_en_validacion(ruta, validacion):
    from core.checkpoint import cargar_checkpoint
    from core.data import documentos_desde_texto
    from trainer_engine import precision_de_respuestas

    documentos = documentos_desde_texto(validacion.read_text(encoding="utf-8"))
    modelo = cargar_checkpoint(str(ruta), con_optimizador=False)["modelo"]
    return precision_de_respuestas(modelo, documentos)


def entrenar_guiado(pasos, lr, *, tiempo_maximo=600):
    """Entrena una copia local y conserva el candidato solo si mejora."""
    if not 1 <= pasos <= 1000:
        raise ValueError("Los pasos deben estar entre 1 y 1000")
    if not 0 < lr <= 0.001:
        raise ValueError("La tasa de aprendizaje debe estar entre 0 y 0.001")
    if not 30 <= tiempo_maximo <= 3600:
        raise ValueError("El tiempo máximo debe estar entre 30 y 3600 segundos.")
    ultimo, mejor = Path(config.CKPT_ULTIMO), Path(config.CKPT_MEJOR)
    validacion = Path(config.VALIDACION_FILE)
    if not mejor.is_file():
        raise FileNotFoundError("Se necesita best.npz para iniciar y medir un candidato.")
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
        if ultimo.is_file():
            shutil.copy2(ultimo, carpeta / "checkpoints" / "last.npz")
        shutil.copy2(referencia, carpeta / "checkpoints" / "best.npz")
        antes = evaluar_fijo(referencia, validacion_copia)
        comando = [sys.executable, str(RAIZ / "train.py"), "--resume",
                   "--pasos", str(pasos), "--lr", str(lr)]
        subprocess.run(comando, cwd=RAIZ,
                       env={**os.environ, "CEREBRO_HOME": str(carpeta), "OPENBLAS_NUM_THREADS": "1",
                            "OMP_NUM_THREADS": "1"}, timeout=tiempo_maximo, check=True)
        candidato = carpeta / "checkpoints" / "best.npz"
        despues = evaluar_fijo(candidato, validacion_copia)
        print(f"Validación fija · activo: {antes} · candidato: {despues}", flush=True)
        if not decidir_aceptacion(antes, despues):
            print("Candidato descartado: no mejoró la pérdida fija.", flush=True)
            return False
        aciertos_antes = acierto_en_validacion(referencia, validacion_copia)
        aciertos_despues = acierto_en_validacion(candidato, validacion_copia)
        if aciertos_antes["n"]:
            print(f"Acierto en {aciertos_antes['n']} reformulaciones · "
                  f"activo: {aciertos_antes['exactas']:.1%} · candidato: {aciertos_despues['exactas']:.1%}",
                  flush=True)
            if aciertos_despues["exactas"] < aciertos_antes["exactas"]:
                print("Candidato descartado: empeoró el acierto exacto.", flush=True)
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
    ap.add_argument("--tiempo-maximo", type=int, default=600, help="límite del proceso de entrenamiento en segundos")
    args = ap.parse_args()
    try:
        return 0 if entrenar_guiado(args.pasos, args.lr, tiempo_maximo=args.tiempo_maximo) else 1
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Error de entrenamiento: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
