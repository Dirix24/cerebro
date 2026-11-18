import pytest
from core import ojos_animados


@pytest.mark.parametrize("estado", ["normal", "feliz", "curioso", "pensando", "sorprendido", "dormido"])
def test_expresa_emociones_sin_camara(estado):
    a, b, etiqueta = ojos_animados.fotograma(estado, 1.0)
    assert a and b and etiqueta


def test_parpadeo():
    a, b, _ = ojos_animados.fotograma("normal", 0.0)
    assert a == b == "—"
    a, b, _ = ojos_animados.fotograma("normal", 1.0)
    assert a == b == "◉"


def test_estado_desconocido_no_rompe():
    assert ojos_animados.fotograma("desconocido", 1) == ojos_animados.fotograma("normal", 1)


def test_no_camara_ni_dependencias_externas():
    import inspect
    fuente = inspect.getsource(ojos_animados)
    assert "VideoCapture" not in fuente
    assert "cv2" not in fuente


def test_falta_curses_da_mensaje(monkeypatch):
    monkeypatch.setattr(ojos_animados, "curses", None)
    with pytest.raises(RuntimeError, match="windows-curses"):
        ojos_animados.abrir()
