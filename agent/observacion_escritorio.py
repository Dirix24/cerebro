"""Observación consentida de estados X11, sin captura de entrada ni de pantalla."""
from dataclasses import dataclass, field
import re
from threading import Event, RLock, Thread
from time import monotonic

from agent.control_ventanas import buscar
from core import ventanas_x11


_NOMBRE = r"[\w -]{1,48}"


@dataclass
class Observacion:
    nombre: str
    ventana: dict
    estado: tuple
    caduca: float
    pasos: list = field(default_factory=list)
    detener: Event = field(default_factory=Event)
    listo: bool = False
    motivo: str = ""
    revisado: bool = False


def acciones(antes, despues):
    oculto, maximizado, foco = antes
    ahora_oculto, ahora_max, ahora_foco = despues
    if ahora_oculto and not oculto:
        return ["minimiza"]
    if ahora_max != maximizado:
        return ["maximiza" if ahora_max else "restaura"]
    if ahora_foco and (not foco or oculto):
        return ["enfoca"]
    return []


class Observador:
    def __init__(self, escritorio, categoria):
        self.escritorio = escritorio
        self.categoria = categoria
        self.cerrojo = RLock()
        self.solicitudes = {}
        self.rutinas = {}

    def limpiar(self):
        with self.cerrojo:
            for rutina in self.rutinas.values():
                rutina.detener.set()
            self.solicitudes.clear()
            self.rutinas.clear()

    def _observar(self, rutina):
        agente = self.escritorio.nucleo.agente
        while not rutina.detener.wait(.4) and monotonic() < rutina.caduca:
            if not agente.tiene_permisos("READ", "WRITE"):
                rutina.motivo = "Se revocó un permiso."
                rutina.detener.set()
                break
            try:
                nuevo = ventanas_x11.estado_observable(rutina.ventana)
            except RuntimeError as exc:
                rutina.motivo = str(exc)
                rutina.detener.set()
                break
            with self.cerrojo:
                if rutina.detener.is_set():
                    break
                for accion in acciones(rutina.estado, nuevo):
                    rutina.pasos.append({"accion": accion, "objetivo": rutina.ventana["clase"]})
                rutina.estado = nuevo
                if len(rutina.pasos) >= 12:
                    break
        with self.cerrojo:
            rutina.listo = True

    def consultar(self, orden, cliente):
        solicitud = re.fullmatch(rf"observa (?:la ventana de (.+?)|esta ventana) como ({_NOMBRE})", orden)
        operacion = re.fullmatch(
            r"(?:autoriza observacion|deten la observacion|revisa la observacion|"
            r"quita el paso (\d{1,2}) de la observacion|interpreta la observacion|"
            r"aprueba (?:la )?(?:observacion|demostracion)|cancela la observacion)", orden)
        if not (solicitud or operacion):
            return None
        if orden == "cancela la observacion":
            with self.cerrojo:
                self.solicitudes.pop(cliente, None)
                rutina = self.rutinas.pop(cliente, None)
                if rutina:
                    rutina.detener.set()
            return "Observación cancelada y borrador descartado."
        self.escritorio._autorizar()
        self.escritorio._autorizar_escritura()
        if solicitud:
            ventanas = ventanas_x11.listar()
            candidatas = (buscar(solicitud[1], ventanas, lambda v: [v["titulo"], *v["clase"].split(".")])
                          if solicitud[1] else [ventanas_x11.activa(ventanas)])
            if len(candidatas) != 1 or not candidatas[0] or candidatas[0]["clase"] == "N/A":
                return "Indica el título de una única ventana abierta."
            with self.cerrojo:
                if cliente in self.rutinas:
                    return "Revisa, aprueba o cancela la observación anterior primero."
                self.solicitudes[cliente] = (monotonic() + 60, solicitud[2], candidatas[0])
                if len(self.solicitudes) > 32:
                    self.solicitudes.pop(next(iter(self.solicitudes)))
            return (f"Ventana elegida: «{candidatas[0]['titulo']}». Durante 90 s solo observaré su foco, "
                    "minimización y maximización. Responde «Autoriza observación» o «Cancela la observación».")
        if orden == "autoriza observacion":
            with self.cerrojo:
                datos = self.solicitudes.pop(cliente, None)
                if not datos or datos[0] < monotonic():
                    return "Selecciona una ventana antes de autorizar la observación."
                if any(not r.listo for r in self.rutinas.values()) or len(self.rutinas) >= 32:
                    return "Hay una observación en curso o demasiados borradores."
                _, nombre, ventana = datos
                estado = ventanas_x11.estado_observable(ventana)
                rutina = Observacion(nombre, ventana, estado, monotonic() + 90)
                self.rutinas[cliente] = rutina
                Thread(target=self._observar, args=(rutina,), daemon=True).start()
            return "Observación iniciada. Manipula la ventana elegida y di «Detén la observación»."
        with self.cerrojo:
            rutina = self.rutinas.get(cliente)
            if not rutina:
                return "No hay observación para este chat."
            if orden == "deten la observacion":
                rutina.detener.set()
            if not rutina.listo and not rutina.detener.is_set():
                return "Detén la observación antes de revisarla."
            if orden.startswith("aprueba"):
                if not rutina.revisado or not rutina.pasos:
                    return "Primero revisa un borrador con pasos."
                if rutina.motivo == "Se revocó un permiso.":
                    return "Cancela este borrador y autoriza una observación nueva."
                memoria = self.escritorio.nucleo.memoria
                memoria.cargar_memoria()
                clave = f"{self.categoria}:{rutina.nombre}"
                if clave in memoria.long_term_memory:
                    return "Ya existe un procedimiento con ese nombre. Cancela y elige otro nombre."
                memoria.guardar_largo_plazo(clave, list(rutina.pasos), categoria=self.categoria)
                self.rutinas.pop(cliente)
                return f"Guardé «{rutina.nombre}» con {len(rutina.pasos)} pasos aprobados."
            if operacion[1]:
                numero = int(operacion[1])
                if not 1 <= numero <= len(rutina.pasos):
                    return "Ese paso no existe."
                del rutina.pasos[numero - 1]
            rutina.revisado = True
            lista = "\n".join(f"{i}. {p['accion']}" for i, p in enumerate(rutina.pasos, 1))
            motivo = rutina.motivo
        if not lista:
            return "Todavía no hay cambios de ventana que pueda guardar." + (f" {motivo}" if motivo else "")
        resultado = "Borrador observado:\n" + lista + (f"\nObservación detenida: {motivo}" if motivo else "")
        if orden == "interpreta la observacion":
            profesor = self.escritorio.nucleo.profesor
            if profesor.configurado:
                try:
                    comentario = profesor.conversar("Resume la finalidad probable de estas acciones de ventana, "
                                                     "sin añadir pasos: " + lista)
                except RuntimeError as exc:
                    comentario = str(exc)
                resultado += "\nComentario de Qwen: " + comentario
        return resultado + "\nPuedes quitar un paso o responder «Aprueba la demostración»."
