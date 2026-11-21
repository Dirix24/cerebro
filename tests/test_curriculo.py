from pathlib import Path

import pytest

from core import competencias, curriculo
from core.checkpoint import cargar_checkpoint


def semillas(variantes):
    return {materia: variantes for materia in competencias.PRACTICA}


def test_particion_reservada_independiente_y_contexto_completo():
    practica, reservado = curriculo.banco(semillas([12, 25, 37, 42, 56, 67]))
    otra, mismo_reservado = curriculo.banco(semillas([14, 27, 39, 47, 58, 69]))
    assert reservado == mismo_reservado
    assert practica != otra
    claves = {curriculo._clave("\n".join(c.lineas[:-1])) for casos in practica.values() for c in casos}
    assert not claves & {curriculo._clave("\n".join(c.lineas[:-1]))
                         for casos in reservado.values() for c in casos}
    verificacion = curriculo.verificacion_adicional()
    claves_reservadas = {curriculo._clave("\n".join(c.lineas[:-1]))
                         for casos in reservado.values() for c in casos}
    assert not (claves | claves_reservadas) & {curriculo._clave("\n".join(c.lineas[:-1]))
                                              for casos in verificacion.values() for c in casos}
    assert len(reservado["dialogos"]) == 30 and all(c.contexto for c in reservado["dialogos"])
    origen = Path(__file__).resolve().parents[1] / "checkpoints" / "best.npz"
    modelo = cargar_checkpoint(str(origen), con_optimizador=False)["modelo"]
    todos = [c for etapa in curriculo.ETAPAS for c in practica[etapa] + reservado[etapa]]
    assert curriculo.comprobar_contexto(modelo, todos)["fuera_ventana"] == 0


def test_referencia_estricta_y_semillas_no_son_codigo():
    assert curriculo._canon("-2") != curriculo._canon("2")
    assert curriculo._canon("raíces / raíz") != curriculo._canon("raices raiz")
    with pytest.raises(ValueError):
        curriculo.banco(semillas([12, 25, "no ejecutable"]))


def test_resumen_distingue_candidato_y_alumno_activo():
    banco = {"fundamentos": {m: {"aciertos": 0, "total": 2} for m in competencias.PRACTICA}}
    candidato = {"fundamentos": {m: {"aciertos": 1, "total": 2} for m in competencias.PRACTICA}}
    registro = {"tipo": "curriculo", "elegible_para_revision": False,
                "antes": {"reservadas": banco, "retencion": {"exactas": .5}},
                "despues": {"reservadas": candidato, "retencion": {"exactas": .25}}}
    texto = competencias.resumen(registro)
    assert "Candidato rechazado" in texto
    assert "0/2 base → 1/2 candidato" in texto
    assert "Retención: 50.0% → 25.0%" in texto
