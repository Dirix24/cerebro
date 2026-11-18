from core.estacion_neuronal import construir_estacion, guardar_estacion, ESTADOS


def test_estacion_colores_y_exploracion(tmp_path):
    memoria = {"robot": {"valor": "placa y sensor"}, "sensor": {"valor": "robot y distancia"}}
    html = construir_estacion(memoria, [{"estado": "investigando", "texto": "consulta"}])
    assert "NÚCLEO" in html
    assert "pointerdown" in html and "wheel" in html
    assert "ResizeObserver" in html
    for color in ESTADOS.values():
        assert color in html
    assert "robot" in html
    ruta = tmp_path / "estacion.html"
    guardar_estacion(memoria, ruta)
    assert ruta.exists()


def test_datos_no_inyectan_scripts():
    html = construir_estacion({"<script>alert(1)</script>": {"valor": "</script><img src=x>"}})
    assert "</script><img src=x>" not in html
    assert "\\u003c" in html
