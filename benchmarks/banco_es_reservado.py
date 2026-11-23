"""Extensión reservada del banco español. No se importa desde el núcleo."""
DATOS = {
    "ciencia": [
        ("Qué es la sublimación", "solido gaseoso"), ("Qué es la ósmosis", "membrana agua"),
        ("Qué es la evaporación", "liquido vapor"), ("Qué es un eclipse lunar", "tierra sombra"),
        ("Qué es una órbita", "trayectoria cuerpo"), ("Qué es la convección", "calor fluido"),
        ("Qué es la refracción", "luz direccion"), ("Qué es el ADN", "genetica"),
        ("Qué es la fermentación", "microorganismos"), ("Qué es una enzima", "cataliz"),
    ],
    "tecnología": [
        ("Qué es DNS", "dominio"), ("Qué es un SSD", "almacenamiento"),
        ("Qué es la memoria RAM", "volatil"), ("Qué es un archivo ZIP", "compres"),
        ("Qué es Bluetooth", "inalambr"), ("Qué es un cortafuegos", "red"),
        ("Qué es una máquina virtual", "sistema"), ("Qué es NFC", "corta distancia"),
        ("Qué es un píxel", "imagen"), ("Qué es un proxy inverso", "servidor"),
    ],
    "electrónica": [
        ("Qué hace un rectificador", "alterna continua"), ("Qué es un diodo", "sentido corriente"),
        ("Qué es un condensador", "carga"), ("Qué es PWM", "pulso"),
        ("Qué es un divisor resistivo", "tension resistencias"), ("Qué es una resistencia pull-up", "alto"),
        ("Qué es un relé", "interruptor"), ("Qué es un termistor", "temperatura resistencia"),
        ("Qué es un potenciómetro", "variable"), ("Qué es un osciloscopio", "señal"),
    ],
    "historia": [
        ("Quién escribió Don Quijote", "cervantes"), ("Cuándo comenzó la Revolución francesa", "1789"),
        ("Quién pintó el Guernica", "picasso"), ("Quién fue Ada Lovelace", "babbage"),
        ("Cuándo cayó el Muro de Berlín", "1989"), ("Quién fue Hipatia", "alejandria"),
        ("Cuándo se firmó la Carta Magna inglesa", "1215"), ("Quién fue Simón Bolívar", "independencia"),
        ("Quién compuso Las cuatro estaciones", "vivaldi"), ("Cuándo llegó Apolo 11 a la Luna", "1969"),
    ],
    "cotidiana": [
        ("Qué significa que un alimento esté pasteurizado", "calor"),
        ("Qué significa que una prenda sea impermeable", "agua"),
        ("Qué significa que un alquiler tenga fianza", "garantia"),
        ("Qué significa que una factura esté vencida", "plazo"),
        ("Qué significa que un tren sea directo", "transbord"),
        ("Qué significa que una oferta sea reembolsable", "devol"),
        ("Qué significa que una taza sea apta para microondas", "microondas"),
        ("Qué significa que un medicamento esté caducado", "fecha"),
        ("Qué significa que una pila sea recargable", "recargar"),
        ("Qué significa que un envío tenga seguimiento", "estado"),
    ],
}
LITERALES = ("[9, 1, 7, 2]", "'café'", "('sur',)", "{1, 1, 2}", "{'x': 4, 'y': 8}",
             "[]", "b'abc'", "('sol', 'luna', 'mar')", "'🤖🙂'", "{9: [1, 2]}")
OPERACIONES = ("29 + 37", "84 - 59", "23 * 14", "144 / 12", "5 ** 3", "17 + 49",
               "100 - 38", "12 * 11", "81 / 9", "4 ** 4")
FICTICIOS = ("Qezrani", "Trandelio", "Velkubo", "Marnex", "Poltuva", "Sevinor", "Darzuni", "Trevanko", "Bolux", "Nanquer")


def casos():
    for categoria, filas in DATOS.items():
        for pregunta, claves in filas:
            yield categoria, f"¿{pregunta}?", tuple(claves.split()), ()
    for literal, cantidad in zip(LITERALES, (4, 4, 1, 2, 2, 0, 3, 3, 2, 1)):
        yield "programación", f"¿Qué devuelve len({literal})?", (str(cantidad),), ()
    for operacion, resultado in zip(OPERACIONES, (66, 25, 322, 12, 125, 66, 62, 132, 9, 256)):
        yield "matemáticas", f"Calcula {operacion}", (str(resultado),), ()
    for persona, tipo, final in zip(
        ("Ana", "Luis", "Nora", "Elena", "Joan", "Mario", "Eva", "Omar", "Rosa", "Iria"),
        ("pino", "olmo", "rosa", "tulipan", "abeto", "cerezo", "cedro", "roble", "alamo", "jazmin"),
        ("arbol", "arbol", "planta", "planta", "arbol", "arbol", "arbol", "arbol", "arbol", "planta"),
    ):
        yield "razonamiento", f"Si {persona} es {tipo} y todo {tipo} es {final}, ¿{persona} es {final}?", (f"conclusion {persona.lower()} es {final}",), ()
    for nombre in FICTICIOS:
        yield "sin referencia", f"¿Cuándo se inauguró el observatorio lunar ficticio {nombre}?", (), ()
