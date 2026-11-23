import pytest

from core.comprension_conversacional import consulta_factual
from core.generacion_proyecto import reparar_adicion_no_mutante, revisar_importaciones_locales
from core.matematicas_local import consultar_medidas
from core.respuestas_con_fuentes import seleccion_publica


@pytest.mark.parametrize(("pregunta", "esperado"), [
    ("¿Pasa 0,042 m a milímetros?", "42 mm"),
    ("¿Cuánto es el -25 % de 318,50?", "-79,625"),
    ("Convierte 60000 ms a s", None),
    ("Convierte 2 h a kg", "magnitudes distintas"),
    ("Convierte 2 m a cm y borra archivos", None),
])
def test_medidas_acotadas(pregunta, esperado):
    resultado = consultar_medidas(pregunta)
    if esperado is None:
        assert resultado is None
    else:
        assert esperado in resultado


def test_seleccion_de_fuentes_y_pregunta():
    correcta = {"title": "Magnetorrecepción", "extract": "Algunos animales detectan campos magnéticos.",
                "fullurl": "https://es.wikipedia.org/wiki/Magnetorrecepcion"}
    irrelevante = {**correcta, "title": "Magnetización"}
    tema = consulta_factual("Dime qué significa la magnetorcepción por favor")
    assert tema == "magnetorcepcion"
    assert seleccion_publica(tema, [irrelevante, correcta]) == (correcta["extract"], correcta["fullurl"])
    assert seleccion_publica(tema, [irrelevante]) is None
    assert seleccion_publica(tema, [{**correcta, "pageprops": {"disambiguation": ""}}]) is None
    assert seleccion_publica(tema, [{**correcta, "fullurl": "https://es.wikipedia.org.example/wiki/a"}]) is None


def test_importaciones_modulares_relativas_y_absolutas():
    proyecto = {
        "motor/operaciones.py": "def total(): return 5\n",
        "motor/calculo.py": "from .operaciones import total\n",
        "main.py": "from motor.calculo import total\nimport math\n",
    }
    revisar_importaciones_locales(proyecto)
    for defectuoso in ("from .operacion import total", "import motor.operacion", "from motor import operacion"):
        with pytest.raises(ValueError, match=r"motor/calculo.py:1: falta"):
            revisar_importaciones_locales({**proyecto, "motor/calculo.py": defectuoso})


def test_fallo_logico_multimodulo_requiere_pruebas_de_comportamiento(tmp_path):
    """Fixture revisada y escrita a mano. El ejecutor del producto conserva su bloqueo."""
    import subprocess
    import sys

    modulos = {
        "agregar.py": "from normaliza import limpiar\ndef agregar(items, texto):\n    items.append(limpiar(texto))\n",
        "normaliza.py": "def limpiar(texto): return texto.strip()\n",
        "test_agregar.py": (
            "import unittest\nfrom agregar import agregar\n"
            "class Prueba(unittest.TestCase):\n"
            "    def test_lista_nueva(self):\n"
            "        original = ['a']\n"
            "        self.assertEqual(agregar(original, ' b '), ['a', 'b'])\n"
            "        self.assertEqual(original, ['a'])\n"
        ),
    }
    revisar_importaciones_locales(modulos)
    for nombre, codigo in modulos.items():
        (tmp_path / nombre).write_text(codigo, encoding="utf-8")
    comando = [sys.executable, "-B", "-m", "unittest", "discover"]
    fallo = subprocess.run(comando, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert fallo.returncode == 1 and "AssertionError: None != ['a', 'b']" in fallo.stderr
    assert reparar_adicion_no_mutante("Implementa agregar(items,texto) con una lista nueva", modulos)
    (tmp_path / "agregar.py").write_text(modulos["agregar.py"], encoding="utf-8")
    bien = subprocess.run(comando, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert bien.returncode == 0 and "Ran 1 test" in bien.stderr


def test_seguimiento_no_reutiliza_un_tema_anterior_si_falta_evidencia(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import config
    from universe.nucleo import Nucleo

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))

    def inventar(*_):
        pytest.fail("No debe responder sobre un tema previo tras una consulta sin evidencia.")

    n = Nucleo("local", profesor=SimpleNamespace(configurado=True, conversar=inventar))
    try:
        assert n.conversar("¿Qué es un portátil?")["origen"] == "glosario_local"
        n.conversar("¿Cuándo se celebró la cumbre Xiloria?")
        resultado = n.conversar("Explícamelo más fácil")
        assert resultado["origen"] == "evidencia_insuficiente"
        assert "aportar una referencia" in resultado["respuesta"]
    finally:
        n.ejecutor.shutdown()


def test_contraste_requiere_las_dos_fuentes_e_indica_ausencia_de_red():
    from core.lecciones_colectivas import FUENTES_CONTRASTE, _contraste

    evidencia = [{"tipo": "fuente", "url": url, "titulo": titulo, "extracto": texto}
                 for url, titulo, texto in FUENTES_CONTRASTE]
    assert _contraste({"evidencia": evidencia, "red_autorizada": False})[1] == "no"
    assert _contraste({"evidencia": evidencia[:1], "red_autorizada": False}) is None
    assert _contraste({"evidencia": evidencia, "red_autorizada": True}) is None
