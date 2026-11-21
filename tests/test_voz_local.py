import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core import local_voice
from universe import lanzador
from universe.consultas import destino_desktop


def test_transcripcion_acumula_segmentos_y_final(monkeypatch):
    clasificador = Mock()
    clasificador.AcceptWaveform.side_effect = [True, False]
    clasificador.Result.return_value = json.dumps({"text": "abre"})
    clasificador.FinalResult.return_value = json.dumps({"text": "youtube"})
    monkeypatch.setitem(__import__("sys").modules, "vosk",
                        SimpleNamespace(KaldiRecognizer=lambda *_args: clasificador))
    assert local_voice.transcribir_pcm(b"\x00" * 9000, modelo=object()) == "abre youtube"
    assert clasificador.AcceptWaveform.call_count == 2
    with pytest.raises(ValueError):
        local_voice.transcribir_pcm(b"\x00", modelo=object())


@pytest.mark.parametrize("texto, destino", [
    ("Cerebro, ábreme YouTube.", "youtube"),
    ("abre youtube", "youtube"),
    ("Cerebro abre mi navegador web", "navegador"),
    ("Abre https://example.org", None),
    ("Abre YouTube y descarga el archivo", None),
])
def test_voz_y_texto_comparten_intenciones(texto, destino):
    assert destino_desktop(texto) == destino


def test_destinos_de_escritorio_son_fijos(monkeypatch):
    abrir = Mock(return_value=True)
    monkeypatch.setattr(lanzador, "abrir_web", abrir)
    monkeypatch.setattr(lanzador, "_hay_escritorio", lambda: True)
    assert lanzador.lanzar_destino("youtube")
    abrir.assert_called_once_with("https://www.youtube.com/")
    assert not lanzador.lanzar_destino("https://example.org")
    abrir.assert_called_once()
