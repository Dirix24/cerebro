"""Cálculo seguro y razonamiento simbólico simple, sin eval ni IA externa."""
import ast
import operator

OPERACIONES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
               ast.Mod: operator.mod, ast.Pow: operator.pow}
UNARIOS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def calcular(expresion):
    if len(expresion) > 120:
        raise ValueError("Expresión demasiado larga")
    arbol = ast.parse(expresion, mode="eval")
    def resolver(nodo, profundidad=0):
        if profundidad > 12:
            raise ValueError("Expresión demasiado compleja")
        if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
            valor = nodo.value
        elif isinstance(nodo, ast.UnaryOp) and type(nodo.op) in UNARIOS:
            valor = UNARIOS[type(nodo.op)](resolver(nodo.operand, profundidad + 1))
        elif isinstance(nodo, ast.BinOp) and type(nodo.op) in OPERACIONES:
            a = resolver(nodo.left, profundidad + 1)
            b = resolver(nodo.right, profundidad + 1)
            if isinstance(nodo.op, ast.Pow) and (abs(b) > 12 or abs(a) > 10000):
                raise ValueError("Potencia demasiado grande")
            valor = OPERACIONES[type(nodo.op)](a, b)
        else:
            raise ValueError("Operación no permitida")
        if abs(valor) > 1e15:
            raise ValueError("Resultado fuera de límites")
        return valor
    return resolver(arbol.body)


def deducir(es_un, todos_son):
    """Silogismo explícito: (individuo, clase), (clase, categoría)."""
    individuo, clase = es_un
    origen, destino = todos_son
    return f"{individuo} es {destino}" if clase.casefold() == origen.casefold() else None
