import tempfile
import unittest
from pathlib import Path

import numpy as np

from monitor_neuronal import inspeccionar_pesos


class TestMonitorNeuronal(unittest.TestCase):
    def test_pesos_reales(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "pesos.npz"
            np.savez(ruta, capa=np.array([[1., -1.], [3., -3.]]),
                     texto=np.array(["hola"]))
            datos = inspeccionar_pesos(ruta)
            self.assertEqual(len(datos), 1)
            self.assertEqual(datos[0]["tensor"], "capa")
            self.assertEqual(datos[0]["forma"], [2, 2])
            self.assertAlmostEqual(datos[0]["media"], 0)
            self.assertEqual(datos[0]["magnitud_maxima"], 3)

    def test_limites(self):
        with self.assertRaises(ValueError):
            inspeccionar_pesos("inexistente.npz", 0)
        with self.assertRaises(FileNotFoundError):
            inspeccionar_pesos("inexistente.npz")


if __name__ == "__main__":
    unittest.main()
