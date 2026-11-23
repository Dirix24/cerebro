"""Mapa de conocimiento interactivo nativo para el panel Universe de Studio."""
from math import cos, sin, tau
from datetime import datetime
from tkinter import Canvas, Listbox, StringVar, ttk

from universe.paleta import BORDE, EDITOR, PANEL, SELECCION, TEXTO

COLORES = {
    "memoria": "#7adafa", "aprendizaje": "#85f3b6", "conocimiento": "#55d8bf",
    "relaciones": "#e6c68d", "razonamiento": "#9eacff", "investigación": "#f4ae84",
    "procesamiento": "#c1e1e6", "errores": "#ef8888",
    "creación": "#e7a7f7", "inactividad": "#9aafc3",
}


class MapaStudio(ttk.Frame):
    def __init__(self, padre, actualizar, analizar=None, evaluar=None, eliminar=None):
        super().__init__(padre, padding=10)
        self._nodos = []
        self._inventario = []
        self._puntos = {}
        self._seleccionado = None
        self._arrastre = None
        self._movido = False
        self._giro = .5
        self._inclinacion = -.22
        self._zoom = 1

        controles = ttk.Frame(self)
        controles.pack(fill="x")
        ttk.Button(controles, text="Actualizar mapa", command=actualizar).pack(side="left")
        if analizar is not None:
            ttk.Button(controles, text="Analizar", command=analizar).pack(side="left", padx=(6, 0))
        if evaluar is not None:
            ttk.Button(controles, text="Evaluar alumno", command=evaluar).pack(side="left", padx=(6, 0))
        ttk.Label(controles, text="Arrastra para girar · Rueda para ampliar · Selecciona para inspeccionar").pack(
            side="left", padx=8
        )
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(8, 0))
        self._filtros = {}
        for campo, etiqueta in (("tipo", "Categoría"), ("grupo", "Grupo"),
                                ("estado", "Estado"), ("accion", "Proceso")):
            ttk.Label(filtros, text=etiqueta).pack(side="left", padx=(0, 4))
            selector = ttk.Combobox(filtros, state="readonly", width=13, values=("Todos",))
            selector.current(0)
            selector.pack(side="left", padx=(0, 9))
            selector.bind("<<ComboboxSelected>>", lambda _evento: self._filtrar())
            self._filtros[campo] = selector
        leyenda = ttk.Frame(self)
        leyenda.pack(fill="x", pady=(8, 0))
        for categoria, color in COLORES.items():
            ttk.Label(leyenda, text="● " + categoria.capitalize(), foreground=color).pack(side="left", padx=(0, 9))
        panel = ttk.Panedwindow(self, orient="horizontal")
        panel.pack(fill="both", expand=True, pady=(8, 0))
        self._lienzo = Canvas(panel, width=500, height=350, background=EDITOR, highlightthickness=1, highlightbackground=BORDE)
        panel.add(self._lienzo, weight=5)
        fichas = ttk.Frame(panel, padding=(8, 0))
        panel.add(fichas, weight=2)
        self._lista = Listbox(fichas, background=PANEL, foreground=TEXTO,
                              selectbackground=SELECCION, selectforeground=TEXTO,
                              highlightthickness=1, highlightbackground=BORDE, relief="flat", exportselection=False)
        self._lista.pack(fill="both", expand=True)
        self._detalle = StringVar(value="Selecciona un nodo. La posición es visual.")
        ttk.Label(fichas, textvariable=self._detalle, justify="left", wraplength=285).pack(
            fill="x", pady=(8, 2)
        )
        self._eliminar = eliminar
        self._borrar = ttk.Button(fichas, text="Eliminar recuerdo", command=self._eliminar_seleccionado)
        self._borrar.pack(anchor="w")
        self._borrar.configure(state="disabled")
        self._lienzo.bind("<Configure>", lambda _evento: self._dibujar())
        self._lienzo.bind("<ButtonPress-1>", self._pulsar)
        self._lienzo.bind("<B1-Motion>", self._mover)
        self._lienzo.bind("<ButtonRelease-1>", self._soltar)
        self._lienzo.bind("<MouseWheel>", lambda evento: self._ampliar(1 if evento.delta > 0 else -1))
        self._lienzo.bind("<Button-4>", lambda _evento: self._ampliar(1))
        self._lienzo.bind("<Button-5>", lambda _evento: self._ampliar(-1))
        self._lista.bind("<<ListboxSelect>>", self._desde_lista)

    def _eliminar_seleccionado(self):
        nodo = next((n for n in self._nodos if n["id"] == self._seleccionado and n.get("eliminable")), None)
        if nodo and self._eliminar:
            self._eliminar(nodo)

    def actualizar(self, datos):
        self._inventario = [nodo for nodo in datos.get("nodos", []) if nodo.get("id")]
        for campo, selector in self._filtros.items():
            seleccion = selector.get()
            valores = sorted({nodo[campo] for nodo in self._inventario if nodo.get(campo)})
            selector.configure(values=("Todos", *valores))
            selector.set(seleccion if seleccion in valores else "Todos")
        self._filtrar()

    def _filtrar(self):
        self._borrar.configure(state="disabled")
        filtros = {campo: selector.get() for campo, selector in self._filtros.items()
                   if selector.current() != 0}
        self._nodos = [nodo for nodo in self._inventario
                       if all(nodo.get(campo) == valor for campo, valor in filtros.items())]
        self._lista.delete(0, "end")
        for nodo in self._nodos:
            self._lista.insert("end", nodo["titulo"])
        if self._nodos:
            id_anterior = self._seleccionado
            indice = next((i for i, nodo in enumerate(self._nodos) if nodo["id"] == id_anterior), None)
            if indice is not None:
                self._seleccionar(indice)
            else:
                self._seleccionado = None
                self._detalle.set("Selecciona un recuerdo, una medida, una ficha o un evento.")
        else:
            self._seleccionado = None
            self._detalle.set("No hay nodos que coincidan con los filtros." if self._inventario
                              else "Aún no hay datos. Guarda un recuerdo o aprende de un modelo OBJ.")
        self._dibujar()

    def _dibujar(self):
        lienzo = self._lienzo
        lienzo.delete("all")
        ancho, alto = lienzo.winfo_width(), lienzo.winfo_height()
        cx, cy = ancho / 2, alto / 2
        radio = min(ancho, alto) * .38 * self._zoom
        puntos = {}
        profundidad = []

        for i, nodo in enumerate(self._nodos):
            y = 1 - (2 * (i + .5) / len(self._nodos))
            paralelo = (1 - y * y) ** .5
            fase = self._giro + i * tau * .381966
            x = paralelo * cos(fase)
            z = paralelo * sin(fase)
            vertical = y * cos(self._inclinacion) - z * sin(self._inclinacion)
            fondo = y * sin(self._inclinacion) + z * cos(self._inclinacion)
            escala = 3 / (3.5 - fondo)
            px, py = cx + x * radio * escala, cy + vertical * radio * escala
            puntos[nodo["id"]] = (px, py, escala, i)
            profundidad.append((fondo, nodo["id"]))

        lienzo.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, outline="#234957", dash=(3, 6))
        lienzo.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#478c98", outline="#a5e4e7")
        for nodo in self._nodos:
            x, y, _, _ = puntos[nodo["id"]]
            for destino in nodo.get("vinculos", []):
                if destino in puntos:
                    u, v, _, _ = puntos[destino]
                    lienzo.create_line(x, y, u, v, fill="#407080")
        for _, identificador in sorted(profundidad):
            x, y, escala, indice = puntos[identificador]
            nodo = self._nodos[indice]
            r = (7 if identificador == self._seleccionado else 4) * escala
            lienzo.create_oval(x - r, y - r, x + r, y + r,
                              fill=COLORES.get(nodo["tipo"], "#e0f0f3"), outline="#0c1a24")
        self._puntos = puntos

    def _pulsar(self, evento):
        self._arrastre = (evento.x, evento.y)
        self._movido = False

    def _mover(self, evento):
        if self._arrastre is not None:
            x, y = self._arrastre
            self._giro += (evento.x - x) * .016
            self._inclinacion += (evento.y - y) * .013
            self._arrastre = (evento.x, evento.y)
            self._movido = True
            self._dibujar()

    def _soltar(self, evento):
        self._arrastre = None
        if self._movido:
            return
        cercanos = [((x - evento.x) ** 2 + (y - evento.y) ** 2, -escala, indice)
                    for x, y, escala, indice in self._puntos.values()]
        if cercanos:
            distancia, _, indice = min(cercanos)
            if distancia < 100:
                self._seleccionar(indice)

    def _ampliar(self, sentido):
        self._zoom = max(.6, min(2.2, self._zoom + sentido * .15))
        self._dibujar()

    def _desde_lista(self, _evento):
        seleccion = self._lista.curselection()
        if seleccion:
            self._seleccionar(seleccion[0])

    def _seleccionar(self, indice):
        nodo = self._nodos[indice]
        self._seleccionado = nodo["id"]
        self._lista.selection_clear(0, "end")
        self._lista.selection_set(indice)
        self._lista.see(indice)
        fecha = nodo.get("fecha")
        if fecha:
            try:
                fecha = datetime.fromisoformat(fecha.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            except (ValueError, AttributeError, OSError):
                pass
        proceso = "".join(f"{nombre}: {nodo[campo]}{unidad}\n" for campo, nombre, unidad in
                          (("estado", "Estado", ""), ("accion", "Operación", ""), ("duracion_ms", "Duración", " ms"))
                          if campo in nodo)
        self._detalle.set(f"{nodo['titulo']}\nTipo: {nodo.get('tipo', 'registro')}\n"
                          f"Origen: {nodo.get('origen') or 'Sin registrar'}\n"
                          f"Fecha y hora: {fecha or 'Sin registrar'}\n{proceso}\n{nodo.get('detalle', '')}")
        self._borrar.configure(state="normal" if nodo.get("eliminable") and self._eliminar else "disabled")
        self._dibujar()
