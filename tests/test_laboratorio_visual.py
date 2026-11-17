"""Pruebas del panel visual sin navegador ni NumPy."""
import tempfile
import unittest
from pathlib import Path
from laboratorio_visual import estado, generar


class TestLaboratorioVisual(unittest.TestCase):
    def test_sin_datos_y_simulacion(self):
        with tempfile.TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            salida = raiz / "panel.html"
            generar(raiz, salida)
            contenido = salida.read_text(encoding="utf-8")
            self.assertIn("SIMULACIÓN VISUAL", contenido)
            self.assertIn("No representan neuronas reales", contenido)
            self.assertIn("No se ha accedido a archivos", contenido)
            self.assertEqual(estado(raiz)["checkpoints"], [])

    def test_datos_escapados(self):
        with tempfile.TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            destino = raiz / "data" / "historial_evaluaciones.jsonl"
            destino.parent.mkdir()
            destino.write_text('{"precision": 0.5, "texto": "</script><script>alert(1)</script>"}\n')
            salida = generar(raiz, raiz / "panel.html")
            html = salida.read_text()
            self.assertNotIn("</script><script>alert(1)", html)
            self.assertIn("0.5", html)


if __name__ == "__main__":
    unittest.main()
