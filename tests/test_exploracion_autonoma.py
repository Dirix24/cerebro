"""Pruebas offline de exploración local con límites y exclusiones."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from exploracion_autonoma import explorar_local, comparar_local, rutas_locales


class ExploracionTest(unittest.TestCase):
    def test_excluye_ocultos_y_credenciales_y_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            hogar = Path(d)
            (hogar / "Documentos").mkdir()
            (hogar / "Documentos" / "notas.txt").write_text("Robótica y sensores de movimiento.", encoding="utf-8")
            (hogar / ".ssh").mkdir()
            (hogar / ".ssh" / "claves.txt").write_text("PRIVADO", encoding="utf-8")
            (hogar / "contraseñas").mkdir()
            (hogar / "contraseñas" / "claves.txt").write_text("PRIVADO", encoding="utf-8")
            (hogar / "Documentos" / "enlace.txt").symlink_to(hogar / ".ssh" / "claves.txt")
            rutas = list(rutas_locales(hogar))
            self.assertEqual([p.name for p in rutas], ["notas.txt"])
            db = hogar / "indice.sqlite3"
            self.assertEqual(explorar_local(hogar, db)["archivos"], 1)
            with sqlite3.connect(db) as con:
                texto = con.execute("SELECT texto FROM documentos").fetchone()[0]
            self.assertNotIn("PRIVADO", texto)

    def test_relaciones_sin_red(self):
        with tempfile.TemporaryDirectory() as d:
            hogar = Path(d)
            (hogar / "uno.txt").write_text("sensores motores robots circuitos programa", encoding="utf-8")
            (hogar / "dos.md").write_text("sensores motores robots circuitos electrónica", encoding="utf-8")
            db = hogar / "indice.sqlite3"
            explorar_local(hogar, db)
            self.assertEqual(comparar_local(db), 1)


if __name__ == "__main__":
    unittest.main()
