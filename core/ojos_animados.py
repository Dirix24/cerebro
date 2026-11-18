"""Ojos expresivos de Cerebro: animación terminal sin boca, cámara ni red.

Modo automático opcional basado SOLO en estados de telemetría local.
La actividad representa procesos del programa, no sentimientos.
"""
import time
from datetime import datetime, timezone

try:
    import curses
except ImportError:
    curses = None

from core.actividad_neuronal import ultimos

# Cada estado usa exclusivamente los dos ojos; nunca se dibuja boca.
EXPRESIONES = {
    "atento": ("◉", "◉", "Atento"),
    "feliz": ("⌒", "⌒", "Feliz"),
    "curioso": ("◉", "◎", "Curioso"),
    "pensando": ("·", "◉", "Pensando"),
    "sorprendido": ("O", "O", "Sorprendido"),
    "dormido": ("—", "—", "Descansando"),
    "analizando": ("◉", "·", "Analizando"),
    "aprendiendo": ("✦", "✦", "Aprendiendo"),
    "investigando": ("◎", "◎", "Investigando"),
    "asociando": ("◉", "◉", "Conectando recuerdos"),
    "observando": ("◉", "◉", "Observando actividad"),
    "consolidando": ("◡", "◡", "Consolidando"),
    "error": ("×", "×", "Error detectado"),
    "concentrado": ("▰", "▰", "Concentrado"),
    "dudando": ("◔", "◕", "Evaluando"),
    "esperando": ("·", "·", "Esperando"),
    "saludando": ("◉", "◉", "Saludando"),
    "descansando": ("—", "—", "En reposo"),
}
ESTADO_A_EXPRESION = {
    "analizando": "analizando",
    "aprendido": "aprendiendo",
    "investigando": "investigando",
    "asociando": "asociando",
    "observando": "observando",
    "consolidado": "consolidando",
    "error": "error",
}


def expresion_de_actividad(eventos, ahora=None, caducidad=12):
    """Solo refleja eventos recientes y válidos, sin analizar texto privado."""
    if not eventos:
        return "esperando"
    evento = eventos[-1]
    if not isinstance(evento, dict):
        return "esperando"
    estado = evento.get("estado")
    if estado not in ESTADO_A_EXPRESION:
        return "esperando"
    try:
        fecha = datetime.fromisoformat(str(evento["fecha"]).replace("Z", "+00:00"))
        if fecha.tzinfo is None:
            return "esperando"
        momento = ahora or datetime.now(timezone.utc)
        edad = (momento - fecha).total_seconds()
        if edad < -2 or edad > caducidad:
            return "esperando"
    except (ValueError, TypeError, KeyError, OverflowError):
        return "esperando"
    return ESTADO_A_EXPRESION[estado]


def fotograma(expresion="atento", instante=1.0):
    """Devuelve (ojo izquierdo, ojo derecho, etiqueta). Sin efectos secundarios."""
    if expresion == "normal":
        expresion = "atento"  # Compatibilidad con versión anterior.
    if expresion not in EXPRESIONES:
        expresion = "atento"
    izquierdo, derecho, etiqueta = EXPRESIONES[expresion]
    if expresion not in ("feliz", "dormido", "descansando", "consolidando", "error") and instante % 4.2 < .14:
        izquierdo = derecho = "—"
    # Microgestos suaves de ojos robóticos: destello, guiño y exploración.
    # Los intervalos son breves; sin boca, sensores ni procesamiento externo.
    fase = instante % 8.0
    if expresion == "saludando" and 1.2 <= fase < 1.45:
        izquierdo = "—"  # Guiño corto.
    elif expresion == "aprendiendo" and 2.0 <= fase < 2.25:
        izquierdo = derecho = "✧"  # Destello del aprendizaje.
    elif expresion == "analizando" and int(instante * 2) % 2:
        izquierdo, derecho = derecho, izquierdo  # Mirada de análisis.
    elif expresion == "investigando" and int(instante * 1.5) % 2:
        izquierdo, derecho = "◉", "◎"
    elif expresion == "esperando" and 3.0 <= fase < 3.25:
        izquierdo = derecho = "—"  # Parpadeo en reposo.
    # Movimiento de mirada, sin cámara: solo animación periódica.
    if expresion in ("curioso", "observando", "saludando") and int(instante * 1.3) % 2 and not (expresion == "saludando" and 1.2 <= fase < 1.45):
        izquierdo, derecho = derecho, izquierdo
    return izquierdo, derecho, etiqueta


def _escribir(pantalla, y, x, texto, estilo=0):
    alto, ancho = pantalla.getmaxyx()
    if 0 <= y < alto and 0 <= x < ancho - 1:
        try:
            pantalla.addnstr(y, x, str(texto), ancho - x - 1, estilo)
        except (curses.error, UnicodeError):
            pass


def _mostrar(pantalla, eventos_fn=ultimos):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    pantalla.timeout(90)
    nombres = tuple(EXPRESIONES)
    indice = 0
    automatico = True  # Modo automático por defecto.
    inicio = time.monotonic()
    ultima_lectura = 0
    expresion_auto = "esperando"
    while True:
        ahora = time.monotonic()
        if automatico and ahora - ultima_lectura >= .7:
            try:
                expresion_auto = expresion_de_actividad(eventos_fn())
            except (OSError, ValueError, TypeError):
                expresion_auto = "esperando"
            ultima_lectura = ahora
        expresion = expresion_auto if automatico else nombres[indice]
        ojo1, ojo2, etiqueta = fotograma(expresion, ahora - inicio)
        alto, ancho = pantalla.getmaxyx()
        pantalla.erase()
        if alto < 12 or ancho < 42:
            _escribir(pantalla, 0, 0, "Amplía la terminal (42x12). q: salir")
        else:
            _escribir(pantalla, 1, 2, "CEREBRO  /  OJOS EXPRESIVOS", curses.A_BOLD)
            # Dos ojos, sin boca, nariz ni contorno facial.
            x = max(1, ancho // 2 - 12)
            y = max(3, alto // 2 - 3)
            _escribir(pantalla, y, x, "╭────────╮    ╭────────╮")
            _escribir(pantalla, y + 1, x, "│        │    │        │")
            _escribir(pantalla, y + 2, x, f"│   {ojo1}    │    │   {ojo2}    │")
            _escribir(pantalla, y + 3, x, "│        │    │        │")
            _escribir(pantalla, y + 4, x, "╰────────╯    ╰────────╯")
            _escribir(pantalla, y + 6, x, "Estado: " + etiqueta)
            _escribir(pantalla, alto - 3, 2, f"Modo: {'AUTOMÁTICO (actividad local)' if automatico else 'MANUAL'}  |  a: alternar")
            _escribir(pantalla, alto - 2, 2, "← →: cambiar   1-9: elegir   q: salir")
            _escribir(pantalla, alto - 1, 2, "CÁMARA APAGADA · SIN AUDIO · SIN RED")
        pantalla.refresh()
        tecla = pantalla.getch()
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (ord("a"), ord("A")):
            automatico = not automatico
            ultima_lectura = 0
        elif tecla in (curses.KEY_RIGHT, ord("n")):
            automatico = False
            indice = (indice + 1) % len(nombres)
        elif tecla in (curses.KEY_LEFT, ord("p")):
            automatico = False
            indice = (indice - 1) % len(nombres)
        elif ord("1") <= tecla <= ord("9"):
            automatico = False
            indice = tecla - ord("1")


def abrir(eventos_fn=None):
    if curses is None:
        raise RuntimeError("En Windows instala windows-curses: pip install windows-curses")
    import sys
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("Los ojos requieren una terminal interactiva.")
    try:
        curses.wrapper(_mostrar, eventos_fn or ultimos)
    except (curses.error, KeyboardInterrupt) as exc:
        raise RuntimeError("No se pudo iniciar la animación en esta terminal.") from exc
