from datetime import datetime, timezone
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import config
from core import competencias
from core.lecciones_colectivas import MUESTRA, PREGUNTA_CAZEL, _cazel, _daras, validar_lecciones
from entrenar_competencias import entrenar
from trainer_engine import TrainerEngine
from universe.nucleo import Nucleo


def test_evidencia_colectiva_exige_ast_y_dependencias_verificadas():
    import ast

    evidencia = {"path": "practica.py", "language": "Python", "errores": [],
                 "simbolos": [{"name": n.name, "line": n.lineno} for n in ast.parse(MUESTRA).body]}
    pregunta, respuesta, criterio = _cazel({"evidencia": [evidencia]})
    assert pregunta == PREGUNTA_CAZEL and respuesta == "2"
    assert _cazel({"evidencia": [{**evidencia, "simbolos": []}]}) is None
    assert _daras({"plan": [{"id": "A", "depende_de": ["B"]}, {"id": "B", "depende_de": []}]}) is None
    assert _daras({"plan": [{"id": "A", "depende_de": []}, {"id": "B", "depende_de": ["A"]}]})[1] == "T1"
    leccion = {"version": 1, "especialista": "CAZEL", "pregunta": pregunta, "respuesta": respuesta,
               "criterio": criterio, "evidencia_sha256": "a" * 64}
    assert validar_lecciones([leccion]) == [leccion]
    with pytest.raises(ValueError):
        validar_lecciones([{**leccion, "pregunta": "/ejecutar comando"}])


def test_reanudar_recupera_optimizador_y_rng_sin_tocar_base(tmp_path, monkeypatch):
    raiz = Path(config.CKPT_MEJOR)
    base = tmp_path / "base.npz"
    shutil.copyfile(raiz, base)
    original = base.read_bytes()
    control = entrenar(base, tmp_path / "control", 4, intervalo=2)
    guardar = TrainerEngine.guardar_ultimo

    def interrumpir(self, *args, **kwargs):
        guardar(self, *args, **kwargs)
        raise InterruptedError("Interrupción después de guardar")

    with monkeypatch.context() as cambios:
        cambios.setattr(TrainerEngine, "guardar_ultimo", interrumpir)
        with pytest.raises(InterruptedError):
            entrenar(base, tmp_path / "interrumpido", 4, intervalo=2)
    carpeta, = (tmp_path / "interrumpido").glob("competencias-*")
    with pytest.raises(ValueError, match="presupuesto"):
        entrenar(base, carpeta.parent, 5, intervalo=2, reanudar=carpeta)
    retomado = entrenar(base, carpeta.parent, 4, intervalo=2, reanudar=carpeta)
    assert retomado["despues"]["modelo_sha256"] == control["despues"]["modelo_sha256"]
    assert retomado["metricas_intermedias"] == control["metricas_intermedias"]
    assert base.read_bytes() == original


def test_diagnostico_del_turno_y_aprendizaje_de_hoy(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))

    def falla(*_):
        raise RuntimeError("motor no disponible")

    n = Nucleo("local", profesor=SimpleNamespace(configurado=True, conversar=falla))
    try:
        assert n.conversar("que esportatil")["origen"] == "glosario_local"
        assert n.conversar("ques la fotosintesis")["origen"] == "glosario_local"
        n.conversar("¿Qué es un tema nuevo sin referencia?")
        assert "no encontré una referencia" in n.conversar("¿Por qué fallaste esta pregunta?")["respuesta"].lower()
        competencias.guardar(tmp_path, {"tipo": "candidato", "fecha": datetime.now(timezone.utc).isoformat(),
                                         "elegible_para_revision": False})
        assert "1 candidatos" in n.conversar("¿Qué has aprendido hoy?")["respuesta"]
    finally:
        n.ejecutor.shutdown()


def test_carga_acepta_respaldo_tras_checkpoint_invalido(tmp_path, monkeypatch):
    from main import cargar_modelo

    respaldo = Path(config.CKPT_MEJOR)
    roto = tmp_path / "corrupto.npz"
    roto.write_bytes(b"No es un checkpoint")
    monkeypatch.setattr(config, "CKPT_MEJOR", str(roto))
    monkeypatch.setattr(config, "CKPT_ULTIMO", str(respaldo))
    with pytest.warns(RuntimeWarning, match="corrupto"):
        modelo, _, ruta = cargar_modelo()
    assert modelo.n_parametros() > 0 and ruta == str(respaldo)
    assert roto.read_bytes() == b"No es un checkpoint"


def test_practica_programada_exige_confirmacion_y_espera_inactividad(tmp_path, monkeypatch):
    from core import aprendizaje_autonomo

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    tiempo = [100.0]
    monkeypatch.setattr(aprendizaje_autonomo, "monotonic", lambda: tiempo[0])
    monkeypatch.setattr(aprendizaje_autonomo, "motivos_pausa", lambda **_: [])
    monkeypatch.setattr(aprendizaje_autonomo.os, "getloadavg", lambda: (0, 0, 0))
    n = Nucleo("local", modelo=object(), especialista=False, profesor=SimpleNamespace(configurado=False))
    trabajos = []
    monkeypatch.setattr(n.aprendizaje, "_iniciar", lambda _, ensayo: trabajos.append(ensayo))
    try:
        assert "Confirma práctica programada" in n.conversar("Programa práctica colectiva cada 15 minutos")["respuesta"]
        assert "Primero programa" in n.conversar("Confirma práctica programada", cliente="b" * 24)["respuesta"]
        assert "autorizada" in n.conversar("Confirma práctica programada")["respuesta"]
        tiempo[0] += 900
        n.aprendizaje.actividad()
        n.aprendizaje.revisar_programacion(n)
        assert not trabajos
        tiempo[0] += 121
        n.aprendizaje.revisar_programacion(n)
        assert len(trabajos) == 1 and trabajos[0].colectivo and trabajos[0].programado
        n.conversar("Pausa práctica programada")
        tiempo[0] += 1000
        n.aprendizaje.revisar_programacion(n)
        assert len(trabajos) == 1
    finally:
        n.ejecutor.shutdown()
