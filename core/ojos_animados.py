"""Rostro expresivo de Cerebro, exclusivamente local y sin cámara.

Animación de ojos en curses. No solicita dispositivos, no registra imágenes
ni necesita un modelo entrenado. El usuario controla el estado con teclas.
"""
import math
import time

try:
    import curses
except ImportError:
    curses = None

EXPRESIONES = {
    "normal": ("◉", "◉", "Atento"),
    "feliz": ("^", "^", "Feliz"),
    "curioso": ("◉", "◉", "Curioso"),
    "pensando": ("·", "◉", "Pensando"),
    "sorprendido": ("O", "O", "Sorprendido"),
    "dormido": ("—", "—", "Descansando"),
}


def fotograma(expresion="normal", instante=0.0):
    """Devuelve dos ojos y etiqueta; no tiene efectos secundarios."""
    if expresion not in EXPRESIONES:
        expresion = "normal"
    izquierdo, derecho, etiqueta = EXPRESIONES[expresion]
    # Parpadeo breve cada ~4 segundos, salvo expresiones cerradas.
    if expresion not in ("feliz", "dormido") and instante % 4.2 < .14:
        izquierdo = derecho = "—"
    return izquierdo, derecho, etiqueta


def _mostrar(pantalla):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    pantalla.timeout(70)
    expresiones = tuple(EXPRESIONES)
    indice = 0
    inicio = time.monotonic()
    while True:
        alto, ancho = pantalla.getmaxyx()
        pantalla.erase()
        expresion = expresiones[indice]
        ojo1, ojo2, etiqueta = fotograma(expresion, time.monotonic() - inicio)
        if alto < 10 or ancho < 36:
            try:
                pantalla.addnstr(0, 0, "Amplía la terminal. q: salir", max(0, ancho-1))
            except curses.error:
                pass
        else:
            rostro = (
                "    /-------------\\",
                "   /               \\",
                f"  |    {ojo1}     {ojo2}    |",
                "  |       ___       |",
                "   \\_______________/",
            )
            y = max(1, alto // 2 - 4)
            x = max(0, ancho // 2 - 11)
            try:
                pantalla.addnstr(1, 2, "CEREBRO / OJOS ANIMADOS", ancho - 3, curses.A_BOLD)
                for i, linea in enumerate(rostro):
                    pantalla.addnstr(y+i, x, linea, max(0, ancho-x-1))
                pantalla.addnstr(y+6, x, f"Expresión: {etiqueta}", max(0, ancho-x-1))
                pantalla.addnstr(alto-2, 2, "← →: expresión   1-6: elegir   q: salir", ancho-3)
                pantalla.addnstr(alto-1, 2, "Cámara: APAGADA. No se activa desde esta pantalla.", ancho-3)
            except curses.error:
                pass
        pantalla.refresh()
        tecla = pantalla.getch()
        if tecla in (ord("q"), ord("Q"), 27):
            break
        if tecla in (curses.KEY_RIGHT, ord("n")):
            indice = (indice + 1) % len(expresiones)
        elif tecla in (curses.KEY_LEFT, ord("p")):
            indice = (indice - 1) % len(expresiones)
        elif ord("1") <= tecla <= ord("6"):
            indice = tecla - ord("1")


def abrir():
    if curses is None:
        raise RuntimeError("En Windows instala windows-curses: pip install windows-curses")
    import sys
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("Los ojos requieren una terminal interactiva.")
    try:
        curses.wrapper(_mostrar)
    except (curses.error, KeyboardInterrupt) as exc:
        raise RuntimeError("No se pudo iniciar la animación en esta terminal.") from exc
