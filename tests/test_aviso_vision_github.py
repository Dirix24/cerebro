from datetime import datetime, timedelta, timezone
import json
import pytest
from core.recordatorios_locales import crear
from recordatorios_daemon import revisar
from camara_local import inspeccionar_camara
from core.github_local import incidencias_publicas


def test_avisos_una_vez(tmp_path):
    ruta = tmp_path / "tareas.json"
    futuro = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    crear(futuro, "revisar robot", ruta)
    mensajes = []
    despues = datetime.now(timezone.utc) + timedelta(minutes=10)
    assert len(revisar(ruta, ahora=despues, notificar=mensajes.append)) == 1
    assert revisar(ruta, ahora=despues, notificar=mensajes.append) == []
    assert len(mensajes) == 1


def test_camara_requiere_confirmacion_sin_importar_cv2():
    with pytest.raises(PermissionError):
        inspeccionar_camara()


def test_github_incidencias_filtra_pr():
    class Respuesta:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, *args): return json.dumps([
            {"number": 1, "title": "fallo", "html_url": "https://github.com/a/b/issues/1"},
            {"number": 2, "title": "PR", "html_url": "https://github.com/a/b/pull/2",
             "pull_request": {}}]).encode()
    def abrir(req, timeout):
        assert "/issues?" in req.full_url
        return Respuesta()
    assert len(incidencias_publicas("a/b", abrir=abrir)) == 1
