import pytest

import config
from agent.coordinador_hibrido import validar_plan
from core import aplicaciones_linux, ventanas_x11
from universe.nucleo import Nucleo


def test_esquema_rechaza_acciones_y_objetivos_no_autorizados():
    for texto in ('[{"accion":"cerrar","objetivo":"  todo"}]', '[{"accion":"cerrar","objetivo":"tódo"}]',
                  '[{"accion":"abrir","objetivo":"/tmp/archivo"}]',
                  '[{"accion":"ejecutar","objetivo":"terminal"}]',
                  '[{"accion":"buscar","objetivo":"saldo","extra":true}]'):
        with pytest.raises(ValueError):
            validar_plan(texto)
    assert validar_plan('[{"accion":"abrir","objetivo":"YouTube"}]') == [("youtube", "")]


def test_plan_y_conversacion_comparten_nucleo_y_confirmaciones(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    ejecutadas, llamadas = [], []

    class Profesor:
        configurado = True

        def planificar_escritorio(self, objetivo):
            llamadas.append("plan")
            return '[{"accion":"abrir","objetivo":"Editor"},{"accion":"cerrar","objetivo":"Editor"}]'

        def conversar(self, pregunta, contexto):
            llamadas.append("conversación")
            return "Puedo orientar sobre cómo organizar tus proyectos."

    app = {"id": "test.desktop", "nombre": "Editor", "formatos": []}
    ventana = {"id": "0x120", "pid": "32", "clase": "Editor", "titulo": "Editor"}
    monkeypatch.setattr(aplicaciones_linux, "listar", lambda: [app])
    monkeypatch.setattr(aplicaciones_linux, "lanzar_aplicacion", lambda id: ejecutadas.append(id) or True)
    monkeypatch.setattr(ventanas_x11, "listar", lambda: [ventana])
    monkeypatch.setattr(ventanas_x11, "actuar", lambda accion, v: ejecutadas.append(accion) or True)
    nucleo = Nucleo("local", profesor=Profesor(), documentos_usuario=True)
    cliente = "a" * 24
    try:
        assert "4" in nucleo.conversar("/calc 2 + 2", modo="terminal")["respuesta"]
        assert not llamadas
        assert "Confirmar plan de escritorio" in nucleo.conversar(
            "Prepara un plan de escritorio para abrir el Editor y cerrarlo", modo="studio", cliente=cliente)["respuesta"]
        assert ejecutadas == []
        nucleo.agente.permisos_concedidos.discard("WRITE")
        with pytest.raises(PermissionError):
            nucleo.conversar("Confirmar plan de escritorio", modo="studio", cliente=cliente)
        assert ejecutadas == []
        nucleo.agente.permisos_concedidos.add("WRITE")
        aviso = nucleo.conversar("Confirmar plan de escritorio", modo="studio", cliente=cliente)["respuesta"]
        assert "Confirmar cierre" in aviso
        assert ejecutadas == ["test.desktop"]
        assert "se cerró" in nucleo.conversar("Confirmar cierre", modo="studio", cliente=cliente)["respuesta"]
        assert ejecutadas == ["test.desktop", "cierra"]
        assert nucleo.conversar("Dame ideas para organizar proyectos creativos", modo="escritorio")["origen"] == "profesor_local"
    finally:
        nucleo.ejecutor.shutdown()


def test_demostracion_revisada_y_ejercicios_omiten_objetivos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    nucleo = Nucleo("local", documentos_usuario=True)
    try:
        nucleo.memoria.guardar_largo_plazo("demostracion_escritorio:prueba",
            [{"accion": "enfoca", "objetivo": "Editor.Secreto"}], categoria="demostracion_escritorio")
        assert "Editor.Secreto" in nucleo.conversar("Revisa la demostración prueba")["respuesta"]
        ejercicios = nucleo.conversar("Genera ejercicios de la demostración prueba")["respuesta"]
        assert "enfocar ventana" in ejercicios and "Editor.Secreto" not in ejercicios
        assert any(n["origen"] == "Demostración autorizada" for n in nucleo.nodos()["nodos"])
    finally:
        nucleo.ejecutor.shutdown()


def test_cabezal_real_se_abstiene_y_depende_de_los_pesos_originales(tmp_path):
    from pathlib import Path

    from core.checkpoint import cargar_checkpoint
    from core.especialista_escritorio import Especialista, entrenar

    checkpoint = Path(__file__).resolve().parents[1] / "checkpoints" / "best.npz"
    modelo = cargar_checkpoint(str(checkpoint), con_optimizador=False)["modelo"]
    ruta = tmp_path / "cabezal.npz"
    informe = entrenar(modelo, ruta)
    verificado = informe["certificado"]
    assert informe["umbrales"] == {"buscar": .65}
    assert verificado["materias"]["buscar"]["falsos_positivos"] == 0
    assert verificado["abstenciones_correctas_fuera_de_dominio"] == verificado["fuera_de_dominio"]
    cabeza = Especialista.cargar(ruta, modelo)
    assert cabeza is not None and cabeza.sugerir("No abras Krita") is None
    modelo.params["tok_emb"][0, 0] += 1
    assert Especialista.cargar(ruta, modelo) is None
