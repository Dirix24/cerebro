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


def probar_nucleo():
    """Prueba el servicio HTTP local sin abrir sesiones ni datos reales del usuario."""
    from tempfile import TemporaryDirectory

    receta = """
from threading import Thread
from types import SimpleNamespace
from universe.lanzador import api
from universe.nucleo import Nucleo
from universe.servidor import crear_servidor
n = Nucleo("local", profesor=SimpleNamespace(configurado=False))
try:
    with crear_servidor(0, n, "sonda-local") as servidor:
        hilo = Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        try:
            s = {"url": f"http://127.0.0.1:{servidor.server_port}", "token": "sonda-local"}
            respuesta = api(s, "chat", {"mensaje": "Calcula 23 * 14"}, tiempo=4)
            assert "322" in respuesta["respuesta"]
            assert api(s, "historial", tiempo=4)["turnos"]
        finally:
            servidor.shutdown()
            hilo.join(timeout=2)
finally:
    n.ejecutor.shutdown()
print("CEREBRO_NUCLEO_OK")
"""
    try:
        with TemporaryDirectory(prefix="cerebro-diagnostico-") as temporal:
            resultado = subprocess.run([sys.executable, "-c", receta], timeout=12, capture_output=True, text=True,
                                       cwd=Path(__file__).resolve().parent.parent, stdin=subprocess.DEVNULL,
                                       env={**os.environ, "CEREBRO_HOME": temporal})
    except (OSError, subprocess.TimeoutExpired):
        return False
    return resultado.returncode == 0 and resultado.stdout.strip() == "CEREBRO_NUCLEO_OK"


def diagnosticar(raiz):
    from core.aislamiento_proyecto import perfil_pruebas
    from core.local_voice import dispositivos_audio
    from core.recursos_locales import inspeccionar, perfil_equipo, resumir as resumir_recursos
    from core.profesor_local import diagnostico
    from main import cargar_modelo

    ficha = diagnostico(raiz)
    print(f"Sistema: {ficha['sistema']} {ficha['arquitectura']} · "
          f"CPU: {ficha['procesador'] or 'sin identificar'}")
    baterias = Path("/sys/class/power_supply")
    print("Tipo de equipo: " + ("batería detectada" if any(baterias.glob("BAT*")) else "sin batería visible"))
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
    audio = dispositivos_audio()
    entradas = [nombre for nombre in audio["entradas"] if nombre != "default"]
    print(f"Entradas de audio detectadas: {len(entradas)}. Captura sin probar.")
    print(resumir_recursos(recursos))
    print(f"Perfil de cámara recomendado: {perfil_equipo(raiz)}")
    try:
        propio, _, ruta = cargar_modelo()
        if propio is None:
            print("Modelo neuronal propio: no se encontró un checkpoint.")
        else:
            propio.generar_ids([0], max_nuevos=1, temperatura=0)
            print(f"Modelo neuronal propio: {Path(ruta).name}, inferencia CPU ejecutada.")
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"Modelo neuronal propio: no se pudo validar. {error}")
    for interfaz, modulo in (("Studio", "universe.studio"), ("Universe", "universe.mapa_studio"),
                             ("Terminal y Acompañante", "universe.lanzador")):
        try:
            prueba = subprocess.run([sys.executable, "-c", f"import {modulo}"], timeout=12,
                                    cwd=Path(__file__).resolve().parent.parent,
                                    stdin=subprocess.DEVNULL, capture_output=True)
            print(f"{interfaz}: " + ("módulo cargado" if prueba.returncode == 0 else "fallo al cargar"))
        except (OSError, subprocess.TimeoutExpired):
            print(f"{interfaz}: fallo al comprobar el módulo.")
    from core.motores_instalados import descubrir, resumir
    from core.profesor_local import ProfesorLocal

    try:
        print(resumir(descubrir(ProfesorLocal.desde_entorno())))
    except ValueError as error:
        print(f"Configuración de motores: {error}")
    _, aislamiento, _ = perfil_pruebas()
    print(aislamiento)
    print("Servicio local: " + ("arranque, consulta HTTP, historial y cierre comprobados."
                               if probar_nucleo() else "no superó la prueba de arranque o de loopback."))
    print("El diagnóstico no abre cámaras, micrófonos ni ventanas.")


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



def fallo_detector_manos(modelo):
    instruccion = ("import sys; from universe.tactil import _detector; "
                   "_detector(sys.argv[1]).close()")
    try:
        comprobacion = subprocess.run([sys.executable, "-c", instruccion, str(Path(modelo).expanduser())],
                                     cwd=Path(__file__).resolve().parent.parent, timeout=15,
                                     stdin=subprocess.DEVNULL, capture_output=True, text=True)
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(error)
    if comprobacion.returncode:
        lineas = comprobacion.stderr.strip().splitlines()
        return lineas[-1][:250] if lineas else "El detector terminó sin cargar el modelo."
    return None


def preparar_gestos_automaticos():
    if sys.prefix == sys.base_prefix:
        raise ValueError("Instala los gestos desde el entorno virtual de Cerebro.")
    if (probar_importacion("cv2") and probar_importacion("mediapipe")) or instalar_gestos("manos"):
        modelo = modelo_manos()
        try:
            if not modelo or not Path(modelo).expanduser().is_file():
                instalar_modelo_oficial()
                modelo = modelo_manos()
            fallo = fallo_detector_manos(modelo) if modelo else "No hay modelo configurado."
        except (OSError, ValueError) as error:
            fallo = str(error)
        if fallo:
            return f"OpenCV disponible. Usa Marcador verde. El detector de manos falló: {fallo}"
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
