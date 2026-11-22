import json

import pytest

from core import controles_accesibles as atspi


def test_selector_exige_identidad_y_transicion_booleana():
    clave = "a" * 64
    assert atspi.selector(json.dumps(["gtk.Clase", clave, False, True])) == ["gtk.Clase", clave, False, True]
    for valor in (["gtk.Clase", clave, True, True], ["gtk.Clase", "nombre en claro", False, True],
                  ["gtk.Clase", clave, 0, 1], ["", clave, False, True]):
        with pytest.raises(ValueError):
            atspi.selector(json.dumps(valor))


def test_repeticion_pausa_y_cancela_desde_otro_request(tmp_path, monkeypatch):
    from threading import Event, Thread
    from time import monotonic, sleep

    import config
    from core import ventanas_x11
    from universe.lanzador import api
    from universe.nucleo import Nucleo
    from universe.servidor import crear_servidor

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    n = Nucleo("local", documentos_usuario=True)
    cliente = "a" * 24
    paso = {"accion": "casilla", "objetivo": json.dumps(["gtk.Clase", "a" * 64, False, True])}
    n.escritorio._guardar_pendiente(cliente, repetir_casillas=[paso] * 3, nombre_demostracion="prueba")
    llamados = []
    liberaciones = [Event(), Event(), Event()]

    def ejecutar(*_):
        indice = len(llamados)
        llamados.append(indice)
        return liberaciones[indice].wait(4)

    monkeypatch.setattr(atspi, "ejecutar", ejecutar)
    monkeypatch.setattr(ventanas_x11, "listar", lambda: [{"clase": "gtk.Clase"}])

    def esperar(predicado):
        limite = monotonic() + 3
        while monotonic() < limite:
            if predicado():
                return
            sleep(.02)
        pytest.fail("No se alcanzó el estado esperado.")

    try:
        servidor = crear_servidor(0, n, "prueba")
    except PermissionError:
        n.ejecutor.shutdown()
        pytest.skip("El entorno no permite sockets locales.")
    with servidor:
        hilo = Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        sesion = {"url": f"http://127.0.0.1:{servidor.server_port}", "token": "prueba"}

        def ordenar(mensaje):
            return api(sesion, "chat", {"mensaje": mensaje, "modo": "studio", "cliente": cliente},
                       tiempo=2)["respuesta"]

        try:
            assert "iniciada" in ordenar("Confirma la repetición")
            esperar(lambda: llamados == [0])
            assert "en pausa" in ordenar("Espera")
            liberaciones[0].set()
            esperar(lambda: "1/3" in ordenar("Estado de la repetición"))
            assert llamados == [0]
            assert "en curso" in ordenar("Continúa")
            esperar(lambda: llamados == [0, 1])
            assert "cancelando" in ordenar("Para")
            liberaciones[1].set()
            esperar(lambda: "cancelada" in ordenar("Estado de la repetición"))
            assert llamados == [0, 1]
        finally:
            for liberacion in liberaciones:
                liberacion.set()
            servidor.shutdown()
            hilo.join(timeout=2)
            n.ejecutor.shutdown()
