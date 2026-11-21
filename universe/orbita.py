"""Animación del acompañante inspirada en NeuralCore de Arquitectura-Arus (MIT)."""
from math import cos, sin, tau
from time import monotonic
from tkinter import Canvas


class Orbita(Canvas):
    """Anillos, pulsos y nodos decorativos animados mientras el panel está visible."""

    def __init__(self, padre):
        super().__init__(padre, width=330, height=122, bg="#102027", highlightthickness=0)
        self._inicio = monotonic()
        self._turno = None
        self._procesando = False
        self.create_text(16, 20, text="CEREBRO", anchor="w", fill="#9be8e8",
                         font=("TkDefaultFont", 10, "bold"))
        self._etiqueta = self.create_text(16, 42, text="Disponible", anchor="w",
                                          fill="#a9c1c9", font=("TkDefaultFont", 8))
        self.bind("<Map>", self._reanudar)
        self.bind("<Unmap>", self._pausar)
        self.bind("<Destroy>", self._pausar)
        self._dibujar(0)

    def procesando(self, valor):
        self._procesando = bool(valor)
        self.itemconfigure(self._etiqueta, text="Procesando" if valor else "Disponible")
        self._dibujar(monotonic() - self._inicio)

    def _reanudar(self, _evento):
        if self._turno is None:
            self._fotograma()

    def _pausar(self, _evento):
        if self._turno is not None:
            self.after_cancel(self._turno)
            self._turno = None

    def _fotograma(self):
        self._dibujar(monotonic() - self._inicio)
        self._turno = self.after(40, self._fotograma)

    def _dibujar(self, segundos):
        self.delete("orbita")
        centro_x, centro_y = 171, 60
        radio = 49

        def caja(r, x=centro_x, y=centro_y):
            return x - r, y - r, x + r, y + r

        color = "#82f5ff" if self._procesando else "#51d5e7"
        velocidad = 0.9 if self._procesando else 0.35
        angulo = segundos * velocidad
        self.create_oval(*caja(radio), outline="#326470", dash=(2, 4), tags="orbita")
        self.create_oval(*caja(radio * .72), outline="#367b88", tags="orbita")
        self.create_oval(*caja(radio * .42 + 2 * sin(segundos * 4)), outline=color, tags="orbita")
        self.create_arc(*caja(radio + 4), start=angulo * 57.3, extent=84, style="arc",
                        outline=color, width=2, tags="orbita")

        for i in range(16):
            fase = i * tau / 16 + angulo
            distancia = radio - 4 + 2.5 * sin(segundos * 2 + i)
            x = centro_x + distancia * cos(fase)
            y = centro_y + distancia * sin(fase)
            self.create_line(centro_x, centro_y, x, y,
                             fill="#326773" if self._procesando else "#244750", tags="orbita")
            self.create_oval(*caja(2.3, x, y), fill="#102027", outline=color, tags="orbita")

        pulso = 6.4 + (2.4 if self._procesando else 1.3) * sin(segundos * 4)
        self.create_oval(*caja(pulso + 5), outline="#286675", tags="orbita")
        self.create_oval(*caja(pulso), fill=color, outline="#e2fdff", tags="orbita")
