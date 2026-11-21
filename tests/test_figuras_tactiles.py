import pytest

from core.figuras_tactiles import Trazo, extruir, obj
from core.modelos_3d import analizar_obj


def mano(x, y, pinza):
    puntos = [(x, y)] * 21
    puntos[0] = x, y + .2
    puntos[9] = x, y + .05
    puntos[4] = x - (.02 if pinza else .09), y
    return puntos


def test_trazo_y_obj_con_grosor(tmp_path):
    trazo = Trazo()
    trazo.actualizar(mano(.2, .2, True))
    assert trazo.estado == "esperando"
    trazo.actualizar(mano(.2, .2, False))
    for x, y in ((.2, .2), (.8, .2), (.8, .8), (.2, .8), (.2, .2)):
        trazo.actualizar(mano(x, y, True))
    trazo.actualizar(mano(.2, .2, False))
    assert trazo.estado == "terminado"
    vertices, caras = extruir(trazo.puntos)
    assert len(vertices) == 8 and len(caras) == 6
    assert {v[2] for v in vertices} == {-.12, .12}
    ruta = tmp_path / "figura.obj"
    ruta.write_text(obj(vertices, caras))
    modelo = analizar_obj(ruta)
    assert modelo["vertices"] == 8 and modelo["caras"] == 6


def test_trazo_perdido_y_contorno_cruzado():
    trazo = Trazo()
    trazo.actualizar(mano(.2, .2, False))
    trazo.actualizar(mano(.2, .2, True))
    trazo.actualizar(None)
    assert trazo.estado == "interrumpido"
    with pytest.raises(ValueError, match="cruza"):
        extruir([(.2, .2), (.8, .8), (.8, .2), (.2, .8)])
