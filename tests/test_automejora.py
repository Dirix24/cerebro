"""Pruebas de propuestas de automejora sin efectos sobre pesos."""
import json
import tempfile
import unittest
from pathlib import Path
from core.automejora import analizar, generar


class TestAutomejora(unittest.TestCase):
    def test_sin_datos_propone_evaluacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            informe = analizar(tmp)
            self.assertEqual(informe["modo"], "solo propuestas")
            self.assertTrue(any("evaluación" in p["objetivo"] for p in informe["propuestas"]))
            self.assertTrue(all(not p["automatica"] for p in informe["propuestas"]))

    def test_regresion_y_errores(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            datos = raiz / "data"
            datos.mkdir()
            (datos / "historial_evaluaciones.jsonl").write_text('{"precision": 0.4}\n')
            (datos / "errores_aprendizaje.jsonl").write_text('{"estado":"pendiente_revision"}\n')
            evolucion = datos / "aprendizaje_internet" / "evolucion.json"
            evolucion.parent.mkdir()
            evolucion.write_text('[{"resultado":"revertido"}]')
            informe = generar(raiz, datos / "informe_automejora.json")
            self.assertEqual(informe["correcciones_pendientes"], 1)
            self.assertEqual(len(informe["propuestas"]), 3)
            self.assertEqual(json.loads((datos / "informe_automejora.json").read_text())["modo"], "solo propuestas")


if __name__ == "__main__":
    unittest.main()
