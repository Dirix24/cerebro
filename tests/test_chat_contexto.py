"""El chat no debe exceder el contexto al usar perfiles pequeños."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from chat import Conversacion


class TokenizadorFalso:
    def codificar(self, texto):
        return [5] * len(texto)
    def decodificar(self, ids):
        return "respuesta"


def test_prompt_no_desborda_ventana_pequena():
    modelo = SimpleNamespace(tokenizer=TokenizadorFalso(),
                             cfg=SimpleNamespace(block_size=16))
    memoria = SimpleNamespace(short_term_context=[], buscar=lambda *a, **k: {})
    chat = Conversacion(modelo, memoria, agente=None)
    ids = chat._armar_prompt_ids("pregunta muy larga " * 10, max_nuevos=15)
    assert len(ids) <= 1


def test_generacion_reserva_contexto():
    modelo = SimpleNamespace(tokenizer=TokenizadorFalso(),
                             cfg=SimpleNamespace(block_size=16),
                             generar_ids=MagicMock(return_value=([7], None)))
    memoria = SimpleNamespace(short_term_context=[], buscar=lambda *a, **k: {},
                              agregar_contexto=lambda *a: None)
    chat = Conversacion(modelo, memoria, agente=None)
    chat.responder_modelo("hola")
    args, kwargs = modelo.generar_ids.call_args
    assert len(args[0]) + kwargs["max_nuevos"] <= 16
