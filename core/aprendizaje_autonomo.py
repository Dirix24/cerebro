"""Preparación, autorización y ejecución acotada de un entrenamiento candidato."""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import mkdtemp
from threading import Event, RLock, Thread
from time import monotonic

from core import competencias


_RAIZ_CODIGO = Path(__file__).resolve().parent.parent
_PASOS = 8
_LIMITE_MIB = 256
_INICIO_LIMITADO = (
    "import resource, runpy; "
    "resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824)); "
    "resource.setrlimit(resource.RLIMIT_CPU, (80, 80)); "
    "resource.setrlimit(resource.RLIMIT_FSIZE, (33554432, 33554432)); "
    "runpy.run_module('entrenar_competencias', run_name='__main__')"
)


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
    cancelado: Event = field(default_factory=Event)
    estado: str = "preparando ejercicios"
    detalle: str = ""


class GestorAprendizaje:
    def __init__(self):
        self.cerrojo = RLock()
        self.pendientes = {}
        self.ensayo = None

    def estado(self):
        with self.cerrojo:
            e = self.ensayo
            return {"estado": e.estado, "detalle": e.detalle, "materias": e.materias.copy()} if e else None

    def consultar(self, orden, nucleo, cliente):
        comandos = {"prepara entrenamiento autonomo", "confirma entrenamiento autonomo",
                    "cancelar entrenamiento autonomo", "cancela entrenamiento autonomo",
                    "estado del entrenamiento autonomo"}
        if orden not in comandos:
            return None
        nucleo.exigir_permisos("READ")
        if orden == "estado del entrenamiento autonomo":
            datos = self.estado()
            return (f"{datos['estado']}. {datos['detalle']}" if datos else
                    "Todavía no se ha iniciado un entrenamiento autónomo en esta sesión.")
        nucleo.exigir_permisos("WRITE")
        cliente = (cliente, nucleo.conversaciones.activa())
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
            if orden.startswith("prepara"):
                materias = debiles(competencias.historial(nucleo.raiz))
                self.pendientes[cliente] = (monotonic() + 180, materias)
                if len(self.pendientes) > 32:
                    self.pendientes.pop(next(iter(self.pendientes)))
                ejemplos = "\n".join(f"• {materia}: {competencias.PRACTICA[materia][0]}" for materia in materias)
                return (f"Prioridades: {', '.join(materias)}. Ejercicios de partida:\n{ejemplos}\n"
                        "Ocho pasos en una copia y evaluación reservada. Un hilo de cálculo, "
                        "límite de 1 GiB de espacio de direcciones y 120 s de ejecución. "
                        "Responde «Confirma entrenamiento autónomo» o «Cancela entrenamiento autónomo».")
            propuesta = self.pendientes.pop(cliente, None)
            if not propuesta or propuesta[0] < monotonic():
                return "Prepara primero un entrenamiento autónomo en este chat."
            if self.ensayo and self.ensayo.estado in {"preparando ejercicios", "entrenando y evaluando"}:
                return "Ya hay un entrenamiento autónomo en curso."
            ensayo = Ensayo(cliente, propuesta[1])
            self.ensayo = ensayo
            Thread(target=self._ejecutar, args=(nucleo, ensayo), daemon=True).start()
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
            if not origen.is_file() or origen.is_symlink() or origen.stat().st_size > 32 * 1024**2:
                raise ValueError("Se requiere un checkpoint local de hasta 32 MiB.")
            if not validacion.is_file() or validacion.is_symlink() or validacion.stat().st_size > 256 * 1024:
                raise ValueError("Falta una validación local acotada.")
            raiz = nucleo.raiz / "learning" / "autonomo"
            if raiz.is_symlink() or raiz.parent.is_symlink():
                raise PermissionError("El directorio de ensayos no admite enlaces simbólicos.")
            raiz.mkdir(parents=True, exist_ok=True)
            uso = sum(p.stat().st_size for p in raiz.rglob("*") if not p.is_symlink() and p.is_file())
            if uso > (_LIMITE_MIB - 64) * 1024**2 or shutil.disk_usage(raiz).free < 128 * 1024**2:
                raise ValueError("No hay espacio reservado para otro candidato.")
            variantes = {}
            for materia in ensayo.materias:
                self._comprobar(nucleo, ensayo)
                if nucleo.profesor.configurado:
                    try:
                        variante = nucleo.profesor.proponer_variante(materia)
                        competencias.ejercicio(materia, variante)
                    except (RuntimeError, ValueError):
                        continue
                    variantes[materia] = variante
            self._comprobar(nucleo, ensayo)
            carpeta = Path(mkdtemp(prefix="ensayo-", dir=raiz))
            entrada = carpeta / "variantes.json"
            entrada.write_text(json.dumps(variantes, ensure_ascii=False), encoding="utf-8")
            self._actualizar(ensayo, "entrenando y evaluando",
                             f"{len(variantes)} propuestas de Qwen verificadas; las demás referencias son locales.")
            limite = monotonic() + 120
            with (carpeta / "entrenador.log").open("w", encoding="utf-8") as log:
                proceso = subprocess.Popen(
                    [sys.executable, "-c", _INICIO_LIMITADO, "--origen", str(origen), "--salida", str(carpeta),
                     "--pasos", str(_PASOS), "--variantes", str(entrada), "--ejecutar"],
                    cwd=_RAIZ_CODIGO, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    env={**os.environ, "CEREBRO_HOME": str(nucleo.raiz), "CEREBRO_SIN_INTERNET": "1",
                         "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
                while proceso.poll() is None:
                    self._comprobar(nucleo, ensayo)
                    if monotonic() >= limite:
                        raise TimeoutError("El entrenamiento excedió los 120 segundos.")
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
                        "bpb_antes": informe["validacion_bpb_antes"], "bpb_despues": informe["validacion_bpb_despues"]}
            competencias.guardar(nucleo.raiz, antes)
            competencias.guardar(nucleo.raiz, registro)
            self._actualizar(ensayo, "terminado", f"{estado}. {len(variantes)} variantes de Qwen. "
                            "Los pesos activos siguen intactos.\n" + competencias.resumen(registro))
        except (PermissionError, InterruptedError) as exc:
            fallo = ("cancelado", str(exc))
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
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
                self._actualizar(ensayo, *fallo)
