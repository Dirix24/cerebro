"""Estación neuronal dentro de la terminal: curses, sin navegador ni red.

Representación de recuerdos, asociaciones léxicas y eventos registrados.
No muestra las neuronas ni los pesos internos del modelo.
"""
try:
    import curses
except ImportError:
    curses = None
import json
import math
import re
import time
from pathlib import Path

import config
from core.actividad_neuronal import ultimos
from core.mapa_memoria import grafo

PALETA = {
    "analizando": 3, "aprendido": 4, "investigando": 3,
    "consolidado": 2, "asociando": 5, "observando": 6, "error": 1,
    "razonando": 5, "recuperando": 6, "creando": 5, "verificado": 2,
}
SIMBOLOS = {"analizando": "?", "aprendido": "o", "investigando": "*",
            "consolidado": "O", "asociando": "+", "observando": "@", "error": "!",
            "razonando": "=", "recuperando": "<", "creando": "#", "verificado": "V"}


def cargar_recuerdos():
    ruta = Path(config.MEMORY_FILE)
    try:
        if not ruta.is_file() or ruta.stat().st_size > 5_000_000:
            return {}
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        memoria = datos.get("long_term", {}) if isinstance(datos, dict) else {}
        return memoria if isinstance(memoria, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir(pantalla, y, x, texto, estilo=0):
    alto, ancho = pantalla.getmaxyx()
    if 0 <= y < alto and 0 <= x < ancho - 1:
        try:
            seguro = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(texto))
            pantalla.addnstr(y, x, seguro, ancho - x - 1, estilo)
        except (curses.error, UnicodeError):
            pass


def _linea(pantalla, x1, y1, x2, y2, estilo=0):
    pasos = max(abs(x2 - x1), abs(y2 - y1), 1)
    for i in range(pasos + 1):
        x = round(x1 + (x2 - x1) * i / pasos)
        y = round(y1 + (y2 - y1) * i / pasos)
        _escribir(pantalla, y, x, ".", estilo)


def _pantalla(pantalla, memoria_fn, eventos_fn):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    pantalla.nodelay(True)
    pantalla.timeout(120)
    estilos = {estado: curses.A_BOLD for estado in PALETA}
    if curses.has_colors() and getattr(curses, "COLOR_PAIRS", 0) >= len(PALETA) + 1:
        curses.start_color()
        try:
            curses.use_default_colors()
            fondo = -1
        except curses.error:
            fondo = curses.COLOR_BLACK
        for i, estado in enumerate(PALETA, 1):
            try:
                primer_plano = (208 if estado == "investigando" and curses.COLORS >= 256
                                 else PALETA[estado])
                curses.init_pair(i, primer_plano, fondo)
                estilos[estado] = curses.color_pair(i) | curses.A_BOLD
            except curses.error:
                pass
    seleccionado, desplazamiento, zoom, congelado = 0, 0, 1.0, False
    memoria, eventos = {}, []
    nodos, enlaces = [], []
    ultima = 0
    while True:
        ahora = time.monotonic()
        if ahora - ultima > .7:
            try:
                memoria = memoria_fn()
                nodos, enlaces = grafo(memoria, limite=120)
                eventos = eventos_fn()
            except (OSError, ValueError, TypeError, KeyError):
                nodos, enlaces, eventos = [], [], []
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
            mapa_alto = alto - 7
            centro_x, centro_y = mapa_ancho // 2, 3 + mapa_alto // 2
            posiciones = []
            for i, nodo in enumerate(nodos):
                angulo = i * 2.399963 + desplazamiento * .04
                radio = min(mapa_ancho * .37, alto * .35) * zoom * (0.4 + .6 * math.sqrt((i + 1) / max(len(nodos), 1)))
                x = round(centro_x + math.cos(angulo) * radio)
                y = round(centro_y + math.sin(angulo) * radio * .55)
                posiciones.append((x, y))
            for a, b in enlaces[:400]:
                if a < len(posiciones) and b < len(posiciones):
                    x1, y1 = posiciones[a]
                    x2, y2 = posiciones[b]
                    if 1 <= x1 < mapa_ancho and 3 <= y1 < alto-5 and 1 <= x2 < mapa_ancho and 3 <= y2 < alto-5:
                        _linea(pantalla, x1, y1, x2, y2, curses.A_DIM)
            for i, nodo in enumerate(nodos):
                x, y = posiciones[i]
                estilo = estilos["aprendido"] | (curses.A_REVERSE if i == seleccionado else 0)
                if not (1 <= x < mapa_ancho and 3 <= y < alto-5):
                    continue
                _escribir(pantalla, y, x, "@" if i == seleccionado else "o", estilo)
                if i == seleccionado:
                    _escribir(pantalla, y + 1, max(1, x - 5), nodo["etiqueta"][:14], estilo)
            estado = eventos[-1].get("estado", "consolidado") if eventos and isinstance(eventos[-1], dict) else "consolidado"
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
                    if 7 + j // largo < alto - 6:
                        _escribir(pantalla, 7 + j // largo, panel_x, texto[j:j+largo])
            _escribir(pantalla, alto - 5, 2, "ESTADOS:", curses.A_BOLD)
            leyenda = "  ".join(f"{SIMBOLOS[k]} {k}" for k in PALETA)
            _escribir(pantalla, alto - 4, 2, leyenda[:ancho-4])
            if eventos:
                e = eventos[-1]
                if isinstance(e, dict):
                    _escribir(pantalla, alto - 3, 2, "Última actividad: " + str(e.get("estado", "")) + " / " + str(e.get("texto", "")))
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


def abrir(memoria_fn=None, eventos_fn=None):
    """Devuelve al chat al pulsar q. Requiere una terminal interactiva."""
    import sys
    if curses is None:
        raise RuntimeError("En Windows instala windows-curses: pip install windows-curses")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("La estación requiere una terminal interactiva")
    try:
        curses.wrapper(_pantalla, memoria_fn or cargar_recuerdos, eventos_fn or ultimos)
    except (curses.error, ValueError, KeyboardInterrupt) as exc:
        raise RuntimeError("No se pudo iniciar la pantalla de terminal") from exc


if __name__ == "__main__":
    abrir()
