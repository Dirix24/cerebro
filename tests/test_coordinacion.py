"""Pruebas de coordinación, autoevaluación y protección de recursos."""
import tempfile
import unittest
from pathlib import Path

from agent.orquestador import seleccionar
from core.autoevaluacion import evaluar_respuesta, ejecutar
from core.repaso_espaciado import anadir
from core.recursos_portatil import motivos_pausa


class TestCoordinacion(unittest.TestCase):
    def test_rutas(self):
        self.assertEqual(seleccionar("¿Qué es la Luna?"), "conocimiento")
        self.assertEqual(seleccionar("Busca en corpus: Luna"), "busqueda_local")
        self.assertEqual(seleccionar("hola"), "modelo")
        self.assertEqual(seleccionar("/escribir prueba.txt hola"), "comando")

    def test_evaluacion_no_autovalida_respuestas_parecidas(self):
        self.assertTrue(evaluar_respuesta("Satélite natural.", "satelite natural"))
        self.assertFalse(evaluar_respuesta("Creo que es un planeta", "satélite natural"))
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "fichas.json"
            anadir(ruta, "¿Qué es la Luna?", "Satélite natural")
            resultados = ejecutar(ruta, lambda _: "Satélite natural")
            self.assertTrue(resultados[0]["correcto"])

    def test_restricciones_recursos(self):
        self.assertEqual(motivos_pausa(bateria=False, memoria=4096, temperatura=55), [])
        self.assertEqual(len(motivos_pausa(bateria=True, memoria=100, temperatura=90)), 3)


if __name__ == "__main__":
    unittest.main()
