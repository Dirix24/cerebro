# Adaptado de CAZEL_IA, Dirix24 (MIT). Véase docs/UNIVERSE.md.
# -*- coding: utf-8 -*-
"""
Protocolo CAZEL-1: un idioma de texto muy simple entre CAZEL y un robot.

Cada mensaje es una línea terminada en salto de línea.

  CAZEL  ->  robot        robot  ->  CAZEL
  ---------------         ---------------------------------------------
  AYUDA                   CAZEL 1 <nombre_del_robot>
                          ORDEN <nombre> [<parametro>:<minimo>:<maximo>]
                          LECTURA <nombre> [<unidad>]
                          FIN
  <orden> [valor]         OK            (o)   ERR <motivo>
  LEER <lectura>          VAL <numero>  (o)   ERR <motivo>
  PARAR                   OK            (siempre, detiene todo)

Ejemplo de respuesta a AYUDA:
  CAZEL 1 robot_ruedas
  ORDEN avanzar cm:0:50
  ORDEN girar grados:-180:180
  ORDEN parar
  LECTURA distancia cm
  FIN

Por qué así: es fácil de programar en un Arduino, fácil de leer para una
persona y, sobre todo, CAZEL solo puede enviar órdenes que el propio robot
ha declarado, con sus límites. Un texto inventado por el modelo de lenguaje
nunca llega al robot tal cual.
"""

import math
import re

VERSION = 1
RESERVADOS = {"ayuda", "parar", "leer", "ok", "err", "val", "fin", "cazel", "orden", "lectura"}
NOMBRE_VALIDO = re.compile(r"[a-z][a-z0-9_]{0,23}")
PARAMETRO_VALIDO = re.compile(r"[a-z][a-z0-9_]{0,15}")
MAX_ORDENES = 40
MAX_LINEA = 120


class ErrorProtocolo(ValueError):
    pass


def _numero(texto):
    try:
        if isinstance(texto, str) and not texto.isascii():
            raise ValueError("solo dígitos ASCII")
        v = float(texto)
    except (TypeError, ValueError):
        raise ErrorProtocolo(f"«{texto}» no es un número.")
    if not math.isfinite(v):
        raise ErrorProtocolo("El número no es finito.")
    return v


def parsear_ayuda(lineas):
    """Convierte la respuesta a AYUDA en un perfil. Lanza ErrorProtocolo si no
    es un robot CAZEL válido."""
    lineas = [str(l).strip() for l in lineas if str(l).strip()]
    if not lineas:
        raise ErrorProtocolo("No hubo respuesta.")
    cab = lineas[0].split()
    if len(cab) < 2 or cab[0].upper() != "CAZEL":
        raise ErrorProtocolo("No habla el protocolo CAZEL.")
    if cab[1] != str(VERSION):
        raise ErrorProtocolo(f"Versión de protocolo no soportada: {cab[1]}.")
    nombre = (cab[2] if len(cab) > 2 else "robot").lower()
    if not NOMBRE_VALIDO.fullmatch(nombre):
        raise ErrorProtocolo("Nombre de robot no válido (usa a-z, 0-9 y _).")

    perfil = {"nombre": nombre, "ordenes": {}, "lecturas": {}}
    terminado = False
    for linea in lineas[1:]:
        partes = linea.split()
        clave = partes[0].upper()
        if clave == "FIN":
            terminado = True
            break
        if clave == "ORDEN" and len(partes) >= 2:
            n = partes[1].lower()
            if not NOMBRE_VALIDO.fullmatch(n) or n in RESERVADOS - {"parar"}:
                raise ErrorProtocolo(f"Nombre de orden no válido: «{partes[1]}».")
            if len(perfil["ordenes"]) >= MAX_ORDENES:
                raise ErrorProtocolo("Demasiadas órdenes.")
            spec = {"parametro": None, "min": None, "max": None}
            if len(partes) >= 3:
                trozos = partes[2].split(":")
                if len(trozos) != 3 or not PARAMETRO_VALIDO.fullmatch(trozos[0].lower()):
                    raise ErrorProtocolo(f"Parámetro mal declarado en «{n}». Usa nombre:min:max.")
                lo, hi = _numero(trozos[1]), _numero(trozos[2])
                if lo > hi:
                    raise ErrorProtocolo(f"Rango invertido en «{n}».")
                spec = {"parametro": trozos[0].lower(), "min": lo, "max": hi}
            perfil["ordenes"][n] = spec
        elif clave == "LECTURA" and len(partes) >= 2:
            n = partes[1].lower()
            if not NOMBRE_VALIDO.fullmatch(n) or n in RESERVADOS:
                raise ErrorProtocolo(f"Nombre de lectura no válido: «{partes[1]}».")
            perfil["lecturas"][n] = {"unidad": (partes[2][:12] if len(partes) > 2 else "")}
        # cualquier otra línea se ignora (compatibilidad hacia delante)
    if not terminado:
        raise ErrorProtocolo("La lista de órdenes no terminó con FIN.")
    return perfil


def formatear_numero(v):
    """20.0 -> '20', 0.5 -> '0.5'. Nunca notación científica ni 'nan'."""
    v = float(v)
    if not math.isfinite(v):
        raise ErrorProtocolo("Número no finito.")
    if v == int(v) and abs(v) < 1e9:
        return str(int(v))
    return f"{v:.4f}".rstrip("0").rstrip(".")


def construir_orden(perfil, nombre, valor=None, tope_absoluto=100000):
    """Línea exacta que se enviará al robot, o ErrorProtocolo. Comprueba que
    la orden exista, que el valor sea un número finito y que esté en rango."""
    nombre = str(nombre).strip().lower()
    if nombre == "parar":
        return "PARAR"
    spec = perfil["ordenes"].get(nombre)
    if spec is None:
        raise ErrorProtocolo(f"Este robot no tiene la orden «{nombre}». "
                             f"Tiene: {', '.join(sorted(perfil['ordenes'])) or 'ninguna'}.")
    if spec["parametro"] is None:
        if valor not in (None, ""):
            raise ErrorProtocolo(f"La orden «{nombre}» no lleva valor.")
        return nombre
    if valor in (None, ""):
        raise ErrorProtocolo(f"La orden «{nombre}» necesita un valor "
                             f"({spec['parametro']}, de {formatear_numero(spec['min'])} "
                             f"a {formatear_numero(spec['max'])}).")
    v = _numero(valor)
    if abs(v) > tope_absoluto:
        raise ErrorProtocolo("Valor fuera de los límites de seguridad.")
    if not (spec["min"] <= v <= spec["max"]):
        raise ErrorProtocolo(f"«{nombre}» acepta de {formatear_numero(spec['min'])} "
                             f"a {formatear_numero(spec['max'])}; me pasaste {formatear_numero(v)}.")
    return f"{nombre} {formatear_numero(v)}"
