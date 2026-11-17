"""Pruebas de instalación/desinstalación sin tocar datos reales."""
import tempfile
import unittest
from pathlib import Path

import cerebro
from core.instalacion import desinstalar
from core.motores import disponibles


class TestInstalacion(unittest.TestCase):
    def test_desinstalar_conserva_datos_y_codigo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for nombre in (".venv", ".cerebro-env", "data", "checkpoints"):
                (raiz / nombre).mkdir()
                (raiz / nombre / "prueba.txt").write_text("dato")
            (raiz / "cerebro.py").write_text("codigo")
            self.assertTrue(desinstalar(raiz)["requiere_confirmacion"])
            self.assertTrue((raiz / ".venv").exists())
            resultado = desinstalar(raiz, confirmar=True)
            self.assertTrue(resultado["datos_conservados"])
            self.assertFalse((raiz / ".venv").exists())
            self.assertTrue((raiz / "data" / "prueba.txt").exists())
            self.assertTrue((raiz / "cerebro.py").exists())

    def test_borrar_datos_requiere_frase_explicita(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "data").mkdir()
            with self.assertRaises(ValueError):
                desinstalar(raiz, confirmar=True, borrar_datos=True)
            self.assertTrue((raiz / "data").exists())
            desinstalar(raiz, confirmar=True, borrar_datos=True,
                        confirmacion_datos="BORRAR MIS DATOS")
            self.assertFalse((raiz / "data").exists())

    def test_motores_integrados(self):
        nombres = {m["nombre"] for m in disponibles()}
        self.assertIn("neuronal_numpy", nombres)
        self.assertIn("neuronal_torch_avanzado", nombres)
        self.assertEqual(cerebro.main(["motores"]), 0)


if __name__ == "__main__":
    unittest.main()
