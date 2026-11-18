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
    ap.add_argument("--estacion-terminal", action="store_true", help="abrir estación neuronal en terminal sin modelo")
    ap.add_argument("--diagnostico-memoria", action="store_true", help="estadísticas locales sin mostrar recuerdos")
    ap.add_argument("--archivados", action="store_true", help="listar claves de recuerdos archivados")
    ap.add_argument("--restaurar-recuerdo", metavar="CLAVE", help="restaurar una clave archivada sin sobrescribir")
    ap.add_argument("--una-vez", default=None, metavar="MENSAJE")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--huesped", choices=["estado", "vincular", "desvincular"], default=None,
                    help="modo simbiótico: consultar o gestionar el equipo autorizado")
    ap.add_argument("--confirmar", action="store_true", help="autorizar expresamente la vinculación del equipo")
    ap.add_argument("--guardar-historial", action="store_true", help="guardar turnos localmente")
    args = ap.parse_args()

    if args.diagnostico_memoria or args.archivados or args.restaurar_recuerdo:
        import json
        from memory.diagnostico import informe, listar_archivados, restaurar
        memoria = AdvancedMemoryManager()
        if args.diagnostico_memoria:
            print(json.dumps(informe(memoria.long_term_memory, memoria.filepath),
                             ensure_ascii=False, indent=2))
        elif args.archivados:
            print(json.dumps(listar_archivados(memoria.filepath), ensure_ascii=False, indent=2))
        else:
            if not args.confirmar:
                ap.error("Restaurar requiere --confirmar y no sobrescribe recuerdos existentes")
            recuperado = restaurar(memoria, args.restaurar_recuerdo, confirmado=True)
            print("Recuerdo restaurado." if recuperado else "No se encontró o ya existe.")
        return

    if args.estacion_terminal:
        from core.estacion_terminal import abrir
        abrir()
        return

    from core.entorno_portatil import verificar_almacenamiento
    verificar_almacenamiento()
    if args.huesped:
        import json
        from core.modo_simbiotico import estado_huesped, vincular_huesped, desvincular_huesped
        if args.huesped == "vincular":
            if not args.confirmar:
                ap.error("Para vincular este equipo añade --confirmar.")
            resultado = vincular_huesped(confirmado=True)
        elif args.huesped == "desvincular":
            resultado = {"desvinculado": desvincular_huesped()}
        else:
            resultado = estado_huesped()
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return
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
        respuesta, _ = conv.procesar(args.una_vez)
        print(respuesta)
        if args.guardar_historial:
            from core.historial_local import guardar
            from pathlib import Path
            ruta_hist = Path(config.CEREBRO_HOME) / "data" / "historial_cerebro.jsonl"
            guardar(ruta_hist, "usuario", args.una_vez)
            if respuesta:
                guardar(ruta_hist, "cerebro", respuesta)
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
        import unicodedata
        normal = "".join(c for c in unicodedata.normalize("NFD", entrada.lower())
                         if unicodedata.category(c) != "Mn")
        if (entrada.strip().lower() == "/estacion-terminal" or
                any(frase in normal for frase in ("abre la estacion neuronal",
                                                  "muestra la estacion neuronal",
                                                  "quiero ver tus neuronas"))):
            try:
                from core.estacion_terminal import abrir
                abrir(memoria_fn=lambda: conv.memoria.long_term_memory)
                print("Cerebro: Has vuelto al chat.")
            except (RuntimeError, OSError) as exc:
                print(f"Cerebro: No pude abrir la estación: {exc}")
            continue
        respuesta, salir = conv.procesar(entrada)
        if respuesta:
            print(f"Cerebro: {respuesta}")
        if args.guardar_historial and entrada.strip() and not entrada.startswith("/"):
            from core.historial_local import guardar
            from pathlib import Path
            ruta_hist = Path(config.CEREBRO_HOME) / "data" / "historial_cerebro.jsonl"
            try:
                guardar(ruta_hist, "usuario", entrada)
                if respuesta:
                    guardar(ruta_hist, "cerebro", respuesta)
            except (ValueError, OSError) as exc:
                print(f"[aviso] No se pudo guardar el historial: {exc}", file=sys.stderr)
        if salir:
            break


if __name__ == "__main__":
    main()
