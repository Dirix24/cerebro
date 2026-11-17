"""Pruebas de memoria local sin servicios externos."""
import tempfile
from pathlib import Path
import unittest
from core.conocimiento import guardar, buscar, respuesta_exacta, _clave


class TestConocimiento(unittest.TestCase):
    def test_guarda_fuentes_y_busca(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "datos.sqlite"
            self.assertEqual(guardar("¿Qué es la Luna?", "Un satélite natural.", "fuente-a", db), [])
            resultados = buscar("Luna satélite", ruta=db)
            self.assertEqual(resultados[0]["fuente"], "fuente-a")

    def test_no_devuelve_articulos_ajenos_a_la_consulta(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "datos.sqlite"
            guardar("¿Qué es Piotr Juszczak?", "Deportista polaco.", "wiki-a", db)
            guardar("¿Qué es Eupithecia muralla?", "Polilla de Ecuador.", "wiki-b", db)
            self.assertEqual(buscar("Luna", ruta=db), [])
            guardar("¿Qué es la Luna?", "Satélite natural.", "wiki-luna", db)
            self.assertEqual(buscar("Luna", ruta=db)[0]["fuente"], "wiki-luna")

    def test_respuesta_exacta_y_conflictos(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "datos.sqlite"
            self.assertIsNone(respuesta_exacta("¿Qué es la Luna?", db))
            guardar("¿Qué es la Luna?", "Satélite natural.", "fuente-a", db)
            self.assertEqual(respuesta_exacta("que es la luna", db)["fuente"], "fuente-a")
            guardar("¿Qué es la Luna?", "Un planeta.", "fuente-b", db)
            self.assertIsNone(respuesta_exacta("¿Qué es la Luna?", db))

    def test_normalizacion_sin_confundir_enye(self):
        self.assertEqual(_clave("¿Qué es la Luna?"), _clave("que es la luna"))
        self.assertNotEqual(_clave("año"), _clave("ano"))

    def test_alerta_de_negacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "datos.sqlite"
            guardar("¿Es seguro?", "Sí, es seguro.", "fuente-a", db)
            alertas = guardar("¿Es seguro?", "No, no es seguro.", "fuente-b", db)
            self.assertTrue(alertas)


if __name__ == "__main__":
    unittest.main()
