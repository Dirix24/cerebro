
import pytest

import config
from core.proyecto_studio import ProyectoStudio
from core.visores_studio import html_estatico, narrar
from universe.nucleo import Nucleo


def test_gestor_real_con_papelera_y_destinos_exclusivos(tmp_path):
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    studio = ProyectoStudio(str(raiz))
    studio.gestionar("carpeta", "web")
    studio.gestionar("crear", "web/index.html", texto="<h1>Inicio</h1>")
    studio.gestionar("copiar", "web", "respaldo")
    studio.gestionar("mover", "respaldo/index.html", "pagina.html")
    assert studio.leer("pagina.html") == "<h1>Inicio</h1>"
    with pytest.raises(FileExistsError):
        studio.gestionar("crear", "pagina.html", texto="No reemplazar")
    with pytest.raises(FileExistsError):
        studio.gestionar("mover", "web/index.html", "pagina.html")
    assert studio.leer("web/index.html") == "<h1>Inicio</h1>"
    with pytest.raises(ValueError):
        studio.gestionar("copiar", "web", "web/copia")
    papelera = studio.gestionar("papelera", "pagina.html")["papelera"]
    assert not (raiz / "pagina.html").exists()
    assert (raiz / papelera).read_text() == "<h1>Inicio</h1>"
    assert all(not item["ruta"].startswith(".") for item in studio.listar()["entradas"])


def test_rutas_enlaces_y_copia_incompleta(tmp_path):
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    externo = tmp_path / "externo.py"
    externo.write_text("valor = 123")
    (raiz / "enlace.py").symlink_to(externo)
    (raiz / "carpeta").mkdir()
    (raiz / "carpeta" / "enlace").symlink_to(externo)
    (raiz / "puente").symlink_to(tmp_path, target_is_directory=True)
    (raiz / "otro.py").hardlink_to(externo)
    studio = ProyectoStudio(str(raiz))
    for nombre in ("../externo.py", "enlace.py", "otro.py", "puente/externo.py"):
        with pytest.raises((ValueError, OSError)):
            studio.inspeccionar(nombre)
    with pytest.raises(PermissionError):
        studio.gestionar("copiar", "carpeta", "copia")
    assert sorted(p.name for p in raiz.iterdir()) == ["carpeta", "enlace.py", "otro.py", "puente"]
    assert externo.read_text() == "valor = 123"


def test_restauracion_exige_reautorizar_y_conserva_editor(tmp_path, monkeypatch):
    datos, raiz = tmp_path / "datos", tmp_path / "proyecto"
    datos.mkdir()
    raiz.mkdir()
    monkeypatch.setattr(config, "raiz_datos", lambda: str(datos))
    monkeypatch.setattr(config, "MEMORY_FILE", str(datos / "memoria.json"))
    primero = Nucleo("local")
    segundo = None
    try:
        base = {"cliente": "f" * 24, "carpeta_esperada": str(raiz)}

        def operar(accion, **datos):
            return primero.operar_proyecto({**base, "accion": accion, **datos})

        operar("abrir", carpeta=str(raiz), confirmar=True)
        with pytest.raises(PermissionError):
            operar("crear_pagina", nombre="index.html")
        operar("crear_pagina", nombre="index.html", confirmar=True)
        operar("recordar", nombre="index.html")
        original = primero.operar_proyecto({**base, "accion": "leer", "nombre": "index.html"})["texto"]
        (raiz / "index.html").write_text("edición externa")
        with pytest.raises(ValueError, match="cambió en disco"):
            operar("guardar", nombre="index.html", texto="Borrador", original=original, confirmar=True)
        assert (raiz / "index.html").read_text() == "edición externa"
        segundo = Nucleo("local")
        assert segundo.operar_proyecto({**base, "accion": "recordado"}) == {
            "carpeta": str(raiz), "archivo": "index.html"}
        with pytest.raises(ValueError, match="autoriza"):
            segundo.operar_proyecto({**base, "accion": "inspeccionar", "nombre": "index.html"})
    finally:
        primero.ejecutor.shutdown()
        if segundo:
            segundo.ejecutor.shutdown()


def test_sintesis_y_previsualizacion_inerte():
    html = '<h1>Visible</h1><script>alert(1)</script><img src="https://example.org" alt="Imagen del robot">'
    fragmentos = html_estatico(html)
    salida = "".join(t for t, _ in fragmentos)
    assert "Visible" in salida and "alert" not in salida and "https" not in salida
    assert ("Visible", "titulo") in fragmentos
    respuesta = narrar([
        {"especialista": "DARAS", "estado": "ok", "plan": [{"titulo": "Diseñar el robot"}]},
        {"especialista": "CAZEL", "estado": "error", "error": "El aislamiento no pudo iniciar."},
    ])
    assert "Diseñar el robot" in respuesta and "aislamiento" in respuesta
    assert "DARAS (" not in respuesta and "CAZEL (" not in respuesta


def test_solo_formatos_autorizados_salen_al_escritorio(tmp_path, monkeypatch):
    datos = tmp_path / "datos"
    proyecto = tmp_path / "proyecto"
    datos.mkdir()
    proyecto.mkdir()
    (proyecto / "acta.odt").write_bytes(b"simulado")
    (proyecto / "pagina.html").write_text("<script>throw 1</script>")
    monkeypatch.setattr(config, "raiz_datos", lambda: str(datos))
    monkeypatch.setattr(config, "MEMORY_FILE", str(datos / "memoria.json"))
    aperturas = []

    def abrir_documento(ruta):
        aperturas.append(ruta)
        return {"aceptado": True, "aplicacion": "Editor local"}

    monkeypatch.setattr("core.aplicaciones_linux.abrir_documento", abrir_documento)
    nucleo = Nucleo("local", documentos_usuario=True)
    base = {"cliente": "c" * 24, "carpeta_esperada": str(proyecto)}
    try:
        nucleo.operar_proyecto({**base, "accion": "abrir", "carpeta": str(proyecto), "confirmar": True})
        with pytest.raises(PermissionError):
            nucleo.operar_proyecto({**base, "accion": "abrir_externo", "nombre": "acta.odt"})
        with pytest.raises(ValueError):
            nucleo.operar_proyecto({**base, "accion": "abrir_externo", "nombre": "pagina.html", "confirmar": True})
        respuesta = nucleo.operar_proyecto({**base, "accion": "abrir_externo", "nombre": "acta.odt", "confirmar": True})
        assert "Editor local" in respuesta["salida"]
        assert aperturas == [proyecto / "acta.odt"]
    finally:
        nucleo.ejecutor.shutdown()
