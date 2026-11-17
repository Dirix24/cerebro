"""Pruebas de evolución segura y selección explicable."""
import math
import tempfile
import unittest
from pathlib import Path

from agent.orquestador import explicar_seleccion
from core.errores_aprendizaje import registrar, pendientes
from core.puerta_checkpoint import aceptar_checkpoint


class TestEvolucionSegura(unittest.TestCase):
    def test_puerta_calidad(self):
        self.assertTrue(aceptar_checkpoint(2.0, 1.9))
        self.assertTrue(aceptar_checkpoint(2.0, 2.03))
        self.assertFalse(aceptar_checkpoint(2.0, 2.1))
        self.assertFalse(aceptar_checkpoint(2.0, float("nan")))
        self.assertFalse(aceptar_checkpoint(None, None))
        self.assertFalse(aceptar_checkpoint(2.0, math.inf))

    def test_errores_sin_aprobacion_automatica(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "errores.jsonl"
            registrar(ruta, "¿Qué es Marte?", "Un planeta")
            registros = pendientes(ruta)
            self.assertEqual(len(registros), 1)
            self.assertEqual(registros[0]["estado"], "pendiente_revision")

    def test_ruteo_explicable(self):
        self.assertEqual(explicar_seleccion("Busca en corpus: Marte")["motor"], "busqueda_local")
        self.assertEqual(explicar_seleccion("¿Qué es Marte?")["motor"], "conocimiento")
        self.assertTrue(explicar_seleccion("/escribir prueba.txt hola")["requiere_confirmacion_para_escritura"])


if __name__ == "__main__":
    unittest.main()
