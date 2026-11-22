from unittest.mock import patch

import pytest

import config
from core.escritorio_studio import archivo_soltado, carpetas_personales, validar_archivo
from core.proyecto_studio import ProyectoStudio
from universe.lanzador import RelevoInterfaz
from universe.nucleo import Nucleo


def test_xdg_local_y_uri(tmp_path):
    configuracion = tmp_path / "config"
    configuracion.mkdir()
    destino = tmp_path / "Documentos de prueba"
    destino.mkdir()
    (configuracion / "user-dirs.dirs").write_text('XDG_DOCUMENTS_DIR="$HOME/Documentos de prueba"\n'
                                                'XDG_MUSIC_DIR="$(run-not-allowed)"\n')
    assert carpetas_personales(tmp_path, configuracion) == [{"nombre": "Documentos", "ruta": str(destino)}]
    archivo = destino / "robot 1.py"
    assert archivo_soltado(archivo.as_uri()) == archivo
    with pytest.raises(ValueError):
        archivo_soltado("file://remoto/etc/passwd")


def test_relevo_no_arranca_otra_ventana_si_hay_una_activa():
    relevo = RelevoInterfaz()
    with patch("universe.lanzador.acompanante_activo", return_value=False), patch(
            "universe.lanzador.lanzar_acompanante") as lanzar:
        relevo.revisar("escritorio")
        relevo.revisar("studio")
        relevo.revisar("chat")
        lanzar.assert_not_called()
        relevo.revisar("escritorio")
        relevo.revisar("escritorio")
        lanzar.assert_called_once()


def test_documento_suelto_privado_evaluacion_y_preferencias(tmp_path, monkeypatch):
    datos = tmp_path / "datos"
    datos.mkdir()
    documento = tmp_path / "informe.txt"
    contenido = "La fotosíntesis transforma la energía luminosa.\nExplica el proceso.\n"
    documento.write_text(contenido)
    monkeypatch.setattr(config, "raiz_datos", lambda: str(datos))
    monkeypatch.setattr(config, "MEMORY_FILE", str(datos / "memoria.json"))
    n = Nucleo("local")
    base = {"cliente": "e" * 24}

    def operar(accion, **datos):
        return n.operar_proyecto({**base, "accion": accion, **datos})

    try:
        with pytest.raises(PermissionError):
            operar("abrir_suelto", ruta=documento.as_uri())
        assert operar("abrir_suelto", ruta=documento.as_uri(), confirmar=True)["texto"] == contenido
        assert "fotosíntesis" in operar("herramienta_suelto", herramienta="resumir")["salida"]
        ejercicio = operar("herramienta_suelto", herramienta="evaluar")["ejercicio"]
        assert "____" in ejercicio["pregunta"] and "respuesta_esperada" not in ejercicio
        assert operar("responder_ejercicio", respuesta="fotosíntesis", guardar=True)["correcta"]
        documento.write_text(contenido + "Cambio externo.")
        assert "Cambio externo." in operar("suelto")["texto"]
        assert operar("tactil", valor=True)["tactil"] and operar("escritorio")["tactil"]
        assert documento.read_text() == contenido + "Cambio externo."
    finally:
        n.ejecutor.shutdown()


def test_reversion_con_conflicto_y_validaciones(tmp_path):
    raiz = tmp_path / "p"
    raiz.mkdir()
    archivo = raiz / "demo.py"
    original = "def demo()\n    return 1\n"
    archivo.write_text(original)
    proyecto = ProyectoStudio(str(raiz))
    identificador = proyecto.analizar()["propuestas"][0]["id"]
    proyecto.aplicar(identificador)
    editado = archivo.read_text()
    archivo.write_text("x = 5\n")
    with pytest.raises(ValueError, match="cambió en disco"):
        proyecto.cambiar_propuesta("revertir", identificador)
    archivo.write_text(editado)
    proyecto.cambiar_propuesta("revertir", identificador)
    assert archivo.read_text() == original
    identificador = proyecto.analizar()["propuestas"][0]["id"]
    proyecto.cambiar_propuesta("rechazar", identificador)
    with pytest.raises(ValueError):
        proyecto.aplicar(identificador)
    assert validar_archivo('{"ok":1}', "x.json") == "Documento JSON válido."
    with pytest.raises(ValueError, match="columnas"):
        validar_archivo("a,b\n1,2,3\n", "x.csv")
