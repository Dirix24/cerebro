"""El criterio es de solo lectura y no sustituye la autorización real."""
from agent.criterio import evaluar_peticion


def test_creacion_requiere_permiso():
    denegado = evaluar_peticion("/crear-proyecto demo cli", {"READ"})
    assert denegado["puede_ejecutarse"] is False
    assert denegado["riesgo"] == "media"
    permitido = evaluar_peticion("/crear-proyecto demo cli", {"WRITE"})
    assert permitido["puede_ejecutarse"] is True
    assert permitido["requiere_orden_explicita"] is True


def test_comando_desconocido_no_se_aprueba():
    resultado = evaluar_peticion("/comando-desconocido", {"WRITE"})
    assert resultado["puede_ejecutarse"] is False


def test_consulta_no_ejecuta():
    resultado = evaluar_peticion("¿Qué es una red?", set())
    assert resultado["accion"] == "consulta"
    assert resultado["nota"].startswith("Solo clasificación")
