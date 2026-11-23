"""Inventario bajo demanda de motores configurados y adaptadores locales."""
from http.client import HTTPConnection, HTTPException
import json
import os
from pathlib import Path
from shutil import which


def _modelos_ollama(puerto):
    conexion = HTTPConnection("127.0.0.1", puerto, timeout=1.5)
    try:
        conexion.request("GET", "/api/tags")
        with conexion.getresponse() as respuesta:
            if respuesta.status != 200:
                return None
            datos = respuesta.read(128 * 1024 + 1)
        if len(datos) > 128 * 1024:
            return None
        registros = json.loads(datos).get("models")
        if not isinstance(registros, list):
            return None
        return [nombre[:160] for registro in registros[:30] if isinstance(registro, dict)
                and isinstance(nombre := registro.get("name"), str)
                and not nombre.casefold().endswith(("-cloud", ":cloud"))]
    except (OSError, ValueError, AttributeError, HTTPException):
        return None
    finally:
        conexion.close()


def _adaptador_vecino(nombre, modulo):
    base = Path(__file__).resolve().parents[2]
    carpeta = {"CAZEL": "CAZEL_IA", "DARAS": "Daras-IA"}[nombre]
    ruta = base / carpeta
    return ruta if (ruta / modulo).is_file() else None


def descubrir(profesor):
    try:
        puerto = int(os.environ.get("CEREBRO_OLLAMA_PUERTO", "11434"))
    except ValueError:
        puerto = 0
    modelos = _modelos_ollama(puerto) if 1024 <= puerto <= 65535 else None
    gguf = os.environ.get("CEREBRO_PROFESOR_MODELO")
    ruta_gguf = Path(gguf).expanduser() if gguf else None
    gguf_instalado = bool(ruta_gguf and ruta_gguf.suffix.lower() == ".gguf" and ruta_gguf.is_file())
    resultado = [
        {"nombre": "Ollama", "estado": "servicio local respondió" if modelos is not None else
         ("binario detectado, servicio sin verificar" if which("ollama") else "sin respuesta local"),
         "modelos": modelos or [], "capacidades": "inferencia de texto según el modelo configurado"},
        {"nombre": "llama.cpp", "estado": "binario detectado" if which("llama-server") else "binario fuera de PATH",
         "modelos": [ruta_gguf.name] if gguf_instalado else [], "capacidades": "inferencia con GGUF configurado"},
        {"nombre": "PROFESOR", "estado": "modelo configurado" if profesor.configurado else "evaluación local",
         "modelos": [], "capacidades": "enseñanza y evaluación verificable"},
    ]
    for nombre, modulo, capacidad in (
        ("CAZEL", "cazel/especialista.py", "análisis técnico y programación según permisos"),
        ("DARAS", "especialista.py", "investigación y planificación según permisos"),
    ):
        raiz = os.environ.get("CEREBRO_" + nombre + "_RAIZ")
        presente = bool(raiz and (Path(raiz).expanduser() / modulo).is_file())
        estado = "adaptador v1 presente" if presente else "falta configurar el adaptador v1"
        if not raiz and (vecino := _adaptador_vecino(nombre, modulo)):
            estado = f"adaptador v1 detectado en {vecino}; requiere configuración"
        if nombre == "CAZEL" and presente and not os.environ.get("CEREBRO_CAZEL_PROYECTO"):
            estado += "; falta seleccionar el proyecto"
        resultado.append({"nombre": nombre, "estado": estado, "modelos": [], "capacidades": capacidad})
    return resultado


def resumir(registro):
    return "\n".join(f"{motor['nombre']}: {motor['estado']}. {motor['capacidades']}."
                     + (" Modelos: " + ", ".join(motor["modelos"]) if motor["modelos"] else "")
                     for motor in registro)
