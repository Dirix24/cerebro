import json
import pytest

from memory.consolidacion import plan_duplicados, consolidar
from memory.advanced_memory import AdvancedMemoryManager


def test_no_borra_conocimientos_diferentes(tmp_path):
    memoria = {f"concepto_{i}": {"valor": "dato compartido", "categoria": "general"}
               for i in range(510)}
    assert plan_duplicados(memoria) == []
    assert consolidar(memoria, tmp_path / "memory.json") == 0
    assert len(memoria) == 510


def test_consolida_variantes_de_la_misma_clave_y_respalda(tmp_path):
    memoria = {f"otro_{i}": {"valor": str(i)} for i in range(500)}
    memoria[" Robot "] = {"valor": "sensor", "categoria": "general", "importancia": 1}
    memoria["robot"] = {"valor": "sensor", "categoria": "general", "importancia": 3}
    eliminados = consolidar(memoria, tmp_path / "memory.json")
    assert eliminados == 1
    assert "robot" in memoria
    assert " Robot " not in memoria
    archivo = tmp_path / "memory.json.duplicados.jsonl"
    registro = json.loads(archivo.read_text().splitlines()[0])
    assert " Robot " in registro["duplicados"]


def test_automatico_no_toca_memoria_antes_de_umbral(tmp_path):
    gestor = AdvancedMemoryManager(filepath=str(tmp_path / "memory.json"))
    gestor.guardar_largo_plazo("uno", "aprendido", importancia=3)
    gestor.guardar_largo_plazo("dos", "aprendido", importancia=3)
    assert len(gestor.long_term_memory) == 2
    assert gestor.recuperar_largo_plazo("uno") == "aprendido"
    assert not (tmp_path / "memory.json.duplicados.jsonl").exists()


def test_si_falla_respaldo_no_se_elimina(monkeypatch, tmp_path):
    import memory.consolidacion as modulo
    memoria = {f"otro_{i}": {"valor": str(i)} for i in range(500)}
    memoria["ROBOT"] = {"valor": "sensor"}
    memoria["robot"] = {"valor": "sensor"}
    def fallar(*args, **kwargs):
        raise OSError("disco lleno")
    monkeypatch.setattr(modulo.os, "open", fallar)
    with pytest.raises(OSError):
        modulo.consolidar(memoria, tmp_path / "memory.json")
    assert "ROBOT" in memoria and "robot" in memoria
