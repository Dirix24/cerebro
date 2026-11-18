"""Inventario USB/serie de solo lectura. Nunca abre puertos ni instala firmware."""
from importlib.util import find_spec


def listar_puertos():
    if find_spec("serial") is None:
        return {"disponible": False, "puertos": [],
                "nota": "Instala pyserial para enumerar puertos; no se ha accedido a dispositivos."}
    from serial.tools import list_ports
    puertos = []
    for p in list_ports.comports():
        puertos.append({"puerto": str(p.device), "descripcion": str(p.description),
                        "vid": p.vid, "pid": p.pid,
                        "fabricante": p.manufacturer or None})
    return {"disponible": True, "puertos": puertos,
            "nota": "Inventario de metadatos; no identifica de forma fiable la placa ni abre el puerto."}
