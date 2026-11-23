"""Compara ventanas, vocabularios y datos en CPU sin guardar pesos."""
import json
from time import process_time

from core.checkpoint import cargar_checkpoint
from core.data import cargar_documentos, cargar_generalizacion, cargar_test, cargar_validacion
from core.respuestas_con_fuentes import normalizar
from core.tokenizer import TokenizadorBPE
from trainer_engine import ConfigEntrenamiento, TrainerEngine, evaluar_modelo_en_docs, precision_de_respuestas


def diagnostico(modelo, documentos):
    filas = [d.split("\ncerebro:", 1)[0] + "\ncerebro:" for d in documentos if "\ncerebro:" in d]
    longitudes = [len(modelo.tokenizer.codificar(p)) + 1 for p in filas]
    nota = precision_de_respuestas(modelo, documentos)
    return {**nota, "bpb": evaluar_modelo_en_docs(modelo, documentos)["bpb"],
            "prompts_fuera_de_ventana": sum(n > modelo.cfg.block_size for n in longitudes),
            "prompts_max_tokens": max(longitudes, default=0)}


def main():
    reservados = {"generalizacion": cargar_generalizacion(), "test": cargar_test()}
    validacion = cargar_validacion()

    def pregunta(doc):
        return normalizar(doc.partition("\ncerebro:")[0])

    exclusiones = {pregunta(d) for docs in (*reservados.values(), validacion) for d in docs}
    corpus = list(dict.fromkeys(d for d in cargar_documentos()
                               if d.startswith("usuario:") and pregunta(d) not in exclusiones))
    # Reparte candidatos a lo largo del corpus y mantiene el mismo control para cada variante.
    muestra = corpus[::max(1, len(corpus) // 96)][:96]
    origen = cargar_checkpoint("checkpoints/best.npz", con_optimizador=False)["modelo"]
    informe = {"checkpoint": {nombre: diagnostico(origen, docs) for nombre, docs in reservados.items()},
               "experimentos": []}
    for nombre, ventana, vocabulario, datos in (
        ("control", 96, 384, muestra), ("ventana", 144, 384, muestra),
        ("bytes", 96, 260, muestra), ("menos_datos", 96, 384, muestra[::2]),
    ):
        inicio = process_time()
        ce = ConfigEntrenamiento(batch_size=2, lr=.001, seed=29, total_pasos=24,
                                 eval_cada=24, paciencia_early_stop=0, acumulacion_gradientes=1)
        tokenizer = TokenizadorBPE(vocabulario).entrenar(datos)
        motor = TrainerEngine.desde_cero(datos, validacion, perfil="diminuto", ce=ce,
                                         tokenizador=tokenizer, cambios_modelo={"block_size": ventana})
        antes = {grupo: diagnostico(motor.modelo, docs) for grupo, docs in reservados.items()}
        motor.entrenar(24)
        despues = {grupo: diagnostico(motor.modelo, docs) for grupo, docs in reservados.items()}
        informe["experimentos"].append({"nombre": nombre, "ventana": ventana, "vocabulario": len(tokenizer),
                                        "documentos": len(datos), "parametros": motor.modelo.n_parametros(),
                                        "segundos_cpu": process_time() - inicio,
                                        "antes": antes, "despues": despues})
    print(json.dumps(informe, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
