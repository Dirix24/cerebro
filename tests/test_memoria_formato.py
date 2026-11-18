import json
import pytest

from memory.advanced_memory import AdvancedMemoryManager
from core import estacion_terminal
import config


@pytest.mark.parametrize("datos", [None, [], 3, "texto", {"long_term": []}, {"long_term": None}, {"long_term": {"clave": {"valor": "dato"}}}])
def test_carga_memoria_formato_imprevisto(tmp_path, monkeypatch, datos):
    ruta = tmp_path / "memory.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    gestor = AdvancedMemoryManager(filepath=str(ruta))
    esperado = datos["long_term"] if isinstance(datos, dict) and isinstance(datos.get("long_term"), dict) else {}
    assert gestor.long_term_memory == esperado
    monkeypatch.setattr(config, "MEMORY_FILE", str(ruta))
    assert estacion_terminal.cargar_recuerdos() == esperado
