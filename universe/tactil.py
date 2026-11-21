"""Ventana local para autorizar y pausar el seguimiento de manos."""
import importlib.util
import os
from pathlib import Path
from queue import Empty, SimpleQueue
from shutil import which
import subprocess
from threading import Event, Thread
from time import monotonic
import tkinter as tk
from tkinter import messagebox, ttk

from core.gestos_tactiles import Gestos
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


def _requisitos():
    sesion = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if sesion == "wayland" or (not sesion and os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("El control del puntero solo está disponible en X11.")
    if not os.environ.get("DISPLAY") or not which("xdotool"):
        raise RuntimeError("Se necesita una sesión X11 con xdotool.")
    if any(importlib.util.find_spec(modulo) is None for modulo in ("cv2", "mediapipe")):
        raise RuntimeError("Faltan OpenCV y MediaPipe. Consulta la guía de Cerebro.")
    modelo = os.environ.get("CEREBRO_MODELO_MANOS")
    if not modelo or not Path(modelo).is_file():
        raise RuntimeError("Configura CEREBRO_MODELO_MANOS con el archivo local hand_landmarker.task.")
    return modelo


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


def _capturar(indice, modelo, detener, avisos, ancho, alto):
    gestos = Gestos()
    camara = None
    try:
        import cv2
        import mediapipe as mp
        vision = mp.tasks.vision
        opciones = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=modelo),
            running_mode=vision.RunningMode.VIDEO, num_hands=2)
        with vision.HandLandmarker.create_from_options(opciones) as detector:
            if detener.is_set():
                return
            camara = cv2.VideoCapture(indice, cv2.CAP_V4L2)
            if not camara.isOpened():
                raise RuntimeError("No pude abrir esa cámara.")
            camara.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            avisos.put("Cámara activa · control de puntero habilitado")
            anterior = -1
            while not detener.is_set():
                correcto, imagen = camara.read()
                if not correcto:
                    raise RuntimeError("No pude leer la cámara.")
                rgb = cv2.cvtColor(cv2.flip(imagen, 1), cv2.COLOR_BGR2RGB)
                ahora = monotonic()
                marca = max(anterior + 1, round(ahora * 1000))
                anterior = marca
                resultado = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), marca)
                manos = {}
                for clasificacion, puntos in zip(resultado.handedness, resultado.hand_landmarks):
                    if clasificacion:
                        manos[clasificacion[0].category_name] = [(p.x, p.y) for p in puntos]
                if not detener.is_set():
                    eventos = gestos.actualizar(manos.get("Right"), ahora, manos.get("Left"))
                    _control(eventos, ancho, alto)
                detener.wait(.045)
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
    raiz.title("Cerebro · Modo táctil")
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
    valor = tk.StringVar(value="Cámara apagada")
    eventos = SimpleQueue()
    detener = Event()
    activo = False
    cerrando = False
    tk.Label(raiz, text="Modo táctil", bg=FONDO, fg=ACENTO, font=("TkDefaultFont", 15, "bold")).pack(padx=18, pady=10)
    lista = ttk.Combobox(raiz, state="readonly", values=[f"video{i} · {nombre}" for i, nombre in opciones], width=40)
    lista.pack(padx=18, pady=(0, 8))
    if opciones:
        lista.current(0)
    tk.Label(raiz, textvariable=valor, bg=FONDO, fg=TEXTO, width=47, wraplength=370).pack(padx=10)
    tk.Label(raiz, text="Índice derecho: puntero · Pinza breve: clic · Mantén: arrastra\nPinza izquierda: desplaza · Esc: pausa",
             bg=FONDO, fg=TEXTO).pack(padx=14, pady=8)

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
            modelo = _requisitos()
        except RuntimeError as exc:
            valor.set(str(exc))
            return
        if not messagebox.askyesno("Activar cámara", "¿Permitir la cámara seleccionada y el control del puntero?", parent=raiz):
            return
        activo = True
        detener = Event()
        boton.configure(state="disabled")
        lista.configure(state="disabled")
        valor.set("Iniciando cámara…")
        Thread(target=_capturar, args=(opciones[indice][0], modelo, detener, eventos,
                                      raiz.winfo_screenwidth(), raiz.winfo_screenheight()), daemon=True).start()

    def cerrar():
        nonlocal cerrando
        cerrando = True
        if activo:
            pausar()
        else:
            raiz.destroy()

    def actualizar():
        nonlocal activo
        while True:
            try:
                mensaje = eventos.get_nowait()
            except Empty:
                break
            if mensaje is None:
                activo = False
                boton.configure(state="normal" if opciones else "disabled")
                lista.configure(state="readonly")
                if valor.get() in {"Pausando…", "Cámara activa · control de puntero habilitado"}:
                    valor.set("Cámara apagada")
                if cerrando:
                    raiz.destroy()
                    return
            else:
                valor.set(mensaje)
        raiz.after(100, actualizar)

    boton = ttk.Button(raiz, text="Activar cámara", command=iniciar, state="normal" if opciones else "disabled")
    boton.pack(padx=14, pady=(0, 4))
    ttk.Button(raiz, text="Pausar", command=pausar).pack(padx=14, pady=(0, 12))
    if not opciones:
        valor.set("No se detectó una cámara compatible.")
    raiz.bind("<Escape>", pausar)
    raiz.protocol("WM_DELETE_WINDOW", cerrar)
    raiz.after(100, actualizar)
    raiz.mainloop()
