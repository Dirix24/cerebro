"""Preparación, autorización y ejecución acotada de un entrenamiento candidato."""
from dataclasses import dataclass, field
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import mkdtemp
from threading import Event, RLock, Thread
from time import monotonic

from core import competencias
from core.recursos_portatil import memoria_disponible_mb, motivos_pausa


_RAIZ_CODIGO = Path(__file__).resolve().parent.parent
_INICIO_LIMITADO = (
    "import os, resource, runpy, sys; "
    "ram, cpu, archivo = map(int, sys.argv[1:4]); "
    "del sys.argv[1:4]; "
    "resource.setrlimit(resource.RLIMIT_AS, (ram, ram)); "
    "resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu)); "
    "resource.setrlimit(resource.RLIMIT_FSIZE, (archivo, archivo)); "
    "os.nice(5); "
    "runpy.run_module('entrenar_competencias', run_name='__main__')"
)


@dataclass(frozen=True)
class Presupuesto:
    pasos: int
    intervalo: int
    segundos: int
    ram_mib: int


def presupuesto(duracion, ram):
    pasos, intervalo, tiempo = {"corto": (8, 4, 120), "medio": (64, 8, 420),
                                 "largo": (256, 16, 1800)}[duracion]
    if duracion == "largo" and (ram or 0) < 4096:
        raise ValueError("Una sesión larga requiere 4 GiB de RAM disponible medible. Usa una sesión media.")
    if duracion == "medio" and (ram or 0) < 2048:
        raise ValueError("Una sesión media requiere 2 GiB de RAM disponible medible. Usa una sesión corta.")
    return Presupuesto(pasos, intervalo, tiempo, min(4096, max(1024, (ram or 2048) // 3)))


def debiles(historia):
    # Los informes de currículo y de arquitectura tienen su propio esquema.
    evaluacion = next((r["materias"] for r in historia if "materias" in r), {})
    return sorted(competencias.PRACTICA, key=lambda m: (
        evaluacion.get(m, {}).get("aciertos", 0) / max(1, evaluacion.get(m, {}).get("total", 0)),
        m,
    ))[:2]


@dataclass
class Ensayo:
    cliente: tuple
    materias: list
    presupuesto: Presupuesto
    duracion: str
    colectivo: bool = False
    carpeta: Path | None = None
    cancelado: Event = field(default_factory=Event)
    estado: str = "preparando ejercicios"
    detalle: str = ""
    programado: bool = False


@dataclass
class PracticaProgramada:
    minutos: int
    siguiente: float


class GestorAprendizaje:
    def __init__(self):
        self.cerrojo = RLock()
        self.pendientes = {}
        self.ensayo = None
        self.hilo = None
        self.programacion = None
        self.propuesta_programacion = None
        self.ultima_actividad = monotonic()

    def cancelar(self):
        with self.cerrojo:
            if self.ensayo is not None:
                self.ensayo.cancelado.set()
            return self.hilo

    def estado(self):
        with self.cerrojo:
            e = self.ensayo
            return {"estado": e.estado, "detalle": e.detalle, "materias": e.materias.copy(),
                    "sesion": e.carpeta.name if e.carpeta else None} if e else None

    def actividad(self):
        with self.cerrojo:
            self.ultima_actividad = monotonic()

    def _ocupado(self):
        return self.ensayo and self.ensayo.estado in {"preparando ejercicios", "entrenando y evaluando"}

    def _iniciar(self, nucleo, ensayo):
        self.ensayo = ensayo
        self.hilo = Thread(target=self._ejecutar, args=(nucleo, ensayo), daemon=True)
        self.hilo.start()

    def revisar_programacion(self, nucleo):
        ahora = monotonic()
        with self.cerrojo:
            plan = self.programacion
            if (not plan or ahora < plan.siguiente or ahora - self.ultima_actividad < 120
                    or self._ocupado() or nucleo.chat.modelo is None):
                return
            # Si los recursos están justos, reintentar más tarde sin bloquear el servicio.
            plan.siguiente = ahora + 60
            if nucleo.solo_lectura or not nucleo.agente.tiene_permisos("READ", "WRITE"):
                return
            if motivos_pausa(minimo_ram_mb=1024):
                return
            try:
                if os.getloadavg()[0] > max(.7, (os.cpu_count() or 1) / 2):
                    return
            except (AttributeError, OSError):
                pass
            capacidad = presupuesto("corto", memoria_disponible_mb())
            materias = debiles(competencias.historial(nucleo.raiz))
            plan.siguiente = ahora + 60 * plan.minutos
            self._iniciar(nucleo, Ensayo((None, "programada"), materias, capacidad, "corto",
                                        colectivo=True, programado=True))

    def _programar(self, orden, nucleo, cliente):
        solicitud = re.fullmatch(r"programa practica colectiva cada ([0-9]{1,4}) minutos", orden)
        if not solicitud and orden not in {"confirma practica programada", "pausa practica programada",
                                          "estado de la practica programada"}:
            return None
        nucleo.exigir_permisos("READ")
        ahora = monotonic()
        with self.cerrojo:
            if orden == "estado de la practica programada":
                plan = self.programacion
                return (f"Práctica programada cada {plan.minutos} min con comprobación de inactividad y recursos."
                        if plan else "La práctica programada está desactivada.")
            nucleo.exigir_permisos("WRITE")
            if orden == "pausa practica programada":
                self.programacion = self.propuesta_programacion = None
                if self._ocupado() and self.ensayo.programado:
                    self.ensayo.cancelado.set()
                return "Práctica programada pausada."
            if solicitud:
                minutos = int(solicitud[1])
                if not 15 <= minutos <= 1440:
                    return "Indica entre 15 y 1440 minutos."
                if nucleo.chat.modelo is None:
                    return "Carga el modelo alumno antes de programar la práctica."
                self.propuesta_programacion = (cliente, minutos, ahora + 180)
                return (f"Práctica corta cada {minutos} min mientras CEREBRO esté abierto y lleve dos minutos sin uso. "
                        "Incluye especialistas configurados con una muestra sintética sin red. Los pesos activos se conservan. "
                        "Di «Confirma práctica programada» o «Pausa práctica programada».")
            propuesta = self.propuesta_programacion
            if not propuesta or propuesta[0] != cliente or propuesta[2] < ahora:
                return "Primero programa una práctica en este chat."
            _, minutos, _ = propuesta
            self.propuesta_programacion = None
            self.programacion = PracticaProgramada(minutos, ahora + minutos * 60)
            return "Práctica programada autorizada para esta ejecución de CEREBRO."

    def consultar(self, orden, nucleo, cliente):
        cliente_sesion = (cliente, nucleo.conversaciones.activa())
        programacion = self._programar(orden, nucleo, cliente_sesion)
        if programacion is not None:
            return programacion
        comandos = {"prepara entrenamiento autonomo", "confirma entrenamiento autonomo",
                    "cancelar entrenamiento autonomo", "cancela entrenamiento autonomo",
                    "estado del entrenamiento autonomo"}
        preparar = re.fullmatch(r"prepara entrenamiento autonomo(?: (corto|medio|largo))?( colectivo)?", orden)
        retomar = re.fullmatch(r"reanuda entrenamiento autonomo (ensayo-[a-z0-9_]{8})", orden)
        if orden not in comandos and not preparar and not retomar:
            return None
        nucleo.exigir_permisos("READ")
        if orden == "estado del entrenamiento autonomo":
            datos = self.estado()
            return (f"{datos['estado']}. {datos['detalle']}" if datos else
                    "Todavía no se ha iniciado un entrenamiento autónomo en esta sesión.")
        nucleo.exigir_permisos("WRITE")
        cliente = cliente_sesion
        with self.cerrojo:
            if orden.startswith("cancel"):
                borrador = self.pendientes.pop(cliente, None)
                e = self.ensayo
                if e and e.cliente == cliente and e.estado in {"preparando ejercicios", "entrenando y evaluando"}:
                    e.cancelado.set()
                    return "Solicité detener el entrenamiento de este chat."
                return "Borrador cancelado." if borrador else "No hay un entrenamiento pendiente de este chat."
            if nucleo.chat.modelo is None:
                return "Carga el modelo alumno antes de preparar un entrenamiento."
            if preparar or retomar:
                materias = debiles(competencias.historial(nucleo.raiz))
                carpeta = None
                colectivo = bool(preparar and preparar[2])
                try:
                    if retomar:
                        raiz = nucleo.raiz / "learning" / "autonomo"
                        carpeta = raiz / retomar[1]
                        ficha = carpeta / "presupuesto.json"
                        if carpeta.is_symlink() or raiz.is_symlink() or raiz.parent.is_symlink() or ficha.is_symlink():
                            raise ValueError("La sesión debe ser local.")
                        if ficha.stat().st_size > 4096 or any(carpeta.glob("competencias-*/informe.json")):
                            raise ValueError("Esta sesión ya está terminada o no es reanudable.")
                        plan = json.loads(ficha.read_text(encoding="utf-8"))
                        duracion = plan["duracion"]
                        colectivo = plan["colectivo"] is True
                        materias = plan["materias"]
                        if not isinstance(materias, list) or not all(m in competencias.PRACTICA for m in materias):
                            raise ValueError("Materias de la sesión incompatibles.")
                    else:
                        duracion = preparar[1] or "corto"
                    capacidad = presupuesto(duracion, memoria_disponible_mb())
                except (OSError, ValueError, KeyError, TypeError) as error:
                    return f"No pude preparar el entrenamiento: {error}"
                self.pendientes[cliente] = (monotonic() + 180, materias, capacidad, duracion, colectivo, carpeta)
                if len(self.pendientes) > 32:
                    self.pendientes.pop(next(iter(self.pendientes)))
                ejemplos = "\n".join(f"• {materia}: {competencias.PRACTICA[materia][0]}" for materia in materias)
                colaboracion = (" Incluye CAZEL/DARAS configurados: muestra sintética, sin red ni archivos personales."
                                 if colectivo else "")
                return (f"Prioridades: {', '.join(materias)}. Ejercicios de partida:\n{ejemplos}\n"
                        f"Hasta {capacidad.pasos} pasos en una copia, guardado cada {capacidad.intervalo}, "
                        f"un hilo, {capacidad.ram_mib} MiB de memoria virtual y {capacidad.segundos} s por sesión."
                        + colaboracion + "\nResponde «Confirma entrenamiento autónomo» o «Cancela entrenamiento autónomo».")
            propuesta = self.pendientes.pop(cliente, None)
            if not propuesta or propuesta[0] < monotonic():
                return "Prepara primero un entrenamiento autónomo en este chat."
            if self._ocupado():
                return "Ya hay un entrenamiento autónomo en curso."
            motivos = motivos_pausa(minimo_ram_mb=1024)
            if motivos:
                return "Entrenamiento aplazado: " + ", ".join(motivos) + ". Prepara otro cuando se liberen recursos."
            _, materias, capacidad, duracion, colectivo, carpeta = propuesta
            ensayo = Ensayo(cliente, materias, capacidad, duracion, colectivo, carpeta)
            self._iniciar(nucleo, ensayo)
            return "Entrenamiento autorizado. Puedes consultar «Estado del entrenamiento autónomo»."

    def _actualizar(self, ensayo, estado, detalle=""):
        with self.cerrojo:
            ensayo.estado, ensayo.detalle = estado, detalle

    @staticmethod
    def _comprobar(nucleo, ensayo):
        if ensayo.cancelado.is_set():
            raise InterruptedError("Cancelado por el usuario.")
        nucleo.exigir_permisos("READ", "WRITE")

    def _ejecutar(self, nucleo, ensayo):
        proceso = None
        fallo = None
        try:
            self._comprobar(nucleo, ensayo)
            origen = nucleo.raiz / "checkpoints" / "best.npz"
            validacion = nucleo.raiz / "data" / "validacion.txt"
            capacidad = ensayo.presupuesto
            if not origen.is_file() or origen.is_symlink():
                raise ValueError("Se requiere un checkpoint local.")
            maximo_archivo = min(capacidad.ram_mib * 1024**2 // 8, max(32 * 1024**2, origen.stat().st_size * 8))
            if origen.stat().st_size * 2 > maximo_archivo:
                raise ValueError("El checkpoint requiere un presupuesto de memoria mayor.")
            if not validacion.is_file() or validacion.is_symlink() or validacion.stat().st_size > 256 * 1024:
                raise ValueError("Falta una validación local acotada.")
            raiz = nucleo.raiz / "learning" / "autonomo"
            if raiz.is_symlink() or raiz.parent.is_symlink():
                raise PermissionError("El directorio de ensayos no admite enlaces simbólicos.")
            raiz.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(raiz).free < max(128 * 1024**2, 3 * maximo_archivo):
                raise ValueError("No hay espacio reservado para otro candidato.")
            reanudar = []
            if ensayo.carpeta is None:
                variantes = {}
                for materia in ensayo.materias:
                    self._comprobar(nucleo, ensayo)
                    if nucleo.profesor.configurado:
                        try:
                            variante = nucleo.profesor.proponer_variante(materia)
                            competencias.ejercicio(materia, variante)
                        except (RuntimeError, ValueError, AttributeError):
                            continue
                        variantes[materia] = variante
                lecciones = []
                if ensayo.colectivo:
                    from core.lecciones_colectivas import recopilar
                    lecciones = recopilar(ensayo.cancelado)
                self._comprobar(nucleo, ensayo)
                carpeta = Path(mkdtemp(prefix="ensayo-", dir=raiz))
                (carpeta / "variantes.json").write_text(json.dumps(variantes), encoding="utf-8")
                (carpeta / "lecciones.json").write_text(json.dumps(lecciones), encoding="utf-8")
                (carpeta / "presupuesto.json").write_text(json.dumps({
                    "duracion": ensayo.duracion, "materias": ensayo.materias, "colectivo": ensayo.colectivo}), encoding="utf-8")
                with self.cerrojo:
                    ensayo.carpeta = carpeta
            else:
                carpeta = ensayo.carpeta
                variantes = json.loads((carpeta / "variantes.json").read_text(encoding="utf-8"))
                lecciones = json.loads((carpeta / "lecciones.json").read_text(encoding="utf-8"))
                sesiones = list(carpeta.glob("competencias-*/sesion.json"))
                if len(sesiones) > 1:
                    raise ValueError("Hay varias sesiones de entrenamiento para ese identificador.")
                if sesiones:
                    reanudar = ["--reanudar", str(sesiones[0].parent)]
            self._actualizar(ensayo, "entrenando y evaluando",
                             f"{carpeta.name} · {len(lecciones)} lecciones de especialistas verificadas.")
            limite = monotonic() + capacidad.segundos
            with (carpeta / "entrenador.log").open("a", encoding="utf-8") as log:
                proceso = subprocess.Popen(
                    [sys.executable, "-c", _INICIO_LIMITADO, str(capacidad.ram_mib * 1024**2), str(capacidad.segundos),
                     str(maximo_archivo), "--origen", str(origen), "--salida", str(carpeta),
                     "--pasos", str(capacidad.pasos), "--intervalo", str(capacidad.intervalo),
                     "--variantes", str(carpeta / "variantes.json"), "--lecciones", str(carpeta / "lecciones.json"),
                     *reanudar, "--ejecutar"],
                    cwd=_RAIZ_CODIGO, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    env={**os.environ, "CEREBRO_HOME": str(nucleo.raiz), "CEREBRO_SIN_INTERNET": "1",
                         "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
                proxima_revision = monotonic() + 5
                while proceso.poll() is None:
                    self._comprobar(nucleo, ensayo)
                    ahora = monotonic()
                    if ahora >= proxima_revision:
                        motivos = motivos_pausa(minimo_ram_mb=512)
                        if motivos:
                            raise InterruptedError("Entrenamiento detenido: " + ", ".join(motivos) + ".")
                        proxima_revision = ahora + 5
                    if ahora >= limite:
                        raise TimeoutError("El entrenamiento alcanzó el tiempo autorizado. Puedes retomar desde el progreso guardado.")
                    ensayo.cancelado.wait(.25)
            self._comprobar(nucleo, ensayo)
            if proceso.returncode:
                raise RuntimeError(f"El entrenador terminó con código {proceso.returncode}. Consulta {carpeta.name}/entrenador.log.")
            ruta, = carpeta.glob("competencias-*/informe.json")
            informe = json.loads(ruta.read_text(encoding="utf-8"))
            antes, despues = informe["antes"], informe["despues"]
            if antes["modelo_sha256"] != competencias.huella_modelo(nucleo.chat.modelo):
                raise ValueError("El checkpoint evaluado no coincide con el alumno de esta sesión.")
            elegible = informe["elegible_para_revision"]
            estado = "Candidato elegible para revisión manual" if elegible else "Candidato rechazado"
            registro = {**despues, "tipo": "candidato", "elegible_para_revision": elegible,
                        "entrenamiento_autonomo": ensayo.materias, "mejoras": informe["mejoras"],
                        "regresiones": informe["regresiones"], "referencias_qwen": sorted(variantes),
                        "sesion": carpeta.name, "pasos": informe["pasos"], "lecciones_colectivas": lecciones,
                        "bpb_antes": informe["validacion_bpb_antes"], "bpb_despues": informe["validacion_bpb_despues"]}
            competencias.guardar(nucleo.raiz, antes)
            competencias.guardar(nucleo.raiz, registro)
            self._actualizar(ensayo, "terminado", f"{carpeta.name} · {estado}. {len(lecciones)} lecciones verificadas. "
                            "Los pesos activos siguen intactos.\n" + competencias.resumen(registro))
        except (PermissionError, InterruptedError) as exc:
            fallo = ("cancelado", str(exc))
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            fallo = ("error", str(exc))
        finally:
            if proceso is not None and proceso.poll() is None:
                proceso.terminate()
                try:
                    proceso.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proceso.kill()
                    proceso.wait(timeout=3)
            if fallo:
                estado, detalle = fallo
                if ensayo.carpeta is not None:
                    detalle += " Sesión: " + ensayo.carpeta.name + "."
                self._actualizar(ensayo, estado, detalle)
