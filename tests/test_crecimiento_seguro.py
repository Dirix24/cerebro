"""Contratos de aislamiento de datos y crecimiento del núcleo."""
from unittest.mock import patch

import pytest

import config
from core.data import cargar_datos
from trainer_engine import config_modelo_desde_perfil


def test_reservados_no_entran_en_entrenamiento():
    with patch("core.data.cargar_documentos", return_value=["entreno", "prueba", "nuevo", "validar"]), \
         patch("core.data.cargar_test", return_value=["prueba"]), \
         patch("core.data.cargar_generalizacion", return_value=["nuevo"]), \
         patch("core.data.cargar_validacion", return_value=["validar"]):
        train, val, _ = cargar_datos()
    assert train == ["entreno"]
    assert val == ["validar"]


def test_validacion_no_puede_duplicar_test():
    with patch("core.data.cargar_documentos", return_value=["entreno", "validar"]), \
         patch("core.data.cargar_test", return_value=["validar"]), \
         patch("core.data.cargar_generalizacion", return_value=[]), \
         patch("core.data.cargar_validacion", return_value=["validar"]):
        with pytest.raises(ValueError, match="reservados"):
            cargar_datos()


def test_v2_plus_crece_sin_cambiar_perfil_v2():
    normal = config_modelo_desde_perfil("v2")
    grande = config_modelo_desde_perfil("v2_plus")
    assert grande.dim > normal.dim
    assert grande.n_layers > normal.n_layers
    assert grande.block_size > normal.block_size
    assert config.PERFILES["v2"]["dim"] == 96
