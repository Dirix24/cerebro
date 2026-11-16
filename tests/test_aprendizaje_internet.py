"""Pruebas sin red ni entrenamiento costoso del aprendizaje diario."""
import unittest
from aprendizaje_internet import documento, obtener_paginas


class TestAprendizajeInternet(unittest.TestCase):
    def test_formato_compatible_con_entrenador(self):
        p = {"titulo": "La Luna", "texto": "La Luna es un satélite natural."}
        d = documento(p)
        self.assertTrue(d.startswith("usuario: ¿Qué es La Luna?\ncerebro: "))
        self.assertTrue(d.endswith("\n\n"))

    def test_sanitiza_saltos(self):
        p = {"titulo": "Un\ntítulo", "texto": "Primera línea\nsegunda línea"}
        d = documento(p)
        self.assertEqual(d.count("\ncerebro:"), 1)
        self.assertIn("Primera línea segunda línea", d)


if __name__ == "__main__":
    unittest.main()
