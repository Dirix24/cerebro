import unittest
from core.repaso_local import detectar_duplicados, generar_preguntas


class TestRepasoLocal(unittest.TestCase):
    def test_duplicados(self):
        pares = detectar_duplicados(["La Luna es blanca", "la luna es blanca", "Marte rojo"])
        self.assertEqual([(p["primero"], p["segundo"]) for p in pares], [(0, 1)])

    def test_preguntas(self):
        preguntas = generar_preguntas("La Luna es un satélite. Marte es un planeta.")
        self.assertEqual(len(preguntas), 2)
        self.assertEqual(preguntas[0]["respuesta"], "un satélite")

    def test_limites(self):
        with self.assertRaises(ValueError):
            detectar_duplicados(["texto"] * 101)
        with self.assertRaises(ValueError):
            generar_preguntas("a es b", limite=0)


if __name__ == "__main__":
    unittest.main()
