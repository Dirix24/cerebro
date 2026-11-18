from core.mapa_memoria import grafo
from core import actividad_neuronal


def test_grafo_vacio_y_limite():
    assert grafo(None) == ([], [])
    assert grafo({"uno": "a"}, limite=0) == ([], [])


def test_grafo_relaciones_y_limite_grande():
    memoria = {f"recuerdo_{i}": {"valor": "sensor robot"} for i in range(300)}
    nodos, enlaces = grafo(memoria, limite=5000)
    assert len(nodos) == 200
    assert enlaces
    assert len(enlaces) < 5000


def test_grafo_pequeno_conecta_todos():
    nodos, enlaces = grafo({str(i): {"valor": "palabra comun"} for i in range(12)})
    assert len(nodos) == 12
    assert len(enlaces) == 66


def test_telemetria_malformada_no_bloquea(tmp_path, monkeypatch):
    ruta = tmp_path / "actividad.jsonl"
    ruta.write_bytes(b'null\n[]\n{"estado":"aprendido","texto":"memoria"}\n{mal}\n')
    monkeypatch.setattr(actividad_neuronal, "ruta_eventos", lambda: ruta)
    eventos = actividad_neuronal.ultimos()
    assert len(eventos) == 1
    assert eventos[0]["estado"] == "aprendido"
