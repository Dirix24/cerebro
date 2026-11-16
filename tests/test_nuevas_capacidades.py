import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.semantic_memory import buscar_similares
from core.code_tools import analizar_python
from core.local_voice import grabar_wav
import pytest


def test_memoria_similitud():
    docs = ["programar con python", "cocinar una tortilla"]
    assert buscar_similares("programacion python", docs)[0][0] == 0
    assert buscar_similares("", docs) == []


def test_analizador_seguro(tmp_path):
    (tmp_path / "a.py").write_text("import os\nclass X: pass\ndef hola(): return 1\n")
    info = analizar_python("a.py", raiz=tmp_path)
    assert info["funciones"] == ["hola"]
    assert info["clases"] == ["X"]
    with pytest.raises(ValueError):
        analizar_python("../fuera.py", raiz=tmp_path)


def test_voz_limites():
    with pytest.raises(ValueError):
        grabar_wav("audio.wav", 31)


def test_arquitectura_avanzada():
    torch = pytest.importorskip("torch")
    from core.advanced_torch import construir_modelo_avanzado
    modelo = construir_modelo_avanzado("diminuto", 260)
    x = torch.tensor([[3, 4, 5]])
    assert modelo(x).shape == (1, 3, 260)
    assert torch.isfinite(modelo(x)).all()
