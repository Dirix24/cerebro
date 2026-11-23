from hashlib import sha256
from types import SimpleNamespace

import pytest

import config
from core import provision_modelo
from core.habitos_escritorio import Habitos
from core.recuerdo_portable import crear, tipo_cita
from universe.nucleo import Nucleo


def test_descarga_verifica_tamano_y_sha(tmp_path):
    fuente = tmp_path / "fuente"
    fuente.write_bytes(b"modelo de prueba")
    destino = tmp_path / "destino"
    ficha = (fuente.as_uri(), fuente.stat().st_size, sha256(fuente.read_bytes()).hexdigest())
    provision_modelo._descargar(destino, ficha)
    assert destino.read_bytes() == fuente.read_bytes()
    with pytest.raises(ValueError, match="supera"):
        provision_modelo._descargar(destino, (ficha[0], 1, ficha[2]))
    with pytest.raises(ValueError, match="no coincide"):
        provision_modelo._descargar(destino, (*ficha[:2], "0" * 64))


def test_oferta_respeta_respuesta_y_no_descarga(tmp_path, monkeypatch):
    monkeypatch.setattr("core.profesor_local.diagnostico",
                        lambda _: {"ram_disponible_bytes": 3 * 1024**3, "disco_libre_bytes": 2 * 1024**3})
    monkeypatch.setattr(provision_modelo, "binario_llama", lambda: "/usr/bin/llama-server")

    def rechazar(mensaje):
        assert "491 MB" in mensaje
        return False

    assert "omitida" in provision_modelo.ofrecer(tmp_path, rechazar)
    assert not (tmp_path / "models").exists()


def test_habitos_pausa_borrado_y_sugerencia_compartida(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    habitos = Habitos(tmp_path)
    habitos.registrar("code")
    assert not habitos.ruta.exists()
    habitos.cambiar(True)
    for _ in range(3):
        habitos.registrar("code")
        habitos.registrar("code")
        habitos.registrar("gestor-de-contraseñas")
    assert Habitos(tmp_path).leer()["cuentas"] == {"code": 3}
    nucleo = Nucleo("local", profesor=SimpleNamespace(configurado=False))
    try:
        assert "VS Code" in nucleo.conversar("Vamos a programar")["respuesta"]
        habitos.cambiar(False)
        assert "VS Code" not in nucleo.conversar("Vamos a programar")["respuesta"]
        habitos.borrar()
        assert habitos.leer()["cuentas"] == {}
    finally:
        nucleo.ejecutor.shutdown()


def test_recuerdo_avisa_contradiccion_textual_y_no_sustituye(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))

    def fragmento(texto, dia):
        return crear("Servicio local", [{"rol": "usuario", "texto": texto,
                                        "fecha": f"2026-11-{dia}T12:00:00+00:00"}], "Prueba")

    anterior = fragmento("El puerto es 5432.", 24)
    entrada = fragmento("El puerto no es 5432.", 23)
    nucleo = Nucleo("local", profesor=SimpleNamespace(configurado=False))
    try:
        clave = nucleo.recuerdo_portable({"recuerdo": anterior, "confirmar": True})["clave"]
        vista = nucleo.recuerdo_portable({"recuerdo": entrada})
        assert vista["contradicciones_posibles"] == [
            {"seleccion": "El puerto no es 5432.", "guardada": "El puerto es 5432.",
             "fecha": "2026-11-24T12:00:00+00:00"}]
        nucleo.recuerdo_portable({"recuerdo": entrada, "confirmar": True})
        assert nucleo.memoria.recuperar_largo_plazo(clave) == anterior
        assert "instrucción" in tipo_cita("/recordar prueba = orden histórica")
        assert "opinión" in tipo_cita("En mi opinión, vale la pena.")
    finally:
        nucleo.ejecutor.shutdown()


def test_clase_x11_omite_titulo_y_consulta_solo_ventana_activa(monkeypatch):
    from core import ventanas_x11

    monkeypatch.setenv("DISPLAY", ":91")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    llamadas = []

    def ejecutar(*args):
        llamadas.append(args)
        return ('_NET_ACTIVE_WINDOW(WINDOW): window id # 0x123\n' if args[1] == "-root"
                else 'WM_CLASS(STRING) = "code", "Code"\n')

    monkeypatch.setattr(ventanas_x11, "_ejecutar", ejecutar)
    assert ventanas_x11.clase_activa() == "code"
    assert llamadas == [("xprop", "-root", "_NET_ACTIVE_WINDOW"), ("xprop", "-id", "0x123", "WM_CLASS")]


def test_prueba_de_camara_no_requiere_autorizar_puntero(monkeypatch):
    from universe import tactil

    monkeypatch.setattr(tactil, "tecnologias", lambda: {
        "x11": False, "opencv": True, "mediapipe": True, "modelo": "hand.task"})
    assert tactil._requisitos(controlar=False) == "hand.task"
    with pytest.raises(RuntimeError, match="X11"):
        tactil._requisitos()


def test_entrenamiento_se_aplaza_con_bateria_baja(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    monkeypatch.setattr("core.aprendizaje_autonomo.motivos_pausa", lambda **_: ["batería baja"])
    nucleo = Nucleo("local", modelo=object(), profesor=SimpleNamespace(configurado=False),
                    especialista=False)
    try:
        nucleo.conversar("Prepara entrenamiento autónomo")
        resultado = nucleo.conversar("Confirma entrenamiento autónomo")
        assert "batería baja" in resultado["respuesta"]
        assert nucleo.aprendizaje.hilo is None
    finally:
        nucleo.ejecutor.shutdown()
