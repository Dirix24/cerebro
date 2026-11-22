from datetime import datetime, timedelta, timezone
import json
from subprocess import CompletedProcess

import pytest

import config
from core.escritorio_studio import pagina_solicitada, recuperar_fragmentos
from core.recordatorios_locales import cancelar, crear, interpretar, listar, notificar_locales
from universe.nucleo import Nucleo


@pytest.mark.parametrize(("orden", "dia", "hora", "minuto"), [
    ("Recuérdame que en cinco minutos tengo examen", 22, 10, 5),
    ("Recuérdame que tengo examen en una hora", 22, 11, 0),
    ("Recuérdame mañana a las nueve que tengo examen", 23, 9, 0),
    ("Recuérdame el próximo lunes que tengo examen", 23, 9, 0),
    ("Recuérdame esta tarde que tengo examen", 22, 17, 0),
])
def test_fechas_locales(orden, dia, hora, minuto):
    ahora = datetime(2026, 11, 22, 10, tzinfo=timezone(timedelta(hours=1)))
    fecha, texto = interpretar(orden, ahora)
    assert datetime.fromisoformat(fecha) == ahora.replace(day=dia, hour=hora, minute=minuto)
    assert "tengo examen" in texto


def test_recordatorios_persistentes_cancelacion_y_aviso(tmp_path, monkeypatch):
    archivo = tmp_path / "recordatorios.json"
    ahora = datetime.now(timezone.utc)
    registro = crear((ahora + timedelta(minutes=5)).isoformat(), "Examen", archivo)
    assert listar(archivo)[0]["texto"] == "Examen"
    assert cancelar(registro["id"], archivo)
    assert not cancelar(registro["id"], archivo)

    datos = listar(archivo)
    datos += [{"id": "vencido", "fecha": (ahora - timedelta(minutes=1)).isoformat(),
               "texto": "<Examen>", "completado": False}]
    archivo.write_text(json.dumps(datos))
    avisos = []
    monkeypatch.setattr("shutil.which", lambda programa: programa)
    monkeypatch.setattr("subprocess.run", lambda argv, **kwargs: avisos.append(argv) or CompletedProcess(argv, 0))
    assert notificar_locales(archivo) == 1
    assert notificar_locales(archivo) == 0
    assert avisos[0][-1] == "&lt;Examen&gt;"
    assert listar(archivo)[-1]["notificado"]


def test_consultas_y_terminal_sin_ejecutar_codigo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    monkeypatch.setattr(config, "CEREBRO_HOME", str(tmp_path))
    nucleo = Nucleo("local")
    destino = tmp_path / "marca"
    try:
        codigo = f"import pathlib\npathlib.Path({str(destino)!r}).touch()"
        resultado = nucleo.conversar(codigo, "terminal")
        assert resultado["origen"] == "analisis_python"
        assert "pathlib" in resultado["respuesta"] and not destino.exists()
        assert "línea 1" in nucleo.conversar("def prueba()", "terminal")["respuesta"]
        recordatorio = nucleo.conversar("Recuérdame que en cinco minutos tengo examen")["respuesta"]
        assert "Recordatorio guardado" in recordatorio
        identificador = listar()[0]["id"]
        assert "cancelado" in nucleo.conversar("/cancelar-recordatorio " + identificador)["respuesta"]
    finally:
        nucleo.ejecutor.shutdown()
    assert pagina_solicitada("Profesor, explícame la página cuatro") == 4
    assert recuperar_fragmentos("¿Qué dice sobre energía solar?", ["Primera página.", "Energía solar disponible."]) == [
        (2, "Energía solar disponible.")]



def test_pdf_poppler_navegacion_y_renderizado(tmp_path):
    from shutil import which

    from core.proyecto_studio import ProyectoStudio
    from tests.pdf_fixture import pdf_fixture

    if not all(which(programa) for programa in ("pdfinfo", "pdftotext", "pdftoppm", "prlimit")):
        pytest.skip("Poppler y prlimit son necesarios para comprobar el PDF real.")
    (tmp_path / "guia.pdf").write_bytes(pdf_fixture())
    proyecto = ProyectoStudio(str(tmp_path))
    pagina = proyecto.inspeccionar("guia.pdf", pagina=2, resolucion=1200)
    assert pagina["pagina"] == pagina["paginas"] == 2
    assert "energia solar" in pagina["texto"] and pagina["base64"]
    assert proyecto.buscar_pdf("guia.pdf", "solar")["coincidencias"][0]["pagina"] == 2
    assert "entre 1 y 2" in proyecto.inspeccionar("guia.pdf", pagina=3)["aviso"]
