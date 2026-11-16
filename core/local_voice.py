"""Voz local: síntesis opcional con pyttsx3 y grabación WAV opcional.

No incorpora reconocimiento de voz; no descarga ni carga modelos externos.
"""
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
