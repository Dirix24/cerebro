"""Verifica el lanzador único sin instalar paquetes ni abrir procesos reales."""
import unittest
from unittest.mock import patch
import cerebro


class TestInicioAutomatico(unittest.TestCase):
    def test_iniciar_selecciona_lanzador(self):
        with patch.object(cerebro, "iniciar_automatico", return_value=0) as iniciar:
            self.assertEqual(cerebro.main(["iniciar"]), 0)
            iniciar.assert_called_once_with()

    def test_iniciar_rechaza_argumentos_inesperados(self):
        with self.assertRaises(SystemExit):
            cerebro.main(["iniciar", "--algo-desconocido"])


if __name__ == "__main__":
    unittest.main()
