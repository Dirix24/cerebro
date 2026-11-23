"""Observación consentida de estados X11, sin captura de entrada ni de pantalla."""
from dataclasses import dataclass, field
import json
import re
from threading import Event, RLock, Thread
from time import monotonic

from agent.control_ventanas import buscar
from core import controles_accesibles, ventanas_x11


_NOMBRE = r"[\w -]{1,48}"


@dataclass
class Observacion:
    nombre: str
    ventana: dict
    estado: tuple
    caduca: float
    controles: dict | None = None
    pasos: list = field(default_factory=list)
    detener: Event = field(default_factory=Event)
    listo: bool = False
    motivo: str = ""
    revisado: bool = False
    indicador: object = None


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
            if rutina.indicador is not None and rutina.indicador.poll() is not None:
                if rutina.indicador.returncode:
                    rutina.motivo = "El indicador visible no pudo mantenerse abierto."
                rutina.detener.set()
                break
            if not agente.tiene_permisos("READ", "WRITE"):
                rutina.motivo = "Se revocó un permiso."
                rutina.detener.set()
                break
            try:
                nuevo = ventanas_x11.estado_observable(rutina.ventana)
                controles = (controles_accesibles.estado(rutina.ventana)
                             if rutina.controles is not None and nuevo[2] else None)
            except RuntimeError as exc:
                rutina.motivo = str(exc)
                rutina.detener.set()
                break
            with self.cerrojo:
                if rutina.detener.is_set():
                    break
                for accion in acciones(rutina.estado, nuevo):
                    rutina.pasos.append({"accion": accion, "objetivo": rutina.ventana["clase"]})
                if controles is not None:
                    cambios = [clave for clave in sorted(controles.keys() & rutina.controles.keys())
                               if controles[clave] != rutina.controles[clave]] if rutina.estado[2] else []
                    if len(cambios) > 1:
                        rutina.motivo = "Varias casillas cambiaron entre dos lecturas; el orden es ambiguo."
                        rutina.detener.set()
                        break
                    for clave in cambios:
                        selector = [rutina.ventana["clase"], clave, rutina.controles[clave], controles[clave]]
                        rutina.pasos.append({"accion": "casilla", "objetivo": json.dumps(selector)})
                    rutina.controles = controles
                rutina.estado = nuevo
                rutina.pasos = rutina.pasos[:12]
                if len(rutina.pasos) >= 12:
                    break
        if rutina.indicador is not None:
            if rutina.indicador.poll() is None:
                rutina.indicador.terminate()
            rutina.indicador.wait()
        with self.cerrojo:
            rutina.listo = True

    def consultar(self, orden, cliente):
        alias = {"ya termine": "deten la observacion", "deja de observar": "deten la observacion",
                 "apruebalo": "aprueba la demostracion"}
        if orden == "para" and cliente in self.rutinas:
            orden = "deten la observacion"
        orden = alias.get(orden, orden)
        edicion = re.fullmatch(rf"guardalo como ({_NOMBRE})|mueve el paso ([0-9]{{1,2}}) al ([0-9]{{1,2}})|quita el ultimo paso", orden)
        if edicion:
            orden = "revisa la observacion"
        semantica = orden.startswith("observa controles de ")
        texto = "observa la ventana de " + orden.removeprefix("observa controles de ") if semantica else orden
        solicitud = re.fullmatch(rf"observa (?:la ventana de (.+?)|esta ventana) como ({_NOMBRE})", texto)
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
                self.solicitudes[cliente] = (monotonic() + 60, solicitud[2], candidatas[0], semantica)
                if len(self.solicitudes) > 32:
                    self.solicitudes.pop(next(iter(self.solicitudes)))
            if semantica:
                return (f"Ventana elegida: «{candidatas[0]['titulo']}». Durante 90 s observaré cambios de "
                        "casillas accesibles y estados de ventana. Responde «Autoriza observación».")
            return (f"Ventana elegida: «{candidatas[0]['titulo']}». Durante 90 s solo observaré su foco, "
                    "minimización y maximización. Responde «Autoriza observación» o «Cancela la observación».")
        if orden == "autoriza observacion":
            with self.cerrojo:
                datos = self.solicitudes.pop(cliente, None)
                if not datos or datos[0] < monotonic():
                    return "Selecciona una ventana antes de autorizar la observación."
                if any(not r.listo for r in self.rutinas.values()) or len(self.rutinas) >= 32:
                    return "Hay una observación en curso o demasiados borradores."
                _, nombre, ventana, semantica = datos
                estado = ventanas_x11.estado_observable(ventana)
                controles = controles_accesibles.estado(ventana) if semantica else None
                if semantica and not controles:
                    return "La ventana no ofrece casillas accesibles utilizables."
                rutina = Observacion(nombre, ventana, estado, monotonic() + 90, controles)
                rutina.indicador = controles_accesibles.indicador()
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
            if edicion:
                if edicion[1]:
                    rutina.nombre = edicion[1].strip()
                elif edicion[2]:
                    a, b = int(edicion[2]), int(edicion[3])
                    if not 1 <= a <= len(rutina.pasos) or not 1 <= b <= len(rutina.pasos):
                        return "Uno de los números de paso no existe."
                    rutina.pasos.insert(b - 1, rutina.pasos.pop(a - 1))
                elif rutina.pasos:
                    rutina.pasos.pop()
            if operacion[1]:
                numero = int(operacion[1])
                if not 1 <= numero <= len(rutina.pasos):
                    return "Ese paso no existe."
                del rutina.pasos[numero - 1]
            rutina.revisado = True
            lineas = []
            for i, paso in enumerate(rutina.pasos, 1):
                descripcion = paso["accion"]
                if descripcion == "casilla":
                    _, clave, antes, despues = controles_accesibles.selector(paso["objetivo"])
                    descripcion += f" {clave[:8]} · {'marcada' if antes else 'desmarcada'} → "
                    descripcion += "marcada" if despues else "desmarcada"
                lineas.append(f"{i}. {descripcion}")
            lista = "\n".join(lineas)
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
