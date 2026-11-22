from types import SimpleNamespace

import pytest

from core import motores_instalados, recursos_locales
from core.gestos_tactiles import Gestos
from universe import tactil


def test_calibracion_persiste_al_perder_mano():
    gestos = Gestos(.30)
    mano = [(.35, .5)] * 21
    mano[0], mano[9], mano[4] = (.4, .6), (.4, .45), (.55, .5)
    for n in range(3):
        assert gestos.actualizar(mano, n / 20) == []
    assert gestos.actualizar(mano, .15)[0][1] == pytest.approx(.125)
    gestos.pausar()
    assert gestos.margen == .30
    with pytest.raises(ValueError):
        Gestos(.5)


def test_dependencias_y_fallback(monkeypatch):
    monkeypatch.setattr(tactil, "tecnologias", lambda: {
        "x11": True, "opencv": True, "mediapipe": False, "modelo": None,
    })
    with pytest.raises(RuntimeError, match="Falta MediaPipe"):
        tactil._requisitos()
    assert tactil._requisitos(marcador=True) is None


def test_marcador_no_genera_clic():
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    imagen = np.zeros((120, 160, 3), dtype=np.uint8)
    assert tactil._marcador_verde(cv2, imagen, .12) == []
    imagen[40:65, 50:75] = (0, 255, 0)
    [evento] = tactil._marcador_verde(cv2, imagen, .12)
    assert evento[0] == "mover"
    assert all(0 <= eje <= 1 for eje in evento[1:])


def test_inventario_no_arranca_adaptadores(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setenv("CEREBRO_DARAS_RAIZ", str(tmp_path))
    (tmp_path / "especialista.py").write_text("raise RuntimeError('no ejecutar')")
    monkeypatch.setenv("CEREBRO_OLLAMA_PUERTO", "11434")
    monkeypatch.setattr(motores_instalados, "_modelos_ollama",
                        lambda puerto: llamadas.append(puerto) or ["modelo:local"])
    inventario = {fila["nombre"]: fila for fila in motores_instalados.descubrir(SimpleNamespace(configurado=False))}
    assert llamadas == [11434] and inventario["Ollama"]["modelos"] == ["modelo:local"]
    assert inventario["DARAS"]["estado"] == "adaptador v1 presente"
    assert inventario["PROFESOR"]["estado"] == "evaluación local"


def test_recursos_y_recomendaciones(tmp_path):
    datos = recursos_locales.inspeccionar(tmp_path)
    assert datos["procesos_visibles"] >= 1
    assert "Swap libre" in recursos_locales.resumir(datos)
    datos["memoria_mib"]["MemAvailable"] = 512
    assert any("cuantizado" in texto for texto in recursos_locales.sugerir(datos))


def test_inventario_http_loopback():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread

    class OllamaDePrueba(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path == "/api/tags"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"models":[{"name":"modelo:local"},{"name":"otro:cloud"}]}')

        def log_message(self, *_args):
            pass

    try:
        servidor = HTTPServer(("127.0.0.1", 0), OllamaDePrueba)
    except OSError:
        pytest.skip("El entorno no permite abrir un socket local.")
    with servidor:
        hilo = Thread(target=servidor.serve_forever)
        hilo.start()
        try:
            assert motores_instalados._modelos_ollama(servidor.server_port) == ["modelo:local"]
        finally:
            servidor.shutdown()
            hilo.join()
