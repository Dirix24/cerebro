import pytest

from memory.advanced_memory import AdvancedMemoryManager


@pytest.mark.parametrize("operacion", ["guardar", "actualizar", "eliminar"])
def test_fallo_persistencia_revierte_memoria(tmp_path, monkeypatch, operacion):
    gestor = AdvancedMemoryManager(filepath=str(tmp_path / "memory.json"))
    gestor.guardar_largo_plazo("clave", "original")
    anterior = dict(gestor.long_term_memory)
    def fallar():
        raise OSError("disco lleno")
    monkeypatch.setattr(gestor, "persistir", fallar)
    with pytest.raises(OSError):
        if operacion == "guardar":
            gestor.guardar_largo_plazo("nueva", "valor")
        elif operacion == "actualizar":
            gestor.actualizar_largo_plazo("clave", "modificado")
        else:
            gestor.eliminar_largo_plazo("clave")
    assert gestor.long_term_memory == anterior


def test_busquedas_ignoran_recuerdos_malformados(tmp_path):
    gestor = AdvancedMemoryManager(filepath=str(tmp_path / "memory.json"))
    gestor.long_term_memory = {
        "corrupto": None,
        "importancia_mala": {"valor": "sensor robot", "importancia": "incorrecta"},
        "importancia_nan": {"valor": "robot", "importancia": "nan"},
        "normal": {"valor": "robot sensor", "importancia": 3},
    }
    assert "normal" in gestor.buscar("robot")
    assert "normal" in gestor.buscar_similar("robot sensor")


def test_max_turnos_cero(tmp_path):
    gestor = AdvancedMemoryManager(filepath=str(tmp_path / "memory.json"), max_turnos=0)
    gestor.agregar_contexto("usuario", "hola")
    assert gestor.short_term_context == []
