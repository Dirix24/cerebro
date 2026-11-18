"""Inventario pasivo de componentes de un robot a partir de evidencias.

No abre puertos, no sondea buses ni energiza pines. Un listado I2C
solo confirma direcciones observadas, no el modelo exacto de sensor.
"""
import re

_I2C = {
    0x29: ("sensor de distancia o luz (varios modelos)", "posible"),
    0x3C: ("pantalla OLED u otro periférico", "posible"),
    0x48: ("conversor ADC o sensor", "posible"),
    0x68: ("reloj RTC o sensor inercial", "posible"),
    0x76: ("sensor ambiental (varios modelos)", "posible"),
    0x77: ("sensor ambiental (varios modelos)", "posible"),
}


def interpretar_inventario_i2c(direcciones):
    if not isinstance(direcciones, (list, tuple)) or len(direcciones) > 128:
        raise ValueError("Se requiere una lista de hasta 128 direcciones I2C.")
    hallazgos = []
    for direccion in direcciones:
        if type(direccion) is not int or not 0x08 <= direccion <= 0x77:
            raise ValueError("Dirección I2C inválida.")
        tipo, certeza = _I2C.get(direccion, ("dispositivo I2C desconocido", "desconocido"))
        hallazgos.append({"direccion": f"0x{direccion:02X}", "componente": tipo,
                          "certeza": certeza, "identidad_confirmada": False})
    return {"bus": "i2c", "origen": "direcciones proporcionadas, sin sondeo",
            "hallazgos": hallazgos, "motores_detectados": False,
            "acciones_fisicas": False,
            "advertencia": "GPIO, motores y sensores analógicos no se pueden identificar con este inventario."}


def analizar_codigo_robot(codigo):
    if not isinstance(codigo, str) or len(codigo) > 100000:
        raise ValueError("Código inválido o demasiado grande.")
    patrones = {
        "i2c": r"\b(?:I2C|SoftI2C)\s*\(",
        "spi": r"\b(?:SPI|SoftSPI)\s*\(",
        "uart": r"\bUART\s*\(",
        "gpio": r"\bPin\s*\(",
        "pwm": r"\bPWM\s*\(",
        "adc": r"\bADC\s*\(",
    }
    pistas = [nombre for nombre, patron in patrones.items() if re.search(patron, codigo)]
    return {"interfaces_referenciadas": pistas, "componentes_confirmados": [],
            "inspeccion_estatica": True, "codigo_ejecutado": False,
            "advertencia": "El código muestra interfaces usadas, no demuestra qué hay conectado."}
