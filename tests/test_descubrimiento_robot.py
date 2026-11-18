import pytest
from core.descubrimiento_robot import interpretar_inventario_i2c, analizar_codigo_robot

def test_i2c_no_confirma_modelos_ni_acciona():
    r = interpretar_inventario_i2c([0x3c, 0x68])
    assert len(r["hallazgos"]) == 2
    assert not any(x["identidad_confirmada"] for x in r["hallazgos"])
    assert r["acciones_fisicas"] is False

def test_codigo_no_confirma_componentes():
    r = analizar_codigo_robot("from machine import Pin, PWM\nmotor = PWM(Pin(2))")
    assert "pwm" in r["interfaces_referenciadas"]
    assert r["componentes_confirmados"] == []
    assert r["codigo_ejecutado"] is False

def test_direcciones_invalidas():
    with pytest.raises(ValueError):
        interpretar_inventario_i2c([0x7f])
