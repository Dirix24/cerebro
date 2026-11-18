"""Pruebas de registro, laboratorio y generación de PDF."""
import hashlib
from pathlib import Path

import pytest
from agent.motores import capacidades
from core.laboratorio_seguridad import inspeccionar_archivo
from core.documentos_pdf import crear_pdf


def test_registro_no_activa_camara_ni_internet():
    motores = capacidades()
    assert motores["camara"]["activo"] is False
    assert motores["voz"]["activo"] is False
    assert motores["internet"]["activo"] is False


def test_laboratorio_inspeccion_estatica(tmp_path):
    archivo = tmp_path / "ejemplo.py"
    datos = b"import os\ndef sumar(a, b):\n    return a+b\n"
    archivo.write_bytes(datos)
    resultado = inspeccionar_archivo("ejemplo.py", tmp_path)
    assert resultado["sha256"] == hashlib.sha256(datos).hexdigest()
    assert resultado["python_sintaxis"] == "valida"
    assert resultado["funciones"] == 1
    assert resultado["ejecutado"] is False


def test_laboratorio_no_sale_del_workspace(tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        inspeccionar_archivo("../fuera.py", tmp_path)


def test_pdf_sin_sobrescritura(tmp_path):
    pytest.importorskip("reportlab")
    ruta = Path(crear_pdf("informe", "Hola Cerebro", raiz=tmp_path))
    assert ruta.read_bytes().startswith(b"%PDF")
    with pytest.raises(FileExistsError):
        crear_pdf("informe", "otro", raiz=tmp_path)
