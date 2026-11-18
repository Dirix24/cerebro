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
    assert "│       ___" not in fuente
    assert "VideoCapture" not in fuente
    assert "cv2" not in fuente


def test_microanimaciones_sutiles():
    assert ojos_animados.fotograma("saludando", 1.3)[0] == "—"
    assert ojos_animados.fotograma("aprendiendo", 2.1)[:2] == ("✧", "✧")
    assert ojos_animados.fotograma("analizando", 1.0)[:2] != ojos_animados.fotograma("analizando", 1.6)[:2]
    assert ojos_animados.fotograma("investigando", 1.0)[:2] != ojos_animados.fotograma("investigando", 2.0)[:2]


def test_animaciones_sin_camara():
    for nombre in ojos_animados.EXPRESIONES:
        for instante in (0, 0.2, 1.3, 2.1, 3.1, 9.0):
            ojo_izq, ojo_der, etiqueta = ojos_animados.fotograma(nombre, instante)
            assert ojo_izq and ojo_der and etiqueta
