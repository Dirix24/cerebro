"""Aprendizaje local diario desde artículos públicos de Wikipedia.

Opt-in. Conserva pesos/optimizador NumPy mediante --resume; sin modelos
preentrenados ni servicios de IA. Mantén el proceso abierto para el modo diario.
"""
import argparse
from datetime import date
import json
import shutil
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parent
CARPETA = RAIZ / "data" / "aprendizaje_internet"
ESTADO = CARPETA / "estado.json"
CORPUS = CARPETA / "corpus_diario.txt"
FUENTES = CARPETA / "fuentes.jsonl"
API = "https://es.wikipedia.org/w/api.php"


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
            entrenar_pendiente(pasos, perfil, estado_ckpt)
            estado["entrenamiento_pendiente"] = False
            ESTADO.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
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
    ESTADO.write_text(json.dumps({"ultimo_dia": hoy, "vistos": sorted(vistos), "entrenamiento_pendiente": bool(entrenar)},
                                 ensure_ascii=False), encoding="utf-8")
    print(f"Guardados {len(nuevos)} artículos y sus fuentes.")
    if entrenar:
        entrenar_pendiente(pasos, perfil, estado_ckpt)
        estado["entrenamiento_pendiente"] = False
        ESTADO.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")


def entrenar_pendiente(pasos, perfil, estado_ckpt):
    """Entrena con respaldo y validación fija; revierte si empeora."""
    import config
    from core.seguridad_aprendizaje import respaldar, restaurar, evaluar_fijo
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
        cmd = [sys.executable, str(RAIZ / "cerebro.py"), "entrenar",
               "--corpus", str(CORPUS), "--perfil", perfil,
               "--pasos", str(pasos), "--batch", "2"]
        if estado_ckpt.exists():
            cmd.append("--resume")
            print("Reanudando pesos y optimizador guardados.", flush=True)
        else:
            print("Entrenamiento inicial con pesos propios.", flush=True)
        subprocess.run(cmd, cwd=RAIZ, check=True)
        nuevo = evaluar_fijo(Path(config.CKPT_MEJOR), validacion)
        # La mejora en un conjunto de validación fijo es condición necesaria,
        # pero no garantiza que todos los conocimientos se hayan conservado.
        if previo is not None and (nuevo is None or nuevo > previo * 1.02):
            restaurar(copias)
            raise RuntimeError(
                f"Entrenamiento revertido: validación {previo:.4f} -> {nuevo} bpb")
        print(f"Validación fija aceptada: antes={previo}, después={nuevo} bpb.")
    except BaseException:
        restaurar(copias)
        raise
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Recopilación y entrenamiento local diario")
    ap.add_argument("--cada-dia", action="store_true",
                    help="Comprobar diariamente mientras este programa siga abierto")
    ap.add_argument("--entrenar", action="store_true",
                    help="Continuar el entrenamiento NumPy tras recopilar")
    ap.add_argument("--paginas", type=int, default=3)
    ap.add_argument("--pasos", type=int, default=20)
    ap.add_argument("--max-mb", type=int, default=20)
    ap.add_argument("--perfil", default="diminuto")
    args = ap.parse_args()
    if not (1 <= args.paginas <= 5 and 1 <= args.pasos <= 1000 and 1 <= args.max_mb <= 100):
        ap.error("Límites: 1-5 páginas, 1-1000 pasos, 1-100 MB")
    import config
    if args.perfil not in config.PERFILES:
        ap.error("Perfil desconocido")
    # Se utilizan los checkpoints existentes del motor NumPy; al reanudar
    # el perfil efectivo será el almacenado en el checkpoint.
    estado_ckpt = Path(config.CKPT_ULTIMO)
    while True:
        try:
            ciclo(args.paginas, args.pasos, args.entrenar,
                  args.max_mb * 1024 * 1024, args.perfil, estado_ckpt)
        except Exception as exc:
            print(f"Error de actualización: {exc}", file=sys.stderr)
            if not args.cada_dia:
                raise SystemExit(1)
        if not args.cada_dia:
            break
        time.sleep(24 * 60 * 60)


if __name__ == "__main__":
    main()
