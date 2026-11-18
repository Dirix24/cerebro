"""Servidor de visualización solo en loopback. No sirve archivos arbitrarios."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
from core.actividad_neuronal import ultimos
from core.estacion_neuronal import construir_estacion
from core.mapa_memoria import grafo


def _memoria():
    ruta = Path(config.MEMORY_FILE)
    if not ruta.is_file() or ruta.stat().st_size > 5_000_000:
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        memoria = datos.get("long_term", {})
        return memoria if isinstance(memoria, dict) else {}
    except (ValueError, OSError):
        return {}


def snapshot():
    nodos, enlaces = grafo(_memoria(), limite=160)
    from core.estacion_neuronal import ESTADOS
    return {"nodos": nodos, "enlaces": enlaces, "eventos": ultimos(),
            "colores": ESTADOS}


class Manejador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            cuerpo = construir_estacion(_memoria(), ultimos()).encode("utf-8")
            tipo = "text/html; charset=utf-8"
        elif self.path == "/snapshot":
            cuerpo = json.dumps(snapshot(), ensure_ascii=False).encode("utf-8")
            tipo = "application/json; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'unsafe-inline'; "
                         "style-src 'unsafe-inline'; connect-src 'self'")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--puerto", type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador) as servidor:
        print(f"Estación local: http://127.0.0.1:{servidor.server_port}/")
        print("Contiene recuerdos privados: no compartas la URL ni abras puertos externos.")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
