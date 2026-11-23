import json

import pytest
from types import SimpleNamespace

from entrenar_ejemplos_aprobados import preparar
from universe.ensenanza import Ensenanza


def test_verifica_y_solo_exporta_despues_de_aprobar(tmp_path):
    profesor = SimpleNamespace(configurado=True, proponer_variante=lambda _: 15,
                              resolver_leccion=lambda _: "79")
    nucleo = SimpleNamespace(raiz=tmp_path, profesor=profesor, exigir_permisos=lambda *p: None)
    ensenanza = Ensenanza()
    cliente = ("studio", "chat")
    banco = tmp_path / "data" / "ejemplos_aprobados.jsonl"
    respuesta = ensenanza.consultar(nucleo, "profesor prepara una leccion de matematicas", cliente)
    assert respuesta["leccion"]["respuesta"] == "79"
    assert not banco.exists()
    otro = ensenanza.consultar(nucleo, "aprueba leccion del profesor", ("otro", "chat"))
    assert "primero" in otro["respuesta"]
    assert not banco.exists()
    ensenanza.consultar(nucleo, "aprueba leccion del profesor", cliente)
    registro = json.loads(banco.read_text())
    assert registro["procedencia"]["origen"] == "PROFESOR"
    for alumno in ("CEREBRO", "DARAS", "CAZEL"):
        destino = tmp_path / (alumno + ".jsonl")
        assert preparar(banco, destino, aplicar=True, alumno=alumno)["ejemplos"] == 1
        assert json.loads(destino.read_text()) == registro
    assert preparar(banco, tmp_path / "corpus.txt")["ejemplos"] == 1


@pytest.mark.parametrize("incorrecta", ["42", "-79"])
def test_modelo_equivocado_no_prepara_leccion(tmp_path, incorrecta):
    profesor = SimpleNamespace(configurado=True, proponer_variante=lambda _: 15,
                              resolver_leccion=lambda _: incorrecta)
    nucleo = SimpleNamespace(raiz=tmp_path, profesor=profesor, exigir_permisos=lambda *p: None)
    ensenanza = Ensenanza()
    respuesta = ensenanza.consultar(nucleo, "prepara leccion de matematicas", ("a", "b"))
    assert "referencia independiente" in respuesta["respuesta"]
    assert not ensenanza.lecciones


def test_equipo_profesor_sintetiza_y_respeta_el_permiso_de_red(tmp_path, monkeypatch):
    import config
    from universe.nucleo import Nucleo

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    llamadas = []

    def consulta(region, accion, objetivo, *, red, cancelacion):
        llamadas.append((region, red))
        return {"especialista": region, "estado": "ok", "version": 1}

    revisiones = []

    def sintetizar(objetivo, aportes):
        assert objetivo == "calcula 2+2"
        assert [a["especialista"] for a in aportes[:3]] == ["DARAS", "CAZEL", "CEREBRO"]
        assert "4" in aportes[2]["extracto"]
        if revisiones:
            assert aportes[-1]["estado"] == "revision_anterior_sin_verificar"
        revisiones.append(aportes)
        return "Conclusión conjunta de prueba."

    monkeypatch.setattr("universe.especialidades._consulta", consulta)
    cerebro = Nucleo("local", profesor=SimpleNamespace(configurado=True, sintetizar_equipo=sintetizar))
    try:
        salida = cerebro.conversar("Consulta al equipo en internet: calcula 2+2", modo="studio")
        assert "Conclusión conjunta" in salida["respuesta"]
        assert "Internet está desactivado" in salida["respuesta"]
        assert sorted(llamadas) == [("CAZEL", False), ("DARAS", False)]
        cerebro.internet = True
        llamadas.clear()
        cerebro.conversar("Consulta al equipo en internet: calcula 2+2")
        assert len(revisiones) == 2
        assert sorted(llamadas) == [("CAZEL", False), ("DARAS", True)]
    finally:
        cerebro.ejecutor.shutdown()


def test_perfil_se_adapta_a_recursos(monkeypatch):
    from core import recursos_locales

    recursos = {"cpu_logicas": 4, "memoria_mib": {"MemAvailable": 2048}}
    monkeypatch.setattr(recursos_locales, "inspeccionar", lambda _: recursos)
    assert recursos_locales.perfil_equipo(".") == "ligero"
    recursos["memoria_mib"]["MemAvailable"] = 8192
    assert recursos_locales.perfil_equipo(".") == "normal"
