from types import SimpleNamespace

import pytest

import config
from core import github_local
from universe import diagnostico_instalacion
from universe.nucleo import Nucleo


def test_gestos_solo_en_interprete_actual(monkeypatch):
    llamadas = []
    monkeypatch.setattr(diagnostico_instalacion.subprocess, "call", lambda args: llamadas.append(args) or 0)
    monkeypatch.setattr(diagnostico_instalacion, "probar_importacion", lambda _: True)
    assert diagnostico_instalacion.instalar_gestos("marcador")
    assert llamadas == [[diagnostico_instalacion.sys.executable, "-m", "pip", "install",
                         "--only-binary=:all:", "opencv-python"]]


def test_comparacion_github_valida_referencias(monkeypatch):
    llamadas = []
    monkeypatch.setattr(github_local, "_datos_publicos", lambda repo, ruta, **_: llamadas.append((repo, ruta))
                        or {"status": "ahead", "ahead_by": 2, "behind_by": 0})
    assert github_local.comparar_publico("Dirix24/cerebro", "main", "feature/visor")["adelante"] == 2
    assert llamadas == [("Dirix24/cerebro", "/compare/main...feature%2Fvisor")]
    with pytest.raises(ValueError):
        github_local.comparar_publico("Dirix24/cerebro", "main", "../fuera")


def test_github_delega_credencial_y_valida_respuesta(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/bin/gh")

    def ejecutar(argv, **opciones):
        assert argv[:4] == ["/bin/gh", "api", "--hostname", "github.com"]
        assert opciones["env"]["GH_PROMPT_DISABLED"] == "1"
        return SimpleNamespace(stdout=b'["Dirix24/cerebro"]')

    monkeypatch.setattr("subprocess.run", ejecutar)
    assert github_local.repositorios_cuenta() == ["Dirix24/cerebro"]


def test_abrir_original_suelto_requiere_confirmacion(tmp_path, monkeypatch):
    (tmp_path / "datos").mkdir()
    imagen = tmp_path / "foto.png"
    imagen.write_bytes(b"datos de la imagen")
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path / "datos"))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    motor = Nucleo("local", documentos_usuario=True)
    llamadas = []
    monkeypatch.setattr("core.aplicaciones_linux.abrir_documento",
                        lambda ruta: llamadas.append(ruta) or {"aceptado": True, "aplicacion": "Visor"})
    cliente = "a" * 24
    try:
        vista = motor.operar_proyecto({"accion": "abrir_suelto", "cliente": cliente, "ruta": str(imagen),
                                      "confirmar": True})
        assert vista["app_externa"]
        solicitud = {"accion": "abrir_suelto_externo", "cliente": cliente, "nombre": "foto.png"}
        with pytest.raises(PermissionError):
            motor.operar_proyecto(solicitud)
        assert not llamadas
        motor.operar_proyecto({**solicitud, "confirmar": True})
        assert llamadas == [imagen]
    finally:
        motor.ejecutor.shutdown()



def test_pdf_tamano_real_en_poppler():
    from shutil import which
    from tests.pdf_fixture import pdf_fixture
    from core.visores_studio import pdf_vista

    if not all(which(p) for p in ("pdfinfo", "pdftoppm", "pdftotext", "prlimit")):
        pytest.skip("Poppler no está disponible")
    vista = pdf_vista(pdf_fixture(), pagina=2, resolucion=0)
    assert vista["resolucion"] == 267
    assert vista["base64"]


def test_modelo_de_manos_persistente(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostico_instalacion.sys, "prefix", str(tmp_path))
    monkeypatch.delenv("CEREBRO_MODELO_MANOS", raising=False)
    archivo = tmp_path / "hand_landmarker.task"
    archivo.write_bytes(b"modelo de prueba")
    diagnostico_instalacion.configurar_modelo_manos(str(archivo))
    assert diagnostico_instalacion.modelo_manos() == str(archivo)
    monkeypatch.setenv("CEREBRO_MODELO_MANOS", "/otro/modelo.task")
    assert diagnostico_instalacion.modelo_manos() == "/otro/modelo.task"
