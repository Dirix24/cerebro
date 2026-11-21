import base64
import io
import json
from urllib.parse import parse_qs, urlsplit

import pytest

import config
from core import busqueda_web, fuentes_publicas, github_local
from universe.nucleo import Nucleo


def json_respuesta(datos):
    return io.BytesIO(json.dumps(datos).encode())


def test_github_estructura_y_archivo_solo_lectura():
    def abrir(req, timeout):
        assert req.get_method() == "GET" and timeout == 8
        assert req.get_header("Authorization") is None
        assert req.full_url == "https://api.github.com/repos/Dirix24/cerebro/contents/universe"
        return json_respuesta([
            {"type": "file", "name": "nucleo.py"},
            {"type": "dir", "name": "web"},
            {"type": "symlink", "name": "ajeno"},
        ])

    datos = github_local.explorar_publico("https://github.com/Dirix24/cerebro.git", "universe", abrir=abrir)
    assert datos["elementos"] == ["[carpeta] web", "nucleo.py"]

    texto = "Un núcleo local."
    original = texto.encode()

    def abrir_archivo(req, timeout):
        assert req.full_url == "https://api.github.com/repos/Dirix24/cerebro/contents/docs/Gu%C3%ADa%20local.md"
        return json_respuesta({"type": "file", "size": len(original), "encoding": "base64",
                               "content": base64.b64encode(original).decode()})

    assert github_local.leer_publico("Dirix24/cerebro", "docs/Guía local.md", abrir=abrir_archivo)["texto"] == texto


@pytest.mark.parametrize("destino", [
    "http://github.com/Dirix24/cerebro", "https://github.com.ejemplo.test/uno/dos",
    "https://github.com@ejemplo.test/uno/dos", "Dirix24/..", "https://github.com/Dirix24/cerebro/wiki",
])
def test_rechaza_urls_ajenas_y_rutas_invalidas(destino):
    with pytest.raises(ValueError):
        github_local.explorar_publico(destino)
    with pytest.raises(ValueError):
        github_local.leer_publico("Dirix24/cerebro", "docs/../archivo")


def test_busqueda_general_envia_solo_tema_y_filtra_enlaces():
    def abrir(req, timeout):
        assert urlsplit(req.full_url).hostname == "api.search.brave.com"
        assert parse_qs(urlsplit(req.full_url).query)["q"] == ["editores para MX Linux"]
        assert req.get_header("X-subscription-token") == "clave-de-prueba"
        return json_respuesta({"web": {"results": [
            {"title": "<strong>Editor</strong>", "url": "https://example.org/editor", "description": "<em>Guía</em>"},
            {"title": "No permitido", "url": "javascript:alert(1)"},
        ]}})

    assert busqueda_web.buscar("editores para MX Linux", "clave-de-prueba", abrir=abrir) == [
        ("Editor", "Guía", "https://example.org/editor")
    ]
    assert fuentes_publicas.SinRedirecciones().redirect_request(None, None, 302, "", {}, "http://localhost") is None


def test_internet_respeta_permisos_y_rutas_compartidas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "CEREBRO_HOME", str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    monkeypatch.delenv("CEREBRO_BRAVE_API_KEY", raising=False)
    motor = Nucleo("usb", internet=False)
    try:
        with pytest.raises(PermissionError):
            motor.conversar("Explora el repositorio Dirix24/cerebro")
        motor.internet = True
        assert "CEREBRO_BRAVE_API_KEY" in motor.conversar("Busca en la web editores de Linux")["respuesta"]
        monkeypatch.setattr(github_local, "explorar_publico",
                            lambda repo, ruta: {"repo": repo, "elementos": [ruta or "README.md"],
                                                "omitidos": 0, "fuente": "https://github.com/" + repo})
        for modo in ("terminal", "chat", "studio", None):
            salida = motor.conversar("Explora el repositorio Dirix24/cerebro", modo=modo)["respuesta"]
            assert "README.md" in salida and "Fuente:" in salida
        assert "universe" in motor.conversar("/github-explorar Dirix24/cerebro || universe")["respuesta"]
        assert "tema público breve" in motor.conversar("Busca en la web mi contraseña")["respuesta"]
    finally:
        motor.ejecutor.shutdown()
