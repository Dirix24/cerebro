"""Utilidades de aprendizaje local sin red ni modelos preentrenados."""
import re
import unicodedata


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def detectar_duplicados(textos, umbral=0.8):
    """Busca pares similares mediante Jaccard de palabras (no modifica datos)."""
    if not 0 <= umbral <= 1 or len(textos) > 100:
        raise ValueError("Umbral o cantidad fuera de límites")
    if any(not isinstance(t, str) or len(t) > 10000 for t in textos):
        raise ValueError("Cada texto debe tener como máximo 10000 caracteres")
    conjuntos = [set(re.findall(r"\w+", _normalizar(t))) for t in textos]
    encontrados = []
    for i, a in enumerate(conjuntos):
        for j in range(i + 1, len(conjuntos)):
            b = conjuntos[j]
            union = a | b
            similitud = len(a & b) / len(union) if union else 1.0
            if similitud >= umbral:
                encontrados.append({"primero": i, "segundo": j,
                                    "similitud": round(similitud, 3)})
    return encontrados


def generar_preguntas(texto, limite=10):
    """Genera preguntas literales a partir de frases 'X es Y'."""
    if not 1 <= limite <= 30 or len(texto) > 100000:
        raise ValueError("Entrada fuera de límites")
    preguntas = []
    for frase in re.split(r"[.\n!?]+", texto):
        coincidencia = re.fullmatch(
            r"\s*(.{2,100}?)\s+es\s+(.{2,300}?)\s*", frase, re.IGNORECASE)
        if coincidencia:
            sujeto, respuesta = coincidencia.groups()
            preguntas.append({"pregunta": f"¿Qué es {sujeto.strip()}?",
                              "respuesta": respuesta.strip()})
            if len(preguntas) >= limite:
                break
    return preguntas
