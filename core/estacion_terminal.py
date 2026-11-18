"""Estación neuronal dentro de la terminal: curses, sin navegador ni red.

Representación de recuerdos, asociaciones léxicas y eventos registrados.
No muestra las neuronas ni los pesos internos del modelo.
"""
import curses
import json
import math
import time
from pathlib import Path

import config
from core.actividad_neuronal import ultimos
from core.mapa_memoria import grafo

PALETA = {
    "analizando": curses.COLOR_YELLOW, "aprendido": curses.COLOR_BLUE,
    "investigando": curses.COLOR_YELLOW, "consolidado": curses.COLOR_GREEN,
    "asociando": curses.COLOR_MAGENTA, "observando": curses.COLOR_CYAN,
    "error": curses.COLOR_RED,
}
SIMBOLOS = {"analizando": "?", "aprendido": "o", "investigando": "*",
            "consolidado": "O", "asociando": "+", "observando": "@", "error": "!"}


def cargar_recuerdos():
    ruta = Path(config.MEMORY_FILE)
    if not ruta.is_file() or ruta.stat().st_size > 5_000_000:
        return {}
    try:
        memoria = json.loads(ruta.read_text(encoding="utf-8")).get("long_term", {})
        return memoria if isinstance(memoria, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir(pantalla, y, x, texto, estilo=0):
    alto, ancho = pantalla.getmaxyx()
    if 0 <= y < alto and 0 <= x < ancho - 1:
        try:
            pantalla.addnstr(y, x, str(texto), ancho - x - 1, estilo)
        except curses.error:
            pass


def _linea(pantalla, x1, y1, x2, y2, estilo=0):
    pasos = max(abs(x2 - x1), abs(y2 - y1), 1)
    for i in range(pasos + 1):
        x = round(x1 + (x2 - x1) * i / pasos)
        y = round(y1 + (y2 - y1) * i / pasos)
        _escribir(pantalla, y, x, ".", estilo)


def _pantalla(pantalla, memoria_fn, eventos_fn):
    curses.curs_set(0)
    pantalla.nodelay(True)
    pantalla.timeout(120)
    if curses.has_colors():
        curses.start_color()
        for i, estado in enumerate(PALETA, 1):
            curses.init_pair(i, PALETA[estado], -1 if curses.use_default_colors() is None else -1)
    estilos = {estado: curses.color_pair(i) | curses.A_BOLD for i, estado in enumerate(PALETA, 1)}
    seleccionado, desplazamiento, zoom, congelado, tick = 0, 0, 1.0, False, 0
    memoria, eventos = {}, []
    nodos, enlaces = [], []
    ultima = 0
    while True:
        ahora = time.monotonic()
        if ahora - ultima > .7:
            memoria = memoria_fn()
            nodos, enlaces = grafo(memoria, limite=120)
            eventos = eventos_fn()
            ultima = ahora
            if nodos:
                seleccionado %= len(nodos)
        alto, ancho = pantalla.getmaxyx()
        pantalla.erase()
        if alto < 15 or ancho < 52:
            _escribir(pantalla, 1, 2, "Amplía la terminal (mínimo 52 x 15).")
        else:
            _escribir(pantalla, 0, 2, " CEREBRO  /  ESTACIÓN NEURONAL ", curses.A_BOLD)
            _escribir(pantalla, 1, 2, "Flechas: explorar  +/-: zoom  ESPACIO: pausa  q: volver")
            _escribir(pantalla, 2, 2, f"Recuerdos: {len(nodos)}   Enlaces: {len(enlaces)}   Eventos: {len(eventos)}")
            mapa_ancho = max(25, ancho * 2 // 3)
            centro_x, centro_y = mapa_ancho // 2, (alto + 3) // 2
            posiciones = []
            for i, nodo in enumerate(nodos):
                angulo = i * 2.399963 + desplazamiento * .04
                radio = min(mapa_ancho * .37, alto * .35) * zoom * (0.4 + .6 * math.sqrt((i + 1) / max(len(nodos), 1)))
                x = round(centro_x + math.cos(angulo) * radio)
                y = round(centro_y + math.sin(angulo) * radio * .55)
                posiciones.append((x, y))
            for a, b in enlaces:
                if a < len(posiciones) and b < len(posiciones):
                    _linea(pantalla, *posiciones[a], *posiciones[b], curses.A_DIM)
            for i, nodo in enumerate(nodos):
                x, y = posiciones[i]
                estilo = estilos["aprendido"] | (curses.A_REVERSE if i == seleccionado else 0)
                _escribir(pantalla, y, x, "@" if i == seleccionado else "o", estilo)
                if i == seleccionado:
                    _escribir(pantalla, y + 1, max(1, x - 5), nodo["etiqueta"][:14], estilo)
            estado = eventos[-1]["estado"] if eventos else "consolidado"
            _escribir(pantalla, centro_y, centro_x - 4, "[NÚCLEO]", estilos.get(estado, 0))
            if not congelado and eventos:
                _escribir(pantalla, centro_y - 2, centro_x, SIMBOLOS.get(estado, "*"), estilos.get(estado, 0))
            panel_x = mapa_ancho + 2
            _escribir(pantalla, 4, panel_x, "RECUERDO", curses.A_BOLD)
            if nodos:
                n = nodos[seleccionado]
                _escribir(pantalla, 5, panel_x, n["etiqueta"][:ancho-panel_x-2], estilos["aprendido"])
                texto = n["texto"]
                largo = max(8, ancho-panel_x-3)
                for j in range(0, min(len(texto), largo * 7), largo):
                    _escribir(pantalla, 7 + j // largo, panel_x, texto[j:j+largo])
            _escribir(pantalla, alto - 5, 2, "ESTADOS:", curses.A_BOLD)
            leyenda = "  ".join(f"{SIMBOLOS[k]} {k}" for k in PALETA)
            _escribir(pantalla, alto - 4, 2, leyenda[:ancho-4])
            if eventos:
                e = eventos[-1]
                _escribir(pantalla, alto - 3, 2, "Última actividad: " + e["estado"] + " / " + e.get("texto", ""))
            _escribir(pantalla, alto - 2, 2, "Nodos = recuerdos; líneas = palabras compartidas; animación ≠ neuronas físicas.")
        pantalla.refresh()
        tecla = pantalla.getch()
        if tecla in (ord("q"), ord("Q"), 27):
            return
        if tecla in (curses.KEY_RIGHT, curses.KEY_DOWN, ord("j")) and nodos:
            seleccionado = (seleccionado + 1) % len(nodos)
        if tecla in (curses.KEY_LEFT, curses.KEY_UP, ord("k")) and nodos:
            seleccionado = (seleccionado - 1) % len(nodos)
        if tecla in (ord("+"), ord("=")):
            zoom = min(1.8, zoom + .1)
        if tecla == ord("-"):
            zoom = max(.4, zoom - .1)
        if tecla == ord(" "):
            congelado = not congelado
        if not congelado:
            desplazamiento += .03
        tick += 1


def abrir(memoria_fn=None, eventos_fn=None):
    """Devuelve al chat al pulsar q. Requiere una terminal interactiva."""
    import sys
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("La estación requiere una terminal interactiva")
    curses.wrapper(_pantalla, memoria_fn or cargar_recuerdos, eventos_fn or ultimos)


if __name__ == "__main__":
    abrir()
