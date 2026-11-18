import pytest
from core import estacion_terminal


def test_carga_memoria_desde_archivo(tmp_path, monkeypatch):
    import config
    ruta = tmp_path / "memoria.json"
    ruta.write_text('{"long_term":{"robot":{"valor":"sensor"}}}', encoding="utf-8")
    monkeypatch.setattr(config, "MEMORY_FILE", str(ruta))
    assert estacion_terminal.cargar_recuerdos()["robot"]["valor"] == "sensor"


def test_memoria_corrupta_no_rompe_terminal(tmp_path, monkeypatch):
    import config
    ruta = tmp_path / "memoria.json"
    ruta.write_text("{")
    monkeypatch.setattr(config, "MEMORY_FILE", str(ruta))
    assert estacion_terminal.cargar_recuerdos() == {}


def test_estacion_requiere_tty(monkeypatch):
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(RuntimeError, match="interactiva"):
        estacion_terminal.abrir()


def test_paleta_todos_los_estados():
    from core.actividad_neuronal import ESTADOS
    assert ESTADOS == set(estacion_terminal.PALETA)
