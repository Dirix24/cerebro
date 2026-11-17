"""Pruebas de la evolución adaptativa sin red ni entrenamiento real."""
import tempfile
import unittest
from pathlib import Path

from core.evolucion_adaptativa import leer_historial, pasos_adaptativos, registrar


class TestEvolucionAdaptativa(unittest.TestCase):
    def test_sin_historial_mantiene_pasos(self):
        self.assertEqual(pasos_adaptativos(20, []), 20)

    def test_retroceso_reduce_esfuerzo(self):
        self.assertEqual(pasos_adaptativos(20, [{"resultado": "revertido"}]), 10)

    def test_mejoras_sucesivas_aumentan_esfuerzo(self):
        historial = [{"resultado": "aceptado"} for _ in range(3)]
        self.assertEqual(pasos_adaptativos(20, historial), 25)

    def test_limite_de_esfuerzo(self):
        historial = [{"resultado": "aceptado"} for _ in range(5)]
        self.assertEqual(pasos_adaptativos(1000, historial), 1000)

    def test_historial_persistente(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "evolucion.json"
            registrar(ruta, "aceptado", 20, "prueba")
            self.assertEqual(leer_historial(ruta)[0]["pasos"], 20)
            self.assertEqual(leer_historial(ruta)[0]["resultado"], "aceptado")


if __name__ == "__main__":
    unittest.main()
