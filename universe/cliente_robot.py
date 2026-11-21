"""Publica una lectura de sensores mediante HTTPS o loopback."""
from argparse import ArgumentParser
import json
import os
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SinRedireccion(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def publicar_lecturas(base, clave, identificador, sensores):
    destino = urlsplit(base)
    if destino.username or destino.password or destino.query or destino.fragment or destino.path not in ("", "/"):
        raise ValueError("Usa la URL base del servidor.")
    if not (destino.scheme == "https" and destino.hostname or
            destino.scheme == "http" and destino.hostname in {"127.0.0.1", "::1"}):
        raise ValueError("Se requiere HTTPS fuera de loopback.")
    datos = json.dumps({"id": identificador, "sensores": sensores}, allow_nan=False).encode()
    req = Request(base.rstrip("/") + "/api/telemetria", data=datos, headers={
        "Authorization": "Bearer " + clave, "Content-Type": "application/json",
    })
    with build_opener(SinRedireccion()).open(req, timeout=5) as respuesta:
        return json.loads(respuesta.read(4096))


def main():
    ap = ArgumentParser(description="Publica telemetría en el núcleo de Cerebro.")
    ap.add_argument("servidor")
    ap.add_argument("id")
    ap.add_argument("sensores", help='JSON, por ejemplo {"distancia_cm": 12}')
    args = ap.parse_args()
    clave = os.environ.get("CEREBRO_ROBOT_TOKEN")
    if not clave:
        ap.error("Configura CEREBRO_ROBOT_TOKEN en el entorno.")
    try:
        print(json.dumps(publicar_lecturas(args.servidor, clave, args.id, json.loads(args.sensores))))
    except (ValueError, OSError) as exc:
        ap.error(str(exc))


if __name__ == "__main__":
    main()
