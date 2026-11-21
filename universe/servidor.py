"""Servidor HTTP local de un usuario. Para acceso remoto, usar proxy HTTPS."""
from argparse import ArgumentParser
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sqlite3
from threading import Thread
from urllib.parse import parse_qs, urlsplit

from universe.nucleo import MIB, PERFILES, Nucleo

WEB = Path(__file__).with_name("web")
ESTATICOS = {"/": ("index.html", "text/html"), "/chat": ("index.html", "text/html"),
             "/studio": ("index.html", "text/html"), "/proyecto": ("index.html", "text/html"), "/universe": ("index.html", "text/html"), "/app.css": ("app.css", "text/css"),
             "/app.js": ("app.js", "text/javascript"), "/escena.js": ("escena.js", "text/javascript")}


def crear_servidor(puerto, nucleo, clave, clave_robot="", *, permitir_cierre=False, abrir_estudio=None,
                   abrir_terminal=None, mostrar_acompanante=None, abrir_destino=None, abrir_universe=None, abrir_tactil=None):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(12)

        def log_message(self, *_args):
            pass

        def enviar(self, codigo, datos, tipo="application/json"):
            cuerpo = (json.dumps(datos, ensure_ascii=False, allow_nan=False).encode()
                      if tipo == "application/json" else datos)
            self.send_response(codigo)
            self.send_header("Content-Type", tipo + "; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            self.end_headers()
            self.wfile.write(cuerpo)

        def autorizar(self, ruta):
            esperada = clave_robot if ruta == "/api/telemetria" else clave
            autorizacion = self.headers.get("Authorization", "")
            return bool(esperada) and compare_digest(autorizacion.encode(), ("Bearer " + esperada).encode())

        def do_GET(self):
            self.procesar(False)

        def do_POST(self):
            self.procesar(True)

        def procesar(self, escribir):
            try:
                url = urlsplit(self.path)
                ruta = url.path
                if not escribir and abrir_estudio is not None and ruta in ("/", "/studio", "/universe"):
                    self.send_response(302)
                    self.send_header("Location", "/chat")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return
                if not escribir and ruta in ESTATICOS:
                    nombre, tipo = ESTATICOS[ruta]
                    self.enviar(200, (WEB / nombre).read_bytes(), tipo)
                    return
                if not self.autorizar(ruta):
                    self.enviar(401, {"error": "Introduce la clave de esta sesión."})
                    return
                datos = {}
                if escribir:
                    longitud = int(self.headers.get("Content-Length", "0"))
                    limite = (24 if ruta == "/api/adjunto" else 6) * MIB
                    if not 0 < longitud <= limite or self.headers.get_content_type() != "application/json":
                        self.enviar(413, {"error": "Se requiere un cuerpo JSON dentro del límite."})
                        return
                    datos = json.loads(self.rfile.read(longitud))
                    if not isinstance(datos, dict):
                        raise ValueError("El cuerpo debe ser un objeto JSON.")
                resultado = self.operar(ruta, escribir, datos, parse_qs(url.query))
                try:
                    self.enviar(200, resultado)
                finally:
                    if ruta == "/api/apagar" and escribir and permitir_cierre:
                        Thread(target=self.server.shutdown, daemon=True).start()
            except PermissionError as exc:
                self.enviar(403, {"error": str(exc)})
            except (ValueError, RuntimeError, RecursionError, SyntaxError) as exc:
                self.enviar(400, {"error": str(exc)})
            except KeyError:
                self.enviar(404, {"error": "Operación inexistente."})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                return
            except (OSError, sqlite3.Error):
                self.enviar(500, {"error": "No se pudo completar la operación en el almacenamiento local."})

        def responder_chat(self, datos):
            anterior = nucleo.conversaciones.version_activa()
            if "conversacion" in datos and datos["conversacion"] != anterior["activa"]:
                raise ValueError("La conversación activa cambió. Actualiza antes de enviar el mensaje.")
            resultado = nucleo.conversar(datos.get("mensaje"), modo=datos.get("modo"), cliente=datos.get("cliente"))
            if resultado.get("abrir") == "studio" and abrir_estudio is not None:
                if abrir_estudio():
                    resultado.update(abrir="studio_nativo", respuesta="Abrí Cerebro Studio en el escritorio.")
            if resultado.get("abrir") == "tactil" and abrir_tactil is not None and abrir_tactil():
                resultado["respuesta"] = "Solicité el modo táctil. Elige una cámara y autoriza su uso en la ventana local."
            destino = resultado.get("abrir")
            if destino in ("navegador", "youtube", "steam") and abrir_destino is not None:
                abierto = abrir_destino(destino)
                if resultado.get("conservar_respuesta"):
                    aviso = ("Solicité abrir el navegador." if abierto else "No pude abrir el navegador.")
                    resultado["respuesta"] = aviso + "\n\n" + resultado["respuesta"]
                elif destino == "steam":
                    resultado["respuesta"] = ("Solicité abrir Steam." if abierto
                                             else "No encontré Steam instalado o no pude abrirlo.")
                elif abierto:
                    resultado["respuesta"] = "Abrí YouTube." if destino == "youtube" else "Abrí el navegador."
                else:
                    resultado["respuesta"] = "No pude abrir el navegador predeterminado."
            if "conversacion" in datos:
                resultado["revision"] = nucleo.conversaciones.version_activa()["revision"]
                resultado["revision_anterior"] = anterior["revision"]
            return resultado

        def operar(self, ruta, escribir, datos, consulta):
            if ruta == "/api/apagar" and escribir and permitir_cierre:
                return {"cerrando": True}
            if ruta == "/api/escritorio" and escribir:
                accion = datos.get("accion")
                if accion == "terminal":
                    ejecutar = abrir_terminal
                elif accion == "acompanante":
                    ejecutar = mostrar_acompanante
                elif accion == "universe":
                    ejecutar = abrir_universe
                else:
                    raise ValueError("Acción de escritorio desconocida.")
                nucleo.exigir_permisos("READ")
                if ejecutar is None or nucleo.solo_lectura:
                    raise PermissionError("Abre el chat con el lanzador local de Cerebro para usar esta acción.")
                if not ejecutar():
                    raise RuntimeError("No pude encontrar una sesión gráfica o un emulador de terminal.")
                return {"solicitado": True}
            if ruta == "/api/interfaz":
                if escribir:
                    return nucleo.interfaz(datos["id"], datos["modo"], datos["visible"], datos.get("enfocar", False))
                return nucleo.interfaz()
            if ruta in {"/api/body", "/api/telemetria", "/api/dispositivos"}:
                with nucleo.cerrojo_body:
                    if ruta == "/api/telemetria" and escribir:
                        return nucleo.recibir_telemetria(datos)
                    if ruta == "/api/body":
                        if escribir and nucleo.solo_lectura:
                            raise PermissionError("La sesión es de solo lectura.")
                        return nucleo.body(datos.get("accion"), datos.get("valor"))
                    if ruta == "/api/dispositivos" and not escribir:
                        nucleo.exigir_permisos("READ")
                        if nucleo.perfil == "servidor":
                            raise PermissionError("Consulta de puertos disponible en el equipo local.")
                        from core.dispositivos_usb import listar_puertos
                        return {"serie": listar_puertos()}
                    raise KeyError(ruta)
            with nucleo.cerrojo:
                if escribir and ruta == "/api/proyecto":
                    if abrir_estudio is None:
                        raise PermissionError("Los proyectos requieren el lanzador de escritorio local.")
                    return nucleo.operar_proyecto(datos)
                if escribir:
                    acciones = {
                        "/api/chat": lambda: self.responder_chat(datos),
                        "/api/historial": lambda: nucleo.borrar_historial(datos.get("confirmar"), datos.get("id")),
                        "/api/borrar-conversaciones": lambda: nucleo.borrar_conversaciones(
                            datos.get("confirmar"), datos.get("ids")),
                        "/api/conversaciones": lambda: nucleo.cambiar_conversacion(datos.get("accion"), datos.get("id")),
                        "/api/adjunto": lambda: nucleo.adjuntar(datos.get("nombre"), datos.get("contenido")),
                        "/api/archivo": lambda: nucleo.guardar(datos.get("nombre"), datos.get("texto")),
                        "/api/tarea": lambda: nucleo.crear_tarea(datos.get("accion"), datos.get("nombre")),
                        "/api/canvas": lambda: nucleo.guardar_canvas(datos),
                        "/api/memoria": lambda: nucleo.respaldo(datos),
                        "/api/cache": nucleo.limpiar_cache,
                    }
                else:
                    acciones = {
                        "/api/estado": nucleo.estado, "/api/historial": nucleo.historial, "/api/nodos": nucleo.nodos, "/api/archivos": nucleo.archivos,
                        "/api/conversaciones": nucleo.estado_conversaciones,
                        "/api/conversacion-activa": nucleo.conversaciones.version_activa,
                        "/api/analizar-aprendizaje": nucleo.analizar_aprendizaje,
                        "/api/evaluar-alumno": nucleo.evaluar_alumno,
                        "/api/tareas": nucleo.consultar_tareas,
                        "/api/memoria": nucleo.respaldo,
                        "/api/archivo": lambda: nucleo.leer(consulta.get("nombre", [""])[0]),
                        "/api/canvas": lambda: (json.loads(nucleo.leer("canvas.json")["texto"])
                                                if nucleo.ruta("canvas.json").is_file() else {"formas": []}),
                    }
                return acciones[ruta]()

    return ThreadingHTTPServer(("127.0.0.1", puerto), Handler)


def main():
    ap = ArgumentParser(description="Cerebro Universe")
    ap.add_argument("--perfil", choices=PERFILES, default="local")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--cuota-mib", type=int)
    ap.add_argument("--modelo", action="store_true", help="cargar el checkpoint local de Cerebro")
    ap.add_argument("--internet", action="store_true", help="autorizar consultas públicas explícitas")
    ap.add_argument("--solo-lectura", action="store_true")
    ap.add_argument("--investigacion-automatica", action="store_true",
                    help="consultar temas públicos si el núcleo local no tiene respuesta")
    args = ap.parse_args()
    clave_configurada = os.environ.get("CEREBRO_UNIVERSE_TOKEN")
    clave_robot = os.environ.get("CEREBRO_ROBOT_TOKEN", "")
    if args.perfil == "servidor" and not clave_configurada:
        ap.error("El perfil servidor requiere CEREBRO_UNIVERSE_TOKEN (32 caracteres como mínimo).")
    if any(len(clave) < 32 for clave in (clave_configurada, clave_robot) if clave):
        ap.error("Usa tokens distintos de 32 caracteres como mínimo.")
    if clave_configurada and clave_robot == clave_configurada:
        ap.error("El token de telemetría debe ser distinto al del panel.")
    if args.cuota_mib is not None and args.cuota_mib <= 0:
        ap.error("La cuota debe ser positiva.")
    from core.entorno_portatil import verificar_almacenamiento
    verificar_almacenamiento()
    modelo = None
    meta = None
    if args.modelo:
        from main import cargar_modelo
        modelo, meta, _ = cargar_modelo()
        if modelo is None:
            ap.error("No encontré un checkpoint propio de Cerebro.")
    nucleo = Nucleo(args.perfil, cuota=None if args.cuota_mib is None else args.cuota_mib * MIB,
                    modelo=modelo, internet=args.internet, solo_lectura=args.solo_lectura, meta=meta,
                    investigar_auto=args.investigacion_automatica)
    clave = clave_configurada or secrets.token_urlsafe(32)
    try:
        with crear_servidor(args.puerto, nucleo, clave, clave_robot) as servidor:
            url = f"http://127.0.0.1:{servidor.server_port}"
            print(f"Cerebro Universe · {args.perfil} · {url}", flush=True)
            if not clave_configurada:
                print(f"Abre en tu navegador {url}/#{clave}", flush=True)
            servidor.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        nucleo.ejecutor.shutdown(wait=True, cancel_futures=True)


if __name__ == "__main__":
    raise SystemExit(main())
