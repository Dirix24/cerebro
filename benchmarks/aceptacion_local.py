"""Prueba el servicio real con llama.cpp y datos temporales, en Unix o TCP."""
import argparse
from contextlib import contextmanager, closing
import errno
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import resource
import socket
from tempfile import TemporaryDirectory
from threading import Event, Thread
from time import perf_counter


@contextmanager
def servicio(profesor, carpeta, offline):
    from core.profesor_local import _HTTPUnix
    from universe.nucleo import Nucleo
    from universe.servidor import crear_servidor

    n = Nucleo("local", profesor=profesor, internet=not offline, investigar_auto=not offline)
    ruta = carpeta / "cerebro.sock" if offline else None
    if ruta:
        ruta.unlink(missing_ok=True)
    try:
        with crear_servidor(0, n, "prueba-local", abrir_estudio=lambda: False, ruta_unix=ruta) as servidor:
            hilo = Thread(target=servidor.serve_forever, daemon=True)
            hilo.start()

            def pedir(recurso, datos=None, *, codigo=200, clave="prueba-local"):
                conexion = (_HTTPUnix(ruta, 50) if ruta else
                            HTTPConnection("127.0.0.1", servidor.server_port, timeout=50))
                with closing(conexion):
                    conexion.request("GET" if datos is None else "POST", recurso,
                                     None if datos is None else json.dumps(datos).encode(),
                                     {"Authorization": "Bearer " + clave, "Content-Type": "application/json"})
                    respuesta = conexion.getresponse()
                    contenido = respuesta.read()
                    assert respuesta.status == codigo, (recurso, respuesta.status, contenido[:350])
                    return json.loads(contenido) if respuesta.getheader("Content-Type").startswith("application/json") else contenido

            try:
                yield pedir
            finally:
                servidor.shutdown()
                hilo.join(timeout=3)
    finally:
        n.ejecutor.shutdown()
        if ruta:
            ruta.unlink(missing_ok=True)


def verificar_local(profesor, carpeta, offline, adaptadores=False):
    from core.lecciones_colectivas import recopilar, validar_lecciones

    trabajo = carpeta / "proyecto"
    trabajo.mkdir()
    cliente = "a" * 24
    with servicio(profesor, carpeta, offline) as pedir:
        pedir("/api/estado", codigo=401, clave="incorrecta")
        assert "perfil" in pedir("/api/estado")
        chat = lambda mensaje, **datos: pedir("/api/chat", {"mensaje": mensaje, **datos})
        assert "243" in chat("Calcula 27 * 9")["respuesta"]
        ficha = chat("Dime qué significa un diodo")
        assert ficha["origen"] == "referencia_local" and "oldid=" in ficha["respuesta"]
        saludo = chat("Cuéntame algo agradable para empezar el día")
        assert saludo["origen"] == "profesor_local" and saludo["respuesta"]
        chat("Recuerda que el nombre del proyecto de prueba es Mimbre")
        assert "mimbre" in chat("¿Qué recuerdas?")["respuesta"].casefold()
        if offline:
            pedir("/api/chat", {"mensaje": "Busca en internet astronomía"}, codigo=403)
            hallazgo = None
        else:
            hallazgo = chat("Dime qué significa magnetorrecepción")
            assert hallazgo["origen"] == "consulta_publica" and "es.wikipedia.org/wiki/" in hallazgo["respuesta"]
        assert isinstance(pedir("/api/nodos")["nodos"], list)
        pedir("/api/proyecto", {"accion": "abrir", "cliente": cliente, "carpeta": str(trabajo)}, codigo=403)
        pedir("/api/proyecto", {"accion": "abrir", "cliente": cliente, "carpeta": str(trabajo),
                                "confirmar": True, "recordar_permiso": True})

        def proyecto(accion, codigo=200, **datos):
            return pedir("/api/proyecto", {"accion": accion, "cliente": cliente,
                                           "carpeta_esperada": str(trabajo), **datos}, codigo=codigo)

        proyecto("crear", nombre="cuentas.py", texto="def doble(x): return 2*x\n", confirmar=True)
        assert "doble" in proyecto("leer", nombre="cuentas.py")["texto"]
        proyecto("leer", nombre="../fuera.txt", codigo=400)
        proyecto("analizar")
        # Actividad del modelo real. El rechazo se conserva como resultado de la prueba.
        gen = chat("Crea un programa Python con una función doble(x) que devuelve x * 2. "
                   "Archivos planificados: calculo.py, test_calculo.py", cliente=cliente, modo="studio")
        assert not (trabajo / "entrega").exists()
        if gen.get("generacion"):
            identificador = gen["generacion"]["id"]
            proyecto("publicar_generado", nombre="entrega", id=identificador, codigo=403)
            proyecto("publicar_generado", nombre="entrega", id=identificador, confirmar=True)
            assert (trabajo / "entrega" / "calculo.py").is_file()
        assert pedir("/api/historial")["turnos"]

    with servicio(profesor, carpeta, offline) as pedir:
        assert pedir("/api/historial")["turnos"]
        recuerdo = pedir("/api/chat", {"mensaje": "¿Qué recuerdas?"})
        assert "mimbre" in recuerdo["respuesta"].casefold()
        pedir("/api/proyecto", {"accion": "abrir", "cliente": cliente, "carpeta": str(trabajo)})
    lecciones = validar_lecciones(recopilar(Event(), 2)) if adaptadores else []
    if adaptadores:
        assert {leccion["especialista"] for leccion in lecciones} == {"CAZEL", "DARAS"}
    return {"ficha": ficha, "saludo": saludo, "proyecto_real": gen, "hallazgo_publico": hallazgo,
            "lecciones_verificadas": lecciones, "reinicio_nucleo": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modo", choices=("offline", "online"), required=True)
    parser.add_argument("--motor", required=True)
    parser.add_argument("--modelo", required=True)
    parser.add_argument("--adaptadores-configurados", action="store_true")
    args = parser.parse_args()
    offline = args.modo == "offline"
    if offline:
        try:
            with socket.socket(socket.AF_INET):
                parser.error("Ejecuta el modo offline mediante benchmarks.red_bloqueada.")
        except OSError as error:
            if error.errno != errno.EAFNOSUPPORT:
                raise
    inicio = perf_counter()
    with TemporaryDirectory(prefix="cerebro-aceptacion-") as temporal:
        os.environ["CEREBRO_HOME"] = temporal
        from core.profesor_local import ProfesorBajoDemanda

        profesor = ProfesorBajoDemanda(args.motor, args.modelo, usar_socket_unix=offline)
        try:
            salida = verificar_local(profesor, Path(temporal), offline, args.adaptadores_configurados)
        finally:
            profesor.cerrar()
    medidas = {nombre: resource.getrusage(quien) for nombre, quien in
               (("python", resource.RUSAGE_SELF), ("hijos", resource.RUSAGE_CHILDREN))}
    print(json.dumps({"modo": args.modo, "segundos": round(perf_counter() - inicio, 2),
                      "recursos": {nombre: {"cpu_s": round(uso.ru_utime + uso.ru_stime, 2),
                                            "max_rss_kib": uso.ru_maxrss} for nombre, uso in medidas.items()},
                      **salida}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
