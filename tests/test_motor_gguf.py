"""Pruebas sin dependencia llama.cpp ni pesos GGUF descargados."""
from pathlib import Path
import pytest
from core.motor_gguf import cargar_gguf, responder_gguf


def test_gguf_rechaza_ruta_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        cargar_gguf(tmp_path / "modelo.gguf")


def test_gguf_valida_contexto_antes_de_cargar(tmp_path):
    with pytest.raises(ValueError):
        cargar_gguf(tmp_path / "modelo.gguf", n_ctx=20)


def test_gguf_respuesta_con_motor_falso():
    class Motor:
        def create_chat_completion(self, **kwargs):
            assert kwargs["messages"][0]["role"] == "user"
            return {"choices": [{"message": {"content": " Hola desde Cerebro "}}]}
    assert responder_gguf(Motor(), [{"role": "user", "content": "Hola"}]) == "Hola desde Cerebro"


def test_gguf_no_admite_roles_de_herramientas():
    with pytest.raises(ValueError):
        responder_gguf(object(), [{"role": "tool", "content": "ejecutar"}])
