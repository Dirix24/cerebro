"""Pruebas de herramientas educativas sin red ni modelos externos."""
import unittest
from core.herramientas_texto import estadisticas, comparar_textos, fichas_estudio


class TestHerramientasTexto(unittest.TestCase):
    def test_estadisticas(self):
        r = estadisticas("Hola mundo. Hola Luna.")
        self.assertEqual(r["palabras"], 4)
        self.assertEqual(r["palabras_unicas"], 3)
        self.assertEqual(r["frases"], 2)

    def test_comparar(self):
        r = comparar_textos("hola mundo", "hola luna")
        self.assertEqual(r["agregadas"], ["luna"])
        self.assertEqual(r["eliminadas"], ["mundo"])
        self.assertEqual(comparar_textos("igual", "igual")["similitud"], 1.0)

    def test_fichas(self):
        fichas = fichas_estudio("Luna: satélite natural\nMarte: planeta")
        self.assertEqual(len(fichas), 2)
        self.assertEqual(fichas[0]["respuesta"], "satélite natural")

    def test_limites(self):
        with self.assertRaises(ValueError):
            fichas_estudio("x: y", limite=0)
        with self.assertRaises(ValueError):
            comparar_textos("a" * 10001, "b")


if __name__ == "__main__":
    unittest.main()
