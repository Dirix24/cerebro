"""Trazo normalizado de una pinza y extrusión de un contorno plano cerrado."""
from math import hypot


class Trazo:
    def __init__(self):
        self.puntos = []
        self.estado = "esperando"
        self.abierta = False

    def actualizar(self, mano):
        if self.estado in {"terminado", "interrumpido"}:
            return
        if mano is None:
            if self.estado == "dibujando":
                self.estado = "interrumpido"
            return
        distancia = lambda a, b: hypot(mano[a][0] - mano[b][0], mano[a][1] - mano[b][1])
        palma = distancia(0, 9)
        if palma < .025:
            self.actualizar(None)
            return
        pinza = distancia(4, 8) / palma
        if pinza > .43:
            self.abierta = True
            if self.estado == "dibujando":
                self.estado = "terminado"
            return
        if self.abierta and pinza < .29:
            self.estado = "dibujando"
        if self.estado == "dibujando":
            punto = tuple(min(1, max(0, x)) for x in mano[8])
            if not self.puntos or hypot(punto[0] - self.puntos[-1][0], punto[1] - self.puntos[-1][1]) >= .009:
                if len(self.puntos) < 240:
                    self.puntos.append(punto)
                else:
                    self.estado = "terminado"


def _cruz(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _interseccion(a, b, c, d):
    tolerancia = 1e-8
    ab = _cruz(a, b, c), _cruz(a, b, d)
    cd = _cruz(c, d, a), _cruz(c, d, b)
    if ab[0] * ab[1] < 0 and cd[0] * cd[1] < 0:
        return True
    return any(abs(cruz) <= tolerancia and all(
        min(inicio[k], fin[k]) - tolerancia <= punto[k] <= max(inicio[k], fin[k]) + tolerancia
        for k in range(2)) for cruz, punto, inicio, fin in
        ((ab[0], c, a, b), (ab[1], d, a, b), (cd[0], a, c, d), (cd[1], b, c, d)))


def extruir(trazo):
    puntos = list(trazo)
    if len(puntos) > 3 and hypot(puntos[-1][0] - puntos[0][0], puntos[-1][1] - puntos[0][1]) < .016:
        puntos.pop()
    n = len(puntos)
    if n < 3:
        raise ValueError("Dibuja una figura con al menos tres puntos distintos.")
    lados = list(zip(puntos, puntos[1:] + puntos[:1]))
    for i, (a, b) in enumerate(lados):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if _interseccion(a, b, *lados[j]):
                raise ValueError("El contorno se cruza. Dibuja una figura sin cruces.")
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in lados)
    if abs(area) < .003:
        raise ValueError("La figura tiene poca superficie. Prueba con un trazo más amplio.")
    # La cámara muestra Y hacia abajo. Se invierte para exportar un plano cartesiano.
    if area > 0:
        puntos.reverse()
    x_min, y_min = map(min, zip(*puntos))
    x_max, y_max = map(max, zip(*puntos))
    escala = max(x_max - x_min, y_max - y_min)
    centro_x, centro_y = (x_min + x_max) / 2, (y_min + y_max) / 2
    vertices = [((x - centro_x) / escala, (centro_y - y) / escala, z)
                for z in (-.12, .12) for x, y in puntos]
    caras = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        caras.append((i, j, j + n, i + n))
    return vertices, caras


def obj(vertices, caras):
    lineas = ["o figura_cerebro"]
    lineas.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in vertices)
    lineas.extend("f " + " ".join(str(i + 1) for i in cara) for cara in caras)
    return "\n".join(lineas) + "\n"
