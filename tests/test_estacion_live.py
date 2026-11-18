import json
from core import actividad_neuronal
from core.estacion_neuronal import construir_estacion
from estacion_neuronal_live import snapshot


def test_telemetria_sin_texto_privado(tmp_path, monkeypatch):
    monkeypatch.setattr(actividad_neuronal, "ruta_eventos", lambda: tmp_path / "actividad.jsonl")
    actividad_neuronal.registrar("aprendido", "memoria")
    actividad_neuronal.registrar("investigando", "mi secreto personal")
    eventos = actividad_neuronal.ultimos()
    assert eventos[0]["estado"] == "aprendido"
    assert eventos[1]["texto"] == ""
    assert "mi secreto personal" not in (tmp_path / "actividad.jsonl").read_text()


def test_estacion_preparada_para_actualizacion():
    html = construir_estacion({"robot": {"valor": "sensor"}})
    assert 'fetch("/snapshot"' in html
    assert "setInterval(actualizar,1500)" in html
    assert "127.0.0.1" in html


def test_snapshot_no_lee_archivos_arbitrarios(tmp_path, monkeypatch):
    import config
    memoria = tmp_path / "memoria.json"
    memoria.write_text(json.dumps({"long_term": {"robot": {"valor": "sensor"}}}))
    monkeypatch.setattr(config, "MEMORY_FILE", str(memoria))
    monkeypatch.setattr(actividad_neuronal, "ruta_eventos", lambda: tmp_path / "no_existe.jsonl")
    datos = snapshot()
    assert datos["nodos"][0]["id"] == "robot"
    assert datos["eventos"] == []
