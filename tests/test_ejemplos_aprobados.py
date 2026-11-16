import ast
import tempfile
import unittest
from pathlib import Path

from core.ejemplos_aprobados import aprobar, listar


class TestEjemplosAprobados(unittest.TestCase):
    def test_aprobacion_explicita(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "ejemplos.jsonl"
            self.assertEqual(listar(ruta), [])
            aprobar(ruta, "¿Qué es la Luna?", "Un satélite natural.")
            datos = listar(ruta)
            self.assertEqual(len(datos), 1)
            self.assertTrue(datos[0]["aprobado"])
            self.assertEqual(datos[0]["respuesta"], "Un satélite natural.")

    def test_limites(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "ejemplos.jsonl"
            with self.assertRaises(ValueError):
                aprobar(ruta, "", "respuesta")
            with self.assertRaises(ValueError):
                aprobar(ruta, "pregunta", "x" * 2001)
            with self.assertRaises(ValueError):
                listar(ruta, limite=101)

    def test_codigo_chat(self):
        raiz = Path(__file__).resolve().parents[1]
        ast.parse((raiz / "chat.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
