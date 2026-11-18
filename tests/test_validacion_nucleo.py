"""Regresiones para la validación y configuración del entrenamiento."""
import unittest
from types import SimpleNamespace

from trainer_engine import ConfigEntrenamiento, TrainerEngine, precision_de_respuestas


class TestValidacionNucleo(unittest.TestCase):
    def test_ignora_dialogos_sin_respuesta_cerebro(self):
        modelo = SimpleNamespace()
        resultado = precision_de_respuestas(
            modelo, ["usuario: hola\notro: respuesta equivocada"])
        self.assertEqual(resultado["n"], 0)
        self.assertEqual(resultado["exactas"], 0.0)

    def test_eval_cada_cero_da_error_claro(self):
        motor = TrainerEngine.__new__(TrainerEngine)
        motor.ce = ConfigEntrenamiento(eval_cada=0)
        motor.modelo = SimpleNamespace()
        motor.cargador = SimpleNamespace(T=8)
        with self.assertRaisesRegex(ValueError, "eval_cada"):
            motor.entrenar(1, log=None)

    def test_acumulacion_cero_da_error_claro(self):
        motor = TrainerEngine.__new__(TrainerEngine)
        motor.ce = ConfigEntrenamiento(acumulacion_gradientes=0)
        motor.modelo = SimpleNamespace()
        motor.cargador = SimpleNamespace(T=8)
        with self.assertRaisesRegex(ValueError, "acumulacion_gradientes"):
            motor.entrenar(1, log=None)


if __name__ == "__main__":
    unittest.main()
