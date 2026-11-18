"""Regresiones de búsqueda y resiliencia de Internet, sin conexión real."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from core.local_search import buscar
import aprendizaje_internet as internet


class MejorasTest(unittest.TestCase):
    def test_busqueda_prioriza_ambos_terminos(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "indice.sqlite3"
            with sqlite3.connect(db) as con:
                con.execute("CREATE VIRTUAL TABLE corpus USING fts5(texto, origen UNINDEXED)")
                con.executemany("INSERT INTO corpus(texto, origen) VALUES (?, ?)", [
                    ("inteligencia del gato", "gato.txt"),
                    ("inteligencia artificial es un campo", "ia.txt"),
                    ("artificial no basta", "otro.txt")])
            filas = buscar("inteligencia artificial", db=db)
            self.assertEqual(len(filas), 1)
            self.assertEqual(filas[0][1], "ia.txt")

    def test_busqueda_fallback_or(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "indice.sqlite3"
            with sqlite3.connect(db) as con:
                con.execute("CREATE VIRTUAL TABLE corpus USING fts5(texto, origen UNINDEXED)")
                con.execute("INSERT INTO corpus(texto, origen) VALUES (?, ?)", ("robot", "robot.txt"))
            self.assertEqual(buscar("robot humanoide", db=db)[0][1], "robot.txt")

    def test_no_reintenta_403(self):
        exc = HTTPError("https://es.wikipedia.org/w/api.php", 403, "Forbidden", {}, None)
        with patch.object(internet, "urlopen", side_effect=exc) as abrir:
            with self.assertRaises(HTTPError):
                internet.abrir_api(object())
        self.assertEqual(abrir.call_count, 1)

    def test_reintenta_fallo_transitorio(self):
        with patch.object(internet, "urlopen", side_effect=[URLError("temporal"), object()]) as abrir:
            with patch.object(internet.time, "sleep"):
                respuesta = internet.abrir_api(object())
        self.assertIsNotNone(respuesta)
        self.assertEqual(abrir.call_count, 2)


if __name__ == "__main__":
    unittest.main()
