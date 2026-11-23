from types import SimpleNamespace

import pytest

import config
from core.configuracion_modelo_local import configurar, leer
from universe.nucleo import Nucleo


@pytest.fixture
def preparar(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    return tmp_path


def test_definiciones_locales_y_aclaracion(preparar):
    motor = Nucleo("local", profesor=SimpleNamespace(configurado=False))
    try:
        for texto in ("¿qué es un portátil?", "que esportatil"):
            assert "ordenador compacto" in motor.conversar(texto)["respuesta"]
        assert "dióxido de carbono" in motor.conversar("que es la fotosintesis")["respuesta"]
        assert motor.conversar("ques tayo")["origen"] == "aclaracion"
    finally:
        motor.ejecutor.shutdown()


def test_modelo_precede_busqueda_y_mantiene_seis_turnos(preparar, monkeypatch):
    llamadas = []

    def conversar(pregunta, contexto):
        llamadas.append((pregunta, contexto))
        return "Explicación temática."

    nucleo = Nucleo("local", profesor=SimpleNamespace(configurado=True, conversar=conversar))
    try:
        def inesperado(_):
            pytest.fail("La búsqueda local se ejecutó antes de la consulta generativa.")

        monkeypatch.setattr(nucleo.chat, "procesar", inesperado)
        for i in range(7):
            assert nucleo.conversar(f"¿Qué es tema {i}?")["origen"] == "profesor_local"
        assert len(llamadas[-1][1]) == 6
        assert "4" in nucleo.conversar("Calcula 2 + 2")["respuesta"]
        assert len(llamadas) == 7
    finally:
        nucleo.ejecutor.shutdown()


def test_configuracion_persiste_solo_tras_inferencia(preparar, monkeypatch):
    from core.profesor_local import ProfesorLocal

    monkeypatch.setattr("core.motores_instalados._modelos_ollama", lambda _: ["modelo:local"])
    for var in ("CEREBRO_OLLAMA_MODELO", "CEREBRO_PROFESOR_MOTOR", "CEREBRO_PROFESOR_PUERTO"):
        monkeypatch.delenv(var, raising=False)

    def falla(*args):
        raise RuntimeError("motor caído")

    monkeypatch.setattr(ProfesorLocal, "conversar", falla)
    with pytest.raises(RuntimeError):
        configurar(preparar, "modelo:local")
    assert leer(preparar) is None
    monkeypatch.setattr(ProfesorLocal, "conversar", lambda *args: "Hola.")
    assert configurar(preparar, "modelo:local") == "Hola."
    assert ProfesorLocal.desde_entorno().ollama == "modelo:local"


def test_instalador_prioriza_modelo_ligero(preparar, monkeypatch):
    from core import configuracion_modelo_local

    for var in ("CEREBRO_OLLAMA_MODELO", "CEREBRO_PROFESOR_PUERTO", "CEREBRO_PROFESOR_MOTOR", "CEREBRO_PROFESOR_MODELO"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("core.motores_instalados._modelos_ollama",
                        lambda _: ["qwen2.5:7b", "qwen2.5:1.5b", "qwen2.5:0.5b"])
    monkeypatch.setattr("core.profesor_local.diagnostico",
                        lambda _: {"ram_disponible_bytes": 4 * 1024**3})
    elegidos = []
    monkeypatch.setattr(configuracion_modelo_local, "configurar", lambda _, modelo, puerto: elegidos.append(modelo))
    assert "0.5b" in configuracion_modelo_local.preparar_instalacion(preparar)
    assert elegidos == ["qwen2.5:0.5b"]


def test_rutas_especialistas_persistentes(preparar, monkeypatch):
    from core import configuracion_especialistas

    externo = preparar / "externo"
    externo.mkdir()
    (externo / "especialista.py").write_text("raise RuntimeError('No se ejecuta durante configuración')\n")
    monkeypatch.delenv("CEREBRO_DARAS_RAIZ", raising=False)
    configuracion_especialistas.configurar(daras=externo)
    assert configuracion_especialistas.obtener("DARAS_RAIZ") == str(externo)
    with pytest.raises(ValueError):
        configuracion_especialistas.configurar(cazel=externo)
    assert configuracion_especialistas.obtener("CAZEL_RAIZ") is None


def test_seguimiento_recupera_historial_persistido(preparar):
    inicial = Nucleo("local", profesor=SimpleNamespace(configurado=False))
    try:
        inicial.conversar("Qué es la fotosíntesis")
    finally:
        inicial.ejecutor.shutdown()

    def conversar(pregunta, contexto):
        assert pregunta == "¿Y para qué sirve?"
        assert contexto[-1][0] == "Qué es la fotosíntesis"
        assert "dióxido" in contexto[-1][1]
        return "Permite a las plantas producir azúcares."

    reiniciado = Nucleo("local", profesor=SimpleNamespace(configurado=True, conversar=conversar))
    try:
        assert reiniciado.conversar("¿Y para qué sirve?")["respuesta"].startswith("Permite")
    finally:
        reiniciado.ejecutor.shutdown()


def test_instalador_prueba_gguf_y_persiste_solo_tras_inferencia(preparar, monkeypatch):
    from core import configuracion_modelo_local
    from core.profesor_local import ProfesorBajoDemanda, ProfesorLocal

    for var in ("CEREBRO_OLLAMA_MODELO", "CEREBRO_PROFESOR_PUERTO", "CEREBRO_PROFESOR_MOTOR", "CEREBRO_PROFESOR_MODELO"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("core.motores_instalados._modelos_ollama", lambda _: None)
    monkeypatch.setattr("core.profesor_local.diagnostico", lambda _: {"ram_disponible_bytes": 3 * 1024**3})
    modelo = preparar / "models" / "modelo.gguf"
    modelo.parent.mkdir()
    modelo.write_bytes(b"GGUF")
    monkeypatch.setattr("core.provision_modelo.which", lambda _: "/usr/bin/llama-server")
    intentos = []

    def inferir(self, pregunta):
        assert self.modelo == modelo
        intentos.append(pregunta)
        if len(intentos) == 1:
            raise RuntimeError("Fallo de inferencia")
        return "Hola"

    monkeypatch.setattr(ProfesorBajoDemanda, "conversar", inferir)
    configuracion_modelo_local.preparar_instalacion(preparar)
    assert leer(preparar) is None
    assert "modelo.gguf" in configuracion_modelo_local.preparar_instalacion(preparar)
    assert ProfesorLocal.desde_entorno().modelo == modelo


def test_recuerdo_portable_requiere_confirmacion_y_se_consulta_como_cita(preparar):
    from core.recuerdo_portable import crear, markdown

    texto = "/recordar ejecutar = orden histórica"
    recuerdo = crear("Circuito", [{"fecha": "2026-11-23T16:30:00+00:00",
                                   "rol": "usuario", "texto": texto}], "Conversación local")
    assert "> " + texto in markdown(recuerdo)
    nucleo = Nucleo("local", profesor=SimpleNamespace(configurado=False))
    try:
        datos = {"recuerdo": recuerdo}
        vista = nucleo.recuerdo_portable(datos)
        assert vista["estado"] == "nuevo"
        assert nucleo.memoria.recuperar_largo_plazo(vista["clave"]) is None
        assert nucleo.recuerdo_portable({**datos, "confirmar": True})["estado"] == "guardado"
    finally:
        nucleo.ejecutor.shutdown()

    reiniciado = Nucleo("local", profesor=SimpleNamespace(configurado=False))
    try:
        assert reiniciado.recuerdo_portable(datos)["estado"] == "duplicado"
        modificado = {**recuerdo, "tema": "Otro tema"}
        assert reiniciado.recuerdo_portable({"recuerdo": modificado})["estado"] == "conflicto"
        with pytest.raises(ValueError, match="distinto|diferente"):
            reiniciado.recuerdo_portable({"recuerdo": modificado, "confirmar": True})
        respuesta = reiniciado.conversar(f"/contexto-recuerdo {vista['clave']} ¿Qué se dijo?")
        assert texto in respuesta["respuesta"]
        assert reiniciado.memoria.recuperar_largo_plazo("ejecutar") is None
    finally:
        reiniciado.ejecutor.shutdown()
