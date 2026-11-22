import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_ciclo_local_sin_grafica_ni_audio(tmp_path):
    from socket import socket

    try:
        with socket() as enlace:
            enlace.bind(("127.0.0.1", 0))
    except PermissionError:
        pytest.skip("Este entorno no permite loopback.")
    entorno = {**os.environ, "CEREBRO_HOME": str(tmp_path), "XDG_RUNTIME_DIR": str(tmp_path / "runtime"),
               "CEREBRO_SIN_INTERNET": "1", "CEREBRO_MODELO_VOZ": str(tmp_path / "inexistente")}
    for nombre in ("DISPLAY", "WAYLAND_DISPLAY", "CEREBRO_PROFESOR_MOTOR",
                   "CEREBRO_PROFESOR_MODELO", "CEREBRO_PROFESOR_PUERTO"):
        entorno.pop(nombre, None)
    raiz = Path(__file__).resolve().parents[1]
    (tmp_path / ".cerebro_ssd").touch()

    def lanzar(modo, mensajes=None):
        return subprocess.run([sys.executable, "-m", "universe.lanzador", modo],
                              input=mensajes, cwd=raiz, env=entorno, capture_output=True,
                              text=True, check=True, timeout=25).stdout

    try:
        assert "detenido" in lanzar("estado")
        assert "Hora local" in lanzar("terminal", "Por favor dime que hora es\n/salir\n")
        assert "en ejecución" in lanzar("estado")
        lanzar("detener")
        lanzar("detener")
        assert "detenido" in lanzar("estado")
        assert "Último candidato" not in lanzar("terminal", "Estado del alumno\n/salir\n")
        assert "en ejecución" in lanzar("estado")
    finally:
        lanzar("detener")
    assert not (tmp_path / "runtime" / "cerebro-local" / "sesion.json").exists()
