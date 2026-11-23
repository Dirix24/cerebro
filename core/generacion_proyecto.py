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
    firmas = re.findall(r"(?<![.\w])([A-Za-z_]\w*)\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*\)", objetivo)
    if len(firmas) != 1:
        return []
    funcion, lista, elemento = firmas[0]
    if not all(campo.isidentifier() for campo in firmas[0]):
        return []
    reparaciones = []
    for nombre, texto in archivos.items():
        if not nombre.endswith(".py"):
            continue
        arbol = ast.parse(texto)
        candidatos = [nodo for nodo in arbol.body if isinstance(nodo, ast.FunctionDef) and nodo.name == funcion]
        if len(candidatos) != 1:
            continue
        nodo = candidatos[0]
        referencia = ast.parse("def muestra(lista, elemento): pass").body[0]
        referencia.name = funcion
        referencia.args.args[0].arg = lista
        referencia.args.args[1].arg = elemento
        if len(nodo.body) != 1 or not isinstance(nodo.body[0], ast.Expr):
            continue
        llamada = nodo.body[0].value
        if (not isinstance(llamada, ast.Call) or not isinstance(llamada.func, ast.Attribute)
                or llamada.func.attr != "append" or not isinstance(llamada.func.value, ast.Name)
                or llamada.func.value.id != lista or len(llamada.args) != 1 or llamada.keywords
                or isinstance(llamada.args[0], ast.Starred)):
            continue
        referencia.body = nodo.body
        if ast.dump(nodo) != ast.dump(referencia):
            continue
        valor = ast.unparse(llamada.args[0])
        lineas = texto.splitlines(keepends=True)
        lineas[nodo.lineno - 1:nodo.end_lineno] = [f"def {funcion}({lista}, {elemento}):\n",
                                                   f"    return {lista} + [{valor}]\n"]
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


def revisar_importaciones_locales(archivos):
    """Detecta rutas de importación incompatibles con el árbol Python propuesto."""
    from pathlib import PurePosixPath

    modulos = {}
    paquetes = set()
    for nombre, texto in archivos.items():
        ruta = PurePosixPath(nombre)
        if ruta.suffix != ".py":
            continue
        partes = ruta.with_suffix("").parts
        if not all(parte.isidentifier() for parte in partes):
            continue
        es_paquete = partes[-1] == "__init__"
        modulo = partes[:-1] if es_paquete else partes
        modulos[modulo] = (nombre, texto, modulo if es_paquete else modulo[:-1])
        paquetes.update(modulo[:nivel] for nivel in range(1, len(modulo) + int(es_paquete)))
    conocidos = modulos.keys() | paquetes
    raices = {modulo[0] for modulo in conocidos if modulo}
    errores = []
    for nombre, texto, paquete in modulos.values():
        for nodo in ast.walk(ast.parse(texto, filename=nombre)):
            if isinstance(nodo, ast.Import):
                objetivos = [tuple(alias.name.split(".")) for alias in nodo.names]
                objetivos = [objetivo for objetivo in objetivos if objetivo[0] in raices]
            elif isinstance(nodo, ast.ImportFrom):
                partes = tuple(nodo.module.split(".")) if nodo.module else ()
                if nodo.level:
                    if nodo.level > len(paquete):
                        errores.append(f"{nombre}:{nodo.lineno}: importación relativa fuera del paquete.")
                        continue
                    objetivos = [paquete[:len(paquete) + 1 - nodo.level] + partes]
                else:
                    objetivos = [partes] if partes and partes[0] in raices else []
            else:
                continue
            for objetivo in objetivos:
                if objetivo not in conocidos:
                    errores.append(f"{nombre}:{nodo.lineno}: falta el módulo local {'.'.join(objetivo)}.")
                elif (isinstance(nodo, ast.ImportFrom) and objetivo in paquetes
                      and objetivo not in modulos):
                    for alias in nodo.names:
                        if alias.name != "*" and (*objetivo, alias.name) not in conocidos:
                            errores.append(f"{nombre}:{nodo.lineno}: falta {'.'.join((*objetivo, alias.name))}.")
    if errores:
        raise ValueError("Importaciones locales incompletas en la propuesta. " + " ".join(errores[:8]))
