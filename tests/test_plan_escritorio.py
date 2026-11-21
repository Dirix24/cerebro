from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

import config
from agent.plan_escritorio import elaborar, url_navegable
from core import aplicaciones_linux, documentos_usuario
from universe.nucleo import Nucleo


@pytest.fixture
def nucleo(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    (tmp_path / "Documentos").mkdir()
    (tmp_path / "Descargas").mkdir()
    motor = Nucleo("local", internet=True, documentos_usuario=True)
    yield motor
    motor.ejecutor.shutdown()


def test_youtube_y_enlaces_permisos_y_codificacion(nucleo):
    for pregunta in ("Cerebro, abre YouTube y busca un tutorial de Blender",
                     "Busca tutoriales de Blender en YouTube"):
        resultado = nucleo.conversar(pregunta)
        url = urlsplit(resultado["abrir_url"])
        assert url.hostname == "www.youtube.com" and url.path == "/results"
        assert "blender" in parse_qs(url.query)["search_query"][0]
    assert nucleo.conversar("Abre este enlace https://example.org/")["abrir_url"] == "https://example.org/"
    for invalid in ("file:///tmp/demo", "https://user:pass@example.org", "https://example.org:99999"):
        assert url_navegable(invalid) is None
    nucleo.internet = False
    with pytest.raises(PermissionError):
        nucleo.conversar("Busca tutoriales de Blender en YouTube")


def test_busqueda_tipos_y_apertura_recordada(nucleo, tmp_path, monkeypatch):
    documentos = tmp_path / "Documentos"
    for archivo in ("Matemáticas.pdf", "Otro.pdf", "vacaciones.png", "modelo.blend", "texto.odt"):
        (documentos / archivo).touch()
    (tmp_path / "Descargas" / "vacaciones.mp4").touch()
    (documentos / "externo.pdf").symlink_to(tmp_path / "memoria.json")
    abiertos = []

    def abrir(ruta):
        abiertos.append(ruta)
        return {"aceptado": True, "formato": "application/pdf", "aplicacion": "Visor"}

    monkeypatch.setattr(aplicaciones_linux, "abrir_documento", abrir)
    assert "Matemáticas.pdf" in nucleo.conversar("Cerebro, búscame todos mis PDF")["respuesta"]
    assert "vacaciones.png" in nucleo.conversar("Encuentra las fotos de vacaciones")["respuesta"]
    assert "vacaciones.mp4" in nucleo.conversar("Busca los vídeos que descargué esta semana")["respuesta"]
    assert "aceptó la apertura" in nucleo.conversar("Abre mi PDF de matematcas")["respuesta"]
    assert abiertos[-1].name == "Matemáticas.pdf"
    assert "Recordaré" in nucleo.conversar("Sí, recuérdalo")["respuesta"]
    assert "Recordaré" not in nucleo.conversar("Abre mi PDF de matematcas")["respuesta"]
    nucleo.conversar("Abre Blender y busca mi último proyecto")
    assert abiertos[-1].name == "modelo.blend"
    assert not documentos_usuario.permitido(documentos / "externo.pdf")
    assert elaborar("Abre el proyecto de Blender que modifiqué ayer")[0].argumentos["periodo"] == "ayer"
    nucleo.agente.permisos_concedidos.discard("READ")
    with pytest.raises(PermissionError):
        nucleo.conversar("Encuentra las fotos de vacaciones")


def test_resumen_verificado_y_confirmacion_por_cliente(nucleo, tmp_path, monkeypatch):
    (tmp_path / "Documentos" / "física.pdf").touch()
    monkeypatch.setattr("universe.consultas._leer_texto", lambda ruta: "La luz se propaga.")
    monkeypatch.setattr(aplicaciones_linux, "abrir_documento", lambda _: {"aceptado": True})
    cliente = "a" * 24
    orden = "Busca mis PDF de física, abre el más reciente, hazme un resumen y guárdalo en una carpeta"
    assert "La luz se propaga" in nucleo.conversar(orden, cliente=cliente)["respuesta"]
    assert not list(nucleo.estudio.glob("resumenes/*"))
    nucleo.conversar("Confirmar guardar resumen", cliente="b" * 24)
    assert not list(nucleo.estudio.glob("resumenes/*"))
    assert "Guardé y verifiqué" in nucleo.conversar("Confirmar guardar resumen", cliente=cliente)["respuesta"]
    assert "La luz se propaga" in next(nucleo.estudio.glob("resumenes/*")).read_text()


def test_solo_analiza_enlaces_wikipedia_y_recuerda_por_cliente(nucleo, monkeypatch):
    consultas = []
    def consultar(url):
        consultas.append(url)
        return {"query": {"pages": [{"title": "Óptica", "extract": "La óptica estudia la luz."}]}}
    monkeypatch.setattr("core.fuentes_publicas.consultar_json", consultar)
    a, b = "a" * 24, "b" * 24
    nucleo.conversar("Abre https://es.wikipedia.org/wiki/Óptica", cliente=a)
    assert "Pega un enlace" in nucleo.conversar("Analiza este enlace", cliente=b)["respuesta"]
    assert "estudia la luz" in nucleo.conversar("Analiza este enlace", cliente=a)["respuesta"]
    assert parse_qs(urlsplit(consultas[0]).query)["titles"] == ["Óptica"]
    assert "no se consultó" in nucleo.conversar("Analiza este enlace https://example.org")["respuesta"]
    assert len(consultas) == 1


def test_busqueda_por_contenido_es_explicitamente_local(nucleo, tmp_path):
    documentos = tmp_path / "Documentos"
    (documentos / "notas.md").write_text("Presupuesto aéreo confirmado")
    (documentos / "otro.txt").write_text("Texto de otro tema")
    secreto = tmp_path / "fuera.txt"
    secreto.write_text("Presupuesto aéreo")
    (documentos / "enlace.txt").symlink_to(secreto)
    orden = "Busca en el contenido de mis documentos: presupuesto aereo"
    respuesta = nucleo.conversar(orden)["respuesta"]
    assert "notas.md" in respuesta
    assert "fuera.txt" not in respuesta and "enlace.txt" not in respuesta
    assert "confirmado" not in respuesta
    nucleo.agente.permisos_concedidos.discard("READ")
    with pytest.raises(PermissionError):
        nucleo.conversar(orden)


def test_busqueda_reciente_no_confunde_truncado_de_resultados_con_ambito_parcial(tmp_path):
    import os

    documentos = tmp_path / "Documentos"
    documentos.mkdir()
    for indice in range(20):
        ruta = documentos / f"fisica {indice:02d}.pdf"
        ruta.touch()
        os.utime(ruta, (1700000000 + indice, 1700000000 + indice))
    rutas, limitado = documentos_usuario.buscar_filtrado("pdf", "fisica", hogar=tmp_path, reciente=True)
    assert not limitado
    assert [ruta.name for ruta in rutas] == ["fisica 19.pdf"]


def test_busqueda_por_contenido_revisa_mas_de_doce_archivos(tmp_path):
    import os

    documentos = tmp_path / "Documentos"
    documentos.mkdir()
    for indice in range(20):
        ruta = documentos / f"nota {indice:02d}.txt"
        ruta.write_text("hallazgo importante" if indice == 0 else "otra nota")
        os.utime(ruta, (1700000000 + indice, 1700000000 + indice))
    rutas, limitado = documentos_usuario.buscar_por_contenido("hallazgo importante", hogar=tmp_path)
    assert not limitado
    assert [ruta.name for ruta in rutas] == ["nota 00.txt"]


def test_busqueda_por_extension_con_tema(nucleo, tmp_path):
    documentos = tmp_path / "Documentos"
    (documentos / "física.odt").touch()
    (documentos / "física.docx").touch()
    respuesta = nucleo.conversar("Busca documentos ODT de física")["respuesta"]
    assert "física.odt" in respuesta
    assert "física.docx" not in respuesta
