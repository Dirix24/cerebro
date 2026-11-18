from agent.lenguaje_natural import interpretar


def test_usb_en_espanol():
    assert interpretar("Cerebro, mira si tengo una placa conectada")["accion"] == "usb"


def test_github_errores():
    assert interpretar("Revisa errores de mi repositorio GitHub Dirix24/cerebro")["accion"] == "github_errores"


def test_recordatorios():
    assert interpretar("¿Qué tengo pendiente?")["accion"] == "recordatorios"


def test_camara_necesita_confirmacion():
    r = interpretar("Mira con la cámara")
    assert r["accion"] == "camara" and r["requiere_confirmacion"]


def test_sin_orden_no_hay_herramienta():
    assert interpretar("¿Qué es un transistor?") is None
