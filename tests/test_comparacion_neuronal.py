from pathlib import Path

import pytest

from core import comparacion_neuronal as prueba, competencias, curriculo
from core.checkpoint import cargar_checkpoint


def _modelo():
    ruta = Path(__file__).resolve().parents[1] / "checkpoints" / "best.npz"
    return cargar_checkpoint(str(ruta), False)["modelo"]


def test_bancos_y_dialogos_con_pares_contrafactuales():
    nuevo = prueba.banco_nuevo()
    largos = prueba.dialogos_largos(True)
    prueba.verificar_particiones(prueba.dialogos_largos(False), nuevo, largos)
    assert len(nuevo) == 40 and len(largos) == 16
    assert {c.materia for c in nuevo} == set(competencias.PRACTICA)
    modelo = _modelo()
    for a, b in zip(largos[::2], largos[1::2]):
        pa, pb = curriculo.prefijo(modelo, a), curriculo.prefijo(modelo, b)
        assert 112 < len(pa) <= 180 and 112 < len(pb) <= 180
        assert pa[-100:] == pb[-100:] and a.respuesta != b.respuesta
    with pytest.raises(ValueError, match="duplicadas"):
        prueba.verificar_particiones(nuevo, nuevo)


def test_lotes_igualan_objetivos_samples_y_replay():
    largos = prueba.dialogos_largos(False)
    viejo = "usuario: ¿Qué es un token?\ncerebro: Una unidad de texto."
    docs = [c.documento for c in largos]
    plan = prueba.planificar([viejo], docs, 8, 17, "mixta")
    assert plan == prueba.planificar([viejo], docs, 8, 17, "mixta")
    assert all(par[1] == viejo for par in plan)
    modelo = _modelo()
    pequeno = prueba.Lotes(plan, modelo.tokenizer, 112, set(docs))
    v2 = prueba.Lotes(plan, modelo.tokenizer, 192, set(docs))
    for _ in plan:
        xs, _ = pequeno.siguiente()
        xl, _ = v2.siguiente()
        assert xs.shape[1] == 112 < xl.shape[1]
    assert pequeno.objetivos == v2.objetivos
    assert pequeno.mascara.digest() == v2.mascara.digest()


def test_comparacion_rechaza_presupuestos_distintos():
    from informar_comparacion import agrupar

    a = {"perfil": "pequeno", "semilla": 17, "estrategia": "mixta",
         "fase_base": {"pasos": 1}, "ajuste": {"pasos": 2}}
    b = {"perfil": "v2", "semilla": 17, "estrategia": "mixta",
         "fase_base": {"pasos": 2}, "ajuste": {"pasos": 2}}
    with pytest.raises(ValueError, match="presupuesto"):
        agrupar([a, b])
