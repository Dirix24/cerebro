"""El modo simbiótico nunca vincula equipos sin autorización explícita."""
import pytest
import config
from core.modo_simbiotico import (estado_huesped, vincular_huesped,
                                  desvincular_huesped, ruta_vinculo)


def test_requiere_confirmacion(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CEREBRO_HOME", str(tmp_path))
    with pytest.raises(PermissionError):
        vincular_huesped()
    assert not ruta_vinculo().exists()


def test_vinculacion_local_reversible(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CEREBRO_HOME", str(tmp_path))
    assert estado_huesped()["vinculado"] is False
    estado = vincular_huesped(confirmado=True)
    assert estado["vinculado"] is True
    assert estado["tamano_recomendado"] in config.TAMANOS_NUCLEO
    assert desvincular_huesped() is True
    assert estado_huesped()["vinculado"] is False
