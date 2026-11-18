"""Comprueba que chat.py compile y que los patrones de consulta documental funcionen."""
import ast
from pathlib import Path
import re
import unittest


class SintaxisChatTest(unittest.TestCase):
    def test_chat_compila(self):
        archivo = Path(__file__).resolve().parents[1] / "chat.py"
        ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))

    def test_consulta_documental_identificada(self):
        patron = re.compile(
            r"^\s*(?:busca\s+en\s+mis\s+documentos|consulta\s+mis\s+documentos|en\s+mis\s+documentos)\s+(.+)$",
            re.IGNORECASE,
        )
        for entrada in ("busca en mis documentos sensores",
                        "consulta mis documentos robótica",
                        "en mis documentos electrónica"):
            with self.subTest(entrada=entrada):
                self.assertIsNotNone(patron.match(entrada))
        self.assertIsNone(patron.match("busca en internet sensores"))


if __name__ == "__main__":
    unittest.main()
