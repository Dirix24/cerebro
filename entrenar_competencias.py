"""Entrenamiento explícito y aislado con ejercicios sintéticos verificados."""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
import os
import json
import math
from pathlib import Path
from hashlib import sha256
from platform import machine, processor, system
from random import Random
from tempfile import NamedTemporaryFile
from os import cpu_count
from tempfile import mkdtemp
from time import perf_counter, process_time

import numpy as np

import config
from core import competencias
from core.checkpoint import leer_meta
from core.data import cargar_datos, cargar_generalizacion, cargar_test, cargar_validacion
from entrenamiento_guiado import acierto_en_validacion
from trainer_engine import ConfigEntrenamiento, TrainerEngine, huella_documentos, precision_de_respuestas


def _json_atomico(ruta, datos):
    with NamedTemporaryFile(dir=ruta.parent, mode="w", encoding="utf-8", delete=False) as archivo:
        temporal = Path(archivo.name)
        json.dump(datos, archivo, ensure_ascii=False, indent=2, allow_nan=False)
    try:
        temporal.replace(ruta)
    finally:
        temporal.unlink(missing_ok=True)


@contextmanager
def _bloqueo(salida):
    if os.name != "posix":
        yield
        return
    import fcntl

    fd = os.open(salida / ".sesion.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as archivo:
        try:
            fcntl.flock(archivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Esta sesión ya está en ejecución.") from None
        yield


def _huella_archivo(ruta):
    huella = sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            huella.update(bloque)
    return huella.hexdigest()


def _preguntas(documentos):
    return {" ".join(linea.partition(":")[2].casefold().split())
            for documento in documentos for linea in documento.splitlines()
            if linea.casefold().startswith("usuario:")}


def entrenar(origen, carpeta, pasos, variantes=None, *, reanudar=None, semilla=config.SEED,
             intervalo=None, repeticion=0, lecciones=()):
    if type(pasos) is not int or pasos < 1:
        raise ValueError("El presupuesto debe incluir al menos un paso.")
    intervalo = min(8, pasos) if intervalo is None else intervalo
    if not 1 <= intervalo <= pasos or not 0 <= repeticion <= 256:
        raise ValueError("Los pasos, el intervalo y la muestra de repaso deben formar un presupuesto válido.")
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
    from core.lecciones_colectivas import validar_lecciones

    lecciones = validar_lecciones(lecciones)
    ejercicios.extend((leccion["pregunta"], leccion["respuesta"]) for leccion in lecciones)
    practicas = [f"usuario: {p}\ncerebro: {r}" for p, r in ejercicios]
    reserva = _preguntas(validacion + (cargar_test() or []) + (cargar_generalizacion() or []))
    reserva.update(" ".join(p.casefold().split()) for casos in competencias.RESERVADOS.values() for p, _ in casos)
    if _preguntas(practicas) & reserva:
        raise ValueError("Un ejercicio coincide con una pregunta reservada.")
    if repeticion:
        corpus, _, _ = cargar_datos()
        corpus = [d for d in corpus if _preguntas([d]).isdisjoint(reserva)]
        practicas += Random(semilla).sample(corpus, min(repeticion, len(corpus)))
    optimizacion = ConfigEntrenamiento(batch_size=2, lr=.0001, total_pasos=pasos, seed=semilla,
                                     eval_cada=intervalo, paciencia_early_stop=0)
    ficha = {"version": 1, "origen_sha256": _huella_archivo(origen),
             "optimizacion": asdict(optimizacion),
             "pasos": pasos, "intervalo": intervalo, "semilla": semilla, "repaso": repeticion,
             "entrenamiento_sha256": huella_documentos(practicas),
             "validacion_sha256": huella_documentos(validacion),
             "lecciones": lecciones, "variantes": variantes}
    base.mkdir(parents=True, exist_ok=True)
    if reanudar is None:
        salida = Path(mkdtemp(prefix="competencias-", dir=base))
        _json_atomico(salida / "sesion.json", ficha)
    else:
        salida = Path(reanudar).resolve(strict=True)
        if salida.parent != base or not salida.name.startswith("competencias-"):
            raise ValueError("Selecciona una sesión propia de la carpeta de experimentos.")
        manifiesto = salida / "sesion.json"
        if manifiesto.is_symlink() or manifiesto.stat().st_size > 32 * 1024 or (
                json.loads(manifiesto.read_text(encoding="utf-8")) != ficha):
            raise ValueError("El checkpoint base, los datos o el presupuesto de la sesión cambiaron.")
    with _bloqueo(salida):
        return _entrenar_sesion(origen, salida, ficha, practicas, validacion, reanudar is not None)


def _entrenar_sesion(origen, salida, ficha, practicas, validacion, reanudar):
    if (salida / "informe.json").exists():
        raise ValueError("La sesión ya tiene un informe final.")
    pasos, intervalo, semilla = (ficha[clave] for clave in ("pasos", "intervalo", "semilla"))
    cpu_inicio = process_time()
    ce = ConfigEntrenamiento(**ficha["optimizacion"])
    entrenador = TrainerEngine.desde_checkpoint(str(origen), practicas, validacion, ce,
                                                  con_optimizador=False)
    antes = competencias.evaluar(entrenador.modelo)
    perdida_antes = entrenador.evaluar()["bpb"]
    finales = {"generalizacion": cargar_generalizacion(), "test": cargar_test()}
    final_antes = {nombre: precision_de_respuestas(entrenador.modelo, docs)
                   for nombre, docs in finales.items() if docs}
    entrenador.modelo.rng = np.random.default_rng(semilla)
    entrenador.cargador.rng = np.random.default_rng(semilla)
    mejor, sin_mejora, metricas = perdida_antes, 0, []
    candidato = salida / "candidato.npz"
    if candidato.is_symlink():
        raise ValueError("El candidato debe ser un archivo local.")
    if reanudar and candidato.is_file():
        meta = leer_meta(str(candidato))
        if meta.get("sesion_competencias") != ficha:
            raise ValueError("El checkpoint intermedio no pertenece a esta sesión.")
        entrenador = TrainerEngine.desde_checkpoint(str(candidato), practicas, validacion, ce)
        metricas = meta["metricas_competencias"]
        mejor = min(perdida_antes, *(fila["bpb"] for fila in metricas))
        sin_mejora = meta["sin_mejora_competencias"]
    inicio = perf_counter()
    while entrenador.paso < pasos and sin_mejora < 3:
        entrenador.entrenar(min(intervalo, pasos - entrenador.paso))
        bpb = entrenador.historial[-1]["bpb_val"]
        sin_mejora = 0 if bpb < mejor else sin_mejora + 1
        mejor = min(mejor, bpb)
        metricas.append({"paso": entrenador.paso, "bpb": bpb})
        entrenador.guardar_ultimo(str(candidato), metadatos={"sesion_competencias": ficha,
                                  "metricas_competencias": metricas, "sin_mejora_competencias": sin_mejora})
    duracion = perf_counter() - inicio
    despues = competencias.evaluar(entrenador.modelo)
    final_despues = {nombre: precision_de_respuestas(entrenador.modelo, docs)
                     for nombre, docs in finales.items() if docs}
    perdida_despues = entrenador.evaluar()["bpb"]
    referencia = Path(config.VALIDACION_FILE)
    exactitud_antes = acierto_en_validacion(origen, referencia)
    exactitud_despues = acierto_en_validacion(candidato, referencia)
    regresa = [materia for materia, nota in antes["materias"].items()
               if despues["materias"][materia]["aciertos"] < nota["aciertos"]]
    mejora = [materia for materia, nota in antes["materias"].items()
              if despues["materias"][materia]["aciertos"] > nota["aciertos"]]
    informe = {"banco": 1, "sesion": ficha, "metricas_intermedias": metricas,
               "arquitectura": entrenador.modelo.cfg.to_dict(), "parametros": entrenador.modelo.n_parametros(),
               "hardware": {"sistema": system(), "arquitectura": machine(), "cpu": processor(), "nucleos": cpu_count()},
               "antes": antes, "despues": despues, "mejoras": mejora, "regresiones": regresa,
               "validacion_bpb_antes": perdida_antes, "validacion_bpb_despues": perdida_despues,
               "pasos": entrenador.paso, "parada_temprana": entrenador.paso < pasos, "segundos_entrenamiento": duracion, "candidato": str(candidato),
               "variantes_verificadas": ficha["variantes"], "segundos_cpu": process_time() - cpu_inicio,
               "test_no_selectivo_antes": final_antes, "test_no_selectivo_despues": final_despues,
               "validacion_exacta_antes": exactitud_antes, "validacion_exacta_despues": exactitud_despues,
               "elegible_para_revision": bool(
                   mejora and not regresa and math.isfinite(perdida_despues) and perdida_despues <= perdida_antes
                   and exactitud_despues["exactas"] >= exactitud_antes["exactas"])}
    _json_atomico(salida / "informe.json", informe)
    return informe


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--origen", default=config.CKPT_MEJOR)
    argumentos.add_argument("--salida", required=True, help="carpeta separada para copias y resultados")
    argumentos.add_argument("--pasos", type=int, default=3)
    argumentos.add_argument("--intervalo", type=int, help="pasos entre guardados de progreso")
    argumentos.add_argument("--semilla", type=int, default=config.SEED)
    argumentos.add_argument("--repaso", type=int, default=0, help="número de documentos anteriores para el control de retención")
    argumentos.add_argument("--reanudar", type=Path, help="subcarpeta de sesión creada dentro de --salida")
    argumentos.add_argument("--lecciones", type=Path, help="lecciones del protocolo colectivo verificadas")
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
    lecciones = []
    if opciones.lecciones:
        with opciones.lecciones.open(encoding="utf-8") as entrada:
            bruto = entrada.read(8193)
        if len(bruto) > 8192:
            argumentos.error("El archivo de lecciones supera 8 KiB.")
        lecciones = json.loads(bruto)
    informe = entrenar(opciones.origen, opciones.salida, opciones.pasos, variantes,
                       reanudar=opciones.reanudar, semilla=opciones.semilla,
                       intervalo=opciones.intervalo or min(8, opciones.pasos),
                       repeticion=opciones.repaso, lecciones=lecciones)
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
