"""Pruebas de memoria local sin servicios externos."""
import tempfile
from pathlib import Path
import unittest
from core.conocimiento import guardar, buscar


class TestConocimiento(unittest.TestCase):
    def test_guarda_fuentes_y_busca(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "datos.sqlite"
            self.assertEqual(guardar("¿Qué es la Luna?", "Un satélite natural.", "fuente-a", db), [])
            resultados = buscar("Luna satélite", ruta=db)
            self.assertEqual(resultados[0]["fuente"], "fuente-a")

    def test_alerta_de_negacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "datos.sqlite"
            guardar("¿Es seguro?", "Sí, es seguro.", "fuente-a", db)
            alertas = guardar("¿Es seguro?", "No, no es seguro.", "fuente-b", db)
            self.assertTrue(alertas)


if __name__ == "__main__":
    unittest.main()
