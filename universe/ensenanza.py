"""Trabajo supervisado compartido entre las interfaces locales."""
import re
from threading import Lock
from time import monotonic

from core.alumno_supervisado import cargar_activo, entrenar, responder, responder_etiqueta, verificar


class Ensenanza:
    def __init__(self):
        self.cerrojo = Lock()
        self.estado = "sin entrenamiento"
        self.autorizacion = None
        self.en_curso = False
        self.cancelado = False
        self.lecciones = {}

    def cancelar(self):
        with self.cerrojo:
            self.cancelado = True

    def leccion(self, nucleo, orden, clave):
        from core.ejemplos_aprobados import aprobar
        from core.lecciones_profesor import MATERIAS, preparar

        solicitud = re.fullmatch(r"(?:profesor[, ]+)?prepara (?:una )?leccion de (.+)", orden)
        if orden != "aprueba leccion del profesor" and not solicitud:
            return None
        nucleo.exigir_permisos("READ", "WRITE")
        if orden == "aprueba leccion del profesor":
            with self.cerrojo:
                pendiente = self.lecciones.get(clave)
                if pendiente is None or pendiente[0] < monotonic():
                    self.lecciones.pop(clave, None)
                    return {"respuesta": "Pide al Profesor una lección primero en este chat."}
                leccion = pendiente[1]
                destino = nucleo.raiz / "data" / "ejemplos_aprobados.jsonl"
                if destino.is_symlink() or destino.parent.is_symlink():
                    raise PermissionError("El banco de entrenamiento debe permanecer en los datos locales.")
                aprobar(destino, leccion["pregunta"], leccion["respuesta"],
                        procedencia={k: v for k, v in leccion.items() if k not in {"pregunta", "respuesta"}})
                del self.lecciones[clave]
            return {"respuesta": "Lección verificada guardada en el banco de entrenamiento. Los pesos siguen pendientes de entrenamiento y evaluación.",
                    "leccion": leccion}
        materia = MATERIAS.get(solicitud[1])
        if not materia:
            return {"respuesta": "Materias disponibles: " + ", ".join(MATERIAS.values()) + "."}
        with self.cerrojo:
            self.lecciones.pop(clave, None)
        if not nucleo.profesor.configurado:
            return {"respuesta": "Configura un modelo local Ollama o llama.cpp como Profesor."}
        try:
            leccion = preparar(nucleo.profesor, materia)
        except (RuntimeError, ValueError) as error:
            return {"respuesta": f"No pude verificar la lección: {error}"}
        with self.cerrojo:
            if len(self.lecciones) >= 32:
                self.lecciones.pop(next(iter(self.lecciones)))
            self.lecciones[clave] = (monotonic() + 300, leccion)
        return {"respuesta": f"{leccion['pregunta']}\nRespuesta comprobada: {leccion['respuesta']}. "
                "Para incorporarla al banco, escribe «Aprueba lección del Profesor».", "leccion": leccion}

    def consultar(self, nucleo, orden, cliente):
        leccion = self.leccion(nucleo, orden, cliente)
        if leccion is not None:
            return leccion
        if orden not in {"estado del alumno", "entrenar alumno", "confirma entrenar alumno",
                         "cancela entrenar alumno"}:
            return None
        nucleo.exigir_permisos("READ")
        with self.cerrojo:
            if orden == "estado del alumno":
                _, activo = cargar_activo(nucleo.raiz_alumno)
                _, ultimo = cargar_activo(nucleo.raiz_alumno, "ultimo")
                resumen = self.estado
                if ultimo:
                    evaluacion = ultimo["despues"]
                    resumen = resumen.rstrip(".") + f". Último candidato: {evaluacion['aciertos']}/{evaluacion['total']}."
                    resumen += " Promovido." if ultimo["promovido"] else " Rechazado."
                return {"respuesta": resumen, "activo": activo, "ultimo": ultimo}
            nucleo.exigir_permisos("WRITE")
            if orden == "cancela entrenar alumno":
                if self.en_curso and self.estado != "publicando resultados":
                    self.cancelado = True
                    return {"respuesta": "Cancelaré antes del siguiente paso. Qwen puede terminar su consulta actual."}
                if not self.en_curso:
                    self.autorizacion = None
                return {"respuesta": "No hay un entrenamiento que se pueda cancelar ahora."}
            if self.en_curso:
                return {"respuesta": "Ya hay un entrenamiento en curso."}
            if not nucleo.profesor.configurado:
                return {"respuesta": "Configura el profesor Qwen local para entrenar al alumno."}
            if orden == "entrenar alumno":
                self.autorizacion = (cliente, monotonic() + 120)
                return {"respuesta": "Se entrenará un candidato aislado de hora y fecha. Responde «Confirma entrenar alumno»."}
            if not self.autorizacion or self.autorizacion[0] != cliente or self.autorizacion[1] < monotonic():
                return {"respuesta": "Pide «Entrenar alumno» antes de confirmar desde este chat."}
            self.autorizacion = None
            self.en_curso = True
            self.cancelado = False
            self.estado = "en cola"
            nucleo.ejecutor.submit(self._entrenar, nucleo)
            return {"respuesta": "Entrenamiento en cola. Consulta «Estado del alumno» o di «Cancela entrenar alumno»."}

    def _entrenar(self, nucleo):
        def avanzar(fase):
            with self.cerrojo:
                if self.cancelado:
                    raise InterruptedError("Entrenamiento cancelado.")
                nucleo.exigir_permisos("READ", "WRITE")
                self.estado = fase

        try:
            avanzar("preparando datos")
            informe = entrenar(nucleo.profesor, nucleo.raiz_alumno, avanzar=avanzar)
            estado = "entrenamiento completado" if informe["promovido"] else "candidato rechazado por evaluación"
        except (OSError, ValueError, RuntimeError) as exc:
            estado = str(exc)
        finally:
            with self.cerrojo:
                self.estado = locals().get("estado", "fallo interno de entrenamiento")
                self.en_curso = False

    def inferir(self, nucleo, pregunta):
        if len(pregunta) > 150 or not nucleo.agente.tiene_permisos("READ"):
            return None
        pesos, informe = cargar_activo(nucleo.raiz_alumno)
        resultado = responder(pesos, pregunta)
        if resultado is None:
            if verificar(pregunta, variantes=False) != "abstener":
                return None
            respaldo = responder_etiqueta(verificar(pregunta))
            if respaldo is None:
                return None
            respuesta, competencia = respaldo
            return {"respuesta": respuesta, "origen": "regla_hora_fecha", "competencia": competencia}
        respuesta, competencia = resultado
        return {"respuesta": respuesta, "origen": "alumno_supervisado",
                "competencia": competencia, "checkpoint": informe["id"]}
