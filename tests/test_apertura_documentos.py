from pathlib import Path

import pytest

import config
from core import aplicaciones_linux
from universe.nucleo import Nucleo


@pytest.fixture
def nucleo(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    (tmp_path / "Documentos").mkdir()
    servicio = Nucleo("local", documentos_usuario=True)
    yield servicio
    servicio.ejecutor.shutdown()


def test_apertura_confirmada_reinicio_y_olvido(nucleo, monkeypatch, tmp_path):
    documentos = tmp_path / "Documentos"
    for nombre in ("Matemáticas anterior.txt", "Matemáticas actual.txt"):
        (documentos / nombre).touch()
    solicitados = []
    def abrir(ruta):
        solicitados.append(ruta.name)
        return {"aceptado": True, "formato": "text/plain", "aplicacion": "Editor de prueba"}
    monkeypatch.setattr(aplicaciones_linux, "abrir_documento", abrir)
    cliente = "a" * 24
    def conversar(pregunta, id_cliente=cliente):
        return nucleo.conversar(pregunta, modo="escritorio", cliente=id_cliente)["respuesta"]

    assert "varios" in conversar("Cerebro, habre mi documento de matemáticas")
    conversar("1", "b" * 24)
    assert solicitados == []
    assert "aceptó" in conversar("Opción 1")
    assert solicitados == ["Matemáticas actual.txt"]
    assert not Path(config.MEMORY_FILE).exists()
    assert "Recordaré" in conversar("Sí, recuérdalo")
    nodo = next(n for n in nucleo.nodos()["nodos"] if n["id"].startswith("documento:"))
    assert "Editor de prueba" in nodo["detalle"]
    assert "Matemáticas" not in str(nodo)
    banco = tmp_path / "data" / "ejemplos_aprobados.jsonl"
    assert not banco.exists()
    assert "aprobado" in conversar("Aprueba ejemplo de apertura")
    assert "documento de prueba" in banco.read_text()
    assert "Matemáticas" not in banco.read_text()

    reiniciado = Nucleo("local", documentos_usuario=True)
    try:
        assert "aceptó" in reiniciado.conversar("Abre el documento de matemáticas otra vez", modo="chat")["respuesta"]
        assert solicitados == ["Matemáticas actual.txt"] * 2
        reiniciado.agente.permisos_concedidos.discard("READ")
        with pytest.raises(PermissionError):
            reiniciado.conversar("Abre el documento de matemáticas", modo="terminal")
        assert "Olvidé" in reiniciado.conversar("Olvida el documento de matemáticas", modo="studio")["respuesta"]
        reiniciado.agente.permisos_concedidos.add("READ")
        assert "varios" in reiniciado.conversar("Abre mi documento de matemáticas")["respuesta"]
    finally:
        reiniciado.ejecutor.shutdown()


def test_apertura_fallida_y_enlace_fuera_del_ambito(nucleo, monkeypatch, tmp_path):
    documento = tmp_path / "Documentos" / "cuentas.txt"
    documento.touch()
    monkeypatch.setattr(aplicaciones_linux, "abrir_documento",
                        lambda _: {"aceptado": False, "formato": "text/plain", "aplicacion": None})
    assert "aplicación predeterminada" in nucleo.conversar("Abre el documento cuentas")["respuesta"]
    nucleo.conversar("Sí, recuérdalo")
    assert not Path(config.MEMORY_FILE).exists()
    documento.unlink()
    fuera = tmp_path / "fuera.txt"
    fuera.touch()
    documento.symlink_to(fuera)
    assert "No encontré" in nucleo.conversar("Abre el documento cuentas")["respuesta"]


def test_catalogo_y_borrado_de_historial(nucleo, monkeypatch):
    monkeypatch.setattr(aplicaciones_linux, "listar",
                        lambda: [{"nombre": "Editor detectado", "formatos": ["text/plain"]}])
    assert "Editor detectado" in nucleo.conversar("¿Qué aplicaciones tengo instaladas?")["respuesta"]
    nucleo._registrar_turno("Hola", "Hola, ¿cómo estás?")
    with pytest.raises(ValueError):
        nucleo.borrar_historial("true")
    assert len(nucleo.historial()["turnos"]) == 2
    nucleo.memoria.agregar_contexto("usuario", "Hola")
    assert nucleo.borrar_historial(True) == {"turnos": []}
    assert nucleo.historial()["turnos"] == []
    assert nucleo.memoria.short_term_context == []
    nucleo.solo_lectura = True
    with pytest.raises(PermissionError):
        nucleo.borrar_historial(True)
