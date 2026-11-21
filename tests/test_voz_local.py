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


def test_steam_flatpak_usa_identificador_fijo(monkeypatch):
    import subprocess

    monkeypatch.setattr(lanzador, "_hay_escritorio", lambda: True)
    monkeypatch.setattr(lanzador, "which", lambda nombre: "/usr/bin/flatpak" if nombre == "flatpak" else None)
    comprobacion = Mock(return_value=SimpleNamespace(returncode=0))
    ejecutar = Mock(return_value=True)
    monkeypatch.setattr(subprocess, "run", comprobacion)
    monkeypatch.setattr(lanzador, "_lanzar_proceso", ejecutar)
    assert destino_desktop("Cerebro, abre esteam") == "steam"
    assert lanzador.lanzar_destino("steam")
    assert comprobacion.call_args.args[0] == ["/usr/bin/flatpak", "info", "com.valvesoftware.Steam"]
    ejecutar.assert_called_once_with(["/usr/bin/flatpak", "run", "com.valvesoftware.Steam"])


def test_dispositivos_detecta_microfono_sin_capturar_monitor(monkeypatch):
    import shutil
    import subprocess
    monkeypatch.setattr(shutil, "which", lambda nombre: nombre)
    respuestas = {
        ("pactl", "list", "short", "sources"): "0\tcap.monitor\tcontrol\n1\tmicro-usb\tdriver\n",
        ("pactl", "list", "short", "sinks"): "0\taltavoz-usb\tdriver\n",
        ("arecord", "-L"): "null\n    Silencio\nhw:CARD=Mic,DEV=0\n",
    }
    monkeypatch.setattr(subprocess, "run", lambda args, **_kw: SimpleNamespace(stdout=respuestas[tuple(args)]))
    assert local_voice.dispositivos_audio() == {
        "entradas": ["default", "pulse:micro-usb", "hw:CARD=Mic,DEV=0"], "salidas": ["altavoz-usb"],
    }


def test_lectura_cancela_proceso_activo(monkeypatch):
    import shutil
    import subprocess
    from threading import Event

    cancelar = Event()
    proceso = Mock()
    proceso.__enter__ = Mock(return_value=proceso)
    proceso.__exit__ = Mock(return_value=False)

    def agotado(**datos):
        cancelar.set()
        raise subprocess.TimeoutExpired("espeak", datos["timeout"])

    proceso.communicate.side_effect = agotado
    monkeypatch.setattr(shutil, "which", lambda nombre: nombre)
    monkeypatch.setattr(subprocess, "Popen", Mock(return_value=proceso))
    local_voice.leer_en_espanol("Una respuesta.", cancelar)
    proceso.terminate.assert_called_once()
