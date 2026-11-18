"""Pruebas sin red del recuperador de definiciones locales."""
import unittest
from core.respuestas_con_fuentes import concepto_definicion, responder_definicion


class DefinicionesConFuentesTest(unittest.TestCase):
    def test_ia_alias(self):
        self.assertEqual(concepto_definicion("¿Qué es una IA?"), "inteligencia artificial")

    def test_fuente_del_corpus(self):
        doc = ("usuario: ¿Qué es la inteligencia artificial?\n"
               "cerebro: Campo que permite realizar tareas inteligentes.\n")
        buscar = lambda consulta, limite: [(doc, "corpus.txt")]
        resultado = responder_definicion("que es una ia", buscador=buscar, buscar_hechos=lambda _: None)
        self.assertEqual(resultado, ("Campo que permite realizar tareas inteligentes.", "corpus.txt"))

    def test_no_confunde_palabras_con_evidencia(self):
        doc = "usuario: ¿Qué es un ordenador?\ncerebro: Tiene inteligencia artificial.\n"
        buscar = lambda consulta, limite: [(doc, "corpus.txt")]
        self.assertIsNone(responder_definicion("¿Qué es una IA?", buscador=buscar,
                                              buscar_hechos=lambda _: None))

    def test_desconocido_no_inventa(self):
        self.assertIsNone(responder_definicion("¿Qué es Roblox?", buscador=lambda *a, **k: [],
                                              buscar_hechos=lambda _: None))


if __name__ == "__main__":
    unittest.main()
