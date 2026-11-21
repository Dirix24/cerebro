import io
import json
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

from agent.controlled_agent import ControlledAgent
from chat import Conversacion
from memory.advanced_memory import AdvancedMemoryManager


def abrir_chat(ruta):
    return Conversacion(None, AdvancedMemoryManager(str(ruta)), ControlledAgent(), modo_local=True)


def test_transportar_recuerdos_entre_sesiones(tmp_path):
    origen = abrir_chat(tmp_path / "origen.json")
    assert "guardados: 1" in origen.procesar("Inserta un recuerdo: proyecto = Atlas")[0]
    exportado = origen.procesar("Extrae recuerdos")[0]
    assert json.loads(exportado) == {"proyecto": "Atlas"}

    ruta = tmp_path / "destino.json"
    destino = abrir_chat(ruta)
    assert "guardados: 1" in destino.procesar(f"/insertar-recuerdo {exportado}")[0]
    assert "ya estaban guardados" in destino.procesar(f"/insertar-recuerdo {exportado}")[0]
    assert "Ya existe un recuerdo distinto" in destino.procesar(
        '/insertar-recuerdo {"ciudad":"Madrid","proyecto":"Otro"}'
    )[0]
    restaurado = abrir_chat(ruta)
    assert restaurado.procesar("¿Qué recuerdas sobre el proyecto?")[0] == "proyecto = Atlas"
    assert json.loads(restaurado.procesar("/extraer-recuerdos")[0]) == {"proyecto": "Atlas"}


def test_deduccion_multietapa_con_ciclo(tmp_path):
    chat = abrir_chat(tmp_path / "memoria.json")
    premisas = "Ada es ave; ave implica animal; animal implica ave; animal implica ser vivo"
    respuesta, _ = chat.procesar(f"Deduce: {premisas} ? ser vivo")
    assert respuesta.splitlines() == [
        "Ada es ave", "ave implica animal", "animal implica ser vivo",
        "Conclusión: Ada es ser vivo.",
    ]
    assert "no permiten deducir" in chat.procesar(f"/deducir {premisas} ? pez")[0]


def test_consulta_web_envia_solo_tema_publico_y_muestra_fuente(tmp_path):
    chat = abrir_chat(tmp_path / "memoria.json")
    chat.procesar("Inserta un recuerdo: proyecto = Atlas")
    url = "https://es.wikipedia.org/wiki/Fotosíntesis"
    paginas = [{"index": 1, "title": "Fotosíntesis", "extract": "Un proceso biológico.",
                "fullurl": url}]
    datos = json.dumps({"query": {"pages": paginas}}).encode()
    with patch("aprendizaje_internet.abrir_api", return_value=io.BytesIO(datos)) as abrir:
        texto, _ = chat.procesar("Busca en internet fotosíntesis")
        solicitud = abrir.call_args.args[0]
        assert parse_qs(urlsplit(solicitud.full_url).query)["gsrsearch"] == ["fotosíntesis"]
        assert "Atlas" not in solicitud.full_url
    assert url in texto and "Un proceso biológico." in texto

    with patch("aprendizaje_internet.abrir_api", side_effect=URLError(TimeoutError())):
        assert "No pude consultar Wikipedia" in chat.procesar("/internet fotosíntesis")[0]
    assert "Atlas" in chat.procesar("/recuerdo proyecto")[0]
