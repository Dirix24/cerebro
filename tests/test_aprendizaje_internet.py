"""Pruebas sin red ni entrenamiento costoso del aprendizaje diario."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import aprendizaje_internet as ai
from aprendizaje_internet import documento, obtener_paginas


class TestAprendizajeInternet(unittest.TestCase):
    def test_descarga_primero_y_entrena_despues_sin_duplicar(self):
        pagina = {"id": 42, "titulo": "La Luna",
                  "texto": "La Luna es un satélite natural. " * 12,
                  "url": "https://es.wikipedia.org/wiki/Luna"}
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            with patch.multiple(ai, CARPETA=carpeta, ESTADO=carpeta / "estado.json",
                                CORPUS=carpeta / "corpus_diario.txt",
                                FUENTES=carpeta / "fuentes.jsonl"), \\
                 patch.object(ai, "obtener_paginas", return_value=[pagina]) as obtener, \\
                 patch("core.conocimiento.guardar", return_value=[]), \\
                 patch("core.local_search.indexar", return_value=1), \\
                 patch.object(ai, "entrenar_pendiente") as entrenar:
                ai.ciclo(3, 20, False, 1000000, "diminuto", carpeta / "last.npz")
                estado = json.loads(ai.ESTADO.read_text())
                self.assertTrue(estado["entrenamiento_pendiente"])
                ai.ciclo(3, 20, True, 1000000, "diminuto", carpeta / "last.npz")
                entrenar.assert_called_once()
                self.assertEqual(obtener.call_count, 1)
                estado = json.loads(ai.ESTADO.read_text())
                self.assertFalse(estado["entrenamiento_pendiente"])
                self.assertEqual(estado["vistos"], [42])

    def test_fallo_entrenamiento_conserva_pendiente(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            carpeta.mkdir(exist_ok=True)
            from datetime import date
            (carpeta / "estado.json").write_text(json.dumps({
                "ultimo_dia": date.today().isoformat(),
                "vistos": [42], "entrenamiento_pendiente": True}))
            with patch.multiple(ai, CARPETA=carpeta, ESTADO=carpeta / "estado.json",
                                CORPUS=carpeta / "corpus_diario.txt",
                                FUENTES=carpeta / "fuentes.jsonl"), \\
                 patch.object(ai, "entrenar_pendiente", side_effect=RuntimeError("fallo")):
                with self.assertRaises(RuntimeError):
                    ai.ciclo(3, 20, True, 1000000, "diminuto", carpeta / "last.npz")
                self.assertTrue(json.loads(ai.ESTADO.read_text())["entrenamiento_pendiente"])

    def test_formato_compatible_con_entrenador(self):
        p = {"titulo": "La Luna", "texto": "La Luna es un satélite natural."}
        d = documento(p)
        self.assertTrue(d.startswith("usuario: ¿Qué es La Luna?\ncerebro: "))
        self.assertTrue(d.endswith("\n\n"))

    def test_sanitiza_saltos(self):
        p = {"titulo": "Un\ntítulo", "texto": "Primera línea\nsegunda línea"}
        d = documento(p)
        self.assertEqual(d.count("\ncerebro:"), 1)
        self.assertIn("Primera línea segunda línea", d)


if __name__ == "__main__":
    unittest.main()
