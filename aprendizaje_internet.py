"""Aprendizaje local diario desde artículos públicos de Wikipedia.

Opt-in. Conserva pesos/optimizador NumPy mediante --resume; sin modelos
preentrenados ni servicios de IA. Mantén el proceso abierto para el modo diario.
"""
import argparse
from datetime import date, datetime, timedelta
import json
import shutil
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl
import socket

RAIZ = Path(__file__).resolve().parent
CARPETA = RAIZ / "data" / "aprendizaje_internet"
ESTADO = CARPETA / "estado.json"
CORPUS = CARPETA / "corpus_diario.txt"
FUENTES = CARPETA / "fuentes.jsonl"
API = "https://es.wikipedia.org/w/api.php"
PROCESO_ENTRENAMIENTO = None


def detener_entrenamiento(signum, frame):
    """No dejar entrenadores huérfanos al cerrar el modo todo."""
    global PROCESO_ENTRENAMIENTO
    hijo = PROCESO_ENTRENAMIENTO
    if hijo is not None and hijo.poll() is None:
        if os.name == "posix":
            os.killpg(hijo.pid, signal.SIGTERM)
        else:
            hijo.terminate()
        try:
            hijo.wait(timeout=8)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(hijo.pid, signal.SIGKILL)
            else:
                hijo.kill()
            hijo.wait()
    raise SystemExit(128 + signum)




def explicar_error_red(exc):
    """Diagnóstico sin desactivar TLS ni atribuir el fallo al modelo."""
    if isinstance(exc, HTTPError):
        if exc.code == 403:
            return "HTTP 403: el servidor rechaza la solicitud; comprueba el acceso a la API desde tu red."
        if exc.code == 429:
            return "HTTP 429: demasiadas solicitudes; espera antes de volver a intentarlo."
        return f"HTTP {exc.code}: respuesta de error del servidor remoto."
    causa = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(causa, ssl.SSLError):
        return f"Error de certificado o TLS: {causa}"
    if isinstance(causa, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
        return "La conexión fue interrumpida por el servidor o la red (TLS/conexión reiniciada)."
    if isinstance(causa, (TimeoutError, socket.timeout)):
        return "Tiempo de espera agotado; comprueba conexión, DNS o cortafuegos."
    if isinstance(causa, socket.gaierror):
        return "No se pudo resolver el dominio (DNS)."
    return f"Error de conexión: {causa}"


def comprobar_red():
    """Comprueba la API realmente utilizada por el aprendizaje, sin recopilar datos."""
    req = Request(API + "?" + urlencode({"action": "query", "meta": "siteinfo", "format": "json"}),
                  headers={"User-Agent": "CerebroLocal/0.2 (uso personal; contacto: GitHub Dirix24/cerebro)",
                           "Accept": "application/json"})
    try:
        with urlopen(req, timeout=12) as respuesta:
            datos = json.load(respuesta)
        if "query" in datos:
            print("API de Wikipedia accesible. El aprendizaje puede intentar descargar artículos.")
            return 0
        print("La API respondió, pero no devolvió el formato esperado.")
        return 1
    except (HTTPError, URLError, OSError, ValueError) as exc:
        print("API de Wikipedia no disponible: " + explicar_error_red(exc), file=sys.stderr)
        print("El chat, la memoria y la inferencia local siguen funcionando sin Internet.", file=sys.stderr)
        return 1


def obtener_paginas(cantidad):
    params = {"action": "query", "generator": "random", "grnnamespace": "0",
              "grnlimit": str(cantidad), "prop": "extracts|info",
              "explaintext": "1", "exintro": "1", "inprop": "url",
              "format": "json", "formatversion": "2"}
    req = Request(API + "?" + urlencode(params),
                  headers={"User-Agent": "CerebroLocal/0.2 (uso personal; contacto: GitHub Dirix24/cerebro)"})
    with urlopen(req, timeout=25) as respuesta:
        datos = json.load(respuesta)
    salida = []
    for pagina in datos.get("query", {}).get("pages", []):
        texto = " ".join(pagina.get("extract", "").split())
        if (250 <= len(texto) <= 10000 and
                pagina.get("fullurl", "").startswith("https://es.wikipedia.org/") and
                isinstance(pagina.get("pageid"), int)):
            salida.append({"id": pagina["pageid"], "titulo": pagina["title"],
                           "url": pagina["fullurl"], "texto": texto})
    return salida


def documento(pagina):
    # El motor original solo calcula pérdida sobre líneas 'cerebro:'.
    # Transformar artículos a pares evita un entrenamiento sin objetivos.
    titulo = " ".join(pagina["titulo"].replace("\n", " ").split())
    texto = pagina["texto"].replace("\n", " ").strip()
    return f"usuario: ¿Qué es {titulo}?\ncerebro: {texto}\n\n"


def ciclo(paginas, pasos, entrenar, max_bytes, perfil, estado_ckpt):
    CARPETA.mkdir(parents=True, exist_ok=True)
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    hoy = date.today().isoformat()
    if estado.get("ultimo_dia") == hoy:
        print("Hoy ya se recopiló información; no se repite.")
        if entrenar and estado.get("entrenamiento_pendiente"):
            completado = entrenar_pendiente(pasos, perfil, estado_ckpt)
            if completado is False:
                return
            estado_actual = json.loads(ESTADO.read_text(encoding="utf-8"))
            estado_actual["entrenamiento_pendiente"] = False
            ESTADO.write_text(json.dumps(estado_actual, ensure_ascii=False), encoding="utf-8")
        return
    vistos = set(estado.get("vistos", []))
    nuevos = [p for p in obtener_paginas(paginas) if p["id"] not in vistos]
    if not nuevos:
        print("No se encontraron artículos nuevos adecuados.")
        return
    bloque = "".join(documento(p) for p in nuevos)
    anterior = CORPUS.stat().st_size if CORPUS.exists() else 0
    if anterior + len(bloque.encode("utf-8")) > max_bytes:
        print("Límite de almacenamiento alcanzado; no se recopila más.")
        return
    with CORPUS.open("a", encoding="utf-8") as f:
        f.write(bloque)
    with FUENTES.open("a", encoding="utf-8") as f:
        for p in nuevos:
            f.write(json.dumps({k: p[k] for k in ("id", "titulo", "url")},
                               ensure_ascii=False) + "\n")
    vistos.update(p["id"] for p in nuevos)
    # Guardar el día antes del entrenamiento evita duplicar textos si falla.
    ESTADO.write_text(json.dumps({"ultimo_dia": hoy, "vistos": sorted(vistos), "entrenamiento_pendiente": True},
                                 ensure_ascii=False), encoding="utf-8")
    from core.conocimiento import guardar as guardar_conocimiento
    alertas = 0
    for pagina in nuevos:
        pregunta = "¿Qué es " + " ".join(pagina["titulo"].split()) + "?"
        alertas += len(guardar_conocimiento(pregunta, pagina["texto"], pagina["url"]))
    print(f"Guardados {len(nuevos)} artículos y sus fuentes; alertas de contradicción: {alertas}.", flush=True)
    # Actualizar el índice también cuando el chat ya está abierto.
    try:
        from core.local_search import indexar
        print(f"Índice de búsqueda actualizado: {indexar()} documentos.", flush=True)
    except (OSError, ValueError, ImportError) as exc:
        print(f"Aviso: no se pudo actualizar el índice: {exc}", file=sys.stderr)
    if entrenar:
        completado = entrenar_pendiente(pasos, perfil, estado_ckpt)
        if completado is False:
            return
        estado_actual = json.loads(ESTADO.read_text(encoding="utf-8"))
        estado_actual["entrenamiento_pendiente"] = False
        ESTADO.write_text(json.dumps(estado_actual, ensure_ascii=False), encoding="utf-8")


def entrenar_pendiente(pasos, perfil, estado_ckpt):
    """Entrena con respaldo y validación fija; revierte si empeora."""
    import config
    from core.seguridad_aprendizaje import respaldar, restaurar, evaluar_fijo
    from core.puerta_checkpoint import aceptar_checkpoint
    from core.recursos_portatil import motivos_pausa
    motivos = motivos_pausa()
    if motivos:
        print("Entrenamiento aplazado: " + ", ".join(motivos), flush=True)
        return False
    from core.evolucion_adaptativa import leer_historial, pasos_adaptativos, registrar
    historial_ruta = CARPETA / "evolucion.json"
    pasos_efectivos = pasos_adaptativos(pasos, leer_historial(historial_ruta))
    print(f"Evolución adaptativa: {pasos_efectivos} pasos (base: {pasos}).", flush=True)
    if not CORPUS.exists() or not CORPUS.stat().st_size:
        print("No hay textos para entrenar.")
        return
    rutas = [Path(config.CKPT_ULTIMO), Path(config.CKPT_MEJOR)]
    # El test fijo no se incorpora al corpus descargado.
    validacion = Path(config.VALIDACION_FILE)
    if not validacion.is_file():
        raise RuntimeError("Falta data/validacion.txt; no se entrena sin evaluación fija.")
    carpeta, copias = respaldar(rutas)
    try:
        referencia = Path(config.CKPT_MEJOR)
        previo = evaluar_fijo(referencia, validacion)
        ultimo_previo = evaluar_fijo(Path(config.CKPT_ULTIMO), validacion)
        referencia_ultimo = ultimo_previo if ultimo_previo is not None else previo
        cmd = [sys.executable, str(RAIZ / "cerebro.py"), "entrenar",
               "--corpus", str(CORPUS), "--perfil", perfil,
               "--pasos", str(pasos_efectivos), "--batch", "2"]
        if estado_ckpt.exists():
            cmd.append("--resume")
            print("Reanudando pesos y optimizador guardados.", flush=True)
        else:
            print("Entrenamiento inicial con pesos propios.", flush=True)
        global PROCESO_ENTRENAMIENTO
        PROCESO_ENTRENAMIENTO = subprocess.Popen(cmd, cwd=RAIZ,
            start_new_session=(os.name == "posix"))
        codigo = PROCESO_ENTRENAMIENTO.wait()
        PROCESO_ENTRENAMIENTO = None
        if codigo:
            raise subprocess.CalledProcessError(codigo, cmd)
        nuevo = evaluar_fijo(Path(config.CKPT_MEJOR), validacion)
        ultimo_nuevo = evaluar_fijo(Path(config.CKPT_ULTIMO), validacion)
        # La mejora en un conjunto de validación fijo es condición necesaria,
        # pero no garantiza que todos los conocimientos se hayan conservado.
        if not aceptar_checkpoint(previo, nuevo) or not aceptar_checkpoint(referencia_ultimo, ultimo_nuevo):
            restaurar(copias)
            detalle = (f"best {previo} -> {nuevo}; "
                       f"last {referencia_ultimo} -> {ultimo_nuevo} bpb")
            registrar(historial_ruta, "revertido", pasos_efectivos, detalle)
            print(f"Entrenamiento descartado por validación: {detalle}. "
                  "Se restauraron los checkpoints anteriores.", flush=True)
            return True
        print(f"Validación aceptada: best {previo} -> {nuevo}; last {referencia_ultimo} -> {ultimo_nuevo} bpb.")
        registrar(historial_ruta, "aceptado", pasos_efectivos, f"best: {previo} -> {nuevo} bpb")
        return True
    except BaseException as exc:
        restaurar(copias)
        if isinstance(exc, Exception):
            try:
                registrar(historial_ruta, "revertido", pasos_efectivos, str(exc))
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def main():
    signal.signal(signal.SIGTERM, detener_entrenamiento)
    signal.signal(signal.SIGINT, detener_entrenamiento)
    ap = argparse.ArgumentParser(description="Recopilación y entrenamiento local diario")
    ap.add_argument("--comprobar-red", action="store_true",
                    help="comprobar acceso HTTPS a la API de Wikipedia sin descargar artículos")
    ap.add_argument("--dias", type=int, default=None,
                    help="ejecutar como máximo N días naturales y detenerse")
    ap.add_argument("--cada-dia", action="store_true",
                    help="Comprobar diariamente mientras este programa siga abierto")
    ap.add_argument("--entrenar", action="store_true",
                    help="Continuar el entrenamiento NumPy tras recopilar")
    ap.add_argument("--paginas", type=int, default=3)
    ap.add_argument("--pasos", type=int, default=20)
    ap.add_argument("--max-mb", type=int, default=20)
    ap.add_argument("--perfil", default="diminuto")
    args = ap.parse_args()
    if args.comprobar_red:
        return comprobar_red()
    if not (1 <= args.paginas <= 5 and 1 <= args.pasos <= 1000 and 1 <= args.max_mb <= 100):
        ap.error("Límites: 1-5 páginas, 1-1000 pasos, 1-100 MB")
    if args.dias is not None and not 1 <= args.dias <= 30:
        ap.error("--dias debe estar entre 1 y 30")
    import config
    if args.perfil not in config.PERFILES:
        ap.error("Perfil desconocido")
    # Se utilizan los checkpoints existentes del motor NumPy; al reanudar
    # el perfil efectivo será el almacenado en el checkpoint.
    estado_ckpt = Path(config.CKPT_ULTIMO)
    fecha_inicio = date.today()
    fecha_fin = fecha_inicio + timedelta(days=args.dias) if args.dias else None
    while True:
        if fecha_fin is not None and date.today() >= fecha_fin:
            print("Período de aprendizaje finalizado.")
            break
        try:
            ciclo(args.paginas, args.pasos, args.entrenar,
                  args.max_mb * 1024 * 1024, args.perfil, estado_ckpt)
        except (HTTPError, URLError, ConnectionError, TimeoutError, ssl.SSLError) as exc:
            print("No se pudo actualizar desde Wikipedia: " + explicar_error_red(exc), file=sys.stderr)
            print("Los datos y checkpoints locales no se modifican por este fallo de red.", file=sys.stderr)
            if not args.cada_dia:
                raise SystemExit(1)
        except Exception as exc:
            print(f"Error de actualización: {exc}", file=sys.stderr)
            if not args.cada_dia:
                raise SystemExit(1)
        if not args.cada_dia and args.dias is None:
            break
        # Comprobación horaria para respetar el fin del período sin esperar 24 h extra.
        time.sleep(60 * 60)


if __name__ == "__main__":
    raise SystemExit(main())
