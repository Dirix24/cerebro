"""Pruebas de repaso y protección del portátil."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from core.repaso_espaciado import anadir, pendientes, calificar, cargar
from core.recursos_portatil import bateria_baja


class TestRepaso(unittest.TestCase):
    def test_progreso_y_reprogramacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "repaso.json"
            anadir(ruta, "¿Qué es la Luna?", "Un satélite natural")
            self.assertEqual(len(pendientes(ruta)), 1)
            calificar(ruta, "¿Qué es la Luna?", True)
            self.assertEqual(pendientes(ruta), [])
            self.assertEqual(cargar(ruta)[0]["fecha"], (date.today() + timedelta(days=1)).isoformat())
            calificar(ruta, "¿Qué es la Luna?", False)
            self.assertEqual(cargar(ruta)[0]["aciertos"], 0)

    def test_duplicados_rechazados(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "repaso.json"
            anadir(ruta, "Luna", "Satélite")
            with self.assertRaises(ValueError):
                anadir(ruta, "luna", "Planeta")


class TestRecursos(unittest.TestCase):
    def test_bateria_baja(self):
        with tempfile.TemporaryDirectory() as tmp:
            bat = Path(tmp) / "BAT0"
            bat.mkdir()
            (bat / "status").write_text("Discharging")
            (bat / "capacity").write_text("15")
            self.assertTrue(bateria_baja(Path(tmp)))
            (bat / "status").write_text("Charging")
            self.assertFalse(bateria_baja(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
