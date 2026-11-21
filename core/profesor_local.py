"""Profesor opcional y sin herramientas mediante un servidor local autorizado."""
from http.client import HTTPConnection, HTTPException
import json
import os
from pathlib import Path
import re
from threading import Lock

from core.entorno_portatil import detectar_entorno


GIB = 1024 ** 3
MAX_RESPUESTA = 64 * 1024
CATALOGO = (
    {"modelo": "Qwen2.5-1.5B-Instruct GGUF Q4_K_M", "licencia": "Apache-2.0",
     "ram_libre_minima": 3 * GIB, "disco_libre_minimo": 2 * GIB,
     "fuente": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF"},
    {"modelo": "Qwen2.5-0.5B-Instruct GGUF Q4_K_M", "licencia": "Apache-2.0",
     "ram_libre_minima": 2 * GIB, "disco_libre_minimo": 1 * GIB,
     "fuente": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF"},
)


def diagnostico(ruta):
    entorno = detectar_entorno(ruta)
    try:
        meminfo = dict(linea.split(":", 1) for linea in Path("/proc/meminfo").read_text().splitlines())
        disponible = int(meminfo["MemAvailable"].split()[0]) * 1024
    except (OSError, KeyError, ValueError, IndexError):
        disponible = None
    recomendacion = next((dict(modelo) for modelo in CATALOGO if disponible is not None
                          and disponible >= modelo["ram_libre_minima"]
                          and entorno["disco_libre_bytes"] >= modelo["disco_libre_minimo"]
                          and entorno["arquitectura"] in {"x86_64", "aarch64"}), None)
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        modelo_cpu = re.search(r"^model name\s*:\s*(.+)$", cpuinfo, re.M)
        procesador = modelo_cpu[1] if modelo_cpu else None
    except OSError:
        procesador = None
    gpu = []
    for dispositivo in sorted(Path("/sys/class/drm").glob("card[0-9]*/device")):
        try:
            proveedor = (dispositivo / "vendor").read_text().strip()
            identificador = (dispositivo / "device").read_text().strip()
        except OSError:
            continue
        try:
            vram = int((dispositivo / "mem_info_vram_total").read_text())
        except (OSError, ValueError):
            vram = None
        gpu.append({"proveedor_pci": proveedor, "dispositivo_pci": identificador, "vram_bytes": vram})
    return {"sistema": entorno["sistema"], "arquitectura": entorno["arquitectura"],
            "procesador": procesador, "gpu": gpu,
            "cpus_logicas": entorno["cpus_logicas"], "ram_total_bytes": entorno["ram_bytes"],
            "ram_disponible_bytes": disponible, "disco_libre_bytes": entorno["disco_libre_bytes"],
            "ejecucion_prevista": "CPU; velocidad sin medir", "recomendacion": recomendacion}


class ProfesorLocal:
    def __init__(self, puerto=None):
        if puerto is not None and (type(puerto) is not int or not 1024 <= puerto <= 65535):
            raise ValueError("El puerto del profesor local debe estar entre 1024 y 65535.")
        self.puerto = puerto
        self.ocupado = Lock()

    @classmethod
    def desde_entorno(cls):
        valor = os.environ.get("CEREBRO_PROFESOR_PUERTO")
        return cls(int(valor) if valor else None)

    @property
    def configurado(self):
        return self.puerto is not None

    def explicar(self, tema):
        if not self.configurado:
            raise RuntimeError("El profesor local no está configurado.")
        if not isinstance(tema, str) or not 2 <= len(tema.strip()) <= 150:
            raise ValueError("Indica un tema breve.")
        if not self.ocupado.acquire(blocking=False):
            raise RuntimeError("El profesor local está atendiendo otra consulta.")
        conexion = HTTPConnection("127.0.0.1", self.puerto, timeout=18)
        try:
            peticion = json.dumps({
                "messages": [
                    {"role": "system", "content": "Explica en español y en pocas frases. "
                     "Distingue hechos de incertidumbre. Responde solo con una explicación textual."},
                    {"role": "user", "content": "Explícame este tema: " + tema},
                ],
                "max_tokens": 96, "temperature": 0.2, "stream": False,
            }).encode()
            conexion.request("POST", "/v1/chat/completions", peticion, {"Content-Type": "application/json"})
            with conexion.getresponse() as respuesta:
                if respuesta.status != 200:
                    raise RuntimeError("El profesor local rechazó la consulta.")
                datos = respuesta.read(MAX_RESPUESTA + 1)
            if len(datos) > MAX_RESPUESTA:
                raise RuntimeError("La respuesta del profesor excede el límite.")
            mensaje = json.loads(datos)["choices"][0]["message"]
            texto = mensaje["content"]
            if mensaje.get("tool_calls") or not isinstance(texto, str) or not texto.strip() or len(texto) > 6000:
                raise ValueError("Respuesta textual inválida.")
            return texto.strip()
        except (OSError, HTTPException, AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("No pude obtener una respuesta válida del profesor local.") from exc
        finally:
            conexion.close()
            self.ocupado.release()
