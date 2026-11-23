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
            if clave in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
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

    try:
        carga = [round(valor, 2) for valor in os.getloadavg()]
    except OSError:
        carga = []
    temperaturas = []
    for zona in sorted(Path("/sys/class/thermal").glob("thermal_zone*"))[:24]:
        try:
            grados = int((zona / "temp").read_text()) / 1000
            if -20 <= grados <= 150:
                temperaturas.append({"sensor": (zona / "type").read_text().strip()[:60], "celsius": grados})
        except (OSError, ValueError):
            continue
    procesos = 0
    for proceso in Path("/proc").iterdir():
        if proceso.name.isdecimal():
            procesos += 1

    librerias = {nombre: importlib.util.find_spec(nombre) is not None for nombre in ("cv2", "mediapipe", "numpy", "torch")}
    return {
        "cpu_logicas": os.cpu_count(), "memoria_mib": memoria, "gpu": gpu, "carga": carga,
        "procesos_visibles": procesos, "temperaturas": temperaturas,
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
        f"Swap libre: {memoria.get('SwapFree', 'desconocida')} MiB de {memoria.get('SwapTotal', 'desconocida')} MiB.",
        "Carga 1/5/15 min: " + (" / ".join(map(str, recursos["carga"])) or "sin datos") + ".",
        f"Procesos visibles: {recursos['procesos_visibles']}.",
        "Temperaturas: " + (", ".join(f"{t['sensor']} {t['celsius']:g} °C" for t in recursos["temperaturas"]) or "sin sensores visibles") + ".",
        f"Espacio libre de Cerebro: {recursos['disco_libre_mib']} MiB.",
        "GPU PCI: " + (", ".join(gpu) if gpu else "ninguna detectada por DRM") + ".",
        f"Nodos de cámara detectados: {recursos['camaras_detectadas']}.",
        "Dependencias detectadas: " + (", ".join(nombre for nombre, existe in dependencias.items() if existe) or "ninguna") + ".",
        "Dependencias sin detectar: " + (", ".join(nombre for nombre, existe in dependencias.items() if not existe) or "ninguna") + ".",
    ])



def sugerir(recursos):
    sugerencias = []
    memoria = recursos["memoria_mib"].get("MemAvailable")
    if memoria is not None and memoria < 4096:
        sugerencias.append("Usa un solo modelo pequeño cuantizado cada vez. Reduce la presión de RAM; puede reducir la calidad. "
                            "Puedes volver a seleccionar tu modelo anterior.")
    if recursos["disco_libre_mib"] < 4096:
        sugerencias.append("Evita descargar modelos con tan poco espacio. Revisa el almacenamiento antes de cualquier limpieza.")
    if recursos["camaras_detectadas"]:
        sugerencias.append("Usa CEREBRO_CAMARA_PERFIL=ligero para reducir fotogramas y resolución. "
                            "Puede empeorar el seguimiento; elimina la variable para restaurar el perfil normal.")
    return sugerencias



def perfil_equipo(ruta):
    """Prefiere el perfil ligero si faltan mediciones o recursos."""
    recursos = inspeccionar(ruta)
    memoria = recursos["memoria_mib"].get("MemAvailable", 0)
    return "ligero" if memoria < 4096 or (recursos["cpu_logicas"] or 0) < 4 else "normal"
