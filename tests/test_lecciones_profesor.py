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


def test_universe_enlaza_leccion_aprobada(tmp_path, monkeypatch):
    import config
    from core.ejemplos_aprobados import aprobar
    from universe.nucleo import Nucleo

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    cerebro = Nucleo("local")
    try:
        aprobar(tmp_path / "data" / "ejemplos_aprobados.jsonl", "¿Cuánto es 2+2?", "4",
                procedencia={"verificado": True, "origen": "PROFESOR"})
        nodos = cerebro.nodos()["nodos"]
        leccion = next(n for n in nodos if n["id"].startswith("leccion:"))
        assert leccion["detalle"] == "4"
        assert leccion["vinculos"] == ["aprendizaje:profesor"]
        assert any(n["id"] == leccion["vinculos"][0] for n in nodos)
    finally:
        cerebro.ejecutor.shutdown()


def test_profesor_conserva_la_fuente_publica(tmp_path, monkeypatch):
    import config
    from universe.nucleo import Nucleo

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    monkeypatch.setattr("universe.consultas.consulta_directa", lambda *args, **kwargs: None)
    monkeypatch.setattr("universe.consultas.alternativa_publica",
                        lambda n, pregunta, respuesta: "Fuente pública https://ejemplo.test" if n.investigar_auto else respuesta)
    fuentes = []
    profesor = SimpleNamespace(configurado=True,
                               explicar_fragmentos=lambda pregunta, pasajes: fuentes.extend(pasajes) or "Síntesis")
    cerebro = Nucleo("local", internet=True, investigar_auto=True, profesor=profesor)
    try:
        monkeypatch.setattr(cerebro.chat, "procesar", lambda _: ("No tengo una respuesta fiable.", False))
        resultado = cerebro.conversar("Qué es una simbiosis")
        assert fuentes and "https://ejemplo.test" in fuentes[0]["texto"]
        assert "Síntesis" in resultado["respuesta"] and "https://ejemplo.test" in resultado["respuesta"]
    finally:
        cerebro.ejecutor.shutdown()


def test_simulador_usa_enlace_fijo_y_permiso_de_red(tmp_path, monkeypatch):
    import config
    from universe.nucleo import Nucleo

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    cerebro = Nucleo("local")
    try:
        assert "abrir_url" not in cerebro.conversar("Quiero simular electrónica", modo="escritorio")
        cerebro.internet = True
        assert cerebro.conversar("Quiero simular electrónica")["abrir_url"] == "https://www.falstad.com/circuit/"
        assert cerebro.conversar("Abre Tinkercad")["abrir_url"] == "https://www.tinkercad.com/circuits"
    finally:
        cerebro.ejecutor.shutdown()
