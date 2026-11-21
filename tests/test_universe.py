import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

import config
from universe.cliente_robot import publicar_lecturas
from universe.nucleo import Nucleo
from universe.servidor import crear_servidor


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_RAIZ", str(tmp_path))
    monkeypatch.setattr(config, "CEREBRO_HOME", str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memory" / "memoria.json"))
    nucleo = Nucleo("usb", cuota=1024)
    try:
        http = crear_servidor(0, nucleo, "panel", "robot")
    except PermissionError:
        nucleo.ejecutor.shutdown()
        pytest.skip("El entorno no permite sockets de loopback")
    hilo = Thread(target=http.serve_forever)
    hilo.start()
    url = f"http://127.0.0.1:{http.server_port}"

    def api(ruta, datos=None, clave="panel"):
        headers = {"Authorization": f"Bearer {clave}", "Content-Type": "application/json"}
        cuerpo = None if datos is None else json.dumps(datos).encode()
        with urlopen(Request(url + ruta, data=cuerpo, headers=headers), timeout=5) as respuesta:
            return json.load(respuesta)

    yield api, url, nucleo
    http.shutdown()
    hilo.join()
    http.server_close()
    nucleo.ejecutor.shutdown()


def test_nucleo_compartido_y_eventos_observables(servidor, tmp_path):
    api, _, nucleo = servidor
    assert "Puedo calcular" in api("/api/chat", {"mensaje": "¿Qué sabes hacer?"})["respuesta"]
    assert "/configurar-creador" in api("/api/chat", {"mensaje": "tu creador es Danny"})["respuesta"]
    assert "qué es marvel" in api("/api/chat", {"mensaje": "qeu es marvel"})["respuesta"]
    assert "guardados: 1" in api("/api/chat", {"mensaje": "Guarda esta memoria: perro = Nube"})["respuesta"]
    assert "Conclusión:" in api("/api/chat", {"mensaje": "/deducir Nube es perro; perro implica animal ? animal"})["respuesta"]
    assert "Nube" in api("/api/chat", {"mensaje": "/recuerdo perro"})["respuesta"]
    nodos = api("/api/nodos")["nodos"]
    assert {"razonamiento", "aprendizaje", "memoria", "relaciones"} <= {x["tipo"] for x in nodos}
    assert next(x for x in nodos if x["id"] == "memoria:perro")["detalle"] == "Nube"
    assert all("Nube" not in x["detalle"] for x in nodos if x["origen"] == "Registro de actividad")
    copia = api("/api/memoria")
    assert "fecha" in copia["long_term"]["perro"]
    assert api("/api/memoria", copia) == {"importados": 0}
    copia["long_term"]["perro"]["valor"] = "Otro"
    with pytest.raises(HTTPError, match="400"):
        api("/api/memoria", copia)
    assert nucleo.memoria.recuperar_largo_plazo("perro") == "Nube"
    copia["long_term"]["perro"]["valor"] = "Nube"
    from memory.advanced_memory import AdvancedMemoryManager
    destino = str(tmp_path / "restaurada.json")
    nucleo.memoria.long_term_memory.clear()
    nucleo.memoria.filepath = destino
    assert api("/api/memoria", copia) == {"importados": 1}
    assert AdvancedMemoryManager(destino).long_term_memory == copia["long_term"]


def test_autenticacion_archivos_canvas_y_cuotas(servidor, tmp_path):
    api, url, _ = servidor
    with urlopen(url, timeout=5) as respuesta:
        assert b"Universe" in respuesta.read()
        assert "frame-ancestors 'none'" in respuesta.headers["Content-Security-Policy"]
    with pytest.raises(HTTPError, match="401"):
        api("/api/estado", clave="")
    with pytest.raises(HTTPError, match="401"):
        api("/api/nodos", clave="robot")
    with pytest.raises(HTTPError, match="403"):
        api("/api/chat", {"mensaje": "Busca en internet gimnasia"})
    with pytest.raises(HTTPError, match="400"):
        api("/api/archivo", {"nombre": "../privado.txt", "texto": "dato"})
    sombra = tmp_path / "privado.txt"
    sombra.write_text("dato")
    (tmp_path / "universe-datos" / "enlace.txt").symlink_to(sombra)
    with pytest.raises(HTTPError, match="403"):
        api("/api/archivo?nombre=enlace.txt")
    assert api("/api/archivo", {"nombre": "tema/prueba.py", "texto": "print(1)"})
    assert api("/api/archivo?nombre=tema/prueba.py")["texto"] == "print(1)"
    with pytest.raises(HTTPError, match="400"):
        api("/api/archivo", {"nombre": "grande.txt", "texto": "x" * 1025})
    forma = {"tipo": "texto", "color": "#34ffaa", "texto": "Nodo", "puntos": [[2, 3]]}
    api("/api/canvas", {"formas": [forma]})
    assert api("/api/canvas") == {"formas": [forma]}
    with pytest.raises(HTTPError, match="400"):
        api("/api/canvas", {"formas": [{**forma, "color": "url(https://otro.test)"}]})


def test_tareas_simulador_y_telemetria(servidor):
    api, url, nucleo = servidor
    api("/api/archivo", {"nombre": "prueba.py", "texto": "raise RuntimeError('no se ejecuta')"})
    api("/api/tarea", {"accion": "sintaxis", "nombre": "prueba.py"})
    nucleo.ejecutor.shutdown(wait=True)
    assert api("/api/tareas")[0]["salida"] == "Sintaxis Python válida."
    api("/api/body", {"accion": "armar"})
    assert api("/api/body", {"accion": "avanzar", "valor": 10})["posicion"] == [10, 0]
    with pytest.raises(HTTPError, match="400"):
        api("/api/body", {"accion": "avanzar", "valor": 51})
    assert api("/api/body", {"accion": "parar"})["parado"]
    with pytest.raises(HTTPError, match="403"):
        api("/api/body", {"accion": "avanzar", "valor": 10})
    assert publicar_lecturas(url, "robot", "banco", {"temperatura": 21}) == {"recibido": True}
    assert api("/api/body")["telemetria"]["banco"]["sensores"]["temperatura"] == 21
    with pytest.raises(HTTPError, match="401"):
        api("/api/telemetria", {"id": "banco", "sensores": {}})


def test_borrado_de_historial_requiere_autenticacion_y_confirmacion(servidor):
    api, _, nucleo = servidor
    nucleo._registrar_turno("Hola", "Hola")
    with pytest.raises(HTTPError, match="401"):
        api("/api/historial", {"confirmar": True}, clave="robot")
    with pytest.raises(HTTPError, match="400"):
        api("/api/historial", {"confirmar": False})
    assert len(api("/api/historial")["turnos"]) == 2
    assert api("/api/historial", {"confirmar": True}) == {"turnos": []}
    assert api("/api/historial") == {"turnos": []}


def test_conversaciones_independientes_reinicio_y_migracion(servidor):
    api, _, nucleo = servidor
    nucleo._registrar_turno("Mensaje original", "Respuesta original")
    nueva = api("/api/conversaciones", {"accion": "nueva"})
    identificador = nueva["activa"]
    assert nueva["turnos"] == []
    assert [chat["id"] for chat in nueva["chats"]] == [identificador, "original"]
    nucleo._registrar_turno("Segunda conversación", "Segunda respuesta")
    reiniciado = Nucleo("usb")
    try:
        assert reiniciado.conversaciones.activa() == identificador
        assert reiniciado.historial()["turnos"][0]["texto"] == "Segunda conversación"
    finally:
        reiniciado.ejecutor.shutdown()
    original = api("/api/conversaciones", {"accion": "seleccionar", "id": "original"})
    assert original["turnos"][0]["texto"] == "Mensaje original"
    with pytest.raises(HTTPError, match="400"):
        api("/api/historial", {"confirmar": True, "id": identificador})
    with pytest.raises(HTTPError, match="400"):
        api("/api/chat", {"mensaje": "Mensaje desactualizado", "conversacion": identificador})
    api("/api/historial", {"confirmar": True, "id": "original"})
    assert api("/api/conversacion-activa")["activa"] != "original"
    assert api("/api/historial")["turnos"] == []
    otra = api("/api/conversaciones", {"accion": "seleccionar", "id": identificador})
    assert otra["turnos"][0]["texto"] == "Segunda conversación"
