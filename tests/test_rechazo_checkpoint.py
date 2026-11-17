"""Regresión: descartar pesos peores no es un error del ciclo diario."""
import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
import aprendizaje_internet as ai


class TestRechazoCheckpoint(unittest.TestCase):
    def test_rechazo_restaura_y_registra(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            corpus = carpeta / "corpus.txt"
            corpus.write_text("usuario: hola\ncerebro: mundo\n")
            validacion = carpeta / "validacion.txt"
            validacion.write_text("usuario: hola\ncerebro: mundo\n")
            best = carpeta / "best.npz"
            last = carpeta / "last.npz"
            best.write_bytes(b"mejor")
            last.write_bytes(b"anterior")
            historia = carpeta / "evolucion.json"
            class Proceso:
                def wait(self):
                    return 0
            def ejecutar(*args, **kwargs):
                last.write_bytes(b"peor")
                return Proceso()
            with patch.object(ai, "CARPETA", carpeta), patch.object(ai, "CORPUS", corpus), \
                 patch("config.CKPT_MEJOR", str(best)), patch("config.CKPT_ULTIMO", str(last)), \
                 patch("config.VALIDACION_FILE", str(validacion)), \
                 patch("core.recursos_portatil.motivos_pausa", return_value=[]), \
                 patch("core.seguridad_aprendizaje.evaluar_fijo", side_effect=[1.0, 1.0, 1.0, 5.0]), \
                 patch("subprocess.Popen", side_effect=ejecutar):
                resultado = ai.entrenar_pendiente(20, "diminuto", last)
            self.assertTrue(resultado)
            self.assertEqual(best.read_bytes(), b"mejor")
            self.assertEqual(last.read_bytes(), b"anterior")
            self.assertIn('"revertido"', historia.read_text())


if __name__ == "__main__":
    unittest.main()
