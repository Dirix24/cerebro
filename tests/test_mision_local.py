import json

import pytest

from core.aislamiento_proyecto import limites_agregados
from core.generacion_proyecto import generar_por_archivos
from core.referencias_locales import buscar


def test_referencias_locales_con_erratas_y_limite_de_tema():
    for consulta in ("circuito integrdao", "circuitos integrados", "capacitor"):
        resultado = buscar(consulta)
        assert resultado is not None
        assert "oldid=" in resultado[1]
    assert buscar("transistor de papel ficticio") is None
    assert buscar("transistor o semiconductor") is None


def test_cgroup_v2_comprueba_cada_limite(tmp_path):
    montaje = tmp_path / "montaje"
    grupo = montaje / "cerebro"
    grupo.mkdir(parents=True)
    registro = tmp_path / "cgroup"
    registro.write_text("0::/cerebro\n")
    valores = {"cpu.max": "100000 100000", "memory.max": str(768 * 1024**2),
               "memory.swap.max": "0", "pids.max": "max"}
    for nombre, valor in valores.items():
        (grupo / nombre).write_text(valor)
    assert limites_agregados(registro, montaje) == ["pids.max"]
    (grupo / "pids.max").write_text("64")
    assert limites_agregados(registro, montaje) == []
    registro.write_text("0::/../fuera\n")
    assert limites_agregados(registro, montaje) == ["cgroup v2 no verificable"]


def test_studio_no_confunde_un_segundo_modulo_con_pruebas():
    consultas = []

    def proponer(consulta):
        consultas.append(consulta)
        nombre = "test_mod.py" if "solo test_mod.py." in consulta else "mod.py"
        return json.dumps({"archivos": [{"nombre": nombre, "texto": "def valor(): return 5"}]})

    with pytest.raises(ValueError, match="no contiene una prueba unittest con aserciones"):
        generar_por_archivos("Crea un proyecto. Archivos planificados: test_mod.py, mod.py", proponer)
    assert len(consultas) == 3
    assert "solo mod.py" in consultas[0]
    assert "assertEqual" in consultas[2]


def test_contraste_no_equivale_a_comparar_todas_las_cifras():
    from core.investigador_local import diferencias_numericas

    manual = {"url": "https://manual.example/a", "extracto": "La temperatura máxima del sensor es 60 °C."}
    ensayo = {"url": "https://ensayo.example/a", "extracto": "La temperatura máxima del sensor es 45 °C."}
    assert diferencias_numericas([manual, ensayo]) == (manual["url"], ensayo["url"])
    assert diferencias_numericas([manual, {**ensayo, "extracto": "La temperatura ambiente es 45 °C."}]) is None
    assert diferencias_numericas([manual, {**ensayo, "url": "https://manual.example/copia"}]) is None


def test_pregunta_historica_es_factual():
    from core.comprension_conversacional import consulta_factual, pide_dato

    assert pide_dato("¿Qué fue la exposición universal de 1889?")
    assert consulta_factual("¿Qué fue la exposición universal de 1889?") == "exposicion universal de 1889"
