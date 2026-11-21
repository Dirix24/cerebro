import pytest

import config
from universe.nucleo import Nucleo


@pytest.fixture
def nucleo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    motor = Nucleo("local", documentos_usuario=True)
    yield motor
    motor.ejecutor.shutdown()


def test_revocacion_del_espacio_de_studio_y_respaldo(nucleo):
    nucleo.guardar("ejemplo.txt", "dato")
    nucleo.memoria.guardar_largo_plazo("ejemplo", "recuerdo")
    nucleo.agente.permisos_concedidos.discard("READ")
    for operacion in (lambda: nucleo.leer("ejemplo.txt"), nucleo.archivos, nucleo.respaldo, nucleo.nodos):
        with pytest.raises(PermissionError, match="READ"):
            operacion()
    nucleo.agente.permisos_concedidos.add("READ")
    respaldo = nucleo.respaldo()
    nucleo.agente.permisos_concedidos.discard("WRITE")
    for operacion in (lambda: nucleo.guardar("ejemplo.txt", "otro"),
                      lambda: nucleo.adjuntar("otro.txt", "dGVzdA=="),
                      lambda: nucleo.respaldo(respaldo)):
        with pytest.raises(PermissionError, match="WRITE"):
            operacion()
    assert nucleo.leer("ejemplo.txt")["texto"] == "dato"


@pytest.mark.parametrize("modo", ["terminal", "chat", "studio", "escritorio"])
def test_revocacion_de_recuerdos_en_todas_las_interfaces(nucleo, modo):
    nucleo.memoria.guardar_largo_plazo("ejemplo", "original")
    nucleo.agente.permisos_concedidos.discard("WRITE")
    for pregunta in ("/recordar ejemplo = cambio", "/olvidar ejemplo",
                     "Recuerda que el color es verde", "Me llamo Ana"):
        respuesta = nucleo.conversar(pregunta, modo=modo)["respuesta"]
        assert "WRITE" in respuesta
    assert nucleo.memoria.recuperar_largo_plazo("ejemplo") == "original"
    nucleo.agente.permisos_concedidos.discard("READ")
    assert "READ" in nucleo.conversar("/memoria", modo=modo)["respuesta"]
    assert "4" in nucleo.conversar("/calc 2+2", modo=modo)["respuesta"]
