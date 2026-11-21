"""Pruebas del SpeedDeck: enrutamiento sin cargar motores."""
import unittest
from unittest.mock import patch

from agent.orquestador import seleccionar, extraer_consulta_local, explicar_seleccion
from agent.controlled_agent import ControlledAgent
from chat import Conversacion


class TestSpeedDeck(unittest.TestCase):
    def test_investigacion_local(self):
        self.assertEqual(seleccionar("investiga en el corpus: agujeros negros"),
                         "busqueda_local")
        self.assertEqual(extraer_consulta_local("investiga en el corpus: agujeros negros"),
                         "agujeros negros")

    def test_busqueda_biblioteca(self):
        self.assertEqual(extraer_consulta_local("busca en la biblioteca historia"),
                         "historia")

    def test_pregunta_factual(self):
        self.assertEqual(seleccionar("¿Qué es la fotosíntesis?"), "conocimiento")

    def test_charla_no_activa_investigacion(self):
        self.assertEqual(seleccionar("Hola, ¿cómo estás?"), "modelo")

    def test_escritura_solo_comando(self):
        self.assertEqual(seleccionar("/escribir notas.txt hola"), "comando")
        self.assertEqual(seleccionar("escribe notas.txt hola"), "modelo")

    def test_explicacion_no_ejecuta_motor(self):
        with patch("core.local_search.buscar", side_effect=AssertionError("motor activado")):
            d = explicar_seleccion("consulta el corpus: evolución")
        self.assertEqual(d["motor"], "busqueda_local")

    def test_chat_busca_sin_generar(self):
        chat = Conversacion.__new__(Conversacion)
        chat.pregunta_repaso = None
        chat.modelo = None
        chat.memoria = None
        chat.agente = ControlledAgent()
        with patch("core.local_search.buscar", return_value=[("dato", "fuente")]) as buscar:
            with patch.object(chat, "responder_modelo", side_effect=AssertionError("modelo activado")):
                respuesta, salir = chat.procesar("investiga en el corpus: galaxias")
        buscar.assert_called_once_with("galaxias")
        self.assertIn("dato", respuesta)
        self.assertFalse(salir)


if __name__ == "__main__":
    unittest.main()
