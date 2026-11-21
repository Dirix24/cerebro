import pytest

import config
from core import competencias
from universe.nucleo import Nucleo


def test_ejercicio_verificable_y_banco_reservado():
    reservadas = {pregunta for casos in competencias.RESERVADOS.values() for pregunta, _ in casos}
    for materia, (pregunta, _) in competencias.PRACTICA.items():
        assert pregunta not in reservadas
        for variante in range(10, 100):
            enunciado, referencia = competencias.ejercicio(materia, variante)
            assert enunciado not in reservadas and referencia
    assert competencias.ejercicio("matemáticas", 22)[1] == "86"
    with pytest.raises(ValueError):
        competencias.ejercicio("matemáticas", True)


def test_competencias_en_nucleo_y_analizar_sin_internet(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    llamadas = []

    class Profesor:
        configurado = True

        def proponer_variante(self, materia):
            llamadas.append(materia)
            return 22

        def ensenar(self, materia, pregunta, referencia, respuesta):
            llamadas.append((materia, referencia, respuesta))
            return "Explicación no usada como nota."

    nucleo = Nucleo("local", internet=False, profesor=Profesor())
    try:
        salida = nucleo.conversar("Ejercicio de matemáticas", modo="web")
        assert salida["origen"] == "variante_profesor_verificada"
        assert "102" in salida["respuesta"] and "86" not in salida["respuesta"]
        assert "Referencia verificada: 86" in nucleo.conversar("Explica ejercicio de matemáticas")["respuesta"]
        assert "Referencia verificada: 14" in nucleo.conversar("Explica ejercicio de matemáticas",
                                                             cliente="a" * 24)["respuesta"]
        assert llamadas == ["matemáticas", ("matemáticas", "86", None), ("matemáticas", "14", None)]
        informe = {"banco": 1, "materias": {"español": {"aciertos": 1, "total": 1, "resultados": []}}}
        competencias.guardar(tmp_path, informe)
        assert "Español: 1/1" in nucleo.analizar_aprendizaje()["resumen_competencias"]
        assert nucleo.conversar("Competencias del alumno")["competencias"] == [informe]
        nucleo.agente.permisos_concedidos.discard("READ")
        with pytest.raises(PermissionError):
            nucleo.conversar("Ejercicio de matemáticas", modo="studio")
    finally:
        nucleo.ejecutor.shutdown()
