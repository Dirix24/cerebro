"""Voz local: síntesis opcional con pyttsx3 y grabación WAV opcional.

El dictado opcional usa un modelo Vosk instalado por el usuario.
"""
from functools import lru_cache
import wave
from pathlib import Path


def hablar(texto, velocidad=170):
    if not texto or len(texto) > 2000:
        raise ValueError("Texto vacío o demasiado largo (máximo 2000 caracteres)")
    try:
        import pyttsx3
    except ImportError as e:
        raise RuntimeError("Instala pyttsx3 y un sintetizador de voz del sistema") from e
    motor = pyttsx3.init()
    motor.setProperty("rate", velocidad)
    motor.say(texto)
    motor.runAndWait()


def grabar_wav(destino, segundos=3, frecuencia=16000):
    if not 0 < segundos <= 30:
        raise ValueError("La duración debe estar entre 0 y 30 segundos")
    try:
        import sounddevice as sd
    except ImportError as e:
        raise RuntimeError("Instala sounddevice para grabar audio local") from e
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = sd.rec(int(segundos * frecuencia), samplerate=frecuencia,
                   channels=1, dtype="int16")
    sd.wait()
    with wave.open(str(ruta), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(frecuencia)
        f.writeframes(datos.tobytes())
    return ruta


def _buscar_modelo():
    import os
    ruta = os.environ.get("CEREBRO_MODELO_VOZ")
    if ruta:
        return Path(ruta).expanduser()
    datos = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return datos / "cerebro" / "voz" / "vosk-model-small-es-0.42"


@lru_cache(maxsize=1)
def _cargar_modelo(ruta):
    try:
        from vosk import Model, SetLogLevel
    except ImportError as exc:
        raise RuntimeError("Para dictar, instala Vosk siguiendo la guía de voz de Cerebro.") from exc
    if not ruta.is_dir():
        raise RuntimeError("Configura CEREBRO_MODELO_VOZ con la carpeta local del modelo español.")
    SetLogLevel(-1)
    try:
        return Model(model_path=str(ruta))
    except Exception as exc:
        raise RuntimeError("No pude cargar el modelo de voz. Comprueba la carpeta de Vosk.") from exc


def transcribir_pcm(datos, modelo=None):
    """Reconoce PCM mono firmado de 16 bits a 16 kHz, íntegramente en el equipo."""
    import json

    if not datos or len(datos) % 2 or len(datos) > 30 * 16000 * 2:
        raise ValueError("El audio debe estar en PCM mono de 16 kHz y durar hasta 30 segundos.")
    if modelo is None:
        modelo = _cargar_modelo(_buscar_modelo())
    from vosk import KaldiRecognizer
    reconocedor = KaldiRecognizer(modelo, 16000)
    textos = []
    for inicio in range(0, len(datos), 8000):
        if reconocedor.AcceptWaveform(datos[inicio:inicio + 8000]):
            textos.append(json.loads(reconocedor.Result()).get("text", ""))
    textos.append(json.loads(reconocedor.FinalResult()).get("text", ""))
    return " ".join(fragmento for fragmento in textos if fragmento).strip()


def dictar(segundos=5, dispositivo="default"):
    import shutil
    import subprocess

    if not isinstance(segundos, int) or not 1 <= segundos <= 15:
        raise ValueError("El dictado admite de 1 a 15 segundos.")
    modelo = _cargar_modelo(_buscar_modelo())
    try:
        if dispositivo.startswith("pulse:"):
            grabador = shutil.which("parec")
            if not grabador:
                raise RuntimeError("Para seleccionar una entrada de PipeWire o PulseAudio, instala pulseaudio-utils.")
            try:
                audio = subprocess.run([grabador, "--raw", "--format=s16le", "--rate=16000", "--channels=1",
                                        "--device=" + dispositivo.removeprefix("pulse:")],
                                       capture_output=True, timeout=segundos, check=True).stdout
            except subprocess.TimeoutExpired as exc:
                audio = exc.output or b""
        else:
            grabador = shutil.which("arecord")
            if not grabador:
                raise RuntimeError("Instala alsa-utils para habilitar el dictado en MX Linux.")
            audio = subprocess.run([grabador, "-q", "-D", dispositivo, "-t", "raw", "-f", "S16_LE",
                                    "-r", "16000", "-c", "1", "-d", str(segundos)], capture_output=True,
                                   timeout=segundos + 4, check=True).stdout
    except subprocess.SubprocessError as exc:
        raise RuntimeError("No pude grabar. Comprueba el micrófono y la entrada seleccionada.") from exc
    if not audio:
        raise RuntimeError("No recibí audio. Abre Audio y elige otro micrófono.")
    return transcribir_pcm(audio, modelo=modelo)


def dispositivos_audio():
    """Enumera entradas ALSA y detecta las salidas físicas sin abrirlas."""
    import shutil
    import subprocess

    def listado(programa, *opciones):
        ejecutable = shutil.which(programa)
        if not ejecutable:
            return ""
        try:
            return subprocess.run([ejecutable, *opciones], capture_output=True, text=True,
                                  timeout=3, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            return ""

    entradas = ["default"]
    for linea in listado("pactl", "list", "short", "sources").splitlines():
        campos = linea.split("\t")
        if len(campos) > 1 and campos[1] and not campos[1].endswith(".monitor"):
            entradas.append("pulse:" + campos[1])
    for linea in listado("arecord", "-L").splitlines():
        if linea.startswith(("hw:", "plughw:", "sysdefault:")) and linea not in entradas:
            entradas.append(linea)
    salidas = [linea.split("\t")[1] for linea in listado("pactl", "list", "short", "sinks").splitlines()
               if len(linea.split("\t")) > 1]
    if not salidas:
        salidas = [linea for linea in listado("aplay", "-l").splitlines() if "[" in linea]
    return {"entradas": entradas[:48], "salidas": salidas[:12]}


def leer_en_espanol(texto, cancelar=None):
    import shutil
    import subprocess
    from time import monotonic

    texto = texto.strip()
    if not texto:
        raise ValueError("Todavía no hay una respuesta para leer.")
    sintetizador = shutil.which("espeak-ng") or shutil.which("espeak")
    if not sintetizador:
        raise RuntimeError("Instala espeak-ng para escuchar las respuestas en MX Linux.")
    if cancelar is not None and cancelar.is_set():
        return
    with subprocess.Popen([sintetizador, "-v", "es", "-p", "30", "-s", "155", "--stdin"],
                          stdin=subprocess.PIPE, text=True, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL) as proceso:
        limite = monotonic() + 120
        entrada = texto[:1800]
        while True:
            if (cancelar is not None and cancelar.is_set()) or monotonic() >= limite:
                proceso.terminate()
                try:
                    proceso.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proceso.kill()
                    proceso.wait()
                return
            try:
                proceso.communicate(input=entrada, timeout=.15)
            except subprocess.TimeoutExpired:
                entrada = None
                continue
            if proceso.returncode:
                raise RuntimeError("No pude reproducir el audio. Comprueba la salida del sistema.")
            return
