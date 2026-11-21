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


def dictar(segundos=5):
    import shutil
    import subprocess

    if not isinstance(segundos, int) or not 1 <= segundos <= 15:
        raise ValueError("El dictado admite de 1 a 15 segundos.")
    grabador = shutil.which("arecord")
    if not grabador:
        raise RuntimeError("Instala alsa-utils para habilitar el dictado en MX Linux.")
    modelo = _cargar_modelo(_buscar_modelo())
    try:
        audio = subprocess.run([grabador, "-q", "-t", "raw", "-f", "S16_LE", "-r", "16000",
                                "-c", "1", "-d", str(segundos)], capture_output=True,
                               timeout=segundos + 4, check=True)
    except subprocess.SubprocessError as exc:
        raise RuntimeError("No pude grabar. Comprueba el micrófono y la entrada predeterminada.") from exc
    return transcribir_pcm(audio.stdout, modelo=modelo)


def leer_en_espanol(texto):
    import shutil
    import subprocess

    texto = texto.strip()
    if not texto:
        raise ValueError("Todavía no hay una respuesta para leer.")
    sintetizador = shutil.which("espeak-ng") or shutil.which("espeak")
    if not sintetizador:
        raise RuntimeError("Instala espeak-ng para escuchar las respuestas en MX Linux.")
    try:
        subprocess.run([sintetizador, "-v", "es", "--stdin"], input=texto[:1800],
                       text=True, capture_output=True, timeout=120, check=True)
    except subprocess.SubprocessError as exc:
        raise RuntimeError("No pude reproducir el audio. Comprueba la salida del sistema.") from exc
