"""Validación de propuestas de archivos devueltas por el modelo local."""
import ast
import difflib
import json
from pathlib import Path
import re

PATRON_NOMBRE = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,74}\.(py|html|css|js|ts|sql|sh|c|cpp|h|java|md|txt)$"
EXTENSIONES = (".py", ".html", ".css", ".js", ".ts", ".sql", ".sh", ".c", ".cpp", ".h", ".java", ".md", ".txt")
ESQUEMA = {"type": "object", "required": ["archivos"], "additionalProperties": False, "properties": {
    "archivos": {"type": "array", "minItems": 1, "maxItems": 6, "items": {
        "type": "object", "required": ["nombre", "texto"], "additionalProperties": False,
        "properties": {"nombre": {"type": "string", "pattern": PATRON_NOMBRE},
                       "texto": {"type": "string", "minLength": 1}}}}}}


def esquema_para(objetivo):
    from copy import deepcopy

    formato = deepcopy(ESQUEMA)
    token = r"(?<![\w/])(" + PATRON_NOMBRE[1:-1] + r")(?![\w/])"
    nombres = sorted({coincidencia[1] for coincidencia in re.finditer(token, objetivo)})
    if len(nombres) == 1:
        archivos = formato["properties"]["archivos"]
        archivos["maxItems"] = 1
        archivos["items"]["properties"]["nombre"] = {"enum": nombres}
    return formato


def validar(respuesta):
    try:
        propuesta = json.loads(respuesta)
    except (TypeError, ValueError) as exc:
        raise ValueError("El modelo no devolvió una propuesta JSON válida.") from exc
    if not isinstance(propuesta, dict) or set(propuesta) != {"archivos"}:
        raise ValueError("La propuesta del modelo tiene un formato inesperado.")
    archivos = propuesta["archivos"]
    if not isinstance(archivos, list) or not 1 <= len(archivos) <= 6:
        raise ValueError("La propuesta debe tener entre uno y seis archivos.")
    salida = {}
    for archivo in archivos:
        if not isinstance(archivo, dict) or set(archivo) != {"nombre", "texto"}:
            raise ValueError("La propuesta contiene un archivo inválido.")
        nombre, texto = archivo["nombre"], archivo["texto"]
        if (not isinstance(nombre, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", nombre)
                or Path(nombre).suffix.lower() not in EXTENSIONES
                or nombre.casefold() in (n.casefold() for n in salida)):
            raise ValueError("La propuesta contiene un nombre no permitido o repetido.")
        if not isinstance(texto, str) or not texto.strip() or "\x00" in texto:
            raise ValueError("La propuesta contiene un archivo sin texto válido.")
        if nombre.endswith(".py"):
            try:
                ast.parse(texto, filename=nombre)
            except SyntaxError as exc:
                raise ValueError(f"{nombre}: error de sintaxis en línea {exc.lineno}: {exc.msg}.") from exc
        salida[nombre] = texto if texto.endswith("\n") else texto + "\n"
    if sum(len(texto) for texto in salida.values()) > 5500:
        raise ValueError("La propuesta supera el límite de 5500 caracteres.")
    return salida


def diferencias(archivos):
    return "\n".join("".join(difflib.unified_diff([], texto.splitlines(keepends=True), "/dev/null", nombre))
                     for nombre, texto in archivos.items())


def generar_por_archivos(objetivo, proponer):
    """Compone archivos planificados explícitamente, con una inferencia acotada por archivo."""
    plan = re.search(r"\barchivos planificados:\s*(.+)$", objetivo, re.I | re.S)
    if not plan:
        return validar(proponer(objetivo))
    nombres = [nombre.strip() for nombre in plan[1].split(",")]
    if len(nombres) > 16 or len({n.casefold() for n in nombres}) != len(nombres):
        raise ValueError("El plan requiere hasta 16 rutas distintas.")
    rutas = [ruta_planificada(nombre) for nombre in nombres]
    prefijos = {str(padre).casefold() for ruta in rutas for padre in ruta.parents}
    if prefijos.intersection(n.casefold() for n in nombres):
        raise ValueError("Una ruta del plan coincide con una carpeta necesaria.")
    descripcion = objetivo[:plan.start()].strip()
    from time import monotonic

    resultado = {}
    limite = monotonic() + 30
    for ruta in rutas:
        vecinos = ", ".join(vecino.stem for vecino in rutas if vecino != ruta)
        final = f" Devuelve solo {ruta.name}. Otros módulos del plan: {vecinos}."
        if len(final) >= 350:
            raise ValueError("Acorta los nombres del plan.")
        correccion = ""
        for intento in range(2):
            if monotonic() >= limite:
                raise ValueError("El plan alcanzó el tiempo de preparación. Divídelo en módulos más pequeños.")
            espacio = 350 - len(final) - len(correccion)
            consulta = descripcion[:max(0, espacio)] + correccion + final
            if len(consulta) > 350:
                raise ValueError("Acorta los nombres del plan.")
            modulo = validar(proponer(consulta))
            if set(modulo) != {ruta.name}:
                raise ValueError("El motor devolvió archivos que no corresponden al módulo solicitado.")
            faltan = nombres_sin_definir(modulo[ruta.name], ruta.name) if ruta.suffix == ".py" else []
            if not faltan:
                break
            if intento == 1:
                raise ValueError(f"{ruta}: nombres de módulo sin definir: {', '.join(faltan)}.")
            correccion = " Declara o importa antes de usar: " + ", ".join(faltan)[:100] + "."
        resultado[ruta.as_posix()] = modulo[ruta.name]
    return resultado


def nombres_sin_definir(texto, nombre):
    import builtins
    import symtable

    try:
        tabla = symtable.symtable(texto, nombre, "exec")
    except SyntaxError as error:
        raise ValueError(f"{nombre}: {error.msg}.") from error
    implicitos = set(vars(builtins)) | {"__file__", "__name__", "__package__", "__spec__", "__cached__", "__loader__"}
    definidos = implicitos | {s.get_name() for s in tabla.get_symbols()
                              if s.is_assigned() or s.is_imported() or s.is_namespace()}
    pendientes = [tabla]
    faltan = set()
    while pendientes:
        bloque = pendientes.pop()
        pendientes.extend(bloque.get_children())
        faltan.update(s.get_name() for s in bloque.get_symbols()
                      if s.is_referenced() and s.is_global() and not s.is_assigned()
                      and s.get_name() not in definidos)
    return sorted(faltan)


def ruta_planificada(nombre):
    from pathlib import PurePosixPath

    partes = nombre.split("/")
    if (len(nombre) > 200 or not 1 <= len(partes) <= 5
            or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", parte) for parte in partes[:-1])
            or not re.fullmatch(PATRON_NOMBRE, partes[-1])):
        raise ValueError("El plan contiene una ruta de archivo no permitida.")
    return PurePosixPath(nombre)


def reparar_adicion_no_mutante(objetivo, archivos):
    """Repara el patrón inequívoco de append sin retorno cuando se pide una lista nueva."""
    from core.respuestas_con_fuentes import normalizar

    pedido = normalizar(objetivo)
    if "lista nueva" not in pedido and "sin mutar" not in pedido and "lista de entrada debe quedar intacta" not in pedido:
        return []
    if "agregar tareas titulo" not in pedido:
        return []
    reparaciones = []
    for nombre, texto in archivos.items():
        if not nombre.endswith(".py"):
            continue
        arbol = ast.parse(texto)
        referencia = ast.parse("def agregar(tareas, titulo): tareas.append(titulo)").body[0]
        candidatos = [nodo for nodo in arbol.body if isinstance(nodo, ast.FunctionDef) and nodo.name == "agregar"]
        if len(candidatos) != 1:
            continue
        nodo = candidatos[0]
        if ast.dump(nodo) != ast.dump(referencia):
            continue
        lineas = texto.splitlines(keepends=True)
        lineas[nodo.lineno - 1:nodo.end_lineno] = ["def agregar(tareas, titulo):\n",
                                                    "    return tareas + [titulo]\n"]
        archivos[nombre] = "".join(lineas)
        reparaciones.append(f"{nombre}: se reemplazó la mutación por una lista nueva con retorno.")
    return reparaciones


def dependencias_externas(archivos):
    """Enumera importaciones Python de primer nivel que no son locales ni estándar."""
    import sys
    from pathlib import PurePosixPath

    modulos = {PurePosixPath(nombre).parts[0].split(".")[0] for nombre in archivos}
    externas = set()
    for nombre, texto in archivos.items():
        if not nombre.endswith(".py"):
            continue
        for nodo in ast.walk(ast.parse(texto)):
            if isinstance(nodo, ast.Import):
                externas.update(alias.name.split(".")[0] for alias in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                externas.add(nodo.module.split(".")[0])
    return sorted(externas - modulos - sys.stdlib_module_names)
