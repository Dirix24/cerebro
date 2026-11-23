"""Comprobaciones de instalación que no encienden la cámara."""
import os
from pathlib import Path
from shutil import which
import subprocess
import sys


def probar_importacion(modulo):
    try:
        salida = subprocess.run([sys.executable, "-I", "-c", f"import {modulo}"], timeout=12,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return salida.returncode == 0


def diagnosticar(raiz):
    from core.recursos_locales import inspeccionar, perfil_equipo

    recursos = inspeccionar(raiz)
    base = {m: probar_importacion(m) for m in ("tkinter", "numpy", "PIL", "cv2", "mediapipe")}
    sistema = {p: which(p) is not None for p in
               ("wmctrl", "xdotool", "pdftoppm", "pdftotext", "pdfinfo", "prlimit", "notify-send")}
    dispositivos = [f"{nodo.name}: {'accesible' if os.access(nodo, os.R_OK | os.W_OK) else 'sin permisos R/W'}"
                    for nodo in sorted(Path("/dev").glob("video[0-9]*"))]
    print(f"Python de Cerebro: {sys.executable} ({sys.version.split()[0]})")
    for nombre, resultado in (base | sistema).items():
        print(f"  {nombre}: {'disponible' if resultado else 'no disponible'}")
    modelo = modelo_manos()
    print("Modelo de manos: " + ("archivo disponible" if modelo and Path(modelo).expanduser().is_file() else "sin archivo configurado"))
    print("Cámara V4L2: " + (", ".join(dispositivos) if dispositivos else "sin nodos detectados"))
    print(f"RAM libre: {recursos['memoria_mib'].get('MemAvailable', 'desconocida')} MiB")
    print(f"Perfil de cámara recomendado: {perfil_equipo(raiz)}")
    print(f"Disco libre: {recursos['disco_libre_mib']} MiB")
    from core.motores_instalados import descubrir, resumir
    from core.profesor_local import ProfesorLocal

    try:
        print(resumir(descubrir(ProfesorLocal.desde_entorno())))
    except ValueError as error:
        print(f"Configuración de motores: {error}")
    print("El diagnóstico no inicia modelos ni captura imágenes.")


def instalar_gestos(modo):
    paquetes = ["opencv-contrib-python", "mediapipe"] if modo == "manos" else ["opencv-python"]
    try:
        codigo = subprocess.call([sys.executable, "-m", "pip", "install", "--only-binary=:all:", *paquetes],
                                 timeout=240)
    except (OSError, subprocess.TimeoutExpired):
        codigo = 1
    if codigo:
        print("No pude instalar las ruedas compatibles. Usa --gestos marcador o revisa el Python del entorno virtual.")
        return False
    return all(probar_importacion(modulo) for modulo in (("cv2", "mediapipe") if modo == "manos" else ("cv2",)))


def modelo_manos():
    """Prioriza la configuración explícita sobre la referencia del instalador."""
    modelo = os.environ.get("CEREBRO_MODELO_MANOS")
    if not modelo and sys.prefix != sys.base_prefix:
        referencia = Path(sys.prefix) / "cerebro-modelo-manos.txt"
        try:
            if referencia.is_file() and not referencia.is_symlink() and referencia.stat().st_size <= 4096:
                modelo = referencia.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            pass
    return modelo


def configurar_modelo_manos(ruta):
    if sys.prefix == sys.base_prefix:
        raise ValueError("Configura el modelo desde el entorno virtual del instalador.")
    origen = Path(ruta).expanduser().resolve(strict=True)
    if origen.suffix.lower() != ".task" or not origen.is_file() or not 0 < origen.stat().st_size <= 50 * 1024**2:
        raise ValueError("Selecciona un modelo .task de manos existente de hasta 50 MiB.")
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(mode="w", dir=sys.prefix, encoding="utf-8", delete=False) as temporal:
        temporal.write(str(origen) + "\n")
    try:
        Path(temporal.name).replace(Path(sys.prefix) / "cerebro-modelo-manos.txt")
    finally:
        Path(temporal.name).unlink(missing_ok=True)



def preparar_gestos_automaticos():
    if sys.prefix == sys.base_prefix:
        raise ValueError("Instala los gestos desde el entorno virtual de Cerebro.")
    if probar_importacion("cv2") and probar_importacion("mediapipe") or instalar_gestos("manos"):
        modelo = modelo_manos()
        if modelo and Path(modelo).expanduser().is_file():
            return "Manos disponibles con el modelo configurado."
        try:
            instalar_modelo_oficial()
        except (OSError, ValueError) as error:
            return f"No se pudo preparar el modelo de manos: {error}. Usa Marcador verde."
        return "OpenCV, MediaPipe y modelo de manos preparados."
    if probar_importacion("cv2") or instalar_gestos("marcador"):
        return "OpenCV disponible. Usa Marcador verde; MediaPipe no está preparado."
    return "No se pudo preparar OpenCV en este entorno. La instalación básica está disponible."


def instalar_modelo_oficial():
    from hashlib import sha256
    from tempfile import NamedTemporaryFile
    from urllib.request import urlopen

    url = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
           "hand_landmarker/float16/1/hand_landmarker.task")
    huella = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"
    destino = Path(sys.prefix) / "hand_landmarker.task"
    if destino.is_file() and destino.stat().st_size == 7819105 and sha256(destino.read_bytes()).hexdigest() == huella:
        configurar_modelo_manos(destino)
        return
    print("Descargando el modelo oficial de manos (7,8 MB).", flush=True)
    with urlopen(url, timeout=15) as entrada:
        datos = entrada.read(7819106)
    if len(datos) != 7819105 or sha256(datos).hexdigest() != huella:
        raise ValueError("El archivo descargado no coincide con el modelo publicado.")
    with NamedTemporaryFile(dir=sys.prefix, delete=False) as salida:
        temporal = Path(salida.name)
        salida.write(datos)
    try:
        temporal.replace(destino)
        configurar_modelo_manos(destino)
    finally:
        temporal.unlink(missing_ok=True)
