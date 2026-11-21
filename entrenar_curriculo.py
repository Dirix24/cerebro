"""Entrena y evalúa un currículo por etapas en una copia del alumno."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import random
from tempfile import mkdtemp
from time import perf_counter

from core import competencias, curriculo
from core.checkpoint import cargar_checkpoint
from core.data import cargar_datos
from trainer_engine import ConfigEntrenamiento, TrainerEngine, precision_de_respuestas


def _total(materias):
    return sum(x["aciertos"] for x in materias.values()), sum(x["total"] for x in materias.values())


def experimentar(origen, destino, semillas, pasos, lr, replay=120):
    origen = Path(origen).resolve(strict=True)
    destino = Path(destino).resolve()
    if origen.is_relative_to(destino):
        raise ValueError("El directorio de resultados debe estar separado de los pesos de origen.")
    if not 1 <= pasos <= 240 or not .0001 <= lr <= .002 or not 20 <= replay <= 500:
        raise ValueError("Usa 1–240 pasos por etapa, LR de 0.0001 a 0.002 y 20–500 documentos de retención.")
    firma = sha256(origen.read_bytes()).hexdigest()
    entrenamiento, reservados = curriculo.banco(semillas)
    modelo = cargar_checkpoint(str(origen), con_optimizador=False)["modelo"]
    todos = [c for etapa in curriculo.ETAPAS for c in entrenamiento[etapa] + reservados[etapa]]
    contexto = curriculo.comprobar_contexto(modelo, todos)
    if contexto["fuera_ventana"]:
        raise ValueError(f"{contexto['fuera_ventana']} ejercicios desbordan el contexto del alumno.")
    docs, validacion, _ = cargar_datos()
    verificacion = curriculo.verificacion_adicional()
    preguntas_reservadas = {curriculo._clave(c.pregunta)
                           for banco in (reservados, verificacion) for casos in banco.values() for c in casos}
    docs = [doc for doc in docs if all(
        curriculo._clave(linea.removeprefix("usuario: ")) not in preguntas_reservadas
        for linea in doc.splitlines() if linea.startswith("usuario: "))]
    retencion = random.Random(35).sample(docs, min(replay, len(docs)))
    vistos = [c for etapa in curriculo.ETAPAS for c in entrenamiento[etapa][::24]]
    destino.mkdir(parents=True, exist_ok=True)
    salida = Path(mkdtemp(prefix="curriculo-", dir=destino))

    def medir():
        return {"origen": "alumno_neuronal_sin_asistencia",
                "vistas": curriculo.medir(modelo, vistos),
                "reservadas": {e: curriculo.medir(modelo, reservados[e]) for e in curriculo.ETAPAS},
                "banco_anterior": competencias.evaluar(modelo)["materias"],
                "retencion": precision_de_respuestas(modelo, validacion)}

    def imprimir(etiqueta, medidas):
        print(etiqueta, "reservadas",
              {e: _total(v) for e, v in medidas["reservadas"].items()},
              "vistas", _total(medidas["vistas"]), "retención", medidas["retencion"]["exactas"], flush=True)

    inicio = perf_counter()
    antes = medir()
    imprimir("Base", antes)
    acumulados = []
    fases = []
    motor = None
    for etapa in curriculo.ETAPAS:
        actuales = entrenamiento[etapa]
        recuperados = random.Random(36).sample(acumulados, min(85, len(acumulados)))
        practica = [c.documento for c in actuales + recuperados] + retencion
        ce = ConfigEntrenamiento(batch_size=2, lr=lr, acumulacion_gradientes=1,
                                eval_cada=max(20, pasos), total_pasos=pasos * len(curriculo.ETAPAS))
        motor = TrainerEngine(modelo, practica, validacion, ce,
                              opt_state=motor.optim.state_dict() if motor else None,
                              rng_state=motor.estado_rng() if motor else None)
        if not fases:
            perdida_antes = motor.evaluar()["bpb"]
        motor.entrenar(pasos)
        etapa_metrica = curriculo.medir(modelo, reservados[etapa])
        fases.append({"etapa": etapa, "ejercicios": len(actuales),
                      "aciertos_reservados": _total(etapa_metrica),
                      "tokens_objetivo": motor.stream_train.n_objetivos()})
        acumulados.extend(actuales)

    despues = medir()
    imprimir("Candidato", despues)
    perdida_despues = motor.evaluar()["bpb"]
    candidato = salida / "candidato.npz"
    motor.guardar_ultimo(str(candidato))
    if sha256(origen.read_bytes()).hexdigest() != firma:
        raise RuntimeError("El checkpoint de origen cambió durante la prueba.")
    mejoras, regresiones = [], []
    for etapa in curriculo.ETAPAS:
        for materia, dato in antes["reservadas"][etapa].items():
            delta = despues["reservadas"][etapa][materia]["aciertos"] - dato["aciertos"]
            if delta:
                (mejoras if delta > 0 else regresiones).append([etapa, materia, delta])
    if any(despues["banco_anterior"][m]["aciertos"] < dato["aciertos"]
           for m, dato in antes["banco_anterior"].items()):
        regresiones.append(["banco anterior", "competencias", -1])
    elegible = (bool(mejoras) and not regresiones
                and despues["retencion"]["exactas"] >= antes["retencion"]["exactas"]
                and math.isfinite(perdida_despues) and perdida_despues <= perdida_antes)
    modelo_base = cargar_checkpoint(str(origen), con_optimizador=False)["modelo"]
    adicional = {
        "antes": {e: curriculo.medir(modelo_base, casos) for e, casos in verificacion.items()},
        "despues": {e: curriculo.medir(modelo, casos) for e, casos in verificacion.items()},
    }
    informe = {"tipo": "curriculo", "banco": 2, "antes": antes, "despues": despues, "fases": fases,
               "verificacion_adicional": adicional, "contexto": contexto, "origen_sha256": firma, "candidato": str(candidato), "lr": lr,
               "pasos_por_etapa": pasos, "segundos": round(perf_counter() - inicio, 2),
               "semillas_profesor": semillas, "documentos_repaso": len(retencion),
               "mejoras": mejoras, "regresiones": regresiones, "validacion_bpb_antes": perdida_antes,
               "validacion_bpb_despues": perdida_despues, "elegible_para_revision": elegible,
               "huella_entrenamiento": curriculo.huella(acumulados),
               "huella_reservados": curriculo.huella([c for e in curriculo.ETAPAS for c in reservados[e]])}
    (salida / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return informe


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--origen", default="checkpoints/best.npz")
    cli.add_argument("--salida", required=True)
    cli.add_argument("--semillas", required=True, type=Path)
    cli.add_argument("--pasos", default=80, type=int)
    cli.add_argument("--lr", default=.0006, type=float)
    cli.add_argument("--replay", default=120, type=int)
    cli.add_argument("--registrar", type=Path, help="hogar aislado cuyo registro mostrará la comparación")
    cli.add_argument("--ejecutar", action="store_true")
    args = cli.parse_args()
    if not args.ejecutar:
        cli.error("Confirma el ensayo con --ejecutar.")
    with args.semillas.open(encoding="utf-8") as archivo:
        contenido = archivo.read(4097)
    if len(contenido) > 4096:
        cli.error("El archivo de semillas supera 4 KiB.")
    informe = experimentar(args.origen, args.salida, json.loads(contenido), args.pasos, args.lr, args.replay)
    if args.registrar:
        competencias.guardar(args.registrar, informe)
    print({k: informe[k] for k in ("candidato", "mejoras", "regresiones", "validacion_bpb_antes",
                                   "validacion_bpb_despues", "segundos", "elegible_para_revision")}, flush=True)


if __name__ == "__main__":
    main()
