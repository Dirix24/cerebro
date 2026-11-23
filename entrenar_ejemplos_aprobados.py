"""Preparar ejemplos aprobados para entrenamiento local, sin ejecutarlo por defecto."""
import argparse
import os
from pathlib import Path
import tempfile

import config
from core.lecciones_profesor import ALUMNOS

ORIGEN = Path(config.raiz_datos()) / "data" / "ejemplos_aprobados.jsonl"
DESTINO = ORIGEN.parent / "corpus" / "ejemplos_aprobados.txt"


def preparar(origen=ORIGEN, destino=DESTINO, aplicar=False, *, alumno=None):
    """Valida y deduplica ejemplos; solo escribe cuando aplicar=True."""
    # Leer el archivo entero evita omitir ejemplos antiguos silenciosamente.
    origen = Path(origen)
    if not origen.is_file():
        raise FileNotFoundError("No hay ejemplos aprobados; usa /aprobar-ejemplo.")
    if origen.stat().st_size > 2_000_000:
        raise ValueError("El banco supera 2 MB; revísalo antes de exportar.")
    import json
    if alumno is not None and alumno not in ALUMNOS:
        raise ValueError("Alumno desconocido.")
    pares = []
    registros = []
    vistos = set()
    for numero, linea in enumerate(origen.read_text(encoding="utf-8").splitlines(), 1):
        try:
            obj = json.loads(linea)
        except ValueError as exc:
            raise ValueError(f"JSON inválido en línea {numero}") from exc
        if not isinstance(obj, dict) or obj.get("aprobado") is not True:
            continue
        procedencia = obj.get("procedencia")
        if alumno and (not isinstance(procedencia, dict) or procedencia.get("verificado") is not True
                       or alumno not in procedencia.get("alumnos", [])):
            continue
        pregunta, respuesta = obj.get("pregunta"), obj.get("respuesta")
        if not all(isinstance(t, str) and 1 <= len(t.strip()) <= 2000
                   for t in (pregunta, respuesta)):
            raise ValueError(f"Ejemplo inválido en línea {numero}")
        par = (pregunta.strip(), respuesta.strip())
        if par not in vistos:
            vistos.add(par)
            pares.append(par)
            registros.append(obj)
    if not pares:
        raise ValueError("No hay ejemplos válidos y aprobados.")
    texto = "\n\n".join(f"usuario: {p}\ncerebro: {r}" for p, r in pares) + "\n"
    if alumno:
        texto = "".join(json.dumps(registro, ensure_ascii=False) + "\n" for registro in registros)
    if aplicar:
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destino.parent,
                                         prefix=".aprobados-", delete=False) as archivo:
            temporal = Path(archivo.name)
            archivo.write(texto)
        try:
            os.replace(temporal, destino)
        finally:
            temporal.unlink(missing_ok=True)
    return {"ejemplos": len(pares), "caracteres": len(texto), "escrito": aplicar}


def main():
    ap = argparse.ArgumentParser(description="Exportar ejemplos aprobados al corpus local")
    ap.add_argument("--aplicar", action="store_true", help="escribir el corpus (por defecto vista previa)")
    ap.add_argument("--entrenar", action="store_true", help="entrenar con validación y rollback")
    ap.add_argument("--alumno", choices=ALUMNOS, help="exportar lecciones verificadas como JSONL local")
    ap.add_argument("--pasos", type=int, default=30)
    ap.add_argument("--lr", type=float, default=0.0003)
    args = ap.parse_args()
    if args.entrenar and args.alumno:
        ap.error("--alumno exporta un banco; --entrenar usa el corpus de Cerebro")
    if args.entrenar and not args.aplicar:
        ap.error("--entrenar requiere --aplicar explícito")
    if args.entrenar and (not 1 <= args.pasos <= 1000 or not 0 < args.lr <= 0.001):
        ap.error("Parámetros de entrenamiento fuera de límites")
    try:
        destino = ORIGEN.parent / "lecciones-profesor" / f"{args.alumno.lower()}.jsonl" if args.alumno else DESTINO
        resultado = preparar(destino=destino, aplicar=args.aplicar, alumno=args.alumno)
        print(resultado)
        if args.entrenar:
            from entrenamiento_guiado import entrenar_guiado
            return 0 if entrenar_guiado(args.pasos, args.lr) else 1
        return 0
    except (OSError, ValueError) as exc:
        ap.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
