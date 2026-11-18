"""Pruebas del plan de RAM y de la selección de motores."""
import pytest

from core.plan_entrenamiento import plan_entrenamiento
from agent.enrutador_especializado import proponer_motor


def test_plan_de_entrenamiento_detecta_riesgo():
    plan = plan_entrenamiento("maximo", ram_bytes=128 * 1024 * 1024)
    assert plan["cabe_en_presupuesto"] is False
    assert plan["presupuesto_estimado_bytes"] > plan["minimo_pesos_gradientes_optimizador_bytes"]


def test_plan_mini_con_ram_amplia():
    plan = plan_entrenamiento("mini", ram_bytes=64 * 1024 ** 3)
    assert plan["cabe_en_presupuesto"] is True


def test_plan_rechaza_tamanos_desconocidos():
    with pytest.raises(ValueError):
        plan_entrenamiento("gigantesco")


@pytest.mark.parametrize("texto,motor", [
    ("Quiero programar un proyecto", "proyectos"),
    ("Necesito crear un PDF", "documentos"),
    ("Aprender ciberseguridad defensiva", "ciberseguridad"),
    ("Buenos días", "nucleo"),
])
def test_enrutamiento_sin_ejecucion(texto, motor):
    assert proponer_motor(texto)["motor"] == motor
