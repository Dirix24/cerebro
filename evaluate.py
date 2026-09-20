# -*- coding: utf-8 -*-
"""
Evaluación y diagnóstico de un modelo entrenado (sin simulaciones).

    python3 evaluate.py                 # evalúa checkpoints/best.npz
    python3 evaluate.py --ckpt otro.npz
    python3 evaluate.py --rapido        # omite el benchmark de velocidad

Informa de:
  * respuestas   : % de preguntas reformuladas que el modelo contesta EXACTAMENTE
                   como el corpus (generación voraz) — lo que se nota al chatear.
  * validación   : reformulaciones NUEVAS de cosas que el modelo sí aprendió
                   (data/validacion.txt). Es la métrica con la que se elige el
                   mejor checkpoint.
  * generalización: diálogos totalmente nuevos (data/generalizacion.txt).
                   Mide cuánto CONOCIMIENTO nuevo tiene; en un modelo tan
                   pequeño será alta (mala) y es lo esperado.
  * muestras reales de generación y velocidad medida.
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from benchmarks.benchmark_engine import BenchmarkEngine
from core.checkpoint import cargar_checkpoint
from core.data import cargar_generalizacion, cargar_validacion, cargar_test
from trainer_engine import evaluar_modelo_en_docs, precision_de_respuestas

PRUEBAS = [
    ("pregunta del corpus",        "usuario: ¿Quién eres?\ncerebro:"),
    ("pregunta del corpus",        "usuario: ¿Qué es un token?\ncerebro:"),
    ("reformulada / informal",     "usuario: dime que es la atencion\ncerebro:"),
    ("reformulada / informal",     "usuario: como se entrena cerebro\ncerebro:"),
    ("tema que NO está en corpus", "usuario: ¿Cuál es la capital de Francia?\ncerebro:"),
]


def main():
    ap = argparse.ArgumentParser(description="Evaluación de Cerebro")
    ap.add_argument("--ckpt", default=config.CKPT_MEJOR)
    ap.add_argument("--rapido", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.ckpt):
        sys.exit(f"[!] No existe {args.ckpt}. Entrena primero: python3 train.py")
    datos = cargar_checkpoint(args.ckpt, con_optimizador=False)
    modelo, meta = datos["modelo"], datos["meta"]
    c = modelo.cfg

    print("=" * 60)
    print("INFORME DE EVALUACIÓN DE CEREBRO")
    print("=" * 60)
    print(f"Checkpoint     : {os.path.relpath(args.ckpt)} (mejores pesos del paso {meta.get('mejor_paso', meta.get('paso'))}, {meta.get('fecha')})")
    print(f"Arquitectura   : {c.n_layers} capas x {c.n_heads} cabezas | dim {c.dim} | "
          f"ffn {c.dim_ffn} | contexto {c.block_size} | dropout {c.dropout}")
    print(f"Parámetros     : {modelo.n_parametros():,}")
    print(f"Tokenizador    : {modelo.tokenizer.tipo}, {len(modelo.tokenizer)} tokens")

    val = cargar_validacion()
    if val:
        e = evaluar_modelo_en_docs(modelo, val)
        print(f"Validación     : {e['loss']:.3f} nats/token | ppl {e['ppl']:.2f} | "
              f"{e['bpb']:.3f} bits/byte   (reformulaciones nuevas)")
        p = precision_de_respuestas(modelo, val)
        print(f"Respuestas     : {p['exactas'] * 100:.0f}% exactas | similitud {p['similitud']:.2f} "
              f"({p['n']} preguntas reformuladas, generación voraz)")
    gen = cargar_generalizacion()
    if gen:
        e = evaluar_modelo_en_docs(modelo, gen)
        print(f"Generalización : {e['loss']:.3f} nats/token | ppl {e['ppl']:.2f} | "
              f"{e['bpb']:.3f} bits/byte   (diálogos nunca vistos)")
    test = cargar_test()
    if test:
        e = evaluar_modelo_en_docs(modelo, test)
        p = precision_de_respuestas(modelo, test)
        print(f"TEST FINAL     : {e['loss']:.3f} nats/token | ppl {e['ppl']:.2f} | "
              f"{e['bpb']:.3f} bits/byte | {p['exactas'] * 100:.0f}% exactas "
              f"({p['n']} preguntas). Solo evaluación; no selecciona checkpoints.")

    if not args.rapido:
        b = BenchmarkEngine(modelo).ejecutar_benchmark_completo()
        print(f"RAM del proceso: {b['ram_mb']} MB")
        print(f"Velocidad      : {b['tok_s_entrenamiento']:,} tok/s entrenando | "
              f"{b['tok_s_generacion']} tok/s generando")

    print("\nMuestras reales (temperatura 0.3):")
    for etiqueta, prompt in PRUEBAS:
        r = modelo.generar(prompt, max_nuevos=60, temperatura=0.3, top_k=20, top_p=0.9,
                           penalizacion=1.05, parar_en=("\n",), seed=1, incluir_prompt=False)
        print(f"  [{etiqueta}]\n    {prompt.splitlines()[0]}\n    cerebro:{r}")
    print("\n[OK] Diagnóstico completado sin simulaciones ni APIs externas.")


if __name__ == "__main__":
    main()
