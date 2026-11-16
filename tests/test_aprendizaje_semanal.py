"""Pruebas offline del modo de aprendizaje semanal."""
import ast
import subprocess
import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


class TestAprendizajeSemanal(unittest.TestCase):
    def test_sintaxis(self):
        ast.parse((RAIZ / "aprendizaje_internet.py").read_text(encoding="utf-8"))

    def test_opcion_dias(self):
        resultado = subprocess.run(
            [sys.executable, str(RAIZ / "aprendizaje_internet.py"), "--help"],
            cwd=RAIZ, capture_output=True, text=True, timeout=15)
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("--dias", resultado.stdout)

    def test_dias_invalidos(self):
        resultado = subprocess.run(
            [sys.executable, str(RAIZ / "aprendizaje_internet.py"), "--dias", "31"],
            cwd=RAIZ, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("--dias", resultado.stderr)


if __name__ == "__main__":
    unittest.main()
