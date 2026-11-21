from pathlib import Path
from textwrap import dedent

import pytest

from core import aislamiento_proyecto
from core.proyecto_studio import ejecutar_pruebas


def test_rechaza_pruebas_si_falta_aislamiento(tmp_path, monkeypatch):
    marcador = tmp_path / "se_ejecuto"
    (tmp_path / "test_prohibido.py").write_text(f"open({str(marcador)!r}, 'w').close()")
    monkeypatch.setattr(aislamiento_proyecto.shutil, "which", lambda _: None)
    bien, salida = ejecutar_pruebas(tmp_path)
    assert not bien and "No se ejecutaron" in salida
    assert not marcador.exists()


def test_aislamiento_real(tmp_path, monkeypatch):
    proyecto = tmp_path / "proyecto"
    proyecto.mkdir()
    externo = tmp_path / "fuera.txt"
    externo.write_text("dato sintético")
    monkeypatch.setenv("CEREBRO_SECRETO_DE_PRUEBA", "dato sintético")
    (proyecto / "enlace.txt").symlink_to(externo)
    (proyecto / ".env").write_text("dato sintético")
    (proyecto / "test_limites.py").write_text(dedent(f"""
        import os
        from pathlib import Path
        import socket
        import unittest

        class Aislamiento(unittest.TestCase):
            def test_solo_copia_y_tmp(self):
                self.assertEqual(Path.cwd(), Path("/proyecto"))
                self.assertFalse(Path({str(externo)!r}).exists())
                self.assertFalse(Path("/home").exists())
                self.assertFalse(Path("enlace.txt").exists())
                self.assertFalse(Path(".env").exists())
                self.assertNotIn("CEREBRO_SECRETO_DE_PRUEBA", os.environ)
                Path("/tmp/prueba").write_text("permitido")
                with self.assertRaises(OSError):
                    Path("escritura_prohibida").write_text("no")

            def test_red_sin_interfaz_del_host(self):
                self.assertEqual([nombre for _, nombre in socket.if_nameindex()], ["lo"])
    """))
    bien, salida = ejecutar_pruebas(proyecto)
    if "No se ejecutó" in salida or "No se ejecutaron" in salida:
        pytest.skip(salida.splitlines()[0])
    assert bien, salida
    assert "Ran 2 tests" in salida
    assert externo.read_text() == "dato sintético"
    assert not (proyecto / "escritura_prohibida").exists()
