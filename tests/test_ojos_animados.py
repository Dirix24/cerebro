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


def test_expresiones_de_procesos():
    from datetime import datetime, timezone
    from core.ojos_animados import expresion_de_actividad, ESTADO_A_EXPRESION
    ahora = datetime.now(timezone.utc)
    for estado, expresion in ESTADO_A_EXPRESION.items():
        evento = {"estado": estado, "fecha": ahora.isoformat()}
        assert expresion_de_actividad([evento], ahora=ahora) == expresion


def test_evento_antiguo_no_aparenta_actividad():
    from datetime import datetime, timezone, timedelta
    from core.ojos_animados import expresion_de_actividad
    ahora = datetime.now(timezone.utc)
    viejo = {"estado": "analizando", "fecha": (ahora-timedelta(minutes=2)).isoformat()}
    assert expresion_de_actividad([viejo], ahora=ahora) == "esperando"


def test_evento_invalido_no_produce_expresion_falsa():
    from core.ojos_animados import expresion_de_actividad
    assert expresion_de_actividad([None]) == "esperando"
    assert expresion_de_actividad([{"estado": "analizando"}]) == "esperando"
    assert expresion_de_actividad([{"estado": "inventado", "fecha": "2026-01-01"}]) == "esperando"


def test_solo_ojos_sin_boca():
    import inspect
    fuente = inspect.getsource(ojos_animados._mostrar)
    assert "boca" not in fuente.lower()
    assert "VideoCapture" not in fuente
    assert "cv2" not in fuente
