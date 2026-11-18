"""Pruebas offline de consulta privada, sin red."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.consulta_exploracion import consultar, respuesta_documental
from exploracion_autonoma import explorar_local


class ConsultaAutonomaTest(unittest.TestCase):
    def test_recupera_fuente_y_fragmento(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / "robotica.txt").write_text("Los sensores detectan distancia y movimiento.", encoding="utf-8")
            db = raiz / "indice.sqlite3"
            explorar_local(raiz, db=db)
            respuesta = respuesta_documental("sensores", db=db)
            self.assertIn("sensores", respuesta)
            self.assertIn("robotica.txt", respuesta)
            self.assertIn("no verificada", respuesta)

    def test_sin_indice_y_sin_consulta(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "inexistente.sqlite3"
            self.assertEqual(consultar("sensores", db=db), [])
            self.assertIn("No encontré", respuesta_documental("sensores", db=db))
            self.assertEqual(consultar("de la", db=db), [])


if __name__ == "__main__":
    unittest.main()
