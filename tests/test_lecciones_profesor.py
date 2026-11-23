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
