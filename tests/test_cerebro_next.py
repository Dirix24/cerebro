import json
from datetime import datetime, timezone

import pytest

import config
from core.generacion_proyecto import validar
from core.recordatorios_locales import interpretar
from universe.nucleo import Nucleo
from tests.modelo_fixture import ModeloDePrueba


@pytest.mark.parametrize("nombre", ["../fuera.py", "/tmp/fuera.py", ".git", "dir/sub.py", "archivo.exe"])
def test_validador_rechaza_nombres_externos(nombre):
    with pytest.raises(ValueError):
        validar(json.dumps({"archivos": [{"nombre": nombre, "texto": "pass"}]}))


@pytest.fixture
def nucleo(tmp_path, monkeypatch):
    datos = tmp_path / "datos"
    datos.mkdir()
    monkeypatch.setattr(config, "raiz_datos", lambda: str(datos))
    monkeypatch.setattr(config, "MEMORY_FILE", str(datos / "memoria.json"))
    motor = Nucleo("local", profesor=ModeloDePrueba())
    try:
        yield motor
    finally:
        motor.ejecutor.shutdown()


def test_propuesta_y_publicacion_sin_reemplazar(nucleo, tmp_path):
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    cliente = "a" * 24

    def operar(accion, **datos):
        return nucleo.operar_proyecto({"accion": accion, "cliente": cliente,
                                      "carpeta_esperada": str(raiz), **datos})

    operar("abrir", carpeta=str(raiz), confirmar=True)
    salida = nucleo.conversar("Haz una calculadora", "studio", cliente)
    propuesta = salida["generacion"]
    assert "+def sumar" in propuesta["diff"] and not list(raiz.iterdir())
    with pytest.raises(PermissionError):
        operar("publicar_generado", id=propuesta["id"], nombre="calculadora")
    (raiz / "ocupado").mkdir()
    with pytest.raises(ValueError, match="ya existe"):
        operar("publicar_generado", id=propuesta["id"], nombre="ocupado", confirmar=True)
    assert list(raiz.iterdir()) == [raiz / "ocupado"]
    publicado = operar("publicar_generado", id=propuesta["id"], nombre="calculadora", confirmar=True)
    assert len(publicado["archivos"]) == 2
    assert (raiz / "calculadora" / "calculadora.py").is_file()
    with pytest.raises(ValueError, match="caducó"):
        operar("publicar_generado", id=propuesta["id"], nombre="duplicado", confirmar=True)
    assert "estilo.css" in nucleo.conversar("Diseña una web", "studio", cliente)["generacion"]["archivos"]


def test_documento_modelo_y_conteo(nucleo, tmp_path, monkeypatch):
    cliente = "c" * 24
    (tmp_path / "guia.txt").write_text("La energía solar produce electricidad.")
    nucleo.operar_proyecto({"accion": "abrir", "cliente": cliente, "carpeta": str(tmp_path), "confirmar": True})
    resultado = nucleo.conversar("Según el documento, ¿qué dice sobre energía solar?", "studio", cliente,
                               {"nombre": "guia.txt", "carpeta": str(tmp_path)})
    assert "guia.txt · La energía solar" in resultado["respuesta"]
    assert "Interpretación del modelo local" in resultado["respuesta"]
    monkeypatch.setattr("core.aplicaciones_linux.listar", lambda: [{"id": "uno"}, {"id": "uno"}, {"id": "dos"}])
    assert nucleo.conversar("Cuántos programas tengo instalados")["aplicaciones_visibles"] == 2


def test_lunes_por_la_tarde():
    fecha, tarea = interpretar("Recuérdame el lunes por la tarde que tengo examen",
                               datetime(2026, 11, 22, 10, tzinfo=timezone.utc))
    assert fecha == "2026-11-23T17:00:00+00:00"
    assert tarea == "tengo examen"


def test_modelo_visual_envia_imagen_solo_a_loopback(monkeypatch):
    from unittest.mock import MagicMock
    from core.profesor_local import ProfesorLocal

    conexion = MagicMock()
    respuesta = conexion.getresponse.return_value.__enter__.return_value
    respuesta.status = 200
    respuesta.read.return_value = b'{"message":{"content":"Descripcion"}}'
    abrir = MagicMock(return_value=conexion)
    monkeypatch.setattr("core.profesor_local.HTTPConnection", abrir)
    motor = ProfesorLocal(11434, ollama="vision:local")
    assert motor.describir_imagen("AAAA") == "Descripcion"
    abrir.assert_called_once_with("127.0.0.1", 11434, timeout=40)
    metodo, ruta, carga, _ = conexion.request.call_args.args
    assert (metodo, ruta) == ("POST", "/api/chat")
    assert json.loads(carga)["messages"][-1]["images"] == ["AAAA"]
