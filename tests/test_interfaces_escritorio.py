from base64 import b64encode
import io
import json
from unittest.mock import patch
from zipfile import ZipFile

import pytest

import config
from universe.nucleo import Nucleo


@pytest.fixture
def nucleo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "CEREBRO_HOME", str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    servicio = Nucleo("usb", internet=True, investigar_auto=True)
    yield servicio
    servicio.ejecutor.shutdown()


def test_presencia_navegador_terminal_y_escritorio(nucleo, monkeypatch):
    terminal, navegador = "a" * 24, "b" * 24
    assert nucleo.interfaz()["activa"] == "escritorio"
    assert nucleo.interfaz(terminal, "terminal")["activa"] == "terminal"
    assert nucleo.interfaz(navegador, "chat")["activa"] == "chat"
    assert nucleo.interfaz(terminal, "terminal")["activa"] == "chat"
    assert nucleo.interfaz(terminal, "terminal", enfocar=True)["activa"] == "terminal"
    assert nucleo.interfaz(navegador, "chat")["activa"] == "terminal"
    assert nucleo.interfaz(navegador, "chat", enfocar=True)["activa"] == "chat"
    assert nucleo.interfaz(navegador, "chat", False)["activa"] == "terminal"
    import time
    monkeypatch.setattr("universe.nucleo.monotonic", lambda: time.monotonic() + 8)
    assert nucleo.interfaz()["activa"] == "escritorio"


def test_investigacion_solo_pregunta_publica_e_historial(nucleo):
    with patch("aprendizaje_internet.buscar_tema",
               return_value=("Tardígrados", "Animales microscópicos.", "https://es.wikipedia.org/wiki/Tardigrada")) as buscar:
        assert "Fuente:" in nucleo.conversar("¿Qué son los tardígrados?")["respuesta"]
        buscar.assert_called_once_with("los tardígrados")
        buscar.reset_mock()
        nucleo.conversar("¿Qué es mi contraseña?")
        buscar.assert_not_called()
        assert "Fuente:" in nucleo.conversar("Investiga los tardígrados")["respuesta"]
    assert nucleo.conversar("Quiero programar")["abrir"] == "studio"
    assert "Conclusión: Ada es animal" in nucleo.conversar(
        "Si Ada es un ave y toda ave es un animal, ¿Ada es un animal?"
    )["respuesta"]
    assert "return a + b" in nucleo.conversar("Escribe una función en Python para sumar dos números")["respuesta"]
    otro_cliente = nucleo.historial()["turnos"]
    assert any(turno["texto"] == "Investiga los tardígrados" for turno in otro_cliente)


def adjuntar(nucleo, nombre, datos):
    return nucleo.adjuntar(nombre, b64encode(datos).decode())["nombre"]


def test_documento_y_subtitulos_sin_inferencia_externa(nucleo):
    archivo = adjuntar(nucleo, "informe.txt", b"Este informe identifica los tiempos del proyecto.")
    assert "tiempos del proyecto" in nucleo.conversar(f"Resume {archivo}")["respuesta"]
    explicacion = nucleo.conversar("Explícame", modo="chat")["respuesta"]
    assert "Pasajes principales" in explicacion and "tiempos del proyecto" in explicacion
    assert not any("tiempos del proyecto" in turno["texto"] for turno in nucleo.historial()["turnos"])
    afirmacion = nucleo.conversar("Guarda lo aprendido de este archivo")["respuesta"]
    assert "archivo_informe.txt" in afirmacion
    assert "tiempos del proyecto" in nucleo.conversar("/recuerdo archivo_informe.txt")["respuesta"]
    assert "inspeccionar funciones" in nucleo.conversar("¿Qué sabes hacer?", modo="terminal")["respuesta"]
    comprimido = io.BytesIO()
    with ZipFile(comprimido, "w") as documento:
        documento.writestr("word/document.xml", """
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>Este es el informe de prueba.</w:t></w:r></w:p></w:body>
            </w:document>
        """)
    docx = adjuntar(nucleo, "informe.docx", comprimido.getvalue())
    assert "el informe de prueba." in nucleo.conversar(f"Analiza el documento {docx}")["respuesta"]
    video = adjuntar(nucleo, "clip.mp4", b"flujo de prueba")
    adjuntar(nucleo, "clip.srt", b"1\n00:00:01,000 --> 00:00:02,000\nSemillas de girasol.\n")
    metadatos = json.dumps({"format": {"duration": "2.0"}, "streams": [
        {"codec_type": "video", "codec_name": "h264", "width": 64, "height": 48}
    ]}).encode()
    with patch("universe.consultas.shutil.which", return_value="/usr/bin/ffprobe"), patch(
        "universe.consultas.subprocess.run", return_value=type("Salida", (), {"stdout": metadatos})()
    ):
        respuesta = nucleo.conversar(f"Analiza el vídeo {video}")["respuesta"]
    assert "64×48" in respuesta and "Semillas de girasol." in respuesta
    with pytest.raises(ValueError, match="nombre"):
        adjuntar(nucleo, "../otro.txt", b"dato")


def test_instalador_crea_cuatro_entradas_y_retira_solo_las_propias(tmp_path, monkeypatch):
    from pathlib import Path
    from universe import instalar_escritorio

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    datos = tmp_path / "datos"
    configuracion = tmp_path / "configuracion"
    monkeypatch.setenv("XDG_DATA_HOME", str(datos))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(configuracion))
    instalar_escritorio.instalar()
    entradas = datos / "applications"
    assert len(list(entradas.glob("cerebro-*.desktop"))) == 4
    inicio = configuracion / "autostart" / "cerebro-escritorio.desktop"
    assert inicio.is_file()
    instalar_escritorio.instalar(automatico=False)
    assert not inicio.exists()
    ajeno = entradas / "otra-app.desktop"
    ajeno.write_text("[Desktop Entry]\nName=Otra aplicación\n")
    instalar_escritorio.retirar(Path(instalar_escritorio.__file__).resolve().parent.parent)
    assert list(entradas.iterdir()) == [ajeno]
    assert not (tmp_path / ".local" / "bin" / "cerebro").exists()


def test_lanzador_recupera_cierre_anticipado_al_cambiar_version(tmp_path, monkeypatch):
    from http.client import IncompleteRead
    from universe import lanzador

    registro = tmp_path / "sesion.json"
    antigua = {"url": "http://127.0.0.1:1234", "token": "antigua", "version": "anterior"}
    nueva = {"url": "http://127.0.0.1:1235", "token": "nueva", "version": "actual"}
    registro.write_text(json.dumps(antigua))

    def abrir(req, timeout):
        if req.full_url.endswith("/api/apagar"):
            raise IncompleteRead(b"", 18)
        return io.BytesIO(b'{"activa":"escritorio"}')

    def iniciar(*args, **kwargs):
        assert not registro.exists()
        registro.write_text(json.dumps(nueva))
        return type("Proceso", (), {"poll": lambda self: None})()

    monkeypatch.setattr(lanzador, "carpeta", lambda: tmp_path)
    monkeypatch.setattr(lanzador, "version_local", lambda: "actual")
    monkeypatch.setattr(lanzador.CLIENTE_LOCAL, "open", abrir)
    monkeypatch.setattr(lanzador.subprocess, "Popen", iniciar)
    assert lanzador.conectar() == nueva


def test_apagado_devuelve_respuesta_completa_antes_de_cerrar(nucleo):
    from threading import Thread
    from universe import lanzador
    from universe.servidor import crear_servidor

    try:
        servidor = crear_servidor(0, nucleo, "panel", permitir_cierre=True)
    except PermissionError:
        pytest.skip("El entorno no permite sockets de loopback.")
    hilo = Thread(target=servidor.serve_forever)
    hilo.start()
    try:
        sesion = {"url": f"http://127.0.0.1:{servidor.server_port}", "token": "panel"}
        assert lanzador.api(sesion, "apagar", {}, tiempo=2) == {"cerrando": True}
        hilo.join(timeout=2)
        assert not hilo.is_alive()
    finally:
        servidor.shutdown()
        hilo.join(timeout=2)
        servidor.server_close()
