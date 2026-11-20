import pytest

from agent.intents import detectar_intencion
from core.temas_locales import responder_tema


@pytest.mark.parametrize("entrada,resultado", [
    ("2mas 2", "2+2"),
    ("¿Cuánto es dos más dos?", "2+2"),
    ("2por6", "2*6"),
    ("8 entre cuatro", "8/4"),
])
def test_calculo_informal(entrada, resultado):
    plan = detectar_intencion(entrada)
    assert plan[0]["tool"] == "calculator"
    assert plan[0]["arguments"]["expression"].replace(" ", "") == resultado


def test_no_convierte_frases_arbitrarias_en_calculos():
    assert detectar_intencion("tengo dos opciones por evaluar") is None
    assert detectar_intencion("uno y dos") is None


def test_temas_con_fuente_y_cambio_de_contexto():
    respuesta, tema = responder_tema("que es japon", None)
    assert "Asia oriental" in respuesta and "Fuente: https://" in respuesta
    respuesta, tema = responder_tema("¿y su capital?", tema)
    assert "Tokio" in respuesta and tema == "japon"
    respuesta, tema = responder_tema("¿Dónde queda Portugal?", tema)
    assert "Europa" in respuesta and tema == "portugal"
    respuesta, tema = responder_tema("¿y cuál es su capital?", tema)
    assert "Lisboa" in respuesta and tema == "portugal"
    assert responder_tema("¿Qué es Plutón?", tema) == (None, None)
    assert "¿De qué país" in responder_tema("¿y su capital?", None)[0]
