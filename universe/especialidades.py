"""Coordina especialistas locales v1 y conserva su procedencia para Universe."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from threading import Event, Lock
from time import monotonic

from core.actividad_neuronal import publicar
from core.profesor_local import ejercicio_dependencias, evaluar_dependencia

VERSION = 1
ESTADOS = {"ok", "parcial", "error", "no_disponible"}
REGIONES = {"DARAS", "CAZEL", "PROFESOR"}


def _resultado(region, estado, error=None, **data):
    return {"version": VERSION, "especialista": region, "estado": estado,
            **({"error": error} if error else {}), **data}


class Coordinacion:
    def __init__(self):
        self._lock = Lock()
        self._activo = None

    @contextmanager
    def turno(self):
        with self._lock:
            cancelacion = None
            if self._activo is None:
                cancelacion = self._activo = Event()
        if cancelacion is None:
            yield None
            return
        try:
            yield cancelacion
        finally:
            with self._lock:
                self._activo = None

    def cancelar(self):
        with self._lock:
            if self._activo is None:
                return False
            self._activo.set()
            return True


def _ejecutar(comando, raiz, entrada, entorno, timeout, cancelacion):
    limite = monotonic() + timeout
    with subprocess.Popen(comando, cwd=raiz, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, env=entorno) as proceso:
        while True:
            restante = limite - monotonic()
            if restante <= 0 or cancelacion.is_set():
                proceso.kill()
                proceso.communicate()
                if cancelacion.is_set():
                    raise InterruptedError("Coordinación cancelada.")
                raise subprocess.TimeoutExpired(comando, timeout)
            try:
                salida, _ = proceso.communicate(input=entrada, timeout=min(restante, 0.25))
                return proceso.returncode, salida
            except subprocess.TimeoutExpired:
                entrada = None


def _consulta(region, accion, objetivo, *, red=False, cancelacion=None):
    carpeta = os.environ.get("CEREBRO_" + region + "_RAIZ")
    if not carpeta:
        return _resultado(region, "no_disponible", "Falta configurar el repositorio local.")
    modulo = "especialista" if region == "DARAS" else "cazel.especialista"
    raiz = Path(carpeta).expanduser().resolve()
    punto = raiz.joinpath(*modulo.split(".")).with_suffix(".py")
    if not punto.is_file():
        return _resultado(region, "no_disponible", "El adaptador v1 no existe en la carpeta configurada.")
    comando = [sys.executable, "-E", "-s", "-m", modulo]
    if region == "CAZEL":
        proyecto = os.environ.get("CEREBRO_CAZEL_PROYECTO")
        if not proyecto:
            return _resultado(region, "no_disponible", "Falta seleccionar el proyecto CAZEL.")
        comando += ["--proyecto", str(Path(proyecto).expanduser().resolve())]
        if accion == "probar" and os.environ.get("CEREBRO_CAZEL_PRUEBAS") == "1":
            comando.append("--permitir-pruebas")
        if accion == "proponer" and os.environ.get("CEREBRO_CAZEL_PROPUESTAS") == "1":
            comando.append("--permitir-propuestas")
        if datos := os.environ.get("CEREBRO_CAZEL_DATOS"):
            comando += ["--datos", str(Path(datos).expanduser().resolve())]
    entrada = json.dumps({"version": VERSION, "accion": accion, "objetivo": objetivo, "red": red},
                         ensure_ascii=True).encode("ascii")
    claves = ("PATH", "SYSTEMROOT", "TMPDIR", "TEMP", "LANG")
    if region == "DARAS" and red:
        claves += ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR")
    entorno = {clave: os.environ[clave] for clave in claves if clave in os.environ}
    try:
        codigo, salida = _ejecutar(comando, raiz, entrada, entorno, 72 if accion == "proponer" else 23,
                                   cancelacion or Event())
        if codigo or len(salida) > 96_000:
            raise ValueError("Respuesta no disponible.")
        respuesta = json.loads(salida)
        if (not isinstance(respuesta, dict) or respuesta.get("especialista") != region
                or type(respuesta.get("version")) is not int or respuesta["version"] != VERSION
                or respuesta.get("estado") not in ESTADOS):
            raise ValueError("Contrato incompatible.")
        sintetizar([respuesta])
        return respuesta
    except subprocess.TimeoutExpired:
        return _resultado(region, "error", "Tiempo de espera agotado.")
    except InterruptedError as error:
        return _resultado(region, "parcial", str(error))
    except (OSError, ValueError, TypeError, KeyError):
        return _resultado(region, "error", "El adaptador no devolvió un resultado válido.")


class Experiencias:
    def __init__(self, ruta):
        self.ruta = Path(ruta).absolute()

    @contextmanager
    def _db(self, escritura=False):
        if self.ruta.is_symlink():
            raise PermissionError("La memoria de coordinación requiere un archivo local.")
        destino = self.ruta if escritura else self.ruta.as_uri() + "?mode=ro"
        with closing(sqlite3.connect(destino, uri=not escritura)) as db, db:
            if escritura:
                db.execute("""CREATE TABLE IF NOT EXISTS experiencias (
                    id TEXT PRIMARY KEY, objetivo TEXT, resultados TEXT, fecha TEXT)""")
                db.execute("""CREATE TABLE IF NOT EXISTS ejercicios (
                    conversacion TEXT PRIMARY KEY, experiencia TEXT NOT NULL)""")
            yield db

    def guardar(self, objetivo, resultados, *, conversacion=None):
        datos = json.dumps(resultados, ensure_ascii=True, sort_keys=True)
        ident = sha256(json.dumps([objetivo, datos]).encode("utf-8")).hexdigest()
        with self._db(escritura=True) as db:
            db.execute("INSERT OR IGNORE INTO experiencias VALUES (?, ?, ?, ?)",
                       (ident, objetivo, datos, datetime.now(timezone.utc).isoformat()))
            if conversacion is not None:
                db.execute("INSERT OR REPLACE INTO ejercicios VALUES (?, ?)", (conversacion, ident))
        return ident

    def recientes(self, region=None, limite=20, tema=None):
        if not self.ruta.is_file():
            return []
        with self._db() as db:
            if region is None:
                filas = db.execute(
                    """SELECT id,objetivo,resultados,fecha FROM experiencias
                       WHERE (? IS NULL OR instr(lower(objetivo), lower(?)) > 0)
                       ORDER BY rowid DESC LIMIT ?""", (tema, tema, limite),
                ).fetchall()
            else:
                filas = db.execute(
                    """SELECT x.id,x.objetivo,x.resultados,x.fecha FROM experiencias x
                       WHERE EXISTS (SELECT 1 FROM json_each(x.resultados)
                           WHERE json_extract(value, '$.especialista') = ?)
                       ORDER BY x.rowid DESC LIMIT ?""", (region, limite),
                ).fetchall()
        return [{"id": i, "objetivo": o, "resultados": [
                    r for r in json.loads(b) if region is None or r["especialista"] == region],
                 "fecha": f} for i, o, b, f in filas]

    def ejercicio_activo(self, conversacion):
        if not self.ruta.is_file():
            return None
        with self._db() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='ejercicios'").fetchone():
                return None
            row = db.execute("SELECT experiencia FROM ejercicios WHERE conversacion=?",
                             (conversacion,)).fetchone()
        return row[0] if row else None

    def ejercicio(self, ident):
        if not self.ruta.is_file():
            return None
        with self._db() as db:
            row = db.execute("SELECT resultados FROM experiencias WHERE id=?", (ident,)).fetchone()
        if row is None:
            return None
        return next((r["ejercicio"] for r in json.loads(row[0]) if "ejercicio" in r), None)

    def nodos(self):
        salida = []
        for exp in self.recientes(limite=20):
            vinculo = "experiencia:" + exp["id"]
            salida.append({"id": vinculo, "tipo": "relaciones", "titulo": exp["objetivo"],
                           "detalle": sintetizar(exp["resultados"])[:1200], "grupo": "Coordinación",
                           "origen": "CEREBRO", "fecha": exp["fecha"]})
            for indice, resultado in enumerate(exp["resultados"]):
                region = resultado["especialista"]
                salida.append({"id": f"{vinculo}:{indice}", "tipo": "conocimiento",
                               "titulo": region + " · " + resultado["estado"],
                               "detalle": sintetizar([resultado])[:600], "grupo": region,
                               "vinculos": [vinculo], "origen": "Resultado de especialista",
                               "fecha": exp["fecha"]})
        return salida


def sintetizar(resultados):
    partes = []
    for resultado in resultados:
        region = resultado["especialista"]
        detalles = []
        if resultado.get("error"):
            detalles.append(resultado["error"])
        if plan := resultado.get("plan"):
            detalles.append("Plan: " + " → ".join(p["titulo"] for p in plan))
        if simulacion := resultado.get("simulacion"):
            detalles.append(f"Simulación, p50 {simulacion['p50_horas']} h y p90 {simulacion['p90_horas']} h. "
                            + simulacion["supuestos"])
        for evidencia in resultado.get("evidencia", []):
            if evidencia["tipo"] == "fuente":
                detalles.append(f"Fuente: {evidencia['titulo']} · {evidencia['url']}")
            elif evidencia["tipo"] == "analisis":
                errores = evidencia["errores"]
                detalles.append(f"{evidencia['path']}: {evidencia['language']}, "
                                f"{len(errores)} errores sintácticos en el análisis.")
            elif evidencia["tipo"] == "propuesta":
                detalles.append(f"Propuesta pendiente para {evidencia['path']}.")
            elif evidencia["tipo"] in {"prueba", "prueba_registrada"}:
                nombre = "Prueba registrada" if evidencia["tipo"] == "prueba_registrada" else "Prueba ejecutada"
                detalles.append(f"{nombre}: {evidencia['state']} (código {evidencia['returncode']}).")
        detalles.extend(resultado.get("avisos", []))
        if resultado.get("sesion"):
            detalles.append("Sesión de revisión en CAZEL Studio: " + resultado["sesion"] + ".")
        if ejercicio := resultado.get("ejercicio"):
            detalles.append(ejercicio["pregunta"] + " Responde con el identificador de la tarea.")
        if evaluacion := resultado.get("evaluacion"):
            detalles.append(evaluacion["detalle"])
        partes.append(f"{region} ({resultado['estado']}): " + (" ".join(detalles) or "Sin datos adicionales."))
    return "\n".join(partes)


def _trabajos(intencion, internet):
    daras = bool(re.search(r"\b(?:investiga|planifica|organiza|simula)\b", intencion))
    cazel = bool(re.search(r"\b(?:desarrolla|programa|revisa (?:el )?codigo|analiza (?:el )?proyecto)\b",
                          intencion))
    pide_daras = bool(daras and re.search(r"\bdaras\b", intencion))
    pide_cazel = bool((cazel or re.search(r"\b(?:ejecuta|corre) (?:las )?pruebas\b", intencion))
                      and re.search(r"\bcazel\b", intencion))
    profesor = bool(re.search(r"\b(?:profesor|comprueba lo aprendido|evalua lo aprendido)\b", intencion))
    if not (daras and cazel or pide_daras or pide_cazel):
        return [], False
    cazel = cazel or pide_cazel
    investigar = bool(re.search(r"\binvestiga\b", intencion))
    red = bool(internet and investigar and re.search(r"\b(?:en internet|en la web)\b", intencion))
    probar = bool(re.search(r"\b(?:ejecuta|corre) (?:las )?pruebas\b", intencion))
    trabajos = []
    if daras:
        trabajos.append(("DARAS", "investigar" if investigar else "planificar", red))
    if cazel:
        quiere_propuesta = re.search(r"\b(?:desarrolla|programa)\b", intencion)
        accion = "probar" if probar else "analizar"
        if not probar and quiere_propuesta and os.environ.get("CEREBRO_CAZEL_PROPUESTAS") == "1":
            accion = "proponer"
        trabajos.append(("CAZEL", accion, False))
    return trabajos, profesor


def subobjetivo(region, accion, objetivo):
    if region == "DARAS" and accion == "investigar":
        match = re.search(r"\binvestiga(?: en internet| en la web)?[: ]+([^,.!?]+)", objetivo, re.I)
        if match:
            return match[1].strip()
    if region == "CAZEL" and accion == "proponer":
        preciso = re.search(r"(?:^|[.!?]\s+)(prop[oó]n [^!?]+)", objetivo, re.I)
        if preciso:
            return preciso[1].strip()
    return objetivo


def consultar(nucleo, pregunta, intencion):
    memoria = Experiencias(nucleo.estudio / "experiencias-v1.sqlite3")
    if intencion in {"cancela la coordinacion", "cancela los especialistas"}:
        nucleo.exigir_permisos("READ", "WRITE")
        return {"respuesta": ("Cancelación solicitada." if nucleo.coordinacion.cancelar()
                              else "No hay una coordinación activa.")}
    pruebas = re.fullmatch(r"(?:muestrame|consulta) las pruebas de cazel(?: de la sesion)? ([0-9a-f]{32})",
                           intencion)
    if pruebas:
        nucleo.exigir_permisos("READ", "WRITE")
        with nucleo.coordinacion.turno() as cancelacion:
            if cancelacion is None:
                return {"respuesta": "Ya hay una coordinación activa."}
            resultado = _consulta("CAZEL", "evidencia", pruebas[1], cancelacion=cancelacion)
        ident = memoria.guardar("Pruebas registradas en CAZEL · " + pruebas[1], [resultado])
        return {"respuesta": sintetizar([resultado]), "experiencia": ident, "especialistas": [resultado]}
    if re.fullmatch(r"(?:muestrame|ensename|quiero ver) (?:el plan de daras|el ultimo resultado|que aprendiste)",
                    intencion):
        nucleo.exigir_permisos("READ")
        region = "DARAS" if "plan" in intencion else None
        recientes = memoria.recientes(region, limite=1)
        if recientes:
            return {"respuesta": sintetizar(recientes[0]["resultados"]), "experiencias": recientes,
                    **({"vista": "universe"} if "aprendiste" in intencion else {})}
        return {"respuesta": "Todavía no hay una experiencia guardada para esta consulta."}
    recuperar = re.fullmatch(
        r"(?:muestrame|ensename|quiero ver) (?:que aprendiste de|las simulaciones de|las conexiones entre) "
        r"(cazel|daras|profesor)(?: y cerebro)?", intencion)
    if recuperar:
        nucleo.exigir_permisos("READ")
        resultados = memoria.recientes(recuperar[1].upper(), limite=5)
        if "simulaciones" in intencion:
            resultados = [exp for exp in resultados if any("simulacion" in r for r in exp["resultados"])]
        return {"respuesta": "\n".join(sintetizar(e["resultados"]) for e in resultados)
                             or "Todavía no hay experiencias guardadas para esa consulta.",
                "experiencias": resultados}
    resuelto = re.fullmatch(r"(?:muestrame|ensename) como resolviste (?:el problema de(?:l)? )?(.{2,120})", intencion)
    if resuelto:
        nucleo.exigir_permisos("READ")
        resultados = memoria.recientes(limite=5, tema=resuelto[1])
        return {"respuesta": "\n".join(sintetizar(e["resultados"]) for e in resultados)
                             or "No encontré una experiencia que coincida con ese tema.",
                "experiencias": resultados}
    evaluar = re.fullmatch(r"(?:evalua mi respuesta|mi respuesta es)(?: ([a-f0-9]{64}))?[: ]+(\S{1,60})",
                          intencion)
    if evaluar:
        nucleo.exigir_permisos("READ", "WRITE")
        activa = evaluar[1] or memoria.ejercicio_activo(str(nucleo.conversaciones.activa()))
        ejercicio = memoria.ejercicio(activa) if activa else None
        if ejercicio is None:
            return {"respuesta": "No encontré un ejercicio con ese identificador."}
        nota = evaluar_dependencia(ejercicio, evaluar[2])
        resultado = _resultado("PROFESOR", "ok", evaluacion={**nota, "experiencia": activa})
        ident = memoria.guardar("Evaluación de " + activa, [resultado])
        return {"respuesta": sintetizar([resultado]), "experiencia": ident, "especialistas": [resultado]}
    trabajos, profesor = _trabajos(intencion, nucleo.internet)
    if not trabajos:
        return None
    nucleo.exigir_permisos("READ", "WRITE")
    objetivo = pregunta[:600]
    with nucleo.coordinacion.turno() as cancelacion:
        if cancelacion is None:
            return {"respuesta": "Ya hay una coordinación activa. Puedes pedir que se cancele."}
        publicar("investigando", "Coordinación de especialistas")
        with ThreadPoolExecutor(max_workers=len(trabajos)) as pool:
            futuros = [pool.submit(_consulta, region, accion, subobjetivo(region, accion, objetivo),
                                   red=red, cancelacion=cancelacion)
                       for region, accion, red in trabajos]
            resultados = [futuro.result() for futuro in futuros]
    if profesor:
        plan = next((r["plan"] for r in resultados if r.get("plan")), [])
        ejercicio = ejercicio_dependencias(plan)
        resultados.append(_resultado("PROFESOR", "ok", ejercicio=ejercicio) if ejercicio else
                          _resultado("PROFESOR", "no_disponible", "Hace falta un plan para preparar el ejercicio."))
    hay_ejercicio = any(r.get("ejercicio") for r in resultados)
    conversacion = str(nucleo.conversaciones.activa()) if hay_ejercicio else None
    ident = memoria.guardar(objetivo, resultados, conversacion=conversacion)
    publicar("consolidado", "Experiencia de especialistas guardada")
    respuesta = sintetizar(resultados)
    if hay_ejercicio:
        respuesta += "\nPuedes contestar «Mi respuesta es IDENTIFICADOR»."
    if re.search(r"\b(?:desarrolla|programa)\b", intencion) and not any(r.get("sesion") for r in resultados):
        respuesta += "\nPara desarrollar o editar el programa, continúa en CAZEL y revisa sus propuestas."
    return {"respuesta": respuesta, "experiencia": ident, "especialistas": resultados}
