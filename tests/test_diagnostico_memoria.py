import json
import pytest
from memory.advanced_memory import AdvancedMemoryManager
from memory.consolidacion import consolidar
from memory.diagnostico import informe, listar_archivados, restaurar


def _gestor(tmp_path):
    return AdvancedMemoryManager(filepath=str(tmp_path / "memory.json"))


def test_diagnostico_sin_datos(tmp_path):
    gestor = _gestor(tmp_path)
    datos = informe(gestor.long_term_memory, gestor.filepath)
    assert datos["recuerdos_activos"] == 0
    assert datos["respaldo_existe"] is False


def test_restauracion_exige_confirmacion(tmp_path):
    gestor = _gestor(tmp_path)
    with pytest.raises(PermissionError):
        restaurar(gestor, "robot")


def test_restauracion_no_sobrescribe(tmp_path):
    gestor = _gestor(tmp_path)
    gestor.guardar_largo_plazo("robot", "valor nuevo")
    ruta = tmp_path / "memory.json.duplicados.jsonl"
    ruta.write_text(json.dumps({"duplicados": {"robot": {"valor": "viejo"}}}) + "\n")
    assert restaurar(gestor, "robot", confirmado=True) is False
    assert gestor.recuperar_largo_plazo("robot") == "valor nuevo"


def test_restauracion_tras_consolidacion(tmp_path):
    gestor = _gestor(tmp_path)
    gestor.long_term_memory = {f"otro_{i}": {"valor": str(i)} for i in range(500)}
    gestor.long_term_memory[" Robot "] = {"valor": "sensor", "categoria": "general"}
    gestor.long_term_memory["robot"] = {"valor": "sensor", "categoria": "general", "importancia": 3}
    assert consolidar(gestor.long_term_memory, gestor.filepath) == 1
    gestor.persistir()
    assert " Robot " in listar_archivados(gestor.filepath)
    assert restaurar(gestor, " Robot ", confirmado=True) is True
    assert gestor.long_term_memory[" Robot "]["valor"] == "sensor"
    assert " Robot " in _gestor(tmp_path).long_term_memory
