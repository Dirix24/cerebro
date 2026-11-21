"""Pruebas rápidas del entrenador guiado sin entrenar ni descargar modelos."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from entrenamiento_guiado import decidir_aceptacion, entrenar_guiado


class TestEntrenamientoGuiado(unittest.TestCase):
    def test_acepta_mejora(self):
        self.assertTrue(decidir_aceptacion(1.0, 0.9))

    def test_rechaza_regresion(self):
        self.assertFalse(decidir_aceptacion(1.0, 1.1))

    def test_rechaza_resultado_ausente(self):
        self.assertFalse(decidir_aceptacion(1.0, None))

    def test_igualdad_regresion_y_baseline_ausente_no_mejoran(self):
        self.assertFalse(decidir_aceptacion(1.0, 1.0))
        self.assertFalse(decidir_aceptacion(1.0, 1.01))
        self.assertFalse(decidir_aceptacion(None, .9))

    def test_candidato_mejor_no_toca_modelo_activo(self):
        with TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            ultimo, mejor = raiz / "last.npz", raiz / "best.npz"
            validacion = raiz / "validacion.txt"
            for archivo in (ultimo, mejor, validacion):
                archivo.write_bytes(b"original")

            def entrenar(_comando, **opciones):
                copia = Path(opciones["env"]["CEREBRO_HOME"])
                (copia / "checkpoints" / "best.npz").write_bytes(b"candidato")

            with patch("config.raiz_datos", return_value=raiz), patch("config.CKPT_ULTIMO", str(ultimo)), patch("config.CKPT_MEJOR", str(mejor)), patch("config.VALIDACION_FILE", str(validacion)), patch("entrenamiento_guiado.evaluar_fijo", side_effect=[1.0, .9]), patch("entrenamiento_guiado.subprocess.run", side_effect=entrenar):
                self.assertTrue(entrenar_guiado(1, .0003))
            self.assertEqual(mejor.read_bytes(), b"original")
            self.assertEqual(ultimo.read_bytes(), b"original")
            candidatos = list((raiz / "learning" / "candidatos").glob("*/checkpoints/best.npz"))
            self.assertEqual([ruta.read_bytes() for ruta in candidatos], [b"candidato"])

    def test_limites_sin_tocar_checkpoints(self):
        with self.assertRaises(ValueError):
            entrenar_guiado(0, 0.0003)
        with self.assertRaises(ValueError):
            entrenar_guiado(100, 0.1)


if __name__ == "__main__":
    unittest.main()
