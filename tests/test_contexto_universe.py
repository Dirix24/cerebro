import pytest

import config
from universe.nucleo import Nucleo


@pytest.fixture
def nucleo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    motor = Nucleo("local")
    try:
        yield motor
    finally:
        motor.ejecutor.shutdown()


@pytest.mark.parametrize("pregunta", ["Quiero hacer electrónica", "Quiero hacer algo de eletronica",
                                    "Ayúdame con la electroncia"])
def test_intencion_ambigua_ofrece_opciones_sin_abrir(nucleo, pregunta):
    respuesta = nucleo.conversar(pregunta)
    assert "Arduino" in respuesta["respuesta"] and "KiCad" in respuesta["respuesta"]
    assert "abrir_url" not in respuesta


def test_universe_muestra_fecha_y_elimina_despues_de_confirmar(nucleo):
    nucleo.memoria.guardar_largo_plazo("prueba", "valor", categoria="usuario")
    nodo = next(n for n in nucleo.nodos()["nodos"] if n["id"] == "memoria:prueba")
    assert nodo["fecha"] and nodo["eliminable"]
    with pytest.raises(PermissionError):
        nucleo.eliminar_nodo(nodo["id"], False)
    with pytest.raises(ValueError):
        nucleo.eliminar_nodo("alumno:pesos", True)
    assert nucleo.eliminar_nodo(nodo["id"], True) == {"eliminado": True}
    assert not any(n["id"] == nodo["id"] for n in nucleo.nodos()["nodos"])


def test_actividad_github_acotada(monkeypatch, nucleo):
    from core import github_local

    llamadas = []
    monkeypatch.setattr(github_local, "_datos_publicos", lambda repo, ruta, **kw:
                        llamadas.append(ruta) or [{"name": "main"}])
    with pytest.raises(PermissionError):
        nucleo.conversar("Muestra ramas de GitHub Dirix24/cerebro")
    assert not llamadas
    nucleo.internet = True
    assert nucleo.conversar("Muestra ramas de GitHub Dirix24/cerebro")["actividad"] == ["main"]
    assert llamadas == ["/branches?per_page=10"]


def test_detector_automatico_prefiere_manos_si_carga(monkeypatch):
    from universe import tactil

    ficha = {"opencv": True, "mediapipe": True, "modelo": "/modelo.task"}
    monkeypatch.setattr(tactil, "fallo_detector_manos", lambda _: None)
    assert tactil.elegir_detector(ficha) == (False, None)
    monkeypatch.setattr(tactil, "fallo_detector_manos", lambda _: "libGLES faltante")
    assert tactil.elegir_detector(ficha) == (True, "libGLES faltante")
    assert tactil.elegir_detector({**ficha, "mediapipe": False}) == (True, None)
