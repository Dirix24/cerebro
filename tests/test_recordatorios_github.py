from datetime import datetime, timedelta, timezone
import json
import pytest
from core.recordatorios_locales import crear, listar, pendientes
from core.github_local import estado_publico


def test_recordatorio_local(tmp_path):
    ruta = tmp_path / "tareas.json"
    fecha = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    tarea = crear(fecha, "revisar Cerebro", ruta)
    assert tarea["texto"] == "revisar Cerebro"
    assert len(listar(ruta)) == 1
    assert pendientes(ruta) == []


def test_fecha_sin_zona_rechazada(tmp_path):
    with pytest.raises(ValueError):
        crear("2028-01-01T10:00:00", "revisar", tmp_path / "tareas.json")


def test_github_no_modifica_ni_autentica():
    class Respuesta:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, *args): return b'{"full_name":"Dirix24/cerebro","default_branch":"main","private":false,"html_url":"https://github.com/Dirix24/cerebro"}'
    def abrir(req, timeout):
        assert req.full_url == "https://api.github.com/repos/Dirix24/cerebro"
        assert timeout == 8
        return Respuesta()
    r = estado_publico("Dirix24/cerebro", abrir=abrir)
    assert r["modo"] == "solo_lectura"


def test_github_rechaza_url_arbitraria():
    with pytest.raises(ValueError):
        estado_publico("https://example.org/")
