"""Contratos del catálogo de materias, sin generación ni ejecución externa."""
import pytest
from core.materias import MATERIAS, listar_materias, plan_materia


def test_catalogo_generalista_y_seguridad():
    assert len(listar_materias()) >= 8
    for clave in ("programacion", "ciberseguridad", "matematicas", "ciencias", "idiomas"):
        assert clave in MATERIAS
        assert MATERIAS[clave]["temas"]
        assert MATERIAS[clave]["ejercicio"]
        assert "Práctica:" in plan_materia(clave)
    assert "defensiva" in plan_materia("ciberseguridad").lower()


def test_materia_desconocida():
    with pytest.raises(ValueError):
        plan_materia("inventada")
