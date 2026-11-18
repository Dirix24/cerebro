"""Pruebas de seguridad de datos y muestreo del núcleo."""
import unittest

import numpy as np

from core.data import dividir_documentos
from core.sampling import muestrear


class TestContratosNucleo(unittest.TestCase):
    def test_un_documento_no_puede_ser_train_y_validacion(self):
        with self.assertRaisesRegex(ValueError, "al menos dos"):
            dividir_documentos(["único"])

    def test_division_no_solapa_documentos(self):
        train, val = dividir_documentos([f"doc {i}" for i in range(20)], frac_val=0.2)
        self.assertFalse(set(train) & set(val))
        self.assertEqual(len(train) + len(val), 20)

    def test_fraccion_invalida(self):
        with self.assertRaisesRegex(ValueError, "frac_val"):
            dividir_documentos(["a", "b"], frac_val=1.0)

    def test_no_permite_prohibir_todo_vocabulario(self):
        with self.assertRaisesRegex(ValueError, "ningún token"):
            muestrear(np.array([1.0, 2.0]), np.random.default_rng(0),
                      ids_prohibidos=[0, 1])

    def test_no_permite_logits_no_finitos(self):
        with self.assertRaisesRegex(ValueError, "no finitos"):
            muestrear(np.array([np.nan, 1.0]), np.random.default_rng(0))

    def test_muestreo_voraz_respeta_prohibidos(self):
        elegido = muestrear(np.array([1.0, 9.0, 2.0]), np.random.default_rng(0),
                            temperatura=0, ids_prohibidos=[1])
        self.assertEqual(elegido, 2)


if __name__ == "__main__":
    unittest.main()
