# -*- coding: utf-8 -*-
"""
Evolución de hiperparámetros: un algoritmo evolutivo REAL (no simulado).

  1. Se crea una población de "genomas" (tasa de aprendizaje, dropout,
     decaimiento de pesos, capas, ancho, tamaño de lote).
  2. Cada genoma entrena un modelo desde cero unos pocos pasos y se mide su
     validación real (bits por byte).
  3. Sobreviven los mejores (élite); el resto de la nueva generación son
     hijos: cruce de dos padres + mutación aleatoria.
  4. Tras varias generaciones, el mejor genoma se entrena más tiempo. Su
     checkpoint sustituye a best.npz SOLO si mejora al que ya existía
     (comparación justa: ambos evaluados hoy sobre la misma validación).

Todo está limitado por un presupuesto de parámetros para no salirse de lo
que tu máquina aguanta.

Uso:
    python3 evolve.py                                   # valores por defecto
    python3 evolve.py --poblacion 6 --generaciones 3 --pasos-candidato 250 --pasos-final 3000
"""

import argparse
import json
import math
import os
import random
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from core.data import cargar_datos
from train import bpb_del_mejor_existente
from trainer_engine import ConfigEntrenamiento, TrainerEngine
from core.tokenizer import crear_tokenizador

# Espacio de búsqueda: cada gen es una lista de valores permitidos o un rango log.
ESPACIO = {
    "lr": ("log", 5e-4, 8e-3),
    "dropout": ("lista", [0.0, 0.05, 0.1, 0.15, 0.2, 0.3]),
    "weight_decay": ("lista", [0.0, 0.01, 0.05, 0.1]),
    "n_layers": ("lista", [1, 2, 3, 4]),
    "dim": ("lista", [32, 48, 64, 96]),
    "batch_size": ("lista", [8, 16, 32]),
}


def genoma_aleatorio(rng):
    g = {}
    for nombre, (tipo, *datos) in ESPACIO.items():
        if tipo == "log":
            g[nombre] = math.exp(rng.uniform(math.log(datos[0]), math.log(datos[1])))
        else:
            g[nombre] = rng.choice(datos[0])
    return g


def cruzar(a, b, rng):
    return {k: (a[k] if rng.random() < 0.5 else b[k]) for k in a}


def mutar(g, rng, tasa=0.3):
    g = dict(g)
    for nombre, (tipo, *datos) in ESPACIO.items():
        if rng.random() < tasa:
            if tipo == "log":
                g[nombre] = min(datos[1], max(datos[0], g[nombre] * math.exp(rng.gauss(0, 0.4))))
            else:
                g[nombre] = rng.choice(datos[0])
    return g


def _n_heads(dim):
    return 4 if dim % 4 == 0 else 2


def construir(genoma, docs_train, docs_val, tokenizador, seed):
    ce = ConfigEntrenamiento(lr=genoma["lr"], weight_decay=genoma["weight_decay"],
                             batch_size=genoma["batch_size"], seed=seed, eval_cada=10 ** 9)
    perfil = config.PERFILES[config.PERFIL]
    cambios = dict(dim=genoma["dim"], n_heads=_n_heads(genoma["dim"]),
                   n_layers=genoma["n_layers"], dim_ffn=4 * genoma["dim"],
                   dropout=genoma["dropout"], block_size=perfil["block_size"])
    return TrainerEngine.desde_cero(docs_train, docs_val, ce=ce, tokenizador=tokenizador,
                                    cambios_modelo=cambios)


def evaluar_genoma(genoma, docs_train, docs_val, tokenizador, pasos, seed, max_params):
    trainer = construir(genoma, docs_train, docs_val, tokenizador, seed)
    if trainer.modelo.n_parametros() > max_params:
        return float("inf"), trainer
    trainer.entrenar(pasos, log=None)
    return trainer.evaluar()["bpb"], trainer


def main():
    ap = argparse.ArgumentParser(description="Evolución de hiperparámetros de Cerebro")
    ap.add_argument("--poblacion", type=int, default=6)
    ap.add_argument("--generaciones", type=int, default=3)
    ap.add_argument("--pasos-candidato", type=int, default=250)
    ap.add_argument("--pasos-final", type=int, default=3000)
    ap.add_argument("--max-parametros", type=int, default=600_000)
    ap.add_argument("--corpus", default=None)
    ap.add_argument("--semilla", type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.semilla)
    docs_train, docs_val, origen = cargar_datos(args.corpus, config.FRACCION_VALIDACION)
    print(f"Corpus: {len(docs_train)} entrenamiento / {len(docs_val)} validación ({origen})")

    # Un único tokenizador compartido: así todos los candidatos son comparables.
    tok = crear_tokenizador(config.TOKENIZADOR, config.PERFILES[config.PERFIL]["vocab_objetivo"])
    tok.entrenar(docs_train)

    poblacion = [genoma_aleatorio(rng) for _ in range(args.poblacion)]
    historial, mejor = [], (float("inf"), None)
    n_elite = max(1, args.poblacion // 3)

    for gen in range(1, args.generaciones + 1):
        print(f"\n--- GENERACIÓN {gen}/{args.generaciones} ---")
        puntuados = []
        for i, g in enumerate(poblacion, 1):
            t0 = time.time()
            bpb, _ = evaluar_genoma(g, docs_train, docs_val, tok, args.pasos_candidato,
                                    args.semilla + gen * 100 + i, args.max_parametros)
            puntuados.append((bpb, g))
            historial.append({"generacion": gen, "bpb": bpb, "genoma": g})
            desc = " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in g.items())
            print(f"  candidato {i}: {bpb:.3f} bpb ({time.time() - t0:.0f}s) | {desc}")
        puntuados.sort(key=lambda p: p[0])
        if puntuados[0][0] < mejor[0]:
            mejor = puntuados[0]
        elite = [g for _, g in puntuados[:n_elite]]
        print(f"  mejor de la generación: {puntuados[0][0]:.3f} bpb")

        # Nueva generación: la élite pasa intacta, el resto son hijos mutados.
        hijos = list(elite)
        while len(hijos) < args.poblacion:
            a, b = rng.choice(elite), rng.choice(elite)
            hijos.append(mutar(cruzar(a, b, rng), rng))
        poblacion = hijos

    bpb_mejor, genoma = mejor
    print(f"\n[OK] Mejor genoma encontrado ({bpb_mejor:.3f} bpb): {genoma}")

    os.makedirs(config.DIR_EVOLUTION, exist_ok=True)
    with open(os.path.join(config.DIR_EVOLUTION, "historial.json"), "w", encoding="utf-8") as f:
        json.dump({"mejor": {"bpb": bpb_mejor, "genoma": genoma}, "historial": historial},
                  f, indent=2)

    print(f"\n--- ENTRENAMIENTO FINAL DEL GANADOR ({args.pasos_final} pasos) ---")
    trainer = construir(genoma, docs_train, docs_val, tok, args.semilla + 999)
    trainer.ce.eval_cada = max(100, args.pasos_final // 6)
    resumen = trainer.entrenar(args.pasos_final)
    ruta_evo = os.path.join(config.DIR_EVOLUTION, "best.npz")
    trainer.guardar_mejor(ruta_evo)
    print(f"[OK] Candidato evolucionado guardado en {os.path.relpath(ruta_evo)} "
          f"({resumen['mejor_bpb']:.3f} bpb)")

    previo = bpb_del_mejor_existente(docs_val)
    if previo is None or resumen["mejor_bpb"] < previo:
        trainer.guardar_mejor(config.CKPT_MEJOR)
        print(f"[OK] Mejora al modelo principal -> {os.path.relpath(config.CKPT_MEJOR)} sustituido.")
    else:
        print(f"[i] El modelo principal ya rinde mejor ({previo:.3f} bpb); se conserva sin cambios.")


if __name__ == "__main__":
    main()
