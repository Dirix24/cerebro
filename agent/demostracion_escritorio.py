"""Procedimientos enseñados mediante acciones verificadas por Cerebro."""
from collections import OrderedDict
from dataclasses import dataclass, field
import re
from time import monotonic

from agent.observacion_escritorio import Observador


CATEGORIA = "demostracion_escritorio"
ACCIONES = frozenset({"abrir", "enfoca", "maximiza", "minimiza", "restaura", "izquierda", "derecha", "casilla"})
_EJERCICIOS = {
    "casilla": ("Quieres cambiar una opción accesible y verificar su estado.", "activar casilla accesible"),
    "abrir": ("Quieres iniciar una aplicación instalada.", "abrir aplicación"),
    "enfoca": ("La ventana ya está abierta y quieres ponerla al frente.", "enfocar ventana"),
    "maximiza": ("Quieres ampliar una ventana para ocupar el área disponible.", "maximizar ventana"),
    "minimiza": ("Quieres ocultar una ventana manteniéndola abierta.", "minimizar ventana"),
    "restaura": ("Quieres devolver una ventana maximizada a su tamaño habitual.", "restaurar ventana"),
    "izquierda": ("Quieres llevar una ventana al lado izquierdo del monitor.", "colocar a la izquierda"),
    "derecha": ("Quieres llevar una ventana al lado derecho del monitor.", "colocar a la derecha"),
}
_MAX_PASOS = 12
_NOMBRE = r"[\w -]{1,48}"


@dataclass
class Demostracion:
    nombre: str
    caduca: float
    pasos: list = field(default_factory=list)


class Demostraciones:
    def __init__(self, escritorio):
        self.escritorio = escritorio
        self.activas = OrderedDict()
        self.observador = Observador(escritorio, CATEGORIA)

    def registrar(self, cliente, accion, objetivo):
        activa = self.activas.get(cliente)
        if (activa and activa.caduca >= monotonic() and accion in ACCIONES
                and len(activa.pasos) < _MAX_PASOS
                and self.escritorio.nucleo.agente.tiene_permisos("WRITE")):
            activa.pasos.append({"accion": accion, "objetivo": objetivo})

    def consultar(self, orden, cliente):
        observada = self.observador.consultar(orden, cliente)
        if observada is not None:
            return observada
        if orden.startswith("te voy a ensenar") or orden.startswith("quiero ensenarte"):
            return ("Para observar una ventana, di «Observa la ventana de APLICACIÓN como NOMBRE». "
                    "Te pediré permiso y solo observaré cambios de esa ventana. "
                    "También puedes usar «Empezar demostración NOMBRE» para enseñar con órdenes de chat.")
        inicio = re.fullmatch(rf"empezar demostracion ({_NOMBRE})", orden)
        repetir = re.fullmatch(rf"(?:repite la demostracion ({_NOMBRE})|repite lo que te ensene|ahora hazlo tu|haz lo que te ensene|hazlo tu)", orden)
        revisar = re.fullmatch(rf"(revisa la demostracion|genera ejercicios de la demostracion) ({_NOMBRE})", orden)
        if not (inicio or repetir or revisar or orden in {"guardar demostracion", "cancelar demostracion"}):
            return None
        if orden == "cancelar demostracion":
            self.activas.pop(cliente, None)
            return "Cancelé la demostración de este chat."
        self.escritorio._autorizar()
        memoria = self.escritorio.nucleo.memoria
        if inicio:
            self.escritorio._autorizar_escritura()
            activa = self.activas.get(cliente)
            if activa and activa.caduca >= monotonic():
                return "Ya hay una demostración activa. Guárdala o cancélala antes de empezar otra."
            nombre = inicio[1].strip()
            if not nombre:
                return "Indica un nombre para la demostración."
            self.activas[cliente] = Demostracion(nombre, monotonic() + 600)
            self.activas.move_to_end(cliente)
            if len(self.activas) > 64:
                self.activas.popitem(last=False)
            return ("Demostración iniciada durante 10 minutos. Puedo guardar hasta 12 aperturas y cambios de "
                    "ventana verificados que me pidas desde este chat. Escribe «Guardar demostración» al terminar.")
        memoria.cargar_memoria()
        if repetir or revisar:
            activa = self.activas.get(cliente)
            if repetir and activa and activa.caduca >= monotonic():
                return "Guarda o cancela la demostración activa antes de reproducir otra."
            nombre = repetir[1] if repetir else revisar[2]
            if nombre is None:
                nombres = [clave.partition(":")[2] for clave, dato in memoria.long_term_memory.items()
                           if isinstance(dato, dict) and dato.get("categoria") == CATEGORIA]
                if len(nombres) != 1:
                    return "Indica qué rutina quieres usar, con «Repite la demostración NOMBRE»."
                nombre = nombres[0]
            nombre = nombre.strip()
            entrada = memoria.long_term_memory.get(f"{CATEGORIA}:{nombre}")
            if not isinstance(entrada, dict) or entrada.get("categoria") != CATEGORIA:
                return "No encontré una demostración válida con ese nombre."
            pasos = memoria.recuperar_largo_plazo(f"{CATEGORIA}:{nombre}")
            if (not isinstance(pasos, list) or not 1 <= len(pasos) <= _MAX_PASOS
                    or any(not isinstance(p, dict) or not isinstance(p.get("accion"), str) or p["accion"] not in ACCIONES
                           or not isinstance(p.get("objetivo"), str) or not 0 < len(p["objetivo"]) <= 240 for p in pasos)):
                return "No encontré una demostración válida con ese nombre."
            if revisar:
                if revisar[1] == "revisa la demostracion":
                    return "\n".join(f"{i}. {p['accion']} · {p['objetivo']}"
                                     for i, p in enumerate(pasos, 1))
                ejercicios = []
                for i, accion in enumerate(dict.fromkeys(p["accion"] for p in pasos), 1):
                    contexto, referencia = _EJERCICIOS[accion]
                    ejercicios.append(f"{i}. {contexto} ¿Qué herramienta usarías? Referencia: {referencia}.")
                ejercicios.append("¿Qué permiso comprueba el agente antes de repetir una acción del procedimiento? "
                                  "Referencia: READ.")
                return "Ejercicios para revisión. Los objetivos originales se omiten.\n" + "\n".join(ejercicios)
            if any(p["accion"] == "casilla" for p in pasos):
                self.escritorio._autorizar_escritura()
                self.escritorio._guardar_pendiente(cliente, repetir_casillas=pasos, nombre_demostracion=nombre)
                return f"Rutina «{nombre}»: {len(pasos)} pasos. Responde «Confirma la repetición» o «Cancelar»."
            return self.escritorio.repetir_demostracion(pasos, cliente)
        self.escritorio._autorizar_escritura()
        activa = self.activas.get(cliente)
        if not activa or activa.caduca < monotonic() or not activa.pasos:
            return "No tengo pasos de escritorio verificados para guardar."
        memoria.guardar_largo_plazo(f"{CATEGORIA}:{activa.nombre}", list(activa.pasos), categoria=CATEGORIA)
        self.activas.pop(cliente, None)
        cantidad = len(activa.pasos)
        detalle = "1 paso verificado" if cantidad == 1 else f"{cantidad} pasos verificados"
        return f"Guardé «{activa.nombre}» con {detalle}."
