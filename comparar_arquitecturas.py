"""Comparación reproducible sin modificar ni promover los pesos activos."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import resource
from tempfile import mkdtemp
from time import perf_counter, process_time

from core import comparacion_neuronal as prueba, curriculo
from core.checkpoint import cargar_checkpoint, guardar_checkpoint
from core.data import cargar_datos, cargar_test
from core.tokenizer import crear_tokenizador
from trainer_engine import (ConfigEntrenamiento, OptimizedTransformerLLM, TrainerEngine,
                            config_modelo_desde_perfil, precision_de_respuestas)


def experimental(perfil, semilla, destino, semillas, pasos_base, pasos, estrategia):
    if not 1 <= pasos <= 300 or not 1 <= pasos_base <= 300:
        raise ValueError("Cada fase admite de 1 a 300 pasos.")
    origen = Path("checkpoints/best.npz").resolve(strict=True)
    firma = sha256(origen.read_bytes()).hexdigest()
    anteriores, val, _ = cargar_datos()
    entrenamiento, reserva = curriculo.banco(semillas)
    largos_train = prueba.dialogos_largos(False)
    largos_test = prueba.dialogos_largos(True)
    nuevo_banco = prueba.banco_nuevo()
    casos_train = [c for casos in entrenamiento.values() for c in casos
                   if c.materia in {"programación", "herramientas"}]
    casos_train += largos_train
    reserva_anterior = list(dict.fromkeys(c for casos in reserva.values() for c in casos))
    prueba.verificar_particiones(casos_train, reserva_anterior, nuevo_banco, largos_test)
    preguntas_evaluacion = {curriculo._clave(c.pregunta) for c in nuevo_banco + reserva_anterior + largos_test}
    anteriores = [doc for doc in anteriores
                  if all(curriculo._clave(l.partition(":")[2].strip()) not in preguntas_evaluacion
                         for l in doc.splitlines() if l.startswith("usuario:"))]
    nuevas = [c.documento for c in casos_train]
    especiales = {c.documento for c in largos_train}
    if perfil == "activo":
        modelo = cargar_checkpoint(str(origen), con_optimizador=False)["modelo"]
    else:
        tokenizer = crear_tokenizador("bpe", 768)
        tokenizer.entrenar(anteriores + nuevas)
        cfg = config_modelo_desde_perfil(perfil, vocab_size=len(tokenizer))
        modelo = OptimizedTransformerLLM(cfg, tokenizer=tokenizer, seed=semilla)
    cpu_inicio = process_time()

    def fase(documentos, parejas, lr, dialogos):
        ce = ConfigEntrenamiento(batch_size=2, lr=lr, seed=semilla, acumulacion_gradientes=1,
                                eval_cada=len(parejas))
        motor = TrainerEngine(modelo, documentos, val, ce)
        lotes = prueba.Lotes(parejas, modelo.tokenizer, modelo.cfg.block_size, dialogos)
        motor.cargador = lotes
        inicio = perf_counter()
        motor.entrenar(len(parejas))
        huella = sha256(json.dumps(parejas, ensure_ascii=False).encode()).hexdigest()
        return motor, {"pasos": len(parejas), "segundos": perf_counter() - inicio,
                       "tokens_objetivo": lotes.objetivos, "huella_objetivos": lotes.mascara.hexdigest(),
                       "huella_parejas": huella}

    if perfil != "activo":
        parejas_base = prueba.planificar(anteriores, anteriores, pasos_base, semilla, "solo_nuevos")
        _, base = fase(anteriores, parejas_base, .001, set())
    else:
        base = None

    def medir():
        return {"validacion": precision_de_respuestas(modelo, val),
                "perdida_bpb": TrainerEngine(modelo, anteriores[:10], val).evaluar()["bpb"],
                "final_anterior": precision_de_respuestas(modelo, cargar_test() or []),
                "nuevo_banco": prueba.medir(modelo, nuevo_banco),
                "curriculo_reservado": prueba.medir(modelo, reserva_anterior),
                "dialogo_largo": prueba.medir(modelo, largos_test),
                "dialogo_largo_112": prueba.medir(modelo, largos_test, 112)}

    antes = medir()
    parejas = prueba.planificar(anteriores, nuevas, pasos, semilla + 100, estrategia)
    motor, ajuste = fase(anteriores + nuevas, parejas, .0006 if perfil != "activo" else .0004, especiales)
    despues = medir()
    destino = Path(destino).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    salida = Path(mkdtemp(prefix=f"{perfil}-{semilla}-{estrategia}-", dir=destino))
    checkpoint = salida / "candidato.npz"
    guardar_checkpoint(str(checkpoint), modelo, meta_extra={"semilla": semilla, "paso": pasos,
                                                           "huella_parejas": ajuste["huella_parejas"]})
    if sha256(origen.read_bytes()).hexdigest() != firma:
        raise RuntimeError("El modelo activo cambió.")
    retenido = (despues["validacion"]["exactas"] >= antes["validacion"]["exactas"]
                and despues["perdida_bpb"] <= antes["perdida_bpb"]
                and despues["final_anterior"]["exactas"] >= antes["final_anterior"]["exactas"]
                and all(fila["exitos"] >= antes["nuevo_banco"]["materias"][m]["exitos"]
                        for m, fila in despues["nuevo_banco"]["materias"].items()))
    # Los perfiles desde cero son controles de arquitectura, no sustitutos del alumno activo.
    def total_nuevo(resultado):
        return sum(f["exitos"] for f in resultado["nuevo_banco"]["materias"].values())

    informe = {"perfil": perfil, "semilla": semilla, "estrategia": estrategia,
               "parametros": modelo.n_parametros(), "contexto": modelo.cfg.block_size,
               "vocabulario": len(modelo.tokenizer), "fase_base": base, "ajuste": ajuste,
               "antes": antes, "despues": despues, "rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
               "cpu_s": process_time() - cpu_inicio, "candidato": str(checkpoint),
               "elegible_para_revision": perfil == "activo" and retenido and total_nuevo(despues) > total_nuevo(antes)}
    (salida / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2))
    print(f"Informe: {salida / 'informe.json'}", flush=True)
    print(perfil, semilla, estrategia, "bpb", antes["perdida_bpb"], despues["perdida_bpb"],
          "RSS", informe["rss_mib"], "CPU", informe["cpu_s"], "éxitos nuevos", total_nuevo(despues), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--perfil", choices=["pequeno", "v2", "activo"], required=True)
    parser.add_argument("--semilla", type=int, default=17)
    parser.add_argument("--semillas", type=Path, required=True)
    parser.add_argument("--salida", required=True)
    parser.add_argument("--pasos-base", type=int, default=100)
    parser.add_argument("--pasos", type=int, default=140)
    parser.add_argument("--estrategia", choices=["mixta", "solo_nuevos"], default="mixta")
    parser.add_argument("--ejecutar", action="store_true")
    args = parser.parse_args()
    if not args.ejecutar:
        parser.error("Confirma el entrenamiento con --ejecutar.")
    with args.semillas.open(encoding="utf-8") as archivo:
        bruto = archivo.read(4097)
    if len(bruto) > 4096:
        parser.error("El archivo de semillas supera 4 KiB.")
    experimental(args.perfil, args.semilla, args.salida, json.loads(bruto),
                 args.pasos_base, args.pasos, args.estrategia)


if __name__ == "__main__":
    main()
