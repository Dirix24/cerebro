"""Los perfiles ampliados deben instanciar el Transformer NumPy real."""
import numpy as np
import pytest

from core.transformer.optimized_llm import ModeloConfig, OptimizedTransformerLLM
from trainer_engine import config_modelo_desde_perfil


@pytest.mark.parametrize("perfil,esperados", [
    ("v2_6m", 6910464),
    ("v2_16m", 15920896),
])
def test_parametros_de_perfil(perfil, esperados):
    cfg = config_modelo_desde_perfil(perfil)
    import config
    cfg.vocab_size = config.PERFILES[perfil]["vocab_objetivo"]
    # Verificar la arquitectura sin reservar los estados AdamW del entrenamiento.
    d, f, v, b, l = cfg.dim, cfg.dim_ffn, cfg.vocab_size, cfg.block_size, cfg.n_layers
    calculados = v * d + b * d + l * (4 * d * d + 2 * d * f + 9 * d + f) + 2 * d + v
    assert calculados == esperados
    assert cfg.validar() is cfg


def test_nucleo_numpy_ampliado_forward():
    cfg = config_modelo_desde_perfil("v2_6m", vocab_size=64)
    modelo = OptimizedTransformerLLM(cfg, seed=1)
    entrada = np.array([[1, 2, 3]], dtype=np.int64)
    logits = modelo.forward(entrada, entrenando=False)
    assert logits.shape == (1, 3, 64)
    assert np.isfinite(logits).all()
    import config
    assert modelo.n_parametros() == config.estimar_parametros("v2_6m") - (2048 - 64) * (256 + 1)
