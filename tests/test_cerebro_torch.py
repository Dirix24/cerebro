"""Pruebas del motor neuronal propio PyTorch (opcional)."""
import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import cerebro_torch


def test_perfiles_grandes_disponibles():
    for nombre in ("grande", "experto"):
        p = config.PERFILES[nombre]
        assert p["dim"] % p["n_heads"] == 0
        assert p["n_layers"] >= config.PERFILES["pequeno"]["n_layers"]


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="PyTorch opcional")
def test_torch_forward_y_entrenamiento_minimo(tmp_path):
    import torch
    modelo = cerebro_torch.construir_modelo("diminuto", 260)
    x = torch.tensor([[3, 4, 5]])
    logits = modelo(x)
    assert logits.shape == (1, 3, 260)
    assert torch.isfinite(logits).all()
    corpus = tmp_path / "texto.txt"
    corpus.write_text(("Hola cerebro. Estoy aprendiendo.\n" * 20), encoding="utf-8")
    destino = tmp_path / "propio.pt"
    guardado, n = cerebro_torch.entrenar(corpus, "diminuto", pasos=1, batch=1,
                                        salida=destino, dispositivo="cpu")
    assert guardado == destino
    assert n > 0
    assert destino.is_file()
    assert isinstance(cerebro_torch.generar(destino, "Hola", max_tokens=2), str)


def test_entrenamiento_sin_corpus_falla():
    with pytest.raises(SystemExit) as exc:
        cerebro_torch.main(["--pasos", "1"])
    assert exc.value.code == 2
