# -*- coding: utf-8 -*-
"""
Entrenamiento de Cerebro.

    python3 train.py                       # entrena desde cero (perfil de config.py)
    python3 train.py --pasos 3000          # número de pasos explícito
    python3 train.py --epocas 30           # o expresado en pasadas por el corpus
    python3 train.py --resume              # continúa desde checkpoints/last.npz
    python3 train.py --corpus mis_textos/  # corpus alternativo (archivo o carpeta)
    CEREBRO_PERFIL=diminuto python3 train.py

Al terminar guarda checkpoints/last.npz (con estado del optimizador, para
--resume) y actualiza checkpoints/best.npz SOLO si el nuevo modelo es mejor
que el que ya había (mismo texto de validación, comparado en bits por byte).
Usa --forzar para sobrescribir best.npz sin comparar.
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from core.checkpoint import cargar_checkpoint
from core.data import cargar_datos
from trainer_engine import (ConfigEntrenamiento, TrainerEngine, evaluar_modelo_en_docs,
                            precision_de_respuestas)


def bpb_del_mejor_existente(docs_val):
    """bpb del best.npz actual sobre la validación de HOY (o None)."""
    if not os.path.exists(config.CKPT_MEJOR):
        return None
    try:
        modelo = cargar_checkpoint(config.CKPT_MEJOR, con_optimizador=False)["modelo"]
        return evaluar_modelo_en_docs(modelo, docs_val)["bpb"]
    except Exception as e:  # checkpoint viejo/incompatible: no bloquea entrenar
        print(f"[i] No se pudo evaluar el best.npz existente ({e}); se sobrescribirá.")
        return None


def main():
    ap = argparse.ArgumentParser(description="Entrenamiento de Cerebro")
    ap.add_argument("--pasos", type=int, default=None, help="pasos de entrenamiento")
    ap.add_argument("--perfil", choices=sorted(config.PERFILES), default=None,
                    help="perfil de modelo (también puede usarse CEREBRO_PERFIL)")
    ap.add_argument("--tamano", choices=sorted(config.TAMANOS_NUCLEO), default=None,
                    help="único ajuste de capacidad NumPy: mini, normal, grande, potente, extra, maximo, experimental")
    ap.add_argument("--listar-tamanos", action="store_true", help="mostrar perfiles y memoria estimada sin entrenar")
    ap.add_argument("--epocas", type=float, default=None, help="alternativa a --pasos")
    ap.add_argument("--resume", action="store_true", help="continuar desde last.npz (o best.npz)")
    ap.add_argument("--corpus", default=None, help="archivo o carpeta de corpus alternativo")
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--batch", type=int, default=None)
    ap.add_argument("--dropout", type=float, default=None)
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--forzar", action="store_true", help="sobrescribir best.npz sin comparar")
    args = ap.parse_args()

    if args.listar_tamanos:
        for nombre, perfil in config.TAMANOS_NUCLEO.items():
            n = config.estimar_parametros(perfil)
            # Pesos + gradientes + 2 momentos AdamW, float32 (mínimo teórico).
            memoria_mib = n * 16 / (1024 ** 2)
            print(f"{nombre:14} {perfil:10} {n:>13,} parámetros | >= {memoria_mib:,.0f} MiB para pesos/gradientes/AdamW")
        return
    if args.tamano and args.perfil:
        ap.error("Usa --tamano o --perfil, no ambos.")

    ce = ConfigEntrenamiento()
    if args.lr is not None:
        ce.lr = args.lr
    if args.batch is not None:
        ce.batch_size = args.batch
    if args.semilla is not None:
        ce.seed = args.semilla

    docs_train, docs_val, origen_val = cargar_datos(args.corpus, ce.fraccion_val)
    print(f"Corpus: {len(docs_train)} documentos de entrenamiento / {len(docs_val)} de validación "
          f"({origen_val})")

    if args.resume:
        origen = config.CKPT_ULTIMO if os.path.exists(config.CKPT_ULTIMO) else config.CKPT_MEJOR
        if not os.path.exists(origen):
            sys.exit("[!] No hay checkpoint para reanudar. Entrena primero sin --resume.")
        trainer = TrainerEngine.desde_checkpoint(origen, docs_train, docs_val, ce)
        print(f"[OK] Reanudando desde {os.path.relpath(origen)} (paso {trainer.paso})")
    else:
        cambios = {"dropout": args.dropout} if args.dropout is not None else None
        trainer = TrainerEngine.desde_cero(docs_train, docs_val, perfil=(config.perfil_por_tamano(args.tamano) if args.tamano
                                                       else args.perfil or config.PERFIL),
                                               ce=ce, cambios_modelo=cambios)

    m = trainer.modelo
    print(f"Modelo: {m.n_parametros():,} parámetros | "
          f"{m.cfg.n_layers} capas x {m.cfg.n_heads} cabezas | dim {m.cfg.dim} | "
          f"contexto {m.cfg.block_size} | vocabulario {len(m.tokenizer)} ({m.tokenizer.tipo})")
    print(f"Tokens: {len(trainer.stream_train):,} entrenamiento ({trainer.stream_train.n_objetivos():,} objetivos de "
          f"pérdida) / {len(trainer.stream_val):,} validación")

    tokens_por_paso = ce.batch_size * trainer.cargador.T * ce.acumulacion_gradientes
    if args.pasos is not None:
        pasos = args.pasos
    elif args.epocas is not None:
        pasos = max(1, int(args.epocas * len(trainer.stream_train) / tokens_por_paso))
    else:
        pasos = config.PASOS_POR_DEFECTO
    print(f"\n--- ENTRENANDO {pasos} pasos (batch {ce.batch_size} x {trainer.cargador.T}, "
          f"acumulación {ce.acumulacion_gradientes} = {tokens_por_paso:,} tokens/actualización) ---")

    try:
        resumen = trainer.entrenar(pasos)
    except KeyboardInterrupt:
        print("\n[!] Interrumpido: se guarda lo conseguido hasta ahora.")
        if trainer.mejor is None:
            ev = trainer.evaluar()
            trainer._registrar_mejor(ev)
        resumen = {"mejor_bpb": trainer.mejor["bpb"], "mejor_paso": trainer.mejor["paso"]}

    trainer.guardar_ultimo(config.CKPT_ULTIMO)
    print(f"\n[OK] Estado final guardado en {os.path.relpath(config.CKPT_ULTIMO)}")

    actual = trainer.modelo.state_dict()
    if trainer.mejor:
        trainer.modelo.load_state_dict(trainer.mejor["estado"])
    prec = precision_de_respuestas(trainer.modelo, docs_val)
    trainer.modelo.load_state_dict(actual)
    print(f"Mejor modelo de esta corrida: {prec['exactas'] * 100:.0f}% de respuestas exactas "
          f"(similitud {prec['similitud']:.2f}) sobre {prec['n']} preguntas reformuladas.")

    nuevo = resumen["mejor_bpb"]
    previo = None if args.forzar else bpb_del_mejor_existente(docs_val)
    if previo is None or nuevo < previo:
        trainer.guardar_mejor(config.CKPT_MEJOR)
        extra = "" if previo is None else f" (antes {previo:.3f} bpb)"
        print(f"[OK] Nuevo mejor modelo -> {os.path.relpath(config.CKPT_MEJOR)}: "
              f"{nuevo:.3f} bpb en el paso {resumen['mejor_paso']}{extra}")
    else:
        print(f"[i] best.npz se conserva: ya rinde mejor ({previo:.3f} bpb) que este "
              f"entrenamiento ({nuevo:.3f} bpb). Usa --forzar para sobrescribirlo.")


if __name__ == "__main__":
    main()
