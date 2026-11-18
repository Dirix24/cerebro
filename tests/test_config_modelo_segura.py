"""Regresión: errores de configuración deben dar mensajes comprensibles."""
import pytest
from core.transformer.optimized_llm import ModeloConfig


def test_cero_cabezas_rechazado_sin_dividir_por_cero():
    with pytest.raises(ValueError, match="n_heads"):
        ModeloConfig(n_heads=0).validar()


def test_cabezas_negativas_rechazadas():
    with pytest.raises(ValueError, match="n_heads"):
        ModeloConfig(n_heads=-2).validar()
