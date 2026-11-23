from time import sleep

import pytest

import config
from agent.observacion_escritorio import acciones
from core import ventanas_x11
from universe.nucleo import Nucleo


@pytest.fixture
def nucleo(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    servicio = Nucleo("local", documentos_usuario=True)
    yield servicio
    servicio.escritorio.demostraciones.observador.limpiar()
    servicio.ejecutor.shutdown()


def test_observacion_autorizada_limitada_revisada_y_cancelable(nucleo, monkeypatch):
    from types import SimpleNamespace

    indicador = SimpleNamespace(poll=lambda: None, terminate=lambda: None, wait=lambda: 0)
    monkeypatch.setattr("agent.observacion_escritorio.controles_accesibles.indicador", lambda: indicador)
    cliente = "a" * 24
    ventana = {"id": "0x120", "pid": "315", "clase": "editor.Editor", "titulo": "Editor"}
    llamadas = []
    monkeypatch.setattr(ventanas_x11, "listar", lambda: [ventana])
    estado = [False, False, True]
    monkeypatch.setattr(ventanas_x11, "estado_observable",
                        lambda recibida: llamadas.append(recibida["id"]) or tuple(estado))

    def hablar(orden, id=cliente):
        return nucleo.conversar(orden, cliente=id)["respuesta"]

    assert "Autoriza observación" in hablar("Observa la ventana de Editor como pruebas")
    assert not llamadas
    assert "Selecciona" in hablar("Autoriza observación", "b" * 24)
    assert "iniciada" in hablar("Autoriza observación")
    estado[1] = True
    observador = nucleo.escritorio.demostraciones.observador
    for _ in range(30):
        if observador.rutinas[cliente].pasos:
            break
        sleep(.03)
    assert "maximiza" in hablar("Detén la observación")
    assert "Guardé" in hablar("Aprueba la demostración")
    assert set(llamadas) == {"0x120"}
    assert any(n["origen"] == "Demostración autorizada" and n["vinculos"] for n in nucleo.nodos()["nodos"])
    assert "Autoriza observación" in hablar("Observa la ventana de Editor como borrador")
    assert "cancelada" in hablar("Cancela la observación")
    assert "Selecciona" in hablar("Autoriza observación")
    nucleo.agente.permisos_concedidos.discard("WRITE")
    with pytest.raises(PermissionError):
        hablar("Observa la ventana de Editor como otra")


def test_transiciones_no_registran_contenido_y_priorizan_estado():
    assert acciones((False, False, False), (False, True, True)) == ["maximiza"]
    assert acciones((False, True, True), (True, True, False)) == ["minimiza"]
    assert acciones((False, False, True), (False, False, False)) == []
    assert acciones((True, False, False), (False, False, True)) == ["enfoca"]


def test_preparacion_no_entrena_y_confirmacion_aislada_por_chat(nucleo, monkeypatch):
    nucleo.chat.modelo = object()
    terminal = nucleo.nucleo_terminal()
    try:
        assert terminal.aprendizaje is nucleo.aprendizaje
        lanzados = []
        monkeypatch.setattr(nucleo.aprendizaje, "_ejecutar", lambda *_: lanzados.append(True))
        cliente = "a" * 24
        assert "Confirma entrenamiento autónomo" in nucleo.conversar(
            "Prepara entrenamiento autónomo", cliente=cliente)["respuesta"]
        assert not lanzados
        assert "Prepara primero" in terminal.conversar(
            "Confirma entrenamiento autónomo", cliente="b" * 24)["respuesta"]
        nucleo.agente.permisos_concedidos.discard("WRITE")
        with pytest.raises(PermissionError):
            nucleo.conversar("Confirma entrenamiento autónomo", cliente=cliente)
        assert not lanzados
        nucleo.agente.permisos_concedidos.add("WRITE")
        assert "cancelado" in nucleo.conversar("Cancela entrenamiento autónomo", cliente=cliente)["respuesta"]
        assert not lanzados
    finally:
        terminal.ejecutor.shutdown()
