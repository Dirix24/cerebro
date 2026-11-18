import json
import pytest
from core.memoria_cifrada import exportar, examinar, restaurar


def test_respaldo_privado_y_recuperacion(tmp_path):
    pytest.importorskip("cryptography")
    memoria = tmp_path / "original.json"
    memoria.write_text(json.dumps({"long_term": {"secreto": {
        "valor": "mi recuerdo privado", "categoria": "personal",
        "importancia": 2, "fecha": "2026-01-01"}}}))
    usb = tmp_path / "usb" / "recuerdos.cerebro"
    exportar(usb, "clave-segura-muy-larga", origen=memoria)
    assert b"mi recuerdo privado" not in usb.read_bytes()
    assert examinar(usb, "clave-segura-muy-larga")["entradas"] == 1
    with pytest.raises(ValueError):
        examinar(usb, "clave-equivocada-larga")
    destino = tmp_path / "restaurada.json"
    with pytest.raises(PermissionError):
        restaurar(usb, "clave-segura-muy-larga", destino=destino)
    assert not destino.exists()
    restaurar(usb, "clave-segura-muy-larga", confirmar=True, destino=destino)
    assert json.loads(destino.read_text())["long_term"]["secreto"]["valor"] == "mi recuerdo privado"
    with pytest.raises(FileExistsError):
        restaurar(usb, "clave-segura-muy-larga", confirmar=True, destino=destino)


def test_rechaza_respaldo_modificado(tmp_path):
    pytest.importorskip("cryptography")
    origen = tmp_path / "memoria.json"
    origen.write_text('{"long_term": {}}')
    usb = tmp_path / "usb.cerebro"
    exportar(usb, "clave-segura-muy-larga", origen=origen)
    paquete = json.loads(usb.read_text())
    paquete["datos"] = "AAAA" + paquete["datos"][4:]
    usb.write_text(json.dumps(paquete))
    with pytest.raises((ValueError, Exception)):
        examinar(usb, "clave-segura-muy-larga")
