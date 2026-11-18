"""Catálogo de aprendizaje generalista. Contenido introductorio local, no pesos entrenados."""
MATERIAS = {
    "programacion": {
        "titulo": "Programación",
        "temas": ["Python", "algoritmos", "pruebas", "Git", "arquitectura de software"],
        "ejercicio": "Crea una función que valide una entrada y escribe tres pruebas unitarias.",
    },
    "ciberseguridad": {
        "titulo": "Ciberseguridad defensiva",
        "temas": ["redes TCP/IP", "contraseñas y MFA", "actualizaciones", "registros", "copias de seguridad", "análisis de riesgos"],
        "ejercicio": "Diseña una lista de comprobación de seguridad para tu propio equipo; no escanees sistemas ajenos.",
    },
    "matematicas": {
        "titulo": "Matemáticas",
        "temas": ["aritmética", "álgebra", "estadística", "probabilidad", "lógica"],
        "ejercicio": "Calcula la media y mediana de 2, 3, 3, 8, 9.",
    },
    "ciencias": {
        "titulo": "Ciencias",
        "temas": ["método científico", "física", "química", "biología", "medición"],
        "ejercicio": "Formula una hipótesis comprobable y explica cómo contrastarla.",
    },
    "idiomas": {
        "titulo": "Idiomas",
        "temas": ["comprensión", "vocabulario", "gramática", "traducción", "conversación"],
        "ejercicio": "Escribe cinco frases sencillas en inglés y tradúcelas.",
    },
    "escritura": {
        "titulo": "Escritura y comunicación",
        "temas": ["ortografía", "resumen", "argumentación", "documentación", "presentaciones"],
        "ejercicio": "Resume un texto propio en tres frases y comprueba que no inventas hechos.",
    },
    "sistemas": {
        "titulo": "Sistemas y redes",
        "temas": ["Linux", "Windows", "procesos", "almacenamiento", "redes", "administración"],
        "ejercicio": "Explica la diferencia entre RAM, SSD y CPU.",
    },
    "analisis": {
        "titulo": "Análisis de datos",
        "temas": ["CSV", "NumPy", "limpieza de datos", "gráficos", "sesgos"],
        "ejercicio": "Identifica valores ausentes en un CSV de ejemplo y documenta cómo los tratarías.",
    },
}


def listar_materias():
    return [(clave, materia["titulo"]) for clave, materia in MATERIAS.items()]


def plan_materia(clave):
    if clave not in MATERIAS:
        raise ValueError("Materia desconocida: " + clave)
    m = MATERIAS[clave]
    return (m["titulo"] + "\nTemas: " + ", ".join(m["temas"]) +
            "\nPráctica: " + m["ejercicio"] +
            "\nNota: es una guía local; no certifica conocimientos ni entrena pesos.")
