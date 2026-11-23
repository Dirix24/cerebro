import ast
import json
from types import SimpleNamespace

import pytest

import config
from core.comprension_conversacional import consulta_python_literal
from core.generacion_proyecto import generar_por_archivos, reparar_adicion_no_mutante
from universe.nucleo import Nucleo


def test_plan_no_acepta_traversal_ni_conflicto_y_no_llama_modelo():
    def no_llamar(_):
        pytest.fail("El plan se debe validar completo antes de llamar al motor.")

    for plan in ("../fuera.py", "/tmp/fuera.py", "a.py, a.py", "a.py, a.py/b.py", "src/.oculto.py"):
        with pytest.raises(ValueError):
            generar_por_archivos("Crea un proyecto. Archivos planificados: " + plan, no_llamar)


def test_mas_de_seis_modulos_se_publican_solo_tras_aprobacion(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    carpeta = tmp_path / "proyectos"
    carpeta.mkdir()
    nombres = [f"src/modulo{i}.py" for i in range(7)]
    pedidos = iter(nombres)
    def proponer(consulta):
        nombre = next(pedidos).split("/")[-1]
        assert f"solo {nombre}" in consulta
        return json.dumps({"archivos": [{"nombre": nombre, "texto": "valor = 1"}]})

    n = Nucleo("local", profesor=SimpleNamespace(configurado=True, proponer_proyecto=proponer))
    datos = {"cliente": "a" * 24, "carpeta_esperada": str(carpeta)}
    try:
        n.operar_proyecto({**datos, "accion": "abrir", "carpeta": str(carpeta), "confirmar": True})
        pedido = "Crea un proyecto modular. Archivos planificados: " + ", ".join(nombres)
        propuesta = n.conversar(pedido, modo="studio", cliente=datos["cliente"])["generacion"]
        assert propuesta["archivos"] == nombres
        publicar = {**datos, "accion": "publicar_generado", "id": propuesta["id"], "nombre": "modular"}
        assert not (carpeta / "modular").exists()
        with pytest.raises(PermissionError):
            n.operar_proyecto(publicar)
        resultado = n.operar_proyecto({**publicar, "confirmar": True})
        assert len(resultado["archivos"]) == 7
        assert (carpeta / "modular" / nombres[-1]).read_text() == "valor = 1\n"
    finally:
        n.ejecutor.shutdown()


def test_reparacion_del_gestor_respeta_lista_nueva_sin_ejecutar_codigo():
    archivos = {"tareas.py": "def agregar(tareas, titulo): tareas.append(titulo)\n"}
    assert reparar_adicion_no_mutante("Define agregar(tareas,titulo) con una lista nueva", archivos)
    esperado = ast.parse("def agregar(tareas,titulo): return tareas + [titulo]")
    assert ast.dump(ast.parse(archivos["tareas.py"])) == ast.dump(esperado)
    assert not reparar_adicion_no_mutante("Define agregar(tareas,titulo) con una lista nueva", archivos)
    variante = {"otro.py": "def agregar(tareas, titulo): return tareas.append(titulo)\n"}
    assert not reparar_adicion_no_mutante("Define agregar(tareas,titulo)", variante)


@pytest.mark.parametrize("entrada", ["¿Qué devuelve len(open('datos'))?", "¿Qué retorna len([1] * 50)?"])
def test_len_solo_acepta_literales(entrada):
    assert consulta_python_literal("¿Qué devuelve len({1, 1, 2})?") == "Python devuelve 2."
    assert consulta_python_literal(entrada) is None


def test_importaciones_externas_distinguen_biblioteca_y_archivo_local():
    from core.generacion_proyecto import dependencias_externas

    assert dependencias_externas({
        "principal.py": "import json\nfrom src.modulo import valor\nimport externo_demo.api",
        "src/modulo.py": "valor = 1",
    }) == ["externo_demo"]


def test_modulo_reintenta_una_vez_si_usa_simbolo_sin_definir():
    consultas = []
    def proponer(consulta):
        consultas.append(consulta)
        codigo = "print(VALOR)" if len(consultas) == 1 else "VALOR = 7\nprint(VALOR)"
        return json.dumps({"archivos": [{"nombre": "demo.py", "texto": codigo}]})
    r = generar_por_archivos("Crea un proyecto con VALOR. Archivos planificados: src/demo.py", proponer)
    assert len(consultas) == 2 and "Declara o importa antes de usar: VALOR" in consultas[1]
    assert "VALOR = 7" in r["src/demo.py"]


def test_no_publica_plan_si_el_modelo_oculta_el_nombre_indefinido_en_una_funcion():
    variantes = iter(("print(FALTA)", "def main(): print(FALTA)"))

    def proponer(_):
        return json.dumps({"archivos": [{"nombre": "demo.py", "texto": next(variantes)}]})

    with pytest.raises(ValueError, match="FALTA"):
        generar_por_archivos("Crea un proyecto. Archivos planificados: src/demo.py", proponer)
