"""Pruebas rápidas del entrenador guiado sin entrenar ni descargar modelos."""
import unittest
from unittest.mock import patch

from entrenamiento_guiado import decidir_aceptacion, entrenar_guiado


class TestEntrenamientoGuiado(unittest.TestCase):
    def test_acepta_mejora(self):
        self.assertTrue(decidir_aceptacion(1.0, 0.9))

    def test_rechaza_regresion(self):
        self.assertFalse(decidir_aceptacion(1.0, 1.1))

    def test_rechaza_resultado_ausente(self):
        self.assertFalse(decidir_aceptacion(1.0, None))

    def test_tolerancia(self):
        self.assertTrue(decidir_aceptacion(1.0, 1.01))
        self.assertFalse(decidir_aceptacion(1.0, 1.03))

    def test_limites_sin_tocar_checkpoints(self):
        with self.assertRaises(ValueError):
            entrenar_guiado(0, 0.0003)
        with self.assertRaises(ValueError):
            entrenar_guiado(100, 0.1)


if __name__ == "__main__":
    unittest.main()
