"""Traduce puntos normalizados de la mano a eventos de entrada, sin acceder a hardware."""
from math import hypot


class Gestos:
    def __init__(self, margen=.12):
        if not 0 <= margen <= .35:
            raise ValueError("Margen de calibración fuera de rango.")
        self.margen = margen
        self.posicion = None
        self.pinza_desde = None
        self.abierta = False
        self.estables = 0
        self.arrastrando = False
        self.referencia_scroll = None

    def pausar(self):
        eventos = [("soltar",)] if self.arrastrando else []
        self.__init__(self.margen)
        return eventos

    def actualizar(self, mano, ahora, secundaria=None):
        if not mano or len(mano) != 21:
            return self.pausar()
        palma = _distancia(mano[0], mano[9])
        if palma < .025:
            return self.pausar()
        # La distancia relativa a la palma evita gatillar por acercar la mano a la cámara.
        pinza = _distancia(mano[4], mano[8]) / palma
        x, y = mano[8]
        amplitud = 1 - 2 * self.margen
        x, y = _acotar((x - self.margen) / amplitud), _acotar((y - self.margen) / amplitud)
        anterior = self.posicion or (x, y)
        self.posicion = (.65 * anterior[0] + .35 * x, .65 * anterior[1] + .35 * y)
        self.estables += 1
        if self.estables < 4:
            return []

        if secundaria and len(secundaria) == 21 and not self.arrastrando:
            otra_palma = _distancia(secundaria[0], secundaria[9])
            if otra_palma >= .025 and _distancia(secundaria[4], secundaria[8]) < .32 * otra_palma:
                self.pinza_desde = None
                self.abierta = False
                actual = secundaria[8][1]
                if self.referencia_scroll is None:
                    self.referencia_scroll = actual
                    return []
                diferencia = actual - self.referencia_scroll
                if abs(diferencia) >= .055:
                    self.referencia_scroll = actual
                    return [("scroll", 1 if diferencia < 0 else -1)]
                return []
        self.referencia_scroll = None

        eventos = [("mover", *self.posicion)]
        if pinza > .43:
            if self.arrastrando:
                eventos.append(("soltar",))
            elif self.pinza_desde is not None and .12 <= ahora - self.pinza_desde < .45:
                eventos.append(("clic",))
            self.arrastrando = False
            self.pinza_desde = None
            self.abierta = True
        elif self.abierta and pinza < .29:
            if self.pinza_desde is None:
                self.pinza_desde = ahora
            elif not self.arrastrando and ahora - self.pinza_desde >= .45:
                eventos.append(("presionar",))
                self.arrastrando = True
        return eventos


def _distancia(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def _acotar(valor):
    return max(0, min(1, valor))
