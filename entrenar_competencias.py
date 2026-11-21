"""Entrenamiento explícito y aislado con ejercicios sintéticos verificados."""
import argparse
import json
import math
from pathlib import Path
from tempfile import mkdtemp
from time import perf_counter

import config
from core import competencias
from core.data import cargar_validacion
from entrenamiento_guiado import acierto_en_validacion
from trainer_engine import ConfigEntrenamiento, TrainerEngine


def entrenar(origen, carpeta, pasos, variantes=None):
    if not 1 <= pasos <= 20:
        raise ValueError("El piloto admite entre 1 y 20 pasos.")
    origen = Path(origen).resolve(strict=True)
    base = Path(carpeta).resolve()
    if origen.is_relative_to(base):
        raise ValueError("Usa una carpeta de experimentos separada de los pesos originales.")
    validacion = cargar_validacion()
    if not validacion:
        raise ValueError("Falta la validación fija del alumno.")
    variantes = variantes if variantes is not None else {}
    if not isinstance(variantes, dict) or not variantes.keys() <= competencias.PRACTICA.keys():
        raise ValueError("El archivo solo admite materias del catálogo con variantes numéricas.")
    ejercicios = [competencias.ejercicio(materia, variantes.get(materia)) for materia in competencias.PRACTICA]
    reservadas = {p for casos in competencias.RESERVADOS.values() for p, _ in casos}
    if any(p in reservadas for p, _ in ejercicios):
        raise ValueError("Un ejercicio coincide con el conjunto reservado.")
    practicas = [f"usuario: {p}\ncerebro: {r}" for p, r in ejercicios]
    base.mkdir(parents=True, exist_ok=True)
    salida = Path(mkdtemp(prefix="competencias-", dir=base))
    ce = ConfigEntrenamiento(batch_size=2, lr=.0001)
    entrenador = TrainerEngine.desde_checkpoint(str(origen), practicas, validacion, ce,
                                                  con_optimizador=False)
    antes = competencias.evaluar(entrenador.modelo)
    perdida_antes = entrenador.evaluar()["bpb"]
    inicio = perf_counter()
    entrenador.entrenar(pasos)
    duracion = perf_counter() - inicio
    candidato = salida / "candidato.npz"
    entrenador.guardar_ultimo(str(candidato))
    despues = competencias.evaluar(entrenador.modelo)
    perdida_despues = entrenador.evaluar()["bpb"]
    referencia = Path(config.VALIDACION_FILE)
    exactitud_antes = acierto_en_validacion(origen, referencia)
    exactitud_despues = acierto_en_validacion(candidato, referencia)
    regresa = [materia for materia, nota in antes["materias"].items()
               if despues["materias"][materia]["aciertos"] < nota["aciertos"]]
    mejora = [materia for materia, nota in antes["materias"].items()
              if despues["materias"][materia]["aciertos"] > nota["aciertos"]]
    informe = {"banco": 1, "antes": antes, "despues": despues, "mejoras": mejora, "regresiones": regresa,
               "validacion_bpb_antes": perdida_antes, "validacion_bpb_despues": perdida_despues,
               "pasos": pasos, "segundos_entrenamiento": duracion, "candidato": str(candidato),
               "variantes_verificadas": variantes,
               "validacion_exacta_antes": exactitud_antes, "validacion_exacta_despues": exactitud_despues,
               "elegible_para_revision": bool(
                   mejora and not regresa and math.isfinite(perdida_despues) and perdida_despues <= perdida_antes
                   and exactitud_despues["exactas"] >= exactitud_antes["exactas"])}
    (salida / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return informe


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--origen", default=config.CKPT_MEJOR)
    argumentos.add_argument("--salida", required=True, help="carpeta separada para copias y resultados")
    argumentos.add_argument("--pasos", type=int, default=3)
    argumentos.add_argument("--ejecutar", action="store_true")
    argumentos.add_argument("--variantes", type=Path, help="JSON revisado: materia → variante numérica")
    argumentos.add_argument("--registrar", action="store_true", help="añadir métricas al registro de este hogar de Cerebro")
    opciones = argumentos.parse_args()
    if not opciones.ejecutar:
        argumentos.error("Confirma el entrenamiento explícitamente con --ejecutar.")
    variantes = None
    if opciones.variantes:
        with opciones.variantes.open("r", encoding="utf-8") as entrada:
            datos = entrada.read(4097)
        if len(datos) > 4096:
            argumentos.error("El archivo de variantes supera 4 KiB.")
        variantes = json.loads(datos)
    informe = entrenar(opciones.origen, opciones.salida, opciones.pasos, variantes)
    if opciones.registrar:
        competencias.guardar(config.raiz_datos(), informe["antes"])
        competencias.guardar(config.raiz_datos(), {**informe["despues"], "tipo": "candidato",
                                                      "elegible_para_revision": informe["elegible_para_revision"]})
    print(competencias.resumen(informe["antes"]))
    print("Después del entrenamiento:")
    print(competencias.resumen(informe["despues"]))
    print(f"Validación: {informe['validacion_bpb_antes']:.4f} → {informe['validacion_bpb_despues']:.4f} bits/byte")
    exacta_antes = informe["validacion_exacta_antes"]["exactas"]
    exacta_despues = informe["validacion_exacta_despues"]["exactas"]
    print(f"Acierto de validación: {exacta_antes:.1%} → {exacta_despues:.1%}")
    print(f"Candidato aislado: {informe['candidato']}")
    print("Elegible para revisión manual." if informe["elegible_para_revision"] else "Candidato rechazado.")


if __name__ == "__main__":
    main()
