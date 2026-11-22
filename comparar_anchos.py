"""Control breve de ancho Transformer con validación común y pesos temporales."""

import argparse
import json
from pathlib import Path
import random
from time import perf_counter, process_time

import config
from core.data import cargar_datos
from core.tokenizer import crear_tokenizador
from evolve import construir, genoma_aleatorio


def comparar(semilla, pasos):
    entrenamiento, validacion, origen = cargar_datos()
    tokenizer = crear_tokenizador(config.TOKENIZADOR,
                                  min(384, config.PERFILES[config.PERFIL]["vocab_objetivo"]))
    tokenizer.entrenar(entrenamiento)
    base = {**genoma_aleatorio(random.Random(semilla)), "n_layers": 2, "batch_size": 2, "dropout": 0}
    informe = {"semilla": semilla, "pasos": pasos, "entrenamiento": len(entrenamiento),
               "validacion": len(validacion), "origen": origen, "variantes": []}
    for ancho in (32, 48):
        inicio, cpu = perf_counter(), process_time()
        motor = construir({**base, "dim": ancho}, entrenamiento, validacion, tokenizer, semilla)
        antes = motor.evaluar()["bpb"]
        motor.entrenar(pasos, log=None)
        despues = motor.evaluar()["bpb"]
        informe["variantes"].append({"dim": ancho, "parametros": motor.modelo.n_parametros(),
                                      "bpb_antes": antes, "bpb_despues": despues,
                                      "segundos": round(perf_counter() - inicio, 3),
                                      "cpu_segundos": round(process_time() - cpu, 3)})
    return informe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semilla", type=int, default=17)
    parser.add_argument("--pasos", type=int, default=4)
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    if not 1 <= args.pasos <= 30:
        parser.error("El control breve admite de 1 a 30 pasos.")
    if args.salida and args.salida.suffix.lower() != ".json":
        parser.error("El informe debe usar extensión .json.")
    informe = json.dumps(comparar(args.semilla, args.pasos), ensure_ascii=False, indent=2)
    if args.salida:
        with args.salida.open("x", encoding="utf-8") as archivo:
            archivo.write(informe + "\n")
    print(informe)


if __name__ == "__main__":
    main()
