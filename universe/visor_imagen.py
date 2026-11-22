"""Superficie desplazable de Studio para imágenes y páginas renderizadas."""
from tkinter import Canvas, ttk


class VisorImagen(ttk.Frame):
    def __init__(self, padre, fondo):
        super().__init__(padre)
        self.lienzo = Canvas(self, background=fondo, highlightthickness=0, cursor="fleur")
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.lienzo.xview)
        vertical = ttk.Scrollbar(self, command=self.lienzo.yview)
        self.lienzo.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        horizontal.pack(side="bottom", fill="x")
        vertical.pack(side="right", fill="y")
        self.lienzo.pack(fill="both", expand=True)
        self.elemento = self.lienzo.create_image(0, 0, anchor="nw")
        self.imagen = None
        self.lienzo.bind("<ButtonPress-1>", lambda e: self.lienzo.scan_mark(e.x, e.y))
        self.lienzo.bind("<B1-Motion>", lambda e: self.lienzo.scan_dragto(e.x, e.y, gain=1))

    def ancla(self, x, y):
        if self.imagen is None:
            return None
        return (self.lienzo.canvasx(x) / self.imagen.width(),
                self.lienzo.canvasy(y) / self.imagen.height(), x, y)

    def mostrar(self, imagen, ancla=None):
        self.imagen = imagen
        self.lienzo.itemconfigure(self.elemento, image=imagen)
        ancho, alto = imagen.width(), imagen.height()
        self.lienzo.configure(scrollregion=(0, 0, ancho, alto))
        if ancla:
            u, v, x, y = ancla
            self.lienzo.xview_moveto(max(0, u - x / ancho))
            self.lienzo.yview_moveto(max(0, v - y / alto))
        else:
            self.lienzo.xview_moveto(0)
            self.lienzo.yview_moveto(0)
