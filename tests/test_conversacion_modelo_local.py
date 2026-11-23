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


def test_instalador_prioriza_modelo_ligero(preparar, monkeypatch):
    from core import configuracion_modelo_local

    for var in ("CEREBRO_OLLAMA_MODELO", "CEREBRO_PROFESOR_PUERTO", "CEREBRO_PROFESOR_MOTOR", "CEREBRO_PROFESOR_MODELO"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("core.motores_instalados._modelos_ollama",
                        lambda _: ["qwen2.5:7b", "qwen2.5:1.5b", "qwen2.5:0.5b"])
    elegidos = []
    monkeypatch.setattr(configuracion_modelo_local, "configurar", lambda _, modelo, puerto: elegidos.append(modelo))
    assert "0.5b" in configuracion_modelo_local.preparar_instalacion(preparar)
    assert elegidos == ["qwen2.5:0.5b"]


def test_rutas_especialistas_persistentes(preparar, monkeypatch):
    from core import configuracion_especialistas

    externo = preparar / "externo"
    externo.mkdir()
    (externo / "especialista.py").write_text("raise RuntimeError('No se ejecuta durante configuración')\n")
    monkeypatch.delenv("CEREBRO_DARAS_RAIZ", raising=False)
    configuracion_especialistas.configurar(daras=externo)
    assert configuracion_especialistas.obtener("DARAS_RAIZ") == str(externo)
    with pytest.raises(ValueError):
        configuracion_especialistas.configurar(cazel=externo)
    assert configuracion_especialistas.obtener("CAZEL_RAIZ") is None
