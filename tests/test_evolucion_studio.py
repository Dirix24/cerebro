from io import BytesIO
import json
from unittest.mock import MagicMock
from zipfile import ZipFile

import pytest

import config
from core.documentos_oficina import extraer_texto
from core.escritorio_studio import intencion_archivo, intencion_carpeta
from core.matematicas_local import consultar
from core.profesor_local import ProfesorLocal
from universe.nucleo import Nucleo
from universe.tactil import perfil_camara


def paquete(ruta, xml):
    bytes_zip = BytesIO()
    with ZipFile(bytes_zip, "w") as zip_file:
        zip_file.writestr(ruta, xml)
    return bytes_zip.getvalue()


@pytest.mark.parametrize(("mensaje", "fragmento"), [
    ("resuelve la ecuacion 2x+3=11", "x = 4. Comprobación"),
    ("resuelve (x-3)/2=1/3", "x = 11/3"),
    ("cuanto es 0.1 + 0.2", "3/10"),
    ("resuelve x=x", "todo x"),
    ("resuelve x=x+1", "no tiene solución"),
    ("calcula 1/0", "No pude calcularlo"),
    ("resuelve x*x=1", "ecuaciones lineales"),
])
def test_calculo_verificado(mensaje, fragmento):
    assert fragmento in consultar(mensaje)


def test_contexto_y_perfil(monkeypatch):
    assert consultar("calcula __import__('os')") is None
    assert intencion_archivo("Profesor, evalúame") == "evaluar"
    assert intencion_archivo("¿Resúmelo?") == "resumir"
    assert intencion_carpeta("Cerebro, abre mis descargas", {"Descargas": "/ejemplo"}) == "/ejemplo"
    monkeypatch.setenv("CEREBRO_CAMARA_PERFIL", "ligero")
    assert perfil_camara() == (320, 240, 10)


def test_odt_y_xml_hostil():
    espacio = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    xml = f'<raiz xmlns:t="{espacio}"><t:p>Datos <t:span>reales</t:span>.</t:p></raiz>'
    assert extraer_texto(paquete("content.xml", xml), ".odt") == "Datos reales."
    with pytest.raises(ValueError, match="XML"):
        extraer_texto(paquete("content.xml", '<!DOCTYPE x [<!ENTITY a "texto">]><x>&a;</x>'), ".odt")
    with pytest.raises(ValueError, match="profundidad"):
        extraer_texto(paquete("content.xml", "<x>" * 65 + "</x>" * 65), ".odt")


def test_chat_resume_y_evalua_docx_autorizado(tmp_path, monkeypatch):
    datos = tmp_path / "datos"
    datos.mkdir()
    proyecto = tmp_path / "proyecto"
    proyecto.mkdir()
    xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:p><w:r><w:t>La fotosíntesis transforma la energía luminosa.</w:t></w:r></w:p></w:document>')
    bruto = paquete("word/document.xml", xml)
    (proyecto / "guia.docx").write_bytes(bruto)
    monkeypatch.setattr(config, "raiz_datos", lambda: str(datos))
    monkeypatch.setattr(config, "MEMORY_FILE", str(datos / "memoria.json"))
    n = Nucleo("local")
    cliente = "e" * 24
    contexto = {"carpeta": str(proyecto), "nombre": "guia.docx"}
    try:
        n.operar_proyecto({"cliente": cliente, "accion": "abrir", "carpeta": str(proyecto), "confirmar": True})
        vista = n.operar_proyecto({"cliente": cliente, "accion": "inspeccionar",
                                    "carpeta_esperada": str(proyecto), "nombre": "guia.docx"})
        assert vista["solo_lectura"] and "fotosíntesis" in vista["texto"]
        assert "fotosíntesis" in n.conversar("Resúmelo", "studio", cliente, contexto)["respuesta"]
        ejercicio = n.conversar("Profesor, evalúame", "studio", cliente, contexto)["documento"]["ejercicio"]
        assert "____" in ejercicio["pregunta"] and "respuesta_esperada" not in ejercicio
        assert n.operar_proyecto({"cliente": cliente, "accion": "responder_ejercicio",
                                    "respuesta": "fotosíntesis"})["correcta"]
        assert n.conversar("Resuelve 2x+3=11")["origen"] == "matematicas_local"
        diagnostico = n.conversar("Diagnóstico del equipo")
        assert "RAM" in diagnostico["respuesta"] and isinstance(diagnostico["recursos"]["programas"]["thunar"], bool)
        with pytest.raises(ValueError, match="autoriza"):
            n.conversar("Resúmelo", "studio", "f" * 24, contexto)
        assert (proyecto / "guia.docx").read_bytes() == bruto
    finally:
        n.ejecutor.shutdown()


def test_ollama_usa_http_local_y_descarga_el_modelo_tras_consulta(monkeypatch):
    conexion = MagicMock()
    respuesta = conexion.getresponse.return_value.__enter__.return_value
    respuesta.status = 200
    respuesta.read.return_value = b'{"message":{"content":"Una respuesta"}}'
    conectar = MagicMock(return_value=conexion)
    monkeypatch.setattr("core.profesor_local.HTTPConnection", conectar)
    monkeypatch.setenv("CEREBRO_OLLAMA_MODELO", "qwen2.5:0.5b")
    assert ProfesorLocal.desde_entorno().conversar("Hola Cerebro") == "Una respuesta"
    conectar.assert_called_once_with("127.0.0.1", 11434, timeout=40)
    metodo, ruta, carga, _ = conexion.request.call_args.args
    assert (metodo, ruta) == ("POST", "/api/chat")
    assert json.loads(carga)["keep_alive"] == 0


def test_ollama_rechaza_modelo_cloud():
    with pytest.raises(ValueError, match="local"):
        ProfesorLocal(11434, ollama="modelo:14b-cloud")
