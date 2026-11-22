import config
from core.alumno_supervisado import cargar_activo, entrenar, evaluar, responder, retroceder
from universe.nucleo import Nucleo


class ProfesorDePrueba:
    def generar_consultas_locales(self, etiqueta):
        return (f"Dame la {etiqueta} de ahora\n"
                f"No me digas la {etiqueta}\n"
                "¿Cuál es la fecha local?")


def test_entrena_pesos_reales_y_nucleo_usa_promocion(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memory.json"))
    n = Nucleo("local")
    try:
        empate = entrenar(ProfesorDePrueba(), n.raiz_alumno)
        assert not empate["promovido"]
        assert cargar_activo(n.raiz_alumno) == (None, None)

        # Conserva la prueba de carga y rollback simulando un banco donde
        # la referencia determinista sí es superable.
        from core import alumno_supervisado
        evaluar_real = alumno_supervisado.evaluar
        def referencia_superable(pesos):
            return {**evaluar_real(pesos), "aciertos_regla_sola": 8}
        monkeypatch.setattr(alumno_supervisado, "evaluar", referencia_superable)
        informe = entrenar(ProfesorDePrueba(), n.raiz_alumno)
        assert informe["pesos_iniciales_sha256"] != informe["pesos_finales_sha256"]
        assert len(informe["generados"]) == 2
        assert len(informe["rechazados"]) == 4
        assert informe["promovido"]
        pesos, activo = cargar_activo(n.raiz_alumno)
        assert referencia_superable(pesos) == informe["despues"]
        assert responder(pesos, "¿A qué hora abre el museo?") is None
        for modo in ("terminal", "chat", "studio", "escritorio"):
            salida = n.conversar("¿Cuál es la fecha de hoy?", modo=modo)
            assert salida["checkpoint"] == activo["id"]
            assert salida["origen"] == "alumno_supervisado"
        assert any(nodo["id"] == "alumno:" + activo["id"] for nodo in n.nodos()["nodos"])
        repetido = entrenar(ProfesorDePrueba(), n.raiz_alumno)
        assert not repetido["promovido"]
        assert cargar_activo(n.raiz_alumno)[1]["id"] == informe["id"]
        assert cargar_activo(n.raiz_alumno, "ultimo")[1]["id"] == repetido["id"]
        assert retroceder(n.raiz_alumno) is None
        assert cargar_activo(n.raiz_alumno) == (None, None)
        n.agente.permisos_concedidos.discard("READ")
        assert n.conversar("¿Cuál es la fecha de hoy?").get("origen") != "alumno_supervisado"
    finally:
        n.ejecutor.shutdown()


def test_confirmacion_y_cancelacion_compartidas(tmp_path, monkeypatch):
    from threading import Event

    monkeypatch.setattr(config, "raiz_datos", lambda: str(tmp_path))
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "memory.json"))
    iniciada, liberar = Event(), Event()

    class ProfesorLento(ProfesorDePrueba):
        configurado = True

        def generar_consultas_locales(self, etiqueta):
            iniciada.set()
            assert liberar.wait(5)
            return super().generar_consultas_locales(etiqueta)

    n = Nucleo("local", profesor=ProfesorLento())
    cliente = "a" * 24
    try:
        assert "Confirma" in n.conversar("Entrenar alumno", modo="studio", cliente=cliente)["respuesta"]
        assert "antes de confirmar" in n.conversar("Confirma entrenar alumno", cliente="b" * 24)["respuesta"]
        assert "en cola" in n.conversar("Confirma entrenar alumno", cliente=cliente)["respuesta"]
        assert iniciada.wait(5)
        assert "generando ejemplos" in n.conversar("Estado del alumno")["respuesta"]
        assert "Cancelaré" in n.conversar("Cancela entrenar alumno", cliente=cliente)["respuesta"]
    finally:
        liberar.set()
        n.ejecutor.shutdown()
    assert "cancelado" in n.conversar("Estado del alumno")["respuesta"]
    assert cargar_activo(n.raiz_alumno) == (None, None)


def test_hora_fecha_dictado_y_abstencion():
    from core.alumno_supervisado import verificar

    assert verificar("Por favor, dime qué hora es") == "hora"
    assert verificar("Dme la ora local") == "hora"
    assert verificar("Qué fechaa es") == "fecha"
    assert verificar("Necesito la fecha de ahora") == "fecha"
    for frase in ("No me digas qué hora es", "Dme la ora local en París",
                  '«Qué fechaa es»', "Necesito la fecha de ahora y abre el PDF"):
        assert verificar(frase) == "abstener"
