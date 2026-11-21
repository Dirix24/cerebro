import json
from threading import Lock

import pytest

from universe import studio
from universe.lanzador import ErrorAPI


@pytest.mark.parametrize("error", [ConnectionRefusedError(), ErrorAPI(401, "clave caducada")])
def test_studio_recupera_lectura_en_nuevo_nucleo(tmp_path, monkeypatch, error):
    anterior = {"url": "http://127.0.0.1:20001", "token": "anterior"}
    nueva = {"url": "http://127.0.0.1:20002", "token": "nueva"}
    (tmp_path / "sesion.json").write_text(json.dumps(nueva))
    monkeypatch.setattr(studio, "carpeta", lambda: tmp_path)
    llamadas = []

    def api(sesion, ruta, datos=None, tiempo=25):
        llamadas.append((sesion["token"], ruta, datos))
        if sesion == anterior:
            raise error
        return {"turnos": ["Resultado desde la web"]}

    monkeypatch.setattr(studio, "api", api)
    sesion = anterior.copy()
    assert studio.pedir_con_reconexion(sesion, Lock(), "conversaciones")["turnos"]
    assert sesion == nueva
    assert llamadas == [("anterior", "conversaciones", None), ("nueva", "conversacion-activa", None),
                        ("nueva", "conversaciones", None)]


def test_studio_no_repite_una_escritura_ni_ignora_permisos(tmp_path, monkeypatch):
    sesion = {"url": "http://127.0.0.1:20001", "token": "anterior"}
    (tmp_path / "sesion.json").write_text(json.dumps({"url": "http://127.0.0.1:20002", "token": "nueva"}))
    monkeypatch.setattr(studio, "carpeta", lambda: tmp_path)
    llamadas = []

    def api(sesion, ruta, datos=None, tiempo=25):
        llamadas.append((sesion["token"], ruta, datos))
        if sesion["token"] == "anterior":
            raise ConnectionError("se cortó")
        if ruta != "conversacion-activa":
            raise ErrorAPI(403, "permiso denegado")
        return {"activa": "original"}

    monkeypatch.setattr(studio, "api", api)
    with pytest.raises(RuntimeError, match="cambió de sesión"):
        studio.pedir_con_reconexion(sesion, Lock(), "archivo", {"texto": "prueba"})
    assert sum(ruta == "archivo" for _, ruta, _ in llamadas) == 1
    with pytest.raises(ErrorAPI, match="denegado"):
        studio.pedir_con_reconexion(sesion, Lock(), "historial")
