# -*- coding: utf-8 -*-
"""
Cerebro — chat local.

    python3 main.py                        # conversación interactiva
    python3 main.py --una-vez "hola"       # un solo mensaje (útil en scripts)
    python3 main.py --semilla 7            # respuestas reproducibles
    python3 main.py --ckpt otro.npz        # usar otro checkpoint

Necesita un modelo entrenado (checkpoints/best.npz). Si no existe:
    python3 train.py
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from agent.controlled_agent import ControlledAgent
from chat import Conversacion
from core.checkpoint import cargar_checkpoint
from memory.advanced_memory import AdvancedMemoryManager


def cargar_modelo(ruta=None):
    candidatos = [ruta] if ruta else [config.CKPT_MEJOR, config.CKPT_ULTIMO]
    for r in candidatos:
        if r and os.path.exists(r):
            datos = cargar_checkpoint(r, con_optimizador=False)
            return datos["modelo"], datos["meta"], r
    return None, None, None


def main():
    ap = argparse.ArgumentParser(description="Cerebro - chat local")
    ap.add_argument("--una-vez", default=None, metavar="MENSAJE")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    modelo, meta, ruta = cargar_modelo(args.ckpt)
    if modelo is None:
        sys.exit("[!] No hay ningún modelo entrenado.\n"
                 "    Entrena uno con:  python3 train.py")
    if args.debug:
        print(f"[debug] checkpoint: {ruta} (paso {meta.get('paso')}, "
              f"val {meta.get('val_bpb', float('nan')):.3f} bpb)")

    conv = Conversacion(modelo, AdvancedMemoryManager(), ControlledAgent(),
                        info_checkpoint=meta, seed=args.semilla)

    if args.una_vez is not None:
        print(conv.procesar(args.una_vez)[0])
        return

    print("\n========================================")
    print(" CEREBRO  ·  modelo de lenguaje local")
    print(" Escribe /ayuda para ver los comandos.")
    print("========================================\n")
    while True:
        try:
            entrada = input("Tú: ")
        except (KeyboardInterrupt, EOFError):
            print("\nCerebro: Saliendo...")
            break
        respuesta, salir = conv.procesar(entrada)
        if respuesta:
            print(f"Cerebro: {respuesta}")
        if salir:
            break


if __name__ == "__main__":
    main()
