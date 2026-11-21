from pathlib import Path

import pytest

import config
from universe.nucleo import Nucleo


def test_proyecto_real_propuesta_confirmacion_revocacion_y_unittest(tmp_path, monkeypatch):
    datos = tmp_path / "datos"
    datos.mkdir()
    proyecto = tmp_path / "proyecto"
    proyecto.mkdir()
    fuente = proyecto / "cuentas.py"
    fuente.write_text("def sumar(a, b)\n    return a + b\n")
    (proyecto / "tests").mkdir()
    (proyecto / "tests" / "test_cuentas.py").write_text(
        "import unittest\nfrom cuentas import sumar\n"
        "class Operaciones(unittest.TestCase):\n"
        "    def test_suma(self):\n        self.assertEqual(sumar(2, 3), 5)\n")
    (proyecto / "enlace.py").symlink_to(fuente)
    monkeypatch.setattr(config, "raiz_datos", lambda: str(datos))
    monkeypatch.setattr(config, "MEMORY_FILE", str(datos / "memoria.json"))
    nucleo = Nucleo("local")
    cliente = "a" * 24

    def operar(accion, **carga):
        return nucleo.operar_proyecto({"accion": accion, "cliente": cliente,
                                       "carpeta_esperada": str(proyecto), **carga})

    try:
        with pytest.raises(PermissionError):
            operar("abrir", carpeta=str(proyecto))
        estado = operar("abrir", carpeta=str(proyecto), confirmar=True)
        assert "cuentas.py" in estado["archivos"] and "enlace.py" not in estado["archivos"]
        with pytest.raises(PermissionError):
            operar("leer", nombre="enlace.py")
        with pytest.raises(ValueError):
            operar("leer", nombre="../fuera.py")
        informe = operar("analizar")
        (propuesta,) = informe["propuestas"]
        assert "-def sumar(a, b)" in propuesta["diff"] and "+def sumar(a, b):" in propuesta["diff"]
        assert fuente.read_text().startswith("def sumar(a, b)\n")
        with pytest.raises(PermissionError):
            operar("aplicar", id=propuesta["id"], confirmar=False)
        fuente.write_text("# cambio externo\n" + fuente.read_text())
        with pytest.raises(ValueError, match="cambió en disco"):
            operar("aplicar", id=propuesta["id"], confirmar=True)
        propuesta = operar("analizar")["propuestas"][0]
        nucleo.agente.permisos_concedidos.discard("WRITE")
        with pytest.raises(PermissionError):
            operar("aplicar", id=propuesta["id"], confirmar=True)
        nucleo.agente.permisos_concedidos.add("WRITE")
        operar("aplicar", id=propuesta["id"], confirmar=True)
        assert "válida" in operar("validar", nombre="cuentas.py")["salida"]
        assert operar("pruebas", confirmar=True)["id"]
    finally:
        nucleo.ejecutor.shutdown()
    resultado = nucleo.tareas[-1]["salida"]
    if "No se ejecutó" in resultado or "No se ejecutaron" in resultado:
        assert nucleo.tareas[-1]["estado"] == "error"
        return
    assert nucleo.tareas[-1]["estado"] == "terminada", resultado
    assert "Ran 1 test" in nucleo.tareas[-1]["salida"]


def test_documento_contextual_responde_con_pasaje_y_respeta_read(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    nucleo = Nucleo("local")
    try:
        nucleo.guardar("acta.txt", "El presupuesto aprobado es 750 euros. El viaje saldrá el lunes.")
        nucleo.conversar("Analiza acta.txt")
        pregunta = "¿Qué dice el documento adjunto sobre el presupuesto?"
        respuesta = nucleo.conversar(pregunta)["respuesta"]
        assert "acta.txt" in respuesta and "750 euros" in respuesta and "lunes" not in respuesta
        assert pregunta not in str(nucleo.historial())
        nucleo.agente.permisos_concedidos.discard("READ")
        with pytest.raises(PermissionError):
            nucleo.conversar(pregunta)
    finally:
        nucleo.ejecutor.shutdown()


def test_compilacion_y_propuestas_distintas_de_dos_puntos(tmp_path):
    from core.proyecto_studio import ProyectoStudio

    (tmp_path / "lista.py").write_text("numeros = [1, 2\n")
    (tmp_path / "logica.py").write_text("return 2\n")
    (tmp_path / "datos.py").write_text('ajustes = {"a": 1, "a": 2}\n')
    (tmp_path / "ambiguo.py").write_text("datos = [{\n")
    proyecto = ProyectoStudio(str(tmp_path))
    informe = proyecto.analizar()
    assert informe["revisados"] == 4
    assert any("outside function" in item for item in informe["hallazgos"])
    assert any("clave de diccionario repetida" in item for item in informe["hallazgos"])
    (propuesta,) = informe["propuestas"]
    assert propuesta["archivo"] == "lista.py" and "+]" in propuesta["diff"]
    proyecto.aplicar(propuesta["id"])
    assert (tmp_path / "lista.py").read_text().endswith("]\n")
