"""Fragmentos de conversación portables. Todos los mensajes son citas históricas."""
import json
from datetime import datetime
from hashlib import sha256

FORMATO = "cerebro-recuerdo-v1"
LIMITE = 1_500_000


def crear(tema, mensajes, procedencia):
    if not isinstance(tema, str) or not 1 <= len(tema.strip()) <= 150:
        raise ValueError("Indica un tema de hasta 150 caracteres.")
    if not isinstance(procedencia, str) or not 1 <= len(procedencia) <= 100:
        raise ValueError("Procedencia del recuerdo inválida.")
    if not isinstance(mensajes, list) or not 1 <= len(mensajes) <= 60:
        raise ValueError("Selecciona entre 1 y 60 mensajes.")
    citas = []
    for mensaje in mensajes:
        if (not isinstance(mensaje, dict) or mensaje.get("rol") not in ("usuario", "cerebro")
                or not isinstance(mensaje.get("texto"), str) or not 1 <= len(mensaje["texto"]) <= 4000
                or not isinstance(mensaje.get("fecha"), str) or len(mensaje["fecha"]) > 40):
            raise ValueError("El recuerdo contiene un mensaje inválido.")
        datetime.fromisoformat(mensaje["fecha"])
        citas.append({campo: mensaje[campo] for campo in ("rol", "texto", "fecha")})
    serial = json.dumps(citas, ensure_ascii=True, sort_keys=True).encode()
    if len(serial) > LIMITE - 10000:
        raise ValueError("Selecciona un fragmento más pequeño.")
    return {"formato": FORMATO, "id": sha256(serial).hexdigest(), "tema": tema.strip(),
            "procedencia": procedencia, "mensajes": citas}


def validar(datos):
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ValueError("Selecciona un archivo de recuerdo de Cerebro v1.")
    recuerdo = crear(datos.get("tema"), datos.get("mensajes"), datos.get("procedencia"))
    if datos != recuerdo:
        raise ValueError("El recuerdo tiene campos desconocidos o su identificador no coincide.")
    return recuerdo


def markdown(recuerdo):
    lineas = ["Recuerdo de CEREBRO", "", f"ID {recuerdo['id']}", "",
              "> " + recuerdo["tema"].replace("\n", "\n> "), ""]
    for mensaje in recuerdo["mensajes"]:
        lineas.extend([f"**{mensaje['rol']} · {mensaje['fecha']}**", "",
                       *["> " + linea for linea in mensaje["texto"].splitlines()], ""])
    return "\n".join(lineas)
