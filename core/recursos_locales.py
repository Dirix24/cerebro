"""Inventario local de recursos sin iniciar modelos ni abrir dispositivos."""
import importlib.util
import os
from pathlib import Path
from shutil import disk_usage, which


def inspeccionar(ruta):
    memoria = {}
    try:
        for linea in Path("/proc/meminfo").read_text().splitlines():
            clave, _, valor = linea.partition(":")
            if clave in {"MemTotal", "MemAvailable"}:
                memoria[clave] = int(valor.split()[0]) // 1024
    except (OSError, ValueError, IndexError):
        pass

    gpu = []
    for dispositivo in sorted(Path("/sys/class/drm").glob("card[0-9]*/device")):
        if "-" in dispositivo.parent.name:
            continue
        try:
            fabricante = dispositivo.joinpath("vendor").read_text().strip()
            modelo = dispositivo.joinpath("device").read_text().strip()
        except OSError:
            continue
        controlador = dispositivo / "driver"
        gpu.append({"pci": fabricante + ":" + modelo,
                    "controlador": controlador.resolve().name if controlador.is_symlink() else None})

    librerias = {nombre: importlib.util.find_spec(nombre) is not None for nombre in ("cv2", "mediapipe", "numpy", "torch")}
    return {
        "cpu_logicas": os.cpu_count(), "memoria_mib": memoria, "gpu": gpu,
        "disco_libre_mib": disk_usage(ruta).free // 1024**2,
        "camaras_detectadas": len(list(Path("/dev").glob("video[0-9]*"))),
        "programas": {nombre: which(nombre) is not None for nombre in
                      ("thunar", "xdotool", "wmctrl", "bwrap", "ollama", "llama-server", "pdftotext", "ffmpeg")},
        "librerias": librerias,
    }


def resumir(recursos):
    memoria = recursos["memoria_mib"]
    gpu = [f"{ficha['pci']} ({ficha['controlador'] or 'sin controlador detectado'})" for ficha in recursos["gpu"]]
    dependencias = recursos["programas"] | recursos["librerias"]
    return "\n".join([
        f"CPU lógicas: {recursos['cpu_logicas'] or 'desconocido'}.",
        (f"RAM disponible: {memoria.get('MemAvailable', 'desconocida')} MiB de "
         f"{memoria.get('MemTotal', 'desconocida')} MiB.") if memoria else "RAM: sin información.",
        f"Espacio libre de Cerebro: {recursos['disco_libre_mib']} MiB.",
        "GPU PCI: " + (", ".join(gpu) if gpu else "ninguna detectada por DRM") + ".",
        f"Nodos de cámara detectados: {recursos['camaras_detectadas']}.",
        "Dependencias detectadas: " + (", ".join(nombre for nombre, existe in dependencias.items() if existe) or "ninguna") + ".",
        "Dependencias sin detectar: " + (", ".join(nombre for nombre, existe in dependencias.items() if not existe) or "ninguna") + ".",
    ])
