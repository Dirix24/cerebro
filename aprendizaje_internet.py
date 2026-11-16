"""Actualización diaria opt-in: Wikipedia -> corpus -> entrenamiento local.

No usa APIs de IA ni modelos preentrenados. Sí consulta la API pública de
Wikipedia para obtener textos; requiere conexión y respeta límites de descarga.
"""
import argparse
from datetime import date
import json
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
API = "https://es.wikipedia.org/w/api.php"


def obtener_paginas(cantidad):
    params = {
        "action": "query", "generator": "random", "grnnamespace": "0",
        "grnlimit": str(cantidad), "prop": "extracts|info",
        "explaintext": "1", "exintro": "1", "inprop": "url",
        "format": "json", "formatversion": "2"
    }
    req = Request(API + "?" + urlencode(params),
                  headers={"User-Agent": "CerebroLocal/0.1 (aprendizaje personal; uso moderado)"})
    with urlopen(req, timeout=25) as respuesta:
        datos = json.load(respuesta)
    paginas = datos.get("query", {}).get("pages", [])
    salida = []
    for pagina in paginas:
        texto = " ".join(pagina.get("extract", "").split())
        if 250 <= len(texto) <= 10000 and pagina.get("fullurl", "").startswith("https://es.wikipedia.org/"):
            salida.append({"id": pagina["pageid"], "titulo": pagina["title"],
                           "url": pagina["fullurl"], "texto": texto})
    return salida


def ciclo(paginas, pasos, entrenar, max_bytes):
    CARPETA.mkdir(parents=True, exist_ok=True)
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    hoy = date.today().isoformat()
    if estado.get("ultimo_dia") == hoy:
        print("Hoy ya se realizó la recopilación; no se repite.")
        return
    vistos = set(estado.get("vistos", []))
    nuevos = [p for p in obtener_paginas(paginas) if p["id"] not in vistos]
    if not nuevos:
        print("No se encontraron artículos nuevos adecuados.")
        return
    bloque = "".join("\n\n" + p["texto"] + "\n" for p in nuevos)
    anterior = CORPUS.stat().st_size if CORPUS.exists() else 0
    if anterior + len(bloque.encode("utf-8")) > max_bytes:
        print("Límite de almacenamiento alcanzado; no se descarga más contenido.")
        return
    with CORPUS.open("a", encoding="utf-8") as f:
        f.write(bloque)
    manifiesto = CARPETA / "fuentes.jsonl"
    with manifiesto.open("a", encoding="utf-8") as f:
        for p in nuevos:
            f.write(json.dumps({k: p[k] for k in ("id", "titulo", "url")},
                               ensure_ascii=False) + "\n")
    vistos.update(p["id"] for p in nuevos)
    ESTADO.write_text(json.dumps({"ultimo_dia": hoy, "vistos": sorted(vistos)},
                                 ensure_ascii=False), encoding="utf-8")
    print(f"Guardados {len(nuevos)} artículos con sus URLs de origen.")
    if entrenar:
        # El corpus cambia cada día: el motor PyTorch no permite --resume si
        # cambia la huella. Se entrena el motor NumPy original desde cero.
        print("Entrenamiento local desde cero con el corpus recopilado.")
        subprocess.run([sys.executable, str(RAIZ / "cerebro.py"),
                        "entrenar", "--corpus", str(CORPUS),
                        "--perfil", "diminuto", "--pasos", str(pasos)], check=True)


def main():
    ap = argparse.ArgumentParser(description="Recopilación y entrenamiento diario local")
    ap.add_argument("--cada-dia", action="store_true",
                    help="Mantenerse activo y comprobar una vez cada 24 horas")
    ap.add_argument("--entrenar", action="store_true",
                    help="Entrenar el modelo NumPy original tras recopilar")
    ap.add_argument("--paginas", type=int, default=3)
    ap.add_argument("--pasos", type=int, default=20)
    ap.add_argument("--max-mb", type=int, default=20)
    args = ap.parse_args()
    if not (1 <= args.paginas <= 5 and 1 <= args.pasos <= 1000 and 1 <= args.max_mb <= 100):
        ap.error("Límites: 1-5 páginas, 1-1000 pasos, 1-100 MB")
    while True:
        try:
            ciclo(args.paginas, args.pasos, args.entrenar, args.max_mb * 1024 * 1024)
        except Exception as exc:
            print(f"Error de actualización (se volverá a intentar): {exc}", file=sys.stderr)
            if not args.cada_dia:
                raise SystemExit(1)
        if not args.cada_dia:
            break
        time.sleep(24 * 60 * 60)


if __name__ == "__main__":
    main()
