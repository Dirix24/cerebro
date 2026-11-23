from types import SimpleNamespace

import pytest

import config
from core.configuracion_modelo_local import configurar, leer
from universe.nucleo import Nucleo


@pytest.fixture
def preparar(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    return tmp_path


def test_definiciones_locales_y_aclaracion(preparar):
    motor = Nucleo("local", profesor=SimpleNamespace(configurado=False))
    try:
        for texto in ("¿qué es un portátil?", "que esportatil"):
            assert "ordenador compacto" in motor.conversar(texto)["respuesta"]
        assert "dióxido de carbono" in motor.conversar("que es la fotosintesis")["respuesta"]
        assert motor.conversar("ques tayo")["origen"] == "aclaracion"
    finally:
        motor.ejecutor.shutdown()


def test_modelo_precede_busqueda_y_mantiene_seis_turnos(preparar, monkeypatch):
    llamadas = []

    def conversar(pregunta, contexto):
        llamadas.append((pregunta, contexto))
        return "Explicación temática."

    nucleo = Nucleo("local", profesor=SimpleNamespace(configurado=True, conversar=conversar))
    try:
        def inesperado(_):
            pytest.fail("La búsqueda local se ejecutó antes de la consulta generativa.")

        monkeypatch.setattr(nucleo.chat, "procesar", inesperado)
        for i in range(7):
            assert nucleo.conversar(f"¿Qué es tema {i}?")["origen"] == "profesor_local"
        assert len(llamadas[-1][1]) == 6
        assert "4" in nucleo.conversar("Calcula 2 + 2")["respuesta"]
        assert len(llamadas) == 7
    finally:
        nucleo.ejecutor.shutdown()


def test_configuracion_persiste_solo_tras_inferencia(preparar, monkeypatch):
    from core.profesor_local import ProfesorLocal

    monkeypatch.setattr("core.motores_instalados._modelos_ollama", lambda _: ["modelo:local"])
    for var in ("CEREBRO_OLLAMA_MODELO", "CEREBRO_PROFESOR_MOTOR", "CEREBRO_PROFESOR_PUERTO"):
        monkeypatch.delenv(var, raising=False)

    def falla(*args):
        raise RuntimeError("motor caído")

    monkeypatch.setattr(ProfesorLocal, "conversar", falla)
    with pytest.raises(RuntimeError):
        configurar(preparar, "modelo:local")
    assert leer(preparar) is None
    monkeypatch.setattr(ProfesorLocal, "conversar", lambda *args: "Hola.")
    assert configurar(preparar, "modelo:local") == "Hola."
    assert ProfesorLocal.desde_entorno().ollama == "modelo:local"
