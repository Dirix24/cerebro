from pathlib import Path

import pytest

from core.repositorio_descargado import descargar
from universe.herramientas import resolver


@pytest.mark.parametrize("url", [
    "file:///tmp/proyecto",
    "https://github.com@otro.example/a/b",
    "https://github.com/a/b?credencial=x",
    "https://github.com/a/b/tree/main",
])
def test_rechaza_url_antes_de_crear_destino(tmp_path, url):
    with pytest.raises(ValueError):
        descargar(url, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_destino_existente_se_conserva(tmp_path):
    destino = tmp_path / "repositorios" / "a--b"
    destino.mkdir(parents=True)
    marcador = destino / "original"
    marcador.write_text("conservar")
    with pytest.raises(FileExistsError):
        descargar("https://github.com/a/b", tmp_path)
    assert marcador.read_text() == "conservar"


@pytest.mark.parametrize("internet", [False, True])
def test_permisos_impiden_descarga(internet):
    class NucleoSinEscritura:
        estudio = Path("/no-debe-accederse")

        def exigir_permisos(self, *permisos):
            assert permisos == ("READ", "WRITE")
            raise PermissionError("Falta WRITE")

    nucleo = NucleoSinEscritura()
    nucleo.internet = internet
    mensaje = "Clona https://github.com/a/b y explícame cómo funciona"
    with pytest.raises(PermissionError, match="WRITE" if internet else "internet"):
        resolver(nucleo, mensaje, mensaje.lower())


@pytest.mark.parametrize("url", [
    "https://ejemplo.org/gastos.pdf",
    "https://github.com/a/b/blob/main/gastos.pdf",
    "https://github.com/a/b/releases/download/v1/gastos.pdf",
])
def test_descarga_de_pdf_no_reclama_herramienta_git(url):
    mensaje = f"Descarga el PDF {url}"
    assert resolver(object(), mensaje, mensaje.lower()) is None
