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
    "https://github.com/a/gastos.pdf",
    "https://github.com/a/b/blob/main/gastos.pdf",
    "https://github.com/a/b/releases/download/v1/gastos.pdf",
])
def test_descarga_de_pdf_no_reclama_herramienta_git(url):
    mensaje = f"Descarga el PDF {url}"
    assert resolver(object(), mensaje, mensaje.lower()) is None


def test_limite_total_considera_repositorios_anteriores(tmp_path):
    deposito = tmp_path / "repositorios"
    anterior = deposito / "anterior"
    anterior.mkdir(parents=True)
    datos = anterior / "datos"
    datos.write_bytes(b"x" * 4096)
    with pytest.raises(RuntimeError, match="límite total"):
        descargar("https://github.com/a/b", tmp_path, limite=1024)
    assert datos.read_bytes() == b"x" * 4096
    assert not (deposito / "a--b").exists()


def test_git_termina_grupo_real_al_cancelar(tmp_path):
    import os

    from core.repositorio_descargado import _git

    script = tmp_path / "git"
    script.write_text("#!/bin/sh\nsleep 30 &\necho $! > hijo\nwait\n")
    script.chmod(0o700)
    hijo = tmp_path / "hijo"

    def comprobar():
        if hijo.exists() and hijo.read_text().strip():
            raise InterruptedError("cancelada")

    with pytest.raises(InterruptedError, match="cancelada"):
        _git((), {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.defpath,
                  "PWD": str(tmp_path)}, comprobar, 1024 * 1024, 2, directorio=tmp_path)
    estado = Path("/proc") / hijo.read_text().strip() / "stat"
    if estado.exists():
        try:
            assert estado.read_text().rsplit(")", 1)[1].split()[0] == "Z"
        except FileNotFoundError:
            pass


def test_cancelacion_git_esta_vinculada_al_chat(tmp_path, monkeypatch):
    from threading import Event
    from time import monotonic, sleep

    import config
    from universe import herramientas
    from universe.nucleo import Nucleo

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memory.json"))
    empezado, liberar = Event(), Event()
    def descargar_lento(url, raiz, *, avanzar):
        avanzar("clonando")
        empezado.set()
        assert liberar.wait(5)
        avanzar("publicando")
        pytest.fail("Una descarga cancelada no debe publicarse.")

    monkeypatch.setattr(herramientas, "descargar", descargar_lento)
    n = Nucleo("local", internet=True)
    origen, otro = "a" * 24, "b" * 24
    try:
        assert "en cola" in n.conversar("Clona https://github.com/a/b", cliente=origen)["respuesta"]
        assert empezado.wait(5)
        assert "No hay" in n.conversar("Cancela descarga Git", cliente=otro)["respuesta"]
        assert "clonando" in n.conversar("Estado de descarga Git", cliente=origen)["respuesta"]
        assert "solicitada" in n.conversar("Cancela descarga Git", cliente=origen)["respuesta"]
        liberar.set()
        fin = monotonic() + 5
        while monotonic() < fin:
            if "cancelada" in n.conversar("Estado de descarga Git", cliente=origen)["respuesta"]:
                break
            sleep(.01)
        else:
            pytest.fail("La cancelación no llegó al trabajo.")
    finally:
        liberar.set()
        n.ejecutor.shutdown()
