"""Pruebas de coordinación y transporte sin descargar pesos."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from threading import Thread

import pytest

import config
from core.profesor_local import ProfesorLocal
from universe.nucleo import Nucleo


def test_profesor_usa_loopback_y_trata_salida_como_texto():
    consultas = []

    class Servidor(BaseHTTPRequestHandler):
        def do_POST(self):
            mensaje = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            consultas.append((self.path, mensaje))
            respuesta = {"content": "La fotosíntesis transforma la energía de la luz."}
            if len(consultas) > 1:
                respuesta["tool_calls"] = [{"id": "efecto no permitido"}]
            datos = json.dumps({"choices": [{"message": respuesta}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

    try:
        servidor = HTTPServer(("127.0.0.1", 0), Servidor)
    except PermissionError:
        pytest.skip("El entorno no permite escuchar en loopback.")
    with servidor:
        hilo = Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        try:
            profesor = ProfesorLocal(servidor.server_port)
            assert "fotosíntesis" in profesor.explicar("fotosíntesis")
            with pytest.raises(RuntimeError, match="respuesta válida"):
                profesor.explicar("química")
        finally:
            servidor.shutdown()
            hilo.join(timeout=2)
    ruta, cuerpo = consultas[0]
    assert ruta == "/v1/chat/completions"
    assert "tools" not in cuerpo and cuerpo["max_tokens"] == 96
    assert [m["role"] for m in cuerpo["messages"]] == ["system", "user"]


def test_coordinador_profesor_compartido_respeta_permisos_y_prioriza_herramientas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    enviados = []

    class Profesor:
        configurado = True

        def explicar(self, tema):
            enviados.append(tema)
            return "Explicación de prueba."

    nucleo = Nucleo("local", profesor=Profesor())
    terminal = nucleo.nucleo_terminal()
    try:
        assert terminal.profesor is nucleo.profesor
        espera = "No tengo una respuesta fiable con mis datos locales."
        procesar = nucleo.chat.procesar
        monkeypatch.setattr(nucleo.chat, "procesar",
                            lambda orden: procesar(orden) if orden.startswith("/calc ") else (espera, False))
        for modo in ("web", "studio", "escritorio", "terminal"):
            resultado = nucleo.conversar("Cerebro, explícame la fotosíntesis", modo=modo)
            assert resultado["origen"] == "profesor_local"
        assert len(enviados) == 4
        assert nucleo.conversar("Explícame mi contraseña")["respuesta"] == espera
        assert "4" in nucleo.conversar("/calc 2 + 2")["respuesta"]
        assert len(enviados) == 4
        nucleo.agente.permisos_concedidos.discard("READ")
        with pytest.raises(PermissionError):
            nucleo.conversar("Explícame la fotosíntesis", modo="web")
        assert len(enviados) == 4
    finally:
        nucleo.ejecutor.shutdown()
        terminal.ejecutor.shutdown()
