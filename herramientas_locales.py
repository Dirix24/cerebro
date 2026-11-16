"""Herramientas independientes, locales y explícitas de Cerebro."""
import argparse
import json
from core.code_tools import analizar_python
from core.local_voice import hablar, grabar_wav


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="accion", required=True)
    a = sub.add_parser("analizar")
    a.add_argument("archivo", help="Ruta relativa a data/workspace")
    v = sub.add_parser("hablar")
    v.add_argument("texto")
    g = sub.add_parser("grabar")
    g.add_argument("destino")
    g.add_argument("--segundos", type=float, default=3)
    args = p.parse_args()
    if args.accion == "analizar":
        print(json.dumps(analizar_python(args.archivo), ensure_ascii=False, indent=2))
    elif args.accion == "hablar":
        hablar(args.texto)
    else:
        print(grabar_wav(args.destino, args.segundos))


if __name__ == "__main__":
    main()
