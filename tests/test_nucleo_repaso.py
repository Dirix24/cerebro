"""Pruebas del núcleo: respuesta de repaso sin invocar al generador."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from chat import Conversacion
from core.repaso_espaciado import anadir, cargar


class TestRepasoConversacional(unittest.TestCase):
    def test_respuesta_correcta_no_invoca_modelo(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "data" / "repaso_espaciado.json"
            anadir(ruta, "¿Cuál es la capital de Francia?", "París")
            memoria = SimpleNamespace()
            conversacion = Conversacion.__new__(Conversacion)
            conversacion.pregunta_repaso = None
            conversacion.modelo = None
            conversacion.memoria = memoria
            conversacion.agente = None
            with patch("config._RAIZ", Path(tmp)):
                mensaje, salir = conversacion.procesar("/repasar")
                self.assertIn("capital de Francia", mensaje)
                self.assertFalse(salir)
                with patch.object(conversacion, "responder_modelo", side_effect=AssertionError("modelo invocado")):
                    mensaje, salir = conversacion.procesar("paris")
            self.assertIn("Correcto", mensaje)
            self.assertFalse(salir)
            self.assertIsNone(conversacion.pregunta_repaso)
            self.assertEqual(cargar(ruta)[0]["aciertos"], 1)

    def test_respuesta_incorrecta_no_se_aprueba(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "data" / "repaso_espaciado.json"
            anadir(ruta, "¿Cuál es la capital de Francia?", "París")
            conversacion = Conversacion.__new__(Conversacion)
            conversacion.pregunta_repaso = None
            conversacion.modelo = None
            conversacion.memoria = None
            conversacion.agente = None
            with patch("config._RAIZ", Path(tmp)):
                conversacion.procesar("/repasar")
                mensaje, salir = conversacion.procesar("Londres")
            self.assertIn("Incorrecto", mensaje)
            self.assertFalse(salir)
            self.assertEqual(cargar(ruta)[0]["aciertos"], 0)


if __name__ == "__main__":
    unittest.main()
