"""Aritmética exacta y ecuaciones lineales acotadas, sin ejecutar código."""
import ast
from fractions import Fraction
import re


def _lineal(texto):
    texto = re.sub(r"(?<=\d)\s*(?=x\b)|(?<=\d)\s*(?=\()", "*", texto.strip())
    arbol = ast.parse(texto, mode="eval")

    def visitar(nodo):
        if isinstance(nodo, ast.Constant) and type(nodo.value) in {int, float}:
            literal = ast.get_source_segment(texto, nodo)
            if not re.fullmatch(r"(?:[0-9]{1,20}(?:\.[0-9]{0,20})?|\.[0-9]{1,20})", literal):
                raise ValueError("Usa números enteros o decimales de hasta 20 cifras por parte.")
            return Fraction(0), Fraction(literal)
        if isinstance(nodo, ast.Name) and nodo.id == "x":
            return Fraction(1), Fraction(0)
        if isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, (ast.USub, ast.UAdd)):
            a, b = visitar(nodo.operand)
            return (-a, -b) if isinstance(nodo.op, ast.USub) else (a, b)
        if isinstance(nodo, ast.BinOp):
            a, b = visitar(nodo.left)
            c, d = visitar(nodo.right)
            if isinstance(nodo.op, ast.Add):
                return a + c, b + d
            if isinstance(nodo.op, ast.Sub):
                return a - c, b - d
            if isinstance(nodo.op, ast.Mult) and not (a and c):
                return a * d + b * c, b * d
            if isinstance(nodo.op, ast.Div) and not c:
                return a / d, b / d
        raise ValueError("Se admite aritmética y ecuaciones lineales en x con +, -, * y /.")

    return visitar(arbol.body)


def resolver(texto):
    if not 1 <= len(texto) <= 200:
        raise ValueError("Escribe una expresión de hasta 200 caracteres.")
    izquierda, igual, derecha = texto.partition("=")
    a, b = _lineal(izquierda)
    if not igual:
        if a:
            raise ValueError("Escribe los dos lados de la ecuación en x.")
        return f"Resultado exacto: {b}."
    c, d = _lineal(derecha)
    if a == c:
        return "La igualdad se cumple para todo x." if b == d else "La ecuación no tiene solución."
    x = (d - b) / (a - c)
    return f"x = {x}. Comprobación: al sustituir x, ambos lados dan {a * x + b}."


def consultar(intencion):
    orden = re.fullmatch(r"(?:calcula(?:me)?|resuelve(?:me)?|cuanto es)\s+(?:(?:la |esta )?ecuacion[: ]+)?(.+)", intencion)
    if not orden:
        return None
    expresion = orden[1].replace("×", "*").replace("÷", "/").replace("−", "-")
    if "**" in expresion or not re.fullmatch(r"[x0-9.()+*/=\-\s]{1,200}", expresion):
        return None
    try:
        return resolver(expresion)
    except (SyntaxError, ValueError, ZeroDivisionError) as error:
        return "No pude calcularlo: " + (str(error) if isinstance(error, ValueError) else "revisa la expresión y los divisores.")
