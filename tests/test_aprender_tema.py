"""Aprendizaje dirigido sin red y sin modificar checkpoints."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aprendizaje_internet as ai


class AprenderTemaTest(unittest.TestCase):
    def test_tema_rechaza_titulo_invalido(self):
        with self.assertRaises(ValueError):
            ai.obtener_tema("x")

    def test_tema_consulta_api_con_titulo(self):
        class Respuesta:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, *args):
                return json.dumps({"query": {"pages": [{
                    "pageid": 123, "title": "Robótica",
                    "fullurl": "https://es.wikipedia.org/wiki/Rob%C3%B3tica",
                    "extract": "Una explicación " * 15
                }]}}).encode("utf-8")
        with patch.object(ai, "urlopen", return_value=Respuesta()) as abrir:
            pagina = ai.obtener_tema("Robótica")
        self.assertEqual(pagina["titulo"], "Robótica")
        self.assertIn("titles=Rob", abrir.call_args.args[0].full_url)

    def test_tema_duplicado_no_reescribe(self):
        with tempfile.TemporaryDirectory() as d:
            carpeta = Path(d)
            fuentes = carpeta / "fuentes.jsonl"
            fuentes.write_text('{"id": 123}\n', encoding="utf-8")
            pagina = {"id": 123, "titulo": "Robótica",
                      "url": "https://es.wikipedia.org/wiki/Rob%C3%B3tica",
                      "texto": "Definición"}
            with patch.object(ai, "FUENTES", fuentes), patch.object(ai, "obtener_tema", return_value=pagina):
                self.assertEqual(ai.aprender_tema("Robótica", 100000), 0)


if __name__ == "__main__":
    unittest.main()
