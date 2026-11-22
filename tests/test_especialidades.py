
import config
from universe.especialidades import Experiencias, _trabajos
from universe.nucleo import Nucleo


def test_coordina_y_aprende_de_evidencias(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    llamadas = []

    def consulta(region, accion, objetivo, *, red, cancelacion):
        llamadas.append((region, accion, red))
        base = {"version": 1, "especialista": region, "estado": "ok"}
        if region == "DARAS":
            return {**base, "plan": [{"id": "alcance", "titulo": "Definir alcance", "depende_de": []},
                                     {"id": "robot", "titulo": "Programar", "depende_de": ["alcance"]}]}
        return {**base, "evidencia": [{"tipo": "analisis", "path": "robot.py",
                                       "language": "Python", "errores": []}]}

    monkeypatch.setattr("universe.especialidades._consulta", consulta)
    nucleo = Nucleo("local")
    try:
        objetivo = "Investiga cómo construir un robot, planifica el proyecto, desarrolla el software y comprueba lo aprendido"
        resultado = nucleo.conversar(objetivo)
        assert len(resultado["especialistas"]) == 3
        assert "robot.py" in resultado["respuesta"] and "identificador" in resultado["respuesta"]
        assert sorted(llamadas) == [("CAZEL", "analizar", False), ("DARAS", "investigar", False)]
        assert nucleo.conversar(objetivo)["experiencia"] == resultado["experiencia"]
        assert len(Experiencias(nucleo.estudio / "experiencias-v1.sqlite3").recientes()) == 1
        assert "coincide" in nucleo.conversar("Mi respuesta es alcance")["respuesta"]
        assert "robot.py" in nucleo.conversar("Muéstrame qué aprendiste de CAZEL")["respuesta"]
        nodos = nucleo.nodos()["nodos"]
        assert any(n.get("grupo") == "CAZEL" and n.get("vinculos") for n in nodos)
    finally:
        nucleo.ejecutor.shutdown(wait=True)


def test_intenciones_delimitadas_y_permiso_red():
    assert _trabajos("conecta el robot cazel", True) == ([], False)
    assert _trabajos("investiga con daras en internet", False)[0] == [("DARAS", "investigar", False)]
    assert _trabajos("investiga con daras en internet", True)[0] == [("DARAS", "investigar", True)]

def test_cancelacion_cierra_un_adaptador_lento(tmp_path):
    import subprocess
    import sys
    from threading import Timer

    import pytest

    from universe.especialidades import Coordinacion, _ejecutar

    coordinacion = Coordinacion()
    with coordinacion.turno() as evento:
        with coordinacion.turno() as otro:
            assert otro is None
        timer = Timer(0.1, coordinacion.cancelar)
        timer.start()
        try:
            with pytest.raises(InterruptedError):
                _ejecutar([sys.executable, "-c", "import time; time.sleep(10)"],
                          tmp_path, b"{}", {}, 5, evento)
        finally:
            timer.cancel()
            timer.join()
    assert not coordinacion.cancelar()
