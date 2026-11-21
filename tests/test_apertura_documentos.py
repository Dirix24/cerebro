from pathlib import Path

import pytest

import config
from core import aplicaciones_linux
from universe.nucleo import Nucleo


@pytest.fixture
def nucleo(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memoria.json"))
    (tmp_path / "Documentos").mkdir()
    servicio = Nucleo("local", documentos_usuario=True)
    yield servicio
    servicio.ejecutor.shutdown()


def test_apertura_confirmada_reinicio_y_olvido(nucleo, monkeypatch, tmp_path):
    documentos = tmp_path / "Documentos"
    for nombre in ("Matemáticas anterior.txt", "Matemáticas actual.txt"):
        (documentos / nombre).touch()
    solicitados = []
    def abrir(ruta):
        solicitados.append(ruta.name)
        return {"aceptado": True, "formato": "text/plain", "aplicacion": "Editor de prueba"}
    monkeypatch.setattr(aplicaciones_linux, "abrir_documento", abrir)
    cliente = "a" * 24
    def conversar(pregunta, id_cliente=cliente):
        return nucleo.conversar(pregunta, modo="escritorio", cliente=id_cliente)["respuesta"]

    assert "varios" in conversar("Cerebro, habre mi documento de matemáticas")
    conversar("1", "b" * 24)
    assert solicitados == []
    assert "aceptó" in conversar("Opción 1")
    assert solicitados == ["Matemáticas actual.txt"]
    assert not Path(config.MEMORY_FILE).exists()
    assert "Recordaré" in conversar("Sí, recuérdalo")
    nodo = next(n for n in nucleo.nodos()["nodos"] if n["id"].startswith("documento:"))
    assert "Editor de prueba" in nodo["detalle"]
    assert "Matemáticas" not in str(nodo)
    banco = tmp_path / "data" / "ejemplos_aprobados.jsonl"
    assert not banco.exists()
    assert "aprobado" in conversar("Aprueba ejemplo de apertura")
    assert "documento de prueba" in banco.read_text()
    assert "Matemáticas" not in banco.read_text()

    reiniciado = Nucleo("local", documentos_usuario=True)
    try:
        assert "aceptó" in reiniciado.conversar("Abre el documento de matemáticas otra vez", modo="chat")["respuesta"]
        assert solicitados == ["Matemáticas actual.txt"] * 2
        reiniciado.agente.permisos_concedidos.discard("READ")
        with pytest.raises(PermissionError):
            reiniciado.conversar("Abre el documento de matemáticas", modo="terminal")
        assert "Olvidé" in reiniciado.conversar("Olvida el documento de matemáticas", modo="studio")["respuesta"]
        reiniciado.agente.permisos_concedidos.add("READ")
        assert "varios" in reiniciado.conversar("Abre mi documento de matemáticas")["respuesta"]
    finally:
        reiniciado.ejecutor.shutdown()


def test_apertura_fallida_y_enlace_fuera_del_ambito(nucleo, monkeypatch, tmp_path):
    documento = tmp_path / "Documentos" / "cuentas.txt"
    documento.touch()
    monkeypatch.setattr(aplicaciones_linux, "abrir_documento",
                        lambda _: {"aceptado": False, "formato": "text/plain", "aplicacion": None})
    assert "aplicación predeterminada" in nucleo.conversar("Abre el documento cuentas")["respuesta"]
    nucleo.conversar("Sí, recuérdalo")
    assert not Path(config.MEMORY_FILE).exists()
    documento.unlink()
    fuera = tmp_path / "fuera.txt"
    fuera.touch()
    documento.symlink_to(fuera)
    assert "No encontré" in nucleo.conversar("Abre el documento cuentas")["respuesta"]


def test_catalogo_y_borrado_de_historial(nucleo, monkeypatch):
    monkeypatch.setattr(aplicaciones_linux, "listar",
                        lambda: [{"nombre": "Editor detectado", "formatos": ["text/plain"]}])
    assert "Editor detectado" in nucleo.conversar("¿Qué aplicaciones tengo instaladas?")["respuesta"]
    nucleo._registrar_turno("Hola", "Hola, ¿cómo estás?")
    with pytest.raises(ValueError):
        nucleo.borrar_historial("true")
    assert len(nucleo.historial()["turnos"]) == 2
    nucleo.memoria.agregar_contexto("usuario", "Hola")
    assert nucleo.borrar_historial(True) == {"turnos": []}
    assert nucleo.historial()["turnos"] == []
    assert nucleo.memoria.short_term_context == []
    nucleo.solo_lectura = True
    with pytest.raises(PermissionError):
        nucleo.borrar_historial(True)


def test_revocar_escritura_bloquea_memoria_y_ejemplos_de_apertura(nucleo, monkeypatch, tmp_path):
    (tmp_path / "Documentos" / "calculo.txt").touch()
    monkeypatch.setattr(aplicaciones_linux, "abrir_documento",
                        lambda _: {"aceptado": True, "formato": "text/plain", "aplicacion": "Editor"})
    nucleo.agente.permisos_concedidos.discard("WRITE")
    assert "aceptó" in nucleo.conversar("Abre mi documento de calculo")["respuesta"]
    with pytest.raises(PermissionError):
        nucleo.conversar("Sí, recuérdalo")
    assert not Path(config.MEMORY_FILE).exists()
    nucleo.agente.permisos_concedidos.add("WRITE")
    assert "Recordaré" in nucleo.conversar("Sí, recuérdalo")["respuesta"]
    nucleo.agente.permisos_concedidos.discard("WRITE")
    with pytest.raises(PermissionError):
        nucleo.conversar("Aprueba ejemplo de apertura")
    assert not (tmp_path / "data" / "ejemplos_aprobados.jsonl").exists()
    with pytest.raises(PermissionError):
        nucleo.conversar("Olvida el documento de calculo")


def test_control_dinamico_y_cierre_confirmado(nucleo, monkeypatch):
    from core import ventanas_x11

    aplicaciones = [{"id": "org.ejemplo.Editor.desktop", "nombre": "Editor prueba", "formatos": []}]
    ejecutadas = []
    monkeypatch.setattr(aplicaciones_linux, "listar", lambda: aplicaciones)
    monkeypatch.setattr(aplicaciones_linux, "lanzar_aplicacion", lambda id: ejecutadas.append(id) or True)
    assert "aceptó" in nucleo.conversar("Cerebro, abre Editor prueba")["respuesta"]
    assert ejecutadas == ["org.ejemplo.Editor.desktop"]
    ventana = {"id": "0x123", "pid": "11", "clase": "demo.Editor", "titulo": "Editor prueba"}
    monkeypatch.setattr(ventanas_x11, "listar", lambda: [ventana])
    operaciones = []
    monkeypatch.setattr(ventanas_x11, "actuar", lambda accion, v: operaciones.append((accion, v["id"])) or True)
    cliente = "a" * 24
    assert "Confirmar cierre" in nucleo.conversar("Cierra Editor prueba", cliente=cliente)["respuesta"]
    nucleo.conversar("Confirmar cierre", cliente="b" * 24)
    assert operaciones == []
    assert "se cerró" in nucleo.conversar("Confirmar cierre", cliente=cliente)["respuesta"]
    assert "Minimicé" in nucleo.conversar("Minimiza Editor prueba", cliente=cliente)["respuesta"]
    assert operaciones == [("cierra", "0x123"), ("minimiza", "0x123")]


def test_control_compuesto_espera_confirmacion_y_revalida_permisos(nucleo, monkeypatch):
    from core import ventanas_x11

    cliente = "a" * 24
    ventana = {"id": "0x123", "pid": "11", "clase": "demo.Editor", "titulo": "Editor"}
    operaciones = []
    monkeypatch.setattr(ventanas_x11, "listar", lambda: [ventana])
    monkeypatch.setattr(ventanas_x11, "actuar", lambda accion, v: operaciones.append(accion) or True)
    texto = "Pon Editor delante, cierra esa ventana y maximiza Editor"
    respuesta = nucleo.conversar(texto, cliente=cliente)["respuesta"]
    assert "Enfoqué" in respuesta and "Confirmar cierre" in respuesta
    assert operaciones == ["enfoca"]
    nucleo.agente.permisos_concedidos.discard("WRITE")
    with pytest.raises(PermissionError):
        nucleo.conversar("Confirmar cierre", cliente=cliente)
    assert operaciones == ["enfoca"]
    nucleo.agente.permisos_concedidos.add("WRITE")
    assert "Maximicé" in nucleo.conversar("Confirmar cierre", cliente=cliente)["respuesta"]
    assert operaciones == ["enfoca", "cierra", "maximiza"]


def test_aplicacion_aproximada_pide_elegir(nucleo, monkeypatch):
    app = {"id": "blender.desktop", "nombre": "Blender", "formatos": []}
    ejecutadas = []
    monkeypatch.setattr(aplicaciones_linux, "listar", lambda: [app])
    monkeypatch.setattr(aplicaciones_linux, "lanzar_aplicacion", lambda id: ejecutadas.append(id) or True)
    assert "Elige una aplicación" in nucleo.conversar("Abre Blendr")["respuesta"]
    assert not ejecutadas
    assert "aceptó" in nucleo.conversar("1")["respuesta"]
    assert ejecutadas == [app["id"]]


def test_x11_identifica_ventana_activa_con_valor_adicional(monkeypatch):
    from core import ventanas_x11

    ventana = {"id": "0x000123"}
    monkeypatch.setattr(ventanas_x11, "_ejecutar", lambda *args: "window id # 0x123, 0x0")
    assert ventanas_x11.activa([ventana]) == ventana


def test_cierre_general_protege_clientes_y_detiene_ante_aviso(nucleo, monkeypatch):
    from core import ventanas_x11

    ventanas = [{"id": hex(i), "pid": str(100 + i), "clase": nombre, "titulo": nombre}
                for i, nombre in enumerate(("Bloc", "Dibujo", "Navegador", "Panel", "Cerebro Studio"))]
    apps = [{"id": nombre + ".desktop", "nombre": nombre, "formatos": [],
             "categorias": categorias}
            for nombre, categorias in (("Bloc", []), ("Dibujo", []), ("Navegador", ["WebBrowser"]))]
    operaciones = []
    monkeypatch.setattr(ventanas_x11, "listar", lambda: ventanas)
    monkeypatch.setattr(ventanas_x11, "admite_cierre_general", lambda _: True)
    monkeypatch.setattr(aplicaciones_linux, "listar", lambda: apps)
    monkeypatch.setattr(ventanas_x11, "actuar", lambda accion, ventana: operaciones.append(ventana["titulo"]) or False)
    cliente = "a" * 24
    respuesta = nucleo.conversar("Cierra todo menos el navegador", cliente=cliente)["respuesta"]
    previstas, conservadas = respuesta.split("Conservaré:")
    assert "Bloc" in previstas and "Dibujo" in previstas
    assert all(nombre in conservadas for nombre in ("Navegador", "Panel", "Cerebro Studio"))
    assert not operaciones
    nucleo.conversar("Confirmar cierre", cliente="b" * 24)
    assert not operaciones
    resultado = nucleo.conversar("Confirmar cierre", cliente=cliente)["respuesta"]
    assert operaciones == ["Bloc"]
    assert "sigue abierta" in resultado and "cierre aún no solicitado" in resultado


def test_energia_requiere_confirmacion_propia_y_revisa_impedimentos(nucleo, monkeypatch):
    from core import energia_linux, ventanas_x11

    llamadas = []
    ventanas = []
    monkeypatch.setattr(ventanas_x11, "listar", lambda: ventanas)
    monkeypatch.setattr(energia_linux, "impedimentos", lambda _: [])
    monkeypatch.setattr(energia_linux, "solicitar", lambda accion: llamadas.append(accion))
    cliente = "a" * 24
    assert "Confirmar apagar" in nucleo.conversar("Apaga mi ordenador", cliente=cliente)["respuesta"]
    nucleo.conversar("Confirmar apagar", cliente="b" * 24)
    assert not llamadas
    ventanas.append({"titulo": "Documento con cambios"})
    assert "Hay ventanas abiertas" in nucleo.conversar("Confirmar apagar", cliente=cliente)["respuesta"]
    assert not llamadas
    ventanas.clear()
    nucleo.conversar("Reinicia el ordenador", cliente=cliente)
    nucleo.agente.permisos_concedidos.discard("WRITE")
    with pytest.raises(PermissionError):
        nucleo.conversar("Confirmar reiniciar", cliente=cliente)
    assert not llamadas
    nucleo.agente.permisos_concedidos.add("WRITE")
    assert "aceptó" in nucleo.conversar("Confirmar reiniciar", cliente=cliente)["respuesta"]
    assert llamadas == ["reiniciar"]


def test_login1_respeta_inhibidores_sin_enviar_acciones(monkeypatch):
    import json
    from core import energia_linux

    def respuesta(metodo):
        datos = {"CanSuspend": "yes", "ListInhibitors": [
            ["sleep", "Editor", "Exportando", "block", 1000, 21],
            ["sleep", "Red", "Guardando estado", "delay", 0, 22],
            ["shutdown", "Otro", "Backup", "block", 1000, 23],
        ]}
        return json.dumps({"data": [datos[metodo]]})

    monkeypatch.setattr(energia_linux, "_login1", respuesta)
    assert energia_linux.impedimentos("suspender") == ["Editor: Exportando"]


def test_demostracion_explicita_repite_solo_pasos_verificados(nucleo, monkeypatch):
    from core import ventanas_x11

    ventana = {"id": "0x123", "pid": "10", "clase": "Editor", "titulo": "Editor"}
    operaciones = []
    monkeypatch.setattr(ventanas_x11, "listar", lambda: [ventana])
    monkeypatch.setattr(ventanas_x11, "actuar", lambda accion, v: operaciones.append(accion) or accion != "minimiza")
    cliente = "a" * 24
    assert "Empezar demostración" in nucleo.conversar("Te voy a enseñar", cliente=cliente)["respuesta"]
    assert "iniciada" in nucleo.conversar("Empezar demostración diseño", cliente=cliente)["respuesta"]
    nucleo.conversar("Minimiza Editor", cliente=cliente)
    nucleo.conversar("Maximiza Editor", cliente=cliente)
    assert "1 paso verificado" in nucleo.conversar("Guardar demostración", cliente=cliente)["respuesta"]
    assert "Maximicé" in nucleo.conversar("Ahora hazlo tú", cliente=cliente)["respuesta"]
    assert operaciones == ["minimiza", "maximiza", "maximiza"]
    monkeypatch.setattr(ventanas_x11, "listar", lambda: [])
    assert "Detuve la demostración" in nucleo.conversar("Repite la demostración diseño", cliente=cliente)["respuesta"]
    assert operaciones == ["minimiza", "maximiza", "maximiza"]


def test_colocar_dos_ventanas_pide_seleccion_distinta(nucleo, monkeypatch):
    from core import ventanas_x11

    ventanas = [{"id": hex(i), "pid": str(i), "clase": nombre, "titulo": nombre}
                for i, nombre in enumerate(("Bloc", "Dibujo"), 3)]
    llamadas = []
    monkeypatch.setattr(ventanas_x11, "listar", lambda: ventanas)
    monkeypatch.setattr(ventanas_x11, "colocar_juntas", lambda a, b: llamadas.append((a, b)) or (True, True))
    cliente = "a" * 24
    assert "izquierda a derecha" in nucleo.conversar("Pon las dos ventanas una al lado de la otra",
                                                       cliente=cliente)["respuesta"]
    assert "números distintos" in nucleo.conversar("1 y 1", cliente=cliente)["respuesta"]
    assert not llamadas
    assert "Coloqué a la derecha" in nucleo.conversar("2 y 1", cliente=cliente)["respuesta"]
    assert llamadas == [(ventanas[1], ventanas[0])]
