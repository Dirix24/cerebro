"""Exploración autónoma acotada: archivos de texto del hogar + Wikipedia.

No envía archivos locales a Internet, no sigue enlaces simbólicos ni ejecuta archivos.
El entrenamiento NumPy se delega al ciclo existente con validación y rollback.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

RAIZ = Path(__file__).resolve().parent
EXCLUIDOS = {
    ".ssh", ".gnupg", ".aws", ".config", ".local", ".cache", ".mozilla",
    ".thunderbird", ".git", ".venv", "venv", "node_modules", "checkpoints",
    "memory", "memoria", "private", "privado", "secrets", "secretos",
    "passwords", "contraseñas", "tokens", "credentials", "credenciales",
    "Downloads", "Descargas", "data", "backups", "copias_seguridad",
}
EXTENSIONES = {".txt", ".md", ".rst"}
MAX_ARCHIVO = 64 * 1024
MAX_ARCHIVOS = 300
MAX_TOTAL = 3 * 1024 * 1024
DB = RAIZ / "data" / "exploracion_local.sqlite3"


def rutas_locales(hogar, limite=MAX_ARCHIVOS):
    """Recorre el hogar sin seguir symlinks ni entrar en carpetas ocultas."""
    hogar = Path(hogar).expanduser().resolve()
    encontrados = 0
    for directorio, carpetas, archivos in os.walk(hogar, followlinks=False):
        carpetas[:] = sorted(
            nombre for nombre in carpetas
            if not nombre.startswith(".") and nombre.lower() not in EXCLUIDOS
            and not (Path(directorio) / nombre).is_symlink()
        )
        for nombre in sorted(archivos):
            ruta = Path(directorio) / nombre
            if (nombre.startswith(".") or ruta.suffix.lower() not in EXTENSIONES
                    or ruta.is_symlink() or ruta.name.lower() in EXCLUIDOS):
                continue
            try:
                if not ruta.is_file() or ruta.stat().st_size > MAX_ARCHIVO:
                    continue
            except OSError:
                continue
            yield ruta
            encontrados += 1
            if encontrados >= limite:
                return


def explorar_local(hogar, db=DB):
    """Índice separado, local y reconstruible; no modifica archivos fuente."""
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    total, bytes_leidos = 0, 0
    with sqlite3.connect(db) as con:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documentos USING fts5(texto, origen UNINDEXED)")
        con.execute("DELETE FROM documentos")
        for ruta in rutas_locales(hogar):
            try:
                datos = ruta.read_bytes()
                if bytes_leidos + len(datos) > MAX_TOTAL:
                    break
                texto = datos.decode("utf-8")
                if not texto.strip() or "\x00" in texto:
                    continue
                # Índice privado: solo la ruta y el texto quedan en la BD local.
                con.execute("INSERT INTO documentos(texto, origen) VALUES (?,?)",
                            (texto, str(ruta)))
                bytes_leidos += len(datos)
                total += 1
            except (OSError, UnicodeError):
                continue
    return {"archivos": total, "bytes": bytes_leidos}


def comparar_local(db=DB):
    """Cuenta términos compartidos entre documentos; relación léxica, no semántica."""
    with sqlite3.connect(db) as con:
        filas = con.execute("SELECT texto FROM documentos LIMIT 100").fetchall()
    import re
    grupos = [set(re.findall(r"\b\w{5,}\b", t.casefold())) for (t,) in filas]
    relaciones = sum(len(a & b) >= 4 for i, a in enumerate(grupos)
                     for b in grupos[i + 1:])
    return relaciones


def ejecutar_una_vez(hogar, internet=True, entrenar=False):
    informe = {"local": explorar_local(hogar)}
    informe["relaciones_lexicas"] = comparar_local()
    if internet:
        cmd = [sys.executable, str(RAIZ / "aprendizaje_internet.py"),
               "--paginas", "2", "--max-mb", "20"]
        if entrenar:
            cmd += ["--entrenar", "--pasos", "20"]
        informe["aprendizaje_web_codigo"] = subprocess.call(cmd, cwd=RAIZ)
    informe["aviso"] = ("Las relaciones son coincidencias de términos; "
                        "el entrenamiento no garantiza mejoras conversacionales.")
    return informe


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exploración autónoma local y Wikipedia")
    ap.add_argument("--autorizar-hogar", action="store_true",
                    help="autoriza leer textos .txt/.md/.rst de tu hogar, excluyendo rutas sensibles")
    ap.add_argument("--hogar", type=Path, default=Path.home())
    ap.add_argument("--solo-local", action="store_true")
    ap.add_argument("--entrenar", action="store_true",
                    help="activar entrenamiento NumPy existente, con validación")
    ap.add_argument("--cada-horas", type=int, default=0,
                    help="repetir mientras esté abierto (mínimo 6 horas)")
    args = ap.parse_args(argv)
    if not args.autorizar_hogar:
        ap.error("Para leer archivos debes indicar --autorizar-hogar")
    if args.cada_horas and not 6 <= args.cada_horas <= 168:
        ap.error("--cada-horas debe estar entre 6 y 168")
    try:
        while True:
            print(json.dumps(ejecutar_una_vez(args.hogar, not args.solo_local,
                                              args.entrenar), ensure_ascii=False, indent=2))
            if not args.cada_horas:
                break
            time.sleep(args.cada_horas * 3600)
    except KeyboardInterrupt:
        print("Exploración detenida.")


if __name__ == "__main__":
    main()
