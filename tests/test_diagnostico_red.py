"""Diagnósticos offline: sin peticiones reales de red ni interfaz interactiva."""
import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import aprendizaje_internet as aprendizaje


class DiagnosticoRedTest(unittest.TestCase):
    def test_http_403(self):
        exc = HTTPError("https://es.wikipedia.org/w/api.php", 403, "Forbidden", {}, None)
        self.assertIn("403", aprendizaje.explicar_error_red(exc))

    def test_conexion_reiniciada(self):
        exc = URLError(ConnectionResetError(104, "Connection reset by peer"))
        self.assertIn("interrumpida", aprendizaje.explicar_error_red(exc))

    def test_dns(self):
        import socket
        self.assertIn("DNS", aprendizaje.explicar_error_red(URLError(socket.gaierror(-2, "Name or service not known"))))

    def test_comprobar_red_informa_sin_crash(self):
        with patch.object(aprendizaje, "urlopen", side_effect=URLError(ConnectionResetError(104, "reset"))):
            with redirect_stderr(io.StringIO()) as salida:
                self.assertEqual(aprendizaje.comprobar_red(), 1)
        self.assertIn("Wikipedia", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
