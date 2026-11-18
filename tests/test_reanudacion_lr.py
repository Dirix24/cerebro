"""El calendario de LR debe ser idéntico al reanudar un checkpoint."""
from unittest.mock import patch

import pytest

from trainer_engine import ConfigEntrenamiento, TrainerEngine


def _motor_simulado(total_pasos=6, paso=0):
    motor = TrainerEngine.__new__(TrainerEngine)
    motor.ce = ConfigEntrenamiento(eval_cada=100, total_pasos=total_pasos)
    motor.modelo = type("Modelo", (), {})()
    motor.modelo.perdida_y_gradientes = lambda x, y, entrenando=True: (
        1.0, {"w": __import__("numpy").array([0.1])})
    motor.cargador = type("Lotes", (), {"T": 2, "siguiente": lambda self: (None, None)})()
    motor.optim = type("Opt", (), {"step": lambda self, grads, lr: None})()
    motor.paso = paso
    motor.total_programado = total_pasos
    motor.mejor = None
    motor.historial = []
    motor.mejor_sin_mejora = 0
    motor.evaluar = lambda: {"loss": 1.0, "ppl": 2.0, "bpb": 1.0}
    motor._registrar_mejor = lambda ev: False
    return motor


def test_calendario_igual_en_dos_tramos():
    completos, partidos = [], []
    def capturar(lista):
        return lambda paso, total, *args: (lista.append((paso, total)) or 0.01)
    with patch("trainer_engine.lr_coseno_con_calentamiento", side_effect=capturar(completos)):
        _motor_simulado().entrenar(6, log=None)
    motor = _motor_simulado()
    with patch("trainer_engine.lr_coseno_con_calentamiento", side_effect=capturar(partidos)):
        motor.entrenar(3, log=None)
        motor.entrenar(3, log=None)
    assert partidos == completos == [(i, 6) for i in range(6)]


def test_no_extender_horizonte_silenciosamente():
    motor = _motor_simulado(total_pasos=3, paso=2)
    with pytest.raises(ValueError, match="excede total_pasos"):
        motor.entrenar(2, log=None)
