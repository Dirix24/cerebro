"""Pruebas de métricas sin usar modelo real ni red."""
import json
import tempfile
import unittest
from pathlib import Path

from core.medicion_progreso import medir
from core.repaso_espaciado import anadir


class TestMedicionProgreso(unittest.TestCase):
    def test_mediciones_y_variacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            fichas = Path(tmp) / "fichas.json"
            historial = Path(tmp) / "historial.jsonl"
            anadir(fichas, "Capital de Francia", "París")
            primero = medir(fichas, lambda _: "Madrid", historial)
            self.assertEqual(primero["precision"], 0)
            self.assertIsNone(primero["variacion"])
            segundo = medir(fichas, lambda _: "París", historial)
            self.assertEqual(segundo["precision"], 1)
            self.assertEqual(segundo["variacion"], 1)
            lineas = historial.read_text().splitlines()
            self.assertEqual(len(lineas), 2)
            self.assertEqual(json.loads(lineas[-1])["aciertos"], 1)

    def test_sin_fichas_no_crea_historial(self):
        with tempfile.TemporaryDirectory() as tmp:
            historial = Path(tmp) / "historial.jsonl"
            resumen = medir(Path(tmp) / "nada.json", lambda _: "respuesta", historial)
            self.assertEqual(resumen["evaluadas"], 0)
            self.assertFalse(historial.exists())


if __name__ == "__main__":
    unittest.main()
