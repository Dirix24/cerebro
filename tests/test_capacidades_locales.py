"""Pruebas sin red ni ejecución de modelos para las nuevas capacidades."""
import tempfile
from pathlib import Path
import unittest

from core.razonamiento_local import calcular, deducir
from core.biblioteca_local import buscar_en_biblioteca, leer_documento
from core.planificador_local import Plan
from core.analizador_codigo_local import analizar
from core.investigador_local import preparar_fuente, deduplicar
from core.laboratorio_local import registrar, historial
from core.estudio_local import resumir, palabras_clave


class TestCapacidades(unittest.TestCase):
    def test_calculo(self):
        self.assertEqual(calcular("2+3*4"), 14)
        self.assertEqual(calcular("-(8-3)"), -5)
        with self.assertRaises(ValueError):
            calcular("__import__('os').system('echo hola')")
        with self.assertRaises(ValueError):
            calcular("2**100")

    def test_logica(self):
        self.assertEqual(deducir(("Misi", "gato"), ("gato", "animal")), "Misi es animal")
        self.assertIsNone(deducir(("Misi", "gato"), ("perro", "animal")))

    def test_biblioteca(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "luna.txt").write_text("La Luna es un satélite.", encoding="utf-8")
            self.assertEqual(len(buscar_en_biblioteca("Luna", base)), 1)
            with self.assertRaises(ValueError):
                leer_documento(base.parent / "otro.txt", base)

    def test_plan_con_permiso(self):
        plan = Plan("Prueba")
        plan.agregar("Escribir archivo")
        with self.assertRaises(PermissionError):
            plan.completar(0)
        plan.aprobar(0)
        plan.completar(0)
        self.assertTrue(plan.pasos[0]["completado"])

    def test_analizador(self):
        r = analizar("import math\nclass A: pass\ndef f(): return 1")
        self.assertEqual(r["funciones"], ["f"])
        self.assertEqual(r["clases"], ["A"])

    def test_fuentes(self):
        f = preparar_fuente("https://es.wikipedia.org/wiki/Luna", "texto   de prueba")
        self.assertEqual(len(deduplicar([f, f])), 1)
        with self.assertRaises(ValueError):
            preparar_fuente("http://ejemplo.com", "texto")

    def test_resumen_y_palabras_clave(self):
        texto = "La Luna orbita la Tierra. La Luna es un satélite. Marte es un planeta."
        self.assertEqual(resumir(texto, max_frases=2).count("."), 2)
        self.assertIn("luna", palabras_clave(texto))
        with self.assertRaises(ValueError):
            resumir(texto, max_frases=0)

    def test_laboratorio(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "experimentos.jsonl"
            registrar(ruta, "base", {"pasos": 5}, {"bpb": 2.1})
            self.assertEqual(historial(ruta)[0]["metricas"]["bpb"], 2.1)


if __name__ == "__main__":
    unittest.main()
