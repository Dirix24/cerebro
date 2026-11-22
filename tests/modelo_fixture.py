"""Doble de modelo para pruebas de integración de Cerebro Next."""
import json


class ModeloDePrueba:
    configurado = True

    def proponer_proyecto(self, objetivo):
        if "web" in objetivo:
            archivos = [{"nombre": "index.html", "texto": "<h1>Una web</h1>"},
                        {"nombre": "estilo.css", "texto": "h1{color:navy}"}]
        else:
            archivos = [{"nombre": "calculadora.py", "texto": "def sumar(a, b):\n    return a + b"},
                        {"nombre": "test_calculadora.py", "texto": "import unittest\nfrom calculadora import sumar\n"
                         "class Prueba(unittest.TestCase):\n    def test_suma(self): self.assertEqual(sumar(2, 3), 5)"}]
        return json.dumps({"archivos": archivos})

    def explicar_fragmentos(self, pregunta, fragmentos):
        assert fragmentos[0]["referencia"] == "guia.txt"
        return "Explicación de prueba."
