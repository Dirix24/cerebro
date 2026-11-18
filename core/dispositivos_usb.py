"""Inventario voluntario de puertos serie del equipo actual.

No busca redes, no abre puertos y no carga firmware. VID/PID son pistas, no
identidades fiables de una placa. pyserial es una dependencia opcional.
"""


def listar_puertos():
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError("Instala pyserial para listar puertos: pip install pyserial") from exc
    resultado = []
    for puerto in list_ports.comports():
        resultado.append({
            "puerto": puerto.device,
            "descripcion": puerto.description,
            "fabricante": puerto.manufacturer,
            "vid": puerto.vid,
            "pid": puerto.pid,
            "numero_serie": None,  # No recolectar identificadores persistentes.
            "placa_confirmada": False,
        })
    return resultado
