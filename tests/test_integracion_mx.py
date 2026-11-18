"""Regresiones de integración detectadas en MX Linux."""
import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class IntegracionTest(unittest.TestCase):
    def test_main_no_importa_checkpoint_al_iniciar(self):
        tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
        imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]
        self.assertNotIn("core.checkpoint", [node.module for node in imports])

    def test_conocimiento_desde_lanzador(self):
        source = (ROOT / "cerebro.py").read_text(encoding="utf-8")
        self.assertIn('"-m", "core.conocimiento"', source)

    def test_ojos_automaticos_por_defecto(self):
        source = (ROOT / "core" / "ojos_animados.py").read_text(encoding="utf-8")
        self.assertIn("automatico = True", source)

    def test_telemetria_limite_cero(self):
        from core.actividad_neuronal import ultimos
        self.assertEqual(ultimos(0), [])

    def test_procesar_no_sombrea_modulo_re(self):
        """El import re interno no debe inutilizar preguntas definitorias."""
        tree = ast.parse((ROOT / "chat.py").read_text(encoding="utf-8"))
        clase = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Conversacion")
        procesar = next(n for n in clase.body if isinstance(n, ast.FunctionDef) and n.name == "procesar")
        imports_locales = [n for n in ast.walk(procesar) if isinstance(n, ast.Import)]
        self.assertFalse(any(alias.name == "re" for n in imports_locales for alias in n.names))

    def test_definiciones_guardan_contexto(self):
        source = (ROOT / "chat.py").read_text(encoding="utf-8")
        inicio = source.index("# Preguntas de definición:")
        fin = source.index("resultado = self.responder_modelo(entrada)", inicio)
        ruta = source[inicio:fin]
        self.assertIn('self.memoria.agregar_contexto("usuario", entrada)', ruta)
        self.assertIn('self.memoria.agregar_contexto("ia", respuesta)', ruta)

    def test_preguntas_definicion_sin_generacion_aleatoria(self):
        source = (ROOT / "chat.py").read_text(encoding="utf-8")
        self.assertLess(source.index("pregunta = re.match("),
                        source.index("resultado = self.responder_modelo(entrada)"))


if __name__ == "__main__":
    unittest.main()
