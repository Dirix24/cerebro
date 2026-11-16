import tempfile
import unittest
from pathlib import Path

from core.ejemplos_aprobados import aprobar
from entrenar_ejemplos_aprobados import preparar


class TestExportarEjemplos(unittest.TestCase):
    def test_vista_previa_y_exportacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            origen = Path(tmp) / "aprobados.jsonl"
            destino = Path(tmp) / "corpus" / "ejemplos.txt"
            aprobar(origen, "¿Qué es la Luna?", "Un satélite.")
            aprobar(origen, "¿Qué es la Luna?", "Un satélite.")
            vista = preparar(origen, destino)
            self.assertEqual(vista["ejemplos"], 1)
            self.assertFalse(destino.exists())
            resultado = preparar(origen, destino, aplicar=True)
            self.assertTrue(resultado["escrito"])
            self.assertIn("cerebro: Un satélite.", destino.read_text(encoding="utf-8"))

    def test_rechaza_banco_invalido(self):
        with tempfile.TemporaryDirectory() as tmp:
            origen = Path(tmp) / "aprobados.jsonl"
            origen.write_text("no es json\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                preparar(origen, Path(tmp) / "salida.txt")


if __name__ == "__main__":
    unittest.main()
