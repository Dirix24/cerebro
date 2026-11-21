from core.gestos_tactiles import Gestos


def mano(pinza=False, x=.5, y=.5):
    puntos = [(x, y)] * 21
    puntos[0] = (x, y + .21)
    puntos[9] = (x, y + .05)
    puntos[4] = (x - (.018 if pinza else .095), y)
    return puntos


def habilitar(gestos):
    for instante in (0, .1, .2):
        assert gestos.actualizar(mano(), instante) == []
    assert gestos.actualizar(mano(), .3)[0][0] == "mover"


def test_clic_doble_y_filtro_de_pulso_accidental():
    gestos = Gestos()
    habilitar(gestos)
    gestos.actualizar(mano(True), .4)
    assert ("clic",) not in gestos.actualizar(mano(), .43)
    gestos.actualizar(mano(True), .55)
    assert ("clic",) in gestos.actualizar(mano(), .70)
    gestos.actualizar(mano(True), .76)
    assert ("clic",) in gestos.actualizar(mano(), .91)


def test_arrastre_suelta_en_perdida_y_pausa():
    gestos = Gestos()
    habilitar(gestos)
    gestos.actualizar(mano(True), .4)
    assert ("presionar",) in gestos.actualizar(mano(True, x=.65), .9)
    assert gestos.actualizar(None, 1.0) == [("soltar",)]
    assert gestos.pausar() == []
    habilitar(gestos)
    gestos.actualizar(mano(True), 1.1)
    assert ("presionar",) in gestos.actualizar(mano(True), 1.7)
    assert ("soltar",) in gestos.actualizar(mano(), 1.9)
    assert gestos.pausar() == []


def test_scroll_por_segunda_mano_y_suavizado():
    gestos = Gestos()
    habilitar(gestos)
    movimiento = gestos.actualizar(mano(x=.85), .4)[0]
    assert .5 < movimiento[1] < .85
    assert gestos.actualizar(mano(), .5, mano(True)) == []
    assert gestos.actualizar(mano(), .6, mano(True, y=.4)) == [("scroll", 1)]
    assert gestos.actualizar(mano(), .7, mano(True, y=.55)) == [("scroll", -1)]


def test_comandos_x11_solo_eventos_esperados(monkeypatch):
    from universe import tactil
    ejecutadas = []
    monkeypatch.setattr(tactil.subprocess, "run", lambda argumentos, **_: ejecutadas.append(argumentos))
    tactil._control([("mover", .5, .5), ("presionar",), ("soltar",), ("scroll", -1)], 101, 201)
    assert ejecutadas == [["xdotool", "mousemove", "50", "100", "mousedown", "1",
                            "mouseup", "1", "click", "5"]]
