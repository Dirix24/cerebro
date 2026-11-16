import tempfile
import unittest
from pathlib import Path
from core.historial_local import guardar, consultar


class TestHistorialLocal(unittest.TestCase):
    def test_guardar_y_consultar(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "historial.jsonl"
            self.assertEqual(consultar(ruta), [])
            guardar(ruta, "usuario", "Hola")
            guardar(ruta, "cerebro", "Hola, ¿qué tal?")
            self.assertEqual([x["rol"] for x in consultar(ruta)], ["usuario", "cerebro"])
            self.assertEqual(consultar(ruta, limite=1)[0]["texto"], "Hola, ¿qué tal?")

    def test_limites(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "historial.jsonl"
            with self.assertRaises(ValueError):
                guardar(ruta, "sistema", "instrucción")
            with self.assertRaises(ValueError):
                guardar(ruta, "usuario", "x" * 4001)
            with self.assertRaises(ValueError):
                consultar(ruta, limite=0)

    def test_lineas_corruptas(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "historial.jsonl"
            ruta.write_text('mal json\n{"rol":"usuario","texto":"bien"}\n', encoding="utf-8")
            self.assertEqual(len(consultar(ruta)), 1)


if __name__ == "__main__":
    unittest.main()
