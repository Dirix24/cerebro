"""Ventana local para autorizar y pausar el seguimiento de manos."""
from contextlib import nullcontext
import importlib.util
import os
from math import cos, sin
from pathlib import Path
from queue import Empty, Full, Queue, SimpleQueue
from shutil import which
import subprocess
from threading import Event, Thread
from time import monotonic
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from core.figuras_tactiles import Trazo, extruir, obj
from core.gestos_tactiles import Gestos
from universe.diagnostico_instalacion import modelo_manos
from universe.paleta import ACENTO, BORDE, FONDO, PANEL, SELECCION, TEXTO


def camaras():
    dispositivos = []
    for ruta in sorted(Path("/sys/class/video4linux").glob("video[0-9]*")):
        try:
            if (Path("/dev") / ruta.name).exists():
                dispositivos.append((int(ruta.name[5:]), ruta.joinpath("name").read_text().strip()))
        except (OSError, ValueError):
            continue
    return dispositivos


def tecnologias():
    sesion = os.environ.get("XDG_SESSION_TYPE", "").lower()
    x11 = bool(os.environ.get("DISPLAY") and which("xdotool") and sesion != "wayland"
               and (sesion or not os.environ.get("WAYLAND_DISPLAY")))
    opencv = importlib.util.find_spec("cv2") is not None
    mediapipe = importlib.util.find_spec("mediapipe") is not None
    modelo = modelo_manos()
    dispositivos = [{"nodo": f"/dev/video{indice}", "nombre": nombre,
                     "permisos": os.access(f"/dev/video{indice}", os.R_OK | os.W_OK)}
                    for indice, nombre in camaras()]
    return {"x11": x11, "xdotool": bool(which("xdotool")), "opencv": opencv, "mediapipe": mediapipe,
            "dispositivos": dispositivos,
            "modelo": modelo if modelo and Path(modelo).expanduser().is_file() else None}


def _requisitos(marcador=False):
    ficha = tecnologias()
    if not ficha["x11"]:
        raise RuntimeError("Se necesita X11 y xdotool para controlar el puntero.")
    if not ficha["opencv"]:
        raise RuntimeError("Falta OpenCV en el entorno de Cerebro. Vuelve a ejecutar ./instalar desde tu copia actualizada.")
    if marcador:
        return None
    if not ficha["mediapipe"]:
        raise RuntimeError("Falta MediaPipe. Selecciona Marcador verde para mover solo el puntero.")
    if not ficha["modelo"]:
        raise RuntimeError("Configura CEREBRO_MODELO_MANOS con el archivo local hand_landmarker.task.")
    return str(Path(ficha["modelo"]).expanduser())


def _detector(modelo):
    import mediapipe as mp

    vision = mp.tasks.vision
    opciones = vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=modelo),
        running_mode=vision.RunningMode.VIDEO, num_hands=2)
    return vision.HandLandmarker.create_from_options(opciones)


def _manos(detector, rgb, marca):
    import mediapipe as mp

    resultado = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), marca)
    return {c[0].category_name: [(p.x, p.y) for p in puntos]
            for c, puntos in zip(resultado.handedness, resultado.hand_landmarks) if c}


def _marcador_verde(cv2, rgb, margen):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    mascara = cv2.inRange(hsv, (40, 110, 110), (83, 255, 255))
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return []
    figura = max(contornos, key=cv2.contourArea)
    alto, ancho = rgb.shape[:2]
    if not .002 <= cv2.contourArea(figura) / (alto * ancho) <= .18:
        return []
    momentos = cv2.moments(figura)
    if not momentos["m00"]:
        return []
    x = momentos["m10"] / momentos["m00"] / ancho
    y = momentos["m01"] / momentos["m00"] / alto
    amplitud = 1 - 2 * margen
    return [("mover", max(0, min(1, (x - margen) / amplitud)), max(0, min(1, (y - margen) / amplitud)))]


def _control(eventos, ancho, alto):
    comandos = []
    for evento in eventos:
        tipo = evento[0]
        if tipo == "mover":
            x, y = evento[1:]
            comandos.extend(("mousemove", str(round(x * (ancho - 1))), str(round(y * (alto - 1)))))
        elif tipo == "scroll":
            comandos.extend(("click", "4" if evento[1] > 0 else "5"))
        elif tipo in {"clic", "presionar", "soltar"}:
            comandos.extend(({"clic": "click", "presionar": "mousedown", "soltar": "mouseup"}[tipo], "1"))
    if comandos:
        subprocess.run(["xdotool", *comandos], check=True, timeout=.8, capture_output=True)


_CONEXIONES = ((0, 1, 2, 3, 4), (0, 5, 6, 7, 8), (5, 9, 10, 11, 12),
              (9, 13, 14, 15, 16), (13, 17, 18, 19, 20), (17, 0))


def _publicar_imagen(cuadros, imagen):
    try:
        cuadros.put_nowait(imagen)
    except Full:
        try:
            cuadros.get_nowait()
        except Empty:
            pass
        cuadros.put_nowait(imagen)


def _vista(cv2, rgb, manos):
    imagen = cv2.resize(rgb, (400, 280))
    for nombre, mano in manos.items():
        color = (83, 185, 255) if nombre == "Right" else (140, 231, 165)
        puntos = [(round(x * 399), round(y * 279)) for x, y in mano]
        for cadena in _CONEXIONES:
            for a, b in zip(cadena, cadena[1:]):
                cv2.line(imagen, puntos[a], puntos[b], color, 2)
        for punto in puntos:
            cv2.circle(imagen, punto, 3, color, -1)
    return b"P6\n400 280\n255\n" + imagen.tobytes()


def perfil_camara():
    """Perfil acotado para equipos con CPU y memoria limitadas."""
    from core.recursos_locales import perfil_equipo

    perfil = os.environ.get("CEREBRO_CAMARA_PERFIL", "").casefold()
    if perfil not in {"ligero", "normal"}:
        perfil = perfil_equipo(Path.cwd())
    if perfil == "ligero":
        return 320, 240, 10
    return 640, 480, 20


def _capturar(indice, modelo, detener, avisos, ancho, alto, ver, dibujar, reiniciar, habilitar_puntero, cuadros,
              margen=.12):
    gestos = Gestos(margen)
    camara = None
    try:
        import cv2
        with (_detector(modelo) if modelo else nullcontext()) as detector:
            if detener.is_set():
                return
            camara = cv2.VideoCapture(indice, cv2.CAP_V4L2)
            if not camara.isOpened():
                raise RuntimeError("No pude abrir esa cámara.")
            ancho_cuadro, alto_cuadro, fps = perfil_camara()
            camara.set(cv2.CAP_PROP_FRAME_WIDTH, ancho_cuadro)
            camara.set(cv2.CAP_PROP_FRAME_HEIGHT, alto_cuadro)
            camara.set(cv2.CAP_PROP_FPS, fps)
            avisos.put("Cámara activa")
            anterior = -1
            trazo = None
            ultimo_estado = None
            while not detener.is_set():
                inicio = monotonic()
                correcto, imagen = camara.read()
                if not correcto:
                    raise RuntimeError("No pude leer la cámara.")
                if imagen.shape[1] > ancho_cuadro or imagen.shape[0] > alto_cuadro:
                    escala = min(ancho_cuadro / imagen.shape[1], alto_cuadro / imagen.shape[0])
                    imagen = cv2.resize(imagen, (max(1, round(imagen.shape[1] * escala)),
                                                  max(1, round(imagen.shape[0] * escala))),
                                        interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(cv2.flip(imagen, 1), cv2.COLOR_BGR2RGB)
                ahora = monotonic()
                marca = max(anterior + 1, round(ahora * 1000))
                anterior = marca
                manos = _manos(detector, rgb, marca) if detector else {}
                if detener.is_set():
                    break
                if dibujar.is_set():
                    if trazo is None or reiniciar.is_set():
                        reiniciar.clear()
                        trazo = Trazo()
                        ultimo_estado = None
                    trazo.actualizar(manos.get("Right") or manos.get("Left"))
                    estado_dibujo = (trazo.estado, tuple(trazo.puntos))
                    if estado_dibujo != ultimo_estado:
                        avisos.put(estado_dibujo)
                        ultimo_estado = estado_dibujo
                else:
                    trazo = None
                if ver.is_set():
                    _publicar_imagen(cuadros, (_vista(cv2, rgb, manos), len(manos)))
                if not habilitar_puntero.is_set():
                    _control(gestos.pausar(), ancho, alto)
                elif detector is None:
                    _control(_marcador_verde(cv2, rgb, margen), ancho, alto)
                else:
                    derecha, izquierda = manos.get("Right"), manos.get("Left")
                    _control(gestos.actualizar(derecha or izquierda, ahora, izquierda if derecha else None), ancho, alto)
                detener.wait(max(0, 1 / fps - (monotonic() - inicio)))
    except Exception as exc:
        avisos.put(str(exc))
    finally:
        try:
            _control(gestos.pausar(), ancho, alto)
        except (OSError, subprocess.SubprocessError):
            pass
        finally:
            if camara is not None:
                camara.release()
            avisos.put(None)


def abrir():
    raiz = tk.Tk()
    raiz.title("Cerebro · Modo gestual")
    raiz.configure(bg=FONDO)
    raiz.attributes("-topmost", True)
    raiz.resizable(False, False)
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure(".", background=PANEL, foreground=TEXTO, fieldbackground=PANEL,
                     bordercolor=BORDE, lightcolor=BORDE, darkcolor=BORDE)
    estilo.map("TButton", background=[("active", SELECCION)])
    estilo.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", TEXTO)])
    raiz.option_add("*TCombobox*Listbox.background", PANEL)
    raiz.option_add("*TCombobox*Listbox.foreground", TEXTO)
    opciones = camaras()
    margen = .12
    valor = tk.StringVar(value="Cámara apagada")
    eventos = SimpleQueue()
    detener = Event()
    ver = Event()
    dibujar = Event()
    reiniciar = Event()
    habilitar_puntero = Event()
    habilitar_puntero.set()
    cuadros = Queue(maxsize=1)
    vista = tk.StringVar(value="")
    indicaciones = tk.StringVar(value="Índice: puntero · Pinza: clic o arrastre · Esc: pausa")
    puntos = ()
    figura = None
    trazo_listo = False
    angulo = .45
    foto = None
    activo = False
    cerrando = False
    tk.Label(raiz, text="Modo gestual por cámara", bg=FONDO, fg=ACENTO, font=("TkDefaultFont", 15, "bold")).pack(padx=18, pady=10)
    lista = ttk.Combobox(raiz, state="readonly", values=[f"video{i} · {nombre}" for i, nombre in opciones], width=40)
    lista.pack(padx=18, pady=(0, 8))
    motor = ttk.Combobox(raiz, state="readonly", values=("Manos · MediaPipe", "Marcador verde · solo puntero"), width=40)
    motor.pack(padx=18, pady=(0, 8))
    ficha = tecnologias()
    motor.current(1 if ficha["opencv"] and not (ficha["mediapipe"] and ficha["modelo"]) else 0)

    def calibrar():
        nonlocal margen
        if activo:
            valor.set("Pausa la cámara antes de calibrar.")
            return
        porcentaje = simpledialog.askinteger("Calibrar puntero", "Margen de la cámara en porcentaje (0–35)",
                                              initialvalue=round(margen * 100), minvalue=0, maxvalue=35, parent=raiz)
        if porcentaje is not None:
            margen = porcentaje / 100
            valor.set(f"Margen configurado: {porcentaje} %.")
    if opciones:
        lista.current(0)
    tk.Label(raiz, textvariable=valor, bg=FONDO, fg=TEXTO, width=47, wraplength=370).pack(padx=10)
    tk.Label(raiz, textvariable=indicaciones, bg=FONDO, fg=TEXTO, wraplength=400).pack(padx=14, pady=8)
    visual = tk.Frame(raiz, bg=FONDO)
    visual.pack(padx=12, pady=(0, 6))
    vista_camara = tk.Frame(visual, bg=FONDO)
    pantalla = tk.Label(vista_camara, bg=PANEL, fg=TEXTO, text="Activa la cámara para ver la imagen.")
    pantalla.pack(fill="both", expand=True)
    tk.Label(vista_camara, textvariable=vista, bg=FONDO, fg=ACENTO).pack(pady=4)
    lienzo = tk.Canvas(visual, width=400, height=280, bg=PANEL, highlightthickness=1, highlightbackground=BORDE)

    def pintar():
        lienzo.delete("all")
        if figura:
            vertices, caras = figura
            coseno, seno = cos(angulo), sin(angulo)
            pantalla_3d = []
            for x, y, z in vertices:
                horizontal = x * coseno + z * seno
                fondo = -x * seno + z * coseno
                pantalla_3d.append((200 + 155 * horizontal, 140 - 170 * (y * .87 - fondo * .5)))
            aristas = {tuple(sorted((a, b))) for cara in caras for a, b in zip(cara, cara[1:] + cara[:1])}
            for a, b in sorted(aristas):
                lienzo.create_line(*pantalla_3d[a], *pantalla_3d[b], fill=ACENTO, width=2)
        elif len(puntos) > 1:
            coordenadas = [coordenada for x, y in puntos for coordenada in (x * 400, y * 280)]
            lienzo.create_line(*coordenadas, fill=ACENTO, width=2)

    def alternar_vista():
        nonlocal foto
        if ver.is_set():
            ver.clear()
            foto = None
            pantalla.configure(image="", text="Vista de la cámara oculta.")
            vista_camara.pack_forget()
            boton_ver.configure(text="Ver cámara")
            if not dibujar.is_set():
                indicaciones.set("Vista oculta. Pulsa Usar puntero para volver al escritorio.")
        else:
            habilitar_puntero.clear()
            ver.set()
            vista_camara.pack(side="left", padx=(0, 6))
            boton_ver.configure(text="Ocultar cámara")
            if not dibujar.is_set():
                indicaciones.set("Vista de cámara. El puntero del escritorio está en pausa.")

    def iniciar_trazo():
        nonlocal puntos, figura, trazo_listo
        puntos, figura, trazo_listo = (), None, False
        habilitar_puntero.clear()
        dibujar.set()
        reiniciar.set()
        if not ver.is_set():
            alternar_vista()
        lienzo.pack(side="left", padx=4)
        convertir.configure(state="disabled")
        exportar.configure(state="disabled")
        indicaciones.set("Junta pulgar e índice, dibuja un contorno continuo y separa los dedos para terminar.")
        pintar()

    def modelo_3d():
        nonlocal figura
        if not trazo_listo:
            return
        try:
            figura = extruir(puntos)
        except ValueError as exc:
            indicaciones.set(str(exc))
            return
        indicaciones.set("Figura extruida. Arrastra sobre el dibujo para girarla o guarda un OBJ.")
        exportar.configure(state="normal")
        pintar()

    def guardar_obj():
        if not figura:
            return
        destino = filedialog.asksaveasfilename(parent=raiz, title="Exportar figura para Blender",
                                               defaultextension=".obj", filetypes=[("Wavefront OBJ", "*.obj")])
        if not destino:
            return
        try:
            with Path(destino).open("x", encoding="utf-8") as archivo:
                archivo.write(obj(*figura))
        except OSError as exc:
            messagebox.showerror("Exportar OBJ", str(exc), parent=raiz)
        else:
            indicaciones.set("OBJ guardado en " + Path(destino).name + ".")

    def girar(evento):
        nonlocal angulo
        if figura:
            angulo = (evento.x - 200) / 70
            pintar()

    def puntero():
        nonlocal foto
        if ver.is_set():
            alternar_vista()
        dibujar.clear()
        habilitar_puntero.set()
        foto = None
        lienzo.pack_forget()
        indicaciones.set("Índice: puntero · Pinza: clic o arrastre · Esc: pausa")

    lienzo.bind("<B1-Motion>", girar)
    controles = tk.Frame(raiz, bg=FONDO)
    controles.pack(padx=12, pady=(0, 12))

    def pausar(_evento=None):
        if activo:
            detener.set()
            valor.set("Pausando…")

    def iniciar():
        nonlocal activo, detener
        indice = lista.current()
        if indice < 0 or activo:
            return
        try:
            modelo = _requisitos(marcador=motor.current() == 1)
        except RuntimeError as exc:
            valor.set(str(exc))
            return
        if not messagebox.askyesno("Activar cámara", "¿Permitir la cámara seleccionada y el control del puntero?", parent=raiz):
            return
        activo = True
        motor.configure(state="disabled")
        boton_trazo.configure(state="normal" if modelo else "disabled")
        dibujar.clear()
        detener = Event()
        boton.configure(state="disabled")
        lista.configure(state="disabled")
        valor.set("Iniciando cámara…")
        Thread(target=_capturar, args=(opciones[indice][0], modelo, detener, eventos,
                                      raiz.winfo_screenwidth(), raiz.winfo_screenheight(),
                                      ver, dibujar, reiniciar, habilitar_puntero, cuadros, margen), daemon=True).start()

    def cerrar():
        nonlocal cerrando
        cerrando = True
        if activo:
            pausar()
        else:
            raiz.destroy()

    def actualizar():
        nonlocal activo, foto, puntos, trazo_listo
        while True:
            try:
                mensaje = eventos.get_nowait()
            except Empty:
                break
            if mensaje is None:
                activo = False
                boton.configure(state="normal" if opciones else "disabled")
                lista.configure(state="readonly")
                motor.configure(state="readonly")
                if valor.get() in {"Pausando…", "Cámara activa"}:
                    valor.set("Cámara apagada")
                foto = None
                pantalla.configure(image="", text="La cámara está apagada.")
                vista.set("")
                if cerrando:
                    raiz.destroy()
                    return
            elif isinstance(mensaje, tuple) and dibujar.is_set():
                estado, puntos = mensaje
                if estado in {"terminado", "interrumpido"}:
                    trazo_listo = estado == "terminado"
                    convertir.configure(state="normal" if trazo_listo else "disabled")
                    indicaciones.set("Trazo listo. Pulsa Convertir a 3D." if trazo_listo
                                     else "Se perdió la mano. Pulsa Dibujar figura para intentarlo otra vez.")
                pintar()
            elif isinstance(mensaje, str):
                valor.set(mensaje)
        try:
            imagen, manos = cuadros.get_nowait()
        except Empty:
            pass
        else:
            if activo and not detener.is_set() and ver.is_set():
                foto = tk.PhotoImage(data=imagen, format="ppm")
                pantalla.configure(image=foto, text="")
                vista.set(f"Manos detectadas: {manos} · Azul: derecha · Verde: izquierda")
        raiz.after(60, actualizar)

    def diagnosticar():
        ficha = tecnologias()
        lineas = [f"{nombre}: {'detectado' if ficha[clave] else 'no detectado'}" for clave, nombre in (
            ("x11", "Sesión X11 compatible"), ("xdotool", "xdotool"), ("opencv", "OpenCV"),
            ("mediapipe", "MediaPipe"), ("modelo", "Modelo de manos"))]
        lineas.extend(f"{d['nodo']} · {d['nombre']} · permisos {'disponibles' if d['permisos'] else 'insuficientes'}"
                       for d in ficha["dispositivos"])
        if not ficha["dispositivos"]:
            lineas.append("No se detectaron dispositivos V4L2.")
        lineas.append("La apertura se comprueba al activar la cámara.")
        messagebox.showinfo("Diagnóstico de cámara", "\n".join(lineas), parent=raiz)

    boton = ttk.Button(controles, text="Activar cámara", command=iniciar, state="normal" if opciones else "disabled")
    boton.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
    ttk.Button(controles, text="Pausar", command=pausar).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
    boton_ver = ttk.Button(controles, text="Ver cámara", command=alternar_vista)
    boton_ver.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
    boton_trazo = ttk.Button(controles, text="Dibujar figura", command=iniciar_trazo)
    boton_trazo.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
    ttk.Button(controles, text="Calibrar", command=calibrar).grid(row=3, column=0, columnspan=2, pady=4)
    convertir = ttk.Button(controles, text="Convertir a 3D", command=modelo_3d, state="disabled")
    convertir.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
    exportar = ttk.Button(controles, text="Guardar OBJ", command=guardar_obj, state="disabled")
    exportar.grid(row=1, column=2, padx=2, pady=2, sticky="ew")
    ttk.Button(controles, text="Usar puntero", command=puntero).grid(row=2, column=0, columnspan=3, pady=(4, 0))
    ttk.Button(controles, text="Diagnóstico", command=diagnosticar).grid(row=3, column=2, pady=4)
    if not opciones:
        valor.set("No se detectó una cámara compatible.")
    raiz.bind("<Escape>", pausar)
    raiz.protocol("WM_DELETE_WINDOW", cerrar)
    raiz.after(100, actualizar)
    raiz.mainloop()
