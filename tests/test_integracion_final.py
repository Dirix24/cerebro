"""Pruebas de integración del índice local y enrutamiento en español."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.intents import detectar_intencion
from core import local_search


class TestIntegracionFinal(unittest.TestCase):
    def test_pregunta_matematica_con_signo_apertura(self):
        plan = detectar_intencion("¿Cuánto es 25 + 17?")
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0]["tool"], "calculator")
        self.assertEqual(plan[0]["arguments"]["expression"], "25 + 17")

    def test_articulos_de_internet_se_indexan(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            archivo = raiz / "data" / "aprendizaje_internet" / "corpus_diario.txt"
            archivo.parent.mkdir(parents=True)
            archivo.write_text("usuario: ¿Qué es la Luna?\ncerebro: Satélite natural.\n\n",
                               encoding="utf-8")
            db = raiz / "indice.sqlite3"
            with patch.object(local_search.config, "_RAIZ", str(raiz)), \
                 patch.object(local_search.config, "CORPUS_FILE", str(raiz / "no.txt")), \
                 patch.object(local_search.config, "CORPUS_DIR", str(raiz / "no")):
                self.assertEqual(local_search.indexar(db), 1)
                self.assertTrue(local_search.buscar("Luna", db=db))
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM corpus").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
