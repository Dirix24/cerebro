"""Pruebas de búsqueda FTS5 offline, sin dependencias adicionales."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import local_search


def test_indexacion_y_busqueda(tmp_path, monkeypatch):
    archivo = tmp_path / "corpus.txt"
    archivo.write_text("usuario: ¿Qué es un token?\ncerebro: Una unidad de texto.\n\n"
                       "usuario: ¿Qué es NumPy?\ncerebro: Una biblioteca numérica.",
                       encoding="utf-8")
    monkeypatch.setattr(local_search, "fuentes", lambda: iter([archivo]))
    db = tmp_path / "indice.sqlite3"
    assert local_search.indexar(db) == 2
    resultados = local_search.buscar("token", db)
    assert len(resultados) == 1
    assert "unidad de texto" in resultados[0][0]
    assert local_search.buscar("numpy", db)[0][1] == "corpus.txt"
    assert local_search.buscar("nadairrelevante", db) == []


def test_busqueda_sin_indice_y_consultas_especiales(tmp_path):
    db = tmp_path / "no-existe.sqlite3"
    assert local_search.buscar("hola", db) == []
    assert local_search.buscar('"" OR NOT () *', db) == []
    assert not db.exists()


def test_reindexado_elimina_documentos_viejos(tmp_path, monkeypatch):
    archivo = tmp_path / "corpus.txt"
    db = tmp_path / "indice.sqlite3"
    monkeypatch.setattr(local_search, "fuentes", lambda: iter([archivo]))
    archivo.write_text("primera entrada", encoding="utf-8")
    assert local_search.indexar(db) == 1
    archivo.write_text("segunda entrada", encoding="utf-8")
    assert local_search.indexar(db) == 1
    assert local_search.buscar("primera", db) == []
    assert len(local_search.buscar("segunda", db)) == 1


def test_rechaza_indice_simbolico(tmp_path):
    real = tmp_path / "real.sqlite3"
    real.touch()
    enlace = tmp_path / "enlace.sqlite3"
    try:
        enlace.symlink_to(real)
    except (OSError, NotImplementedError):
        return
    try:
        local_search.indexar(enlace)
    except ValueError:
        pass
    else:
        raise AssertionError("No se rechazó el enlace simbólico")
