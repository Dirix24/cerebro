import pytest
from core import estacion_terminal


def test_carga_memoria_desde_archivo(tmp_path, monkeypatch):
    import config
    ruta = tmp_path / "memoria.json"
    ruta.write_text('{"long_term":{"robot":{"valor":"sensor"}}}', encoding="utf-8")
    monkeypatch.setattr(config, "MEMORY_FILE", str(ruta))
    assert estacion_terminal.cargar_recuerdos()["robot"]["valor"] == "sensor"


def test_memoria_corrupta_no_rompe_terminal(tmp_path, monkeypatch):
    import config
    ruta = tmp_path / "memoria.json"
    ruta.write_text("{")
    monkeypatch.setattr(config, "MEMORY_FILE", str(ruta))
    assert estacion_terminal.cargar_recuerdos() == {}


def test_estacion_requiere_tty(monkeypatch):
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(RuntimeError, match="interactiva"):
        estacion_terminal.abrir()


def test_paleta_todos_los_estados():
    from core.actividad_neuronal import ESTADOS
    assert ESTADOS == set(estacion_terminal.PALETA)


def test_caracteres_de_control_no_llegan_a_curses():
    class Pantalla:
        def __init__(self):
            self.texto = ""
        def getmaxyx(self):
            return (25, 80)
        def addnstr(self, y, x, texto, n, estilo):
            self.texto = texto
    pantalla = Pantalla()
    estacion_terminal._escribir(pantalla, 1, 1, "hola\x1b[31m\nsecreto")
    assert "\x1b" not in pantalla.texto
    assert "\n" not in pantalla.texto


def test_estacion_sin_archivo_de_memoria(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "MEMORY_FILE", str(tmp_path / "ausente.json"))
    assert estacion_terminal.cargar_recuerdos() == {}

def test_pantalla_simulada_se_puede_explorar_y_salir(monkeypatch):
    if estacion_terminal.curses is None:
        pytest.skip("curses no disponible")
    class Pantalla:
        def __init__(self):
            self.teclas = [estacion_terminal.curses.KEY_RIGHT, ord("+"), ord(" "), ord("q")]
            self.escrito = []
        def nodelay(self, _):
            pass
        def timeout(self, _):
            pass
        def getmaxyx(self):
            return 28, 100
        def erase(self):
            pass
        def addnstr(self, y, x, texto, n, estilo):
            self.escrito.append(texto)
        def refresh(self):
            pass
        def getch(self):
            return self.teclas.pop(0)
    pantalla = Pantalla()
    monkeypatch.setattr(estacion_terminal.curses, "curs_set", lambda _: None)
    monkeypatch.setattr(estacion_terminal.curses, "has_colors", lambda: False)
    estacion_terminal._pantalla(
        pantalla,
        lambda: {"robot": {"valor": "sensor"}, "sensor": {"valor": "robot"}},
        lambda: [{"estado": "aprendido", "texto": "memoria"}],
    )
    assert any("NÚCLEO" in t for t in pantalla.escrito)
    assert any("RECUERDO" in t for t in pantalla.escrito)


def test_windows_sin_curses_error_amigable(monkeypatch):
    monkeypatch.setattr(estacion_terminal, "curses", None)
    with pytest.raises(RuntimeError, match="windows-curses"):
        estacion_terminal.abrir()
