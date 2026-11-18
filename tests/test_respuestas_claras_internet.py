"""Respuestas breves y consulta automática sin red real."""
import unittest
from unittest.mock import Mock

from core.respuestas_con_fuentes import (
    respuesta_clara, consultar_internet_si_falta,
)


class RespuestasClarasTest(unittest.TestCase):
    def test_resumen_dos_frases_completas(self):
        texto = ("La robótica diseña robots. Combina ingeniería e informática. "
                 "Una tercera oración que no debe aparecer.")
        self.assertEqual(respuesta_clara(texto), "La robótica diseña robots. Combina ingeniería e informática.")

    def test_no_corta_palabras(self):
        respuesta = respuesta_clara("La inteligencia artificial " + "concepto " * 100, max_caracteres=90)
        self.assertFalse(respuesta.endswith("conce"))

    def test_consulta_y_guarda_fuente(self):
        pagina = {"titulo": "robótica", "texto": "La robótica estudia robots.",
                  "url": "https://es.wikipedia.org/wiki/Rob%C3%B3tica"}
        guardar = Mock()
        dato = consultar_internet_si_falta("¿Qué es la robótica?",
                                          obtener=lambda titulo: pagina, guardar=guardar)
        self.assertEqual(dato[1], pagina["url"])
        guardar.assert_called_once()

    def test_no_envia_preguntas_no_definicion(self):
        obtener = Mock()
        self.assertIsNone(consultar_internet_si_falta("Recuerda mi contraseña",
                                                       obtener=obtener, guardar=Mock()))
        obtener.assert_not_called()

    def test_rechaza_articulo_de_otro_tema(self):
        pagina = {"titulo": "Otra cosa", "texto": "irrelevante",
                  "url": "https://es.wikipedia.org/wiki/Otra"}
        guardar = Mock()
        self.assertIsNone(consultar_internet_si_falta("¿Qué es la robótica?",
                                                       obtener=lambda _: pagina, guardar=guardar))
        guardar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
