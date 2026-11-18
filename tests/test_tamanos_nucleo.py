"""El tamaño del núcleo se controla con una sola opción."""
import pytest
import config


def test_escalones_ordenados_y_validos():
    anterior = 0
    for tamano, perfil in config.TAMANOS_NUCLEO.items():
        assert config.perfil_por_tamano(tamano) == perfil
        n = config.estimar_parametros(perfil)
        assert n > anterior, (tamano, n, anterior)
        anterior = n
        p = config.PERFILES[perfil]
        assert p["dim"] % p["n_heads"] == 0
        assert p["block_size"] >= 1


def test_estimador_6m_y_16m():
    assert config.estimar_parametros("v2_6m") == 6910464
    assert config.estimar_parametros("v2_16m") == 15920896


def test_tamano_invalido():
    with pytest.raises(ValueError, match="Tamaño desconocido"):
        config.perfil_por_tamano("infinito")
