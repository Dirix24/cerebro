from core.mapa_memoria import grafo, svg_memoria, guardar_mapa


def test_relaciones_y_colores(tmp_path):
    memoria = {
        "robot": {"valor": "placa sensor distancia"},
        "sensor": {"valor": "distancia del robot"},
        "historia": {"valor": "creador"},
    }
    nodos, enlaces = grafo(memoria)
    assert len(nodos) == 3
    assert (0, 1) in enlaces
    svg = svg_memoria(memoria)
    assert "#3b82f6" in svg
    assert "Amarillo" in svg and "Naranja" in svg
    ruta = tmp_path / "mapa.svg"
    guardar_mapa(memoria, ruta)
    assert ruta.exists()
    try:
        guardar_mapa(memoria, ruta)
        assert False, "No debería sobrescribir"
    except FileExistsError:
        pass


def test_escape_de_contenido():
    svg = svg_memoria({"<script>": {"valor": "<b>malicioso</b>"}})
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
