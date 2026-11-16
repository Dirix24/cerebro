"""Utilidades de inspección de WAV; no incluye todavía reconocimiento de voz."""
import wave


def informacion_wav(ruta):
    with wave.open(str(ruta), "rb") as audio:
        if audio.getnframes() > audio.getframerate() * 3600:
            raise ValueError("Audio demasiado largo")
        return {"canales": audio.getnchannels(), "frecuencia": audio.getframerate(),
                "segundos": audio.getnframes() / audio.getframerate()}
