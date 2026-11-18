"""Grafo local de recuerdos y estados. No representa neuronas físicas."""
import html
import json
import math
import re
from pathlib import Path

COLORES = {"analizando": "#eab308", "aprendido": "#3b82f6",
           "investigando": "#f97316"}


def grafo(memoria, limite=35):
    """Grafo acotado; evita trabajo cuadrático y enlaces masivos."""
    if not isinstance(memoria, dict):
        return [], []
    limite = max(0, min(int(limite), 200))
    nodos = []
    indices = {}
    enlaces = []
    vistos = set()
    for clave, dato in list(memoria.items())[:limite]:
        valor = str(dato.get("valor", "")) if isinstance(dato, dict) else str(dato)
        nodo = {"id": str(clave), "etiqueta": str(clave)[:45],
                "estado": "aprendido", "texto": valor[:150]}
        i = len(nodos)
        nodos.append(nodo)
        palabras = set(re.findall(r"\w{4,}", (nodo["id"] + " " + nodo["texto"]).lower()))
        for palabra in palabras:
            for j in (indices.get(palabra, []) if limite <= 35 else indices.get(palabra, [])[-8:]):
                par = (j, i)
                if par not in vistos:
                    enlaces.append(par)
                    vistos.add(par)
            indices.setdefault(palabra, []).append(i)
    return nodos, enlaces


def svg_memoria(memoria):
    nodos, enlaces = grafo(memoria)
    ancho, alto = 960, 640
    posiciones = []
    for i in range(len(nodos)):
        angulo = 2 * math.pi * i / max(1, len(nodos))
        posiciones.append((ancho / 2 + 350 * math.cos(angulo),
                           alto / 2 + 240 * math.sin(angulo)))
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
              'role="img" aria-label="Relaciones entre recuerdos guardados">',
              '<rect width="100%" height="100%" fill="#101827"/>',
              '<text x="25" y="35" fill="white" font-size="20">Cerebro · mapa de recuerdos</text>',
              '<text x="25" y="58" fill="#cbd5e1" font-size="12">Azul: aprendido · Amarillo: analizando · Naranja: investigando</text>']
    for i, j in enlaces:
        x1, y1 = posiciones[i]
        x2, y2 = posiciones[j]
        partes.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#64748b" opacity=".55"/>')
    for i, nodo in enumerate(nodos):
        x, y = posiciones[i]
        titulo = html.escape(nodo["etiqueta"] + ": " + nodo["texto"])
        etiqueta = html.escape(nodo["etiqueta"][:18])
        partes.append(f'<g><title>{titulo}</title><circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{COLORES[nodo["estado"]]}"/>'
                      f'<text x="{x+16:.1f}" y="{y+4:.1f}" fill="white" font-size="12">{etiqueta}</text></g>')
    if not nodos:
        partes.append('<text x="280" y="320" fill="white">Todavía no hay recuerdos guardados</text>')
    partes.append('</svg>')
    return "".join(partes)


def guardar_mapa(memoria, destino):
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8") as f:
        f.write(svg_memoria(memoria))
    return str(ruta)
