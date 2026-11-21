"""Acceso acotado a una carpeta seleccionada y propuestas verificables de Python."""
import ast
import difflib
from io import StringIO
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import tokenize
from tempfile import NamedTemporaryFile

FORMATOS = {".py", ".txt", ".md", ".json", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".css", ".js", ".html"}
OMITIR = {"__pycache__", "node_modules", "build", "dist", "venv"}
MAX_ARCHIVO = 512 * 1024


class ProyectoStudio:
    def __init__(self, carpeta):
        if not isinstance(carpeta, str) or not Path(carpeta).is_absolute():
            raise ValueError("Selecciona una carpeta absoluta de proyecto.")
        self.raiz = Path(carpeta).resolve(strict=True)
        if (not self.raiz.is_dir() or self.raiz == Path.home().resolve()
                or self.raiz == Path(self.raiz.anchor)):
            raise ValueError("Selecciona una carpeta concreta de proyecto.")
        self.propuestas = {}

    def ruta(self, nombre):
        if not isinstance(nombre, str) or not nombre or len(nombre) > 240:
            raise ValueError("Ruta de proyecto inválida.")
        partes = PurePosixPath(nombre).parts
        if (not partes or nombre.startswith("/") or any(p.startswith(".") or p in OMITIR for p in partes)
                or Path(nombre).suffix.lower() not in FORMATOS):
            raise ValueError("Selecciona un archivo de texto dentro del proyecto.")
        ruta = self.raiz
        for parte in partes:
            ruta = ruta / parte
            if ruta.is_symlink():
                raise PermissionError("Los enlaces simbólicos quedan fuera del proyecto.")
        if not ruta.resolve().is_relative_to(self.raiz):
            raise PermissionError("Ruta fuera de la carpeta autorizada.")
        return ruta

    def listar(self):
        archivos = []
        vistos = 0
        for base, directorios, nombres in os.walk(self.raiz):
            directorios[:] = sorted(d for d in directorios if not d.startswith(".") and d not in OMITIR
                                    and not (Path(base) / d).is_symlink())
            vistos += 1 + len(nombres)
            for nombre in sorted(nombres):
                ruta = Path(base) / nombre
                if (not nombre.startswith(".") and ruta.suffix.lower() in FORMATOS
                        and not ruta.is_symlink() and ruta.is_file()):
                    relativos = ruta.relative_to(self.raiz).as_posix()
                    if len(relativos) <= 240:
                        archivos.append(relativos)
                if len(archivos) >= 500:
                    return {"archivos": archivos, "limitado": True}
            if vistos >= 10000:
                return {"archivos": archivos, "limitado": True}
        return {"archivos": archivos, "limitado": False}

    def leer(self, nombre):
        ruta = self.ruta(nombre)
        if not ruta.is_file():
            raise ValueError("El archivo no existe dentro del proyecto.")
        with ruta.open("rb") as lector:
            datos = lector.read(MAX_ARCHIVO + 1)
        if len(datos) > MAX_ARCHIVO:
            raise ValueError("El archivo supera 512 KiB.")
        salida = datos.decode("utf-8")
        if "\x00" in salida:
            raise ValueError("El archivo no es texto UTF-8.")
        return salida

    def guardar(self, nombre, texto, original):
        ruta = self.ruta(nombre)
        if not isinstance(texto, str) or "\x00" in texto or len(texto.encode("utf-8")) > MAX_ARCHIVO:
            raise ValueError("Guarda texto UTF-8 de hasta 512 KiB.")
        if self.leer(nombre) != original:
            raise ValueError("El archivo cambió en disco. Vuelve a abrirlo antes de guardar.")
        modo = stat.S_IMODE(ruta.stat().st_mode) & 0o777
        with NamedTemporaryFile(dir=ruta.parent, delete=False) as archivo:
            temporal = Path(archivo.name)
            archivo.write(texto.encode("utf-8"))
        try:
            temporal.chmod(modo)
            temporal.replace(ruta)
        finally:
            temporal.unlink(missing_ok=True)

    def analizar(self):
        self.propuestas.clear()
        inventario = self.listar()
        hallazgos, propuestas = [], []
        revisados = 0
        for nombre in inventario["archivos"]:
            if not nombre.lower().endswith(".py"):
                continue
            if revisados >= 120:
                inventario["limitado"] = True
                break
            revisados += 1
            try:
                original = self.leer(nombre)
                comprobar_python(original, nombre)
                arbol = ast.parse(original, filename=nombre)
                hallazgos.extend(_claves_duplicadas(arbol, nombre))
            except SyntaxError as error:
                hallazgos.append(f"{nombre}:{error.lineno} · {error.msg}")
                candidato = _proponer_reparacion(original, nombre, error)
                if candidato is not None and len(propuestas) < 20:
                    identificador = secrets.token_hex(12)
                    self.propuestas[identificador] = nombre, original, candidato
                    a, b = original.splitlines(keepends=True), candidato.splitlines(keepends=True)
                    diff = "".join(difflib.unified_diff(a, b, "antes/" + nombre, "después/" + nombre))
                    propuestas.append({"id": identificador, "archivo": nombre, "diff": diff})
            except (OSError, ValueError, RecursionError) as error:
                hallazgos.append(f"{nombre} · no se pudo revisar ({error})")
        return {"archivos": len(inventario["archivos"]), "revisados": revisados,
                "hallazgos": hallazgos, "propuestas": propuestas,
                "limitado": inventario["limitado"]}

    def aplicar(self, identificador):
        if not isinstance(identificador, str) or identificador not in self.propuestas:
            raise ValueError("Vuelve a generar la propuesta antes de aplicarla.")
        nombre, original, candidato = self.propuestas[identificador]
        self.guardar(nombre, candidato, original)
        del self.propuestas[identificador]
        return {"archivo": nombre}


def comprobar_python(texto, nombre):
    """Comprueba restricciones del compilador sin ejecutar el archivo."""
    compile(texto, nombre, "exec", dont_inherit=True)


def _claves_duplicadas(arbol, nombre):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Dict):
            vistas = set()
            for clave in nodo.keys:
                if isinstance(clave, ast.Constant) and type(clave.value) in (str, int, bool):
                    if clave.value in vistas:
                        yield f"{nombre}:{clave.lineno} · clave de diccionario repetida; prevalece la última."
                    vistas.add(clave.value)


def _proponer_reparacion(original, nombre, error):
    candidato = (_agregar_dos_puntos(original, error)
                 if error.msg == "expected ':'" else _cerrar_delimitador(original, error))
    if candidato is None:
        return None
    try:
        comprobar_python(candidato, nombre)
    except (SyntaxError, ValueError, RecursionError):
        return None
    return candidato


def _cerrar_delimitador(original, error):
    if "was never closed" not in error.msg:
        return None
    cierres = {"(": ")", "[": "]", "{": "}"}
    aperturas = []
    try:
        for token in tokenize.generate_tokens(StringIO(original).readline):
            if token.type != tokenize.OP:
                continue
            if token.string in cierres:
                aperturas.append((token, cierres[token.string]))
            elif token.string in cierres.values():
                if not aperturas or aperturas.pop()[1] != token.string:
                    return None
    except tokenize.TokenError as exc:
        if "multi-line statement" not in str(exc):
            return None
    if len(aperturas) != 1 or aperturas[0][0].start[0] != error.lineno:
        return None
    return original.rstrip("\r\n") + "\n" + aperturas[0][1] + "\n"


def _agregar_dos_puntos(original, error):
    if not error.lineno:
        return None
    lineas = original.splitlines(keepends=True)
    linea = lineas[error.lineno - 1]
    # Una cabecera con comentario puede requerir un ajuste distinto.
    if "#" in linea:
        return None
    cabecera = linea.rstrip()
    if not re.match(r"\s*(?:async\s+)?(?:def|class|if|elif|else|for|while|try|except|finally|with|match|case)\b", cabecera):
        return None
    lineas[error.lineno - 1] = cabecera + ":" + linea[len(cabecera):]
    return "".join(lineas)


def ejecutar_pruebas(raiz):
    """Ejecuta unittest únicamente sobre una copia dentro de Bubblewrap."""
    from tempfile import TemporaryDirectory

    from core.aislamiento_proyecto import comando_aislado, preparar_copia

    try:
        with TemporaryDirectory(prefix="cerebro-pruebas-") as carpeta:
            copia = Path(carpeta)
            preparar_copia(raiz, copia)
            return _ejecutar_aislado(comando_aislado(copia))
    except (OSError, ValueError, RuntimeError) as error:
        return False, str(error)


def _ejecutar_aislado(comando):
    import selectors
    import signal
    import subprocess
    from time import monotonic

    with subprocess.Popen(comando, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, start_new_session=True) as proceso:
        salida = bytearray()
        limite = monotonic() + 25
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proceso.stdout, selectors.EVENT_READ)
                while True:
                    if not selector.select(max(0, limite - monotonic())):
                        raise RuntimeError("Las pruebas superaron 25 segundos.")
                    bloque = os.read(proceso.stdout.fileno(), 4096)
                    if not bloque:
                        break
                    salida.extend(bloque)
                    if len(salida) > 128 * 1024:
                        raise RuntimeError("Las pruebas superaron 128 KiB de salida.")
            codigo = proceso.wait(timeout=max(.1, limite - monotonic()))
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            try:
                os.killpg(proceso.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return False, str(error) + "\n" + salida[-12000:].decode(errors="replace")
    texto = salida[-12000:].decode(errors="replace")
    if texto.startswith("bwrap:"):
        return False, "Bubblewrap no pudo iniciar el aislamiento. No se ejecutó el proyecto.\n" + texto
    if re.search(r"\bRan 0 tests?\b", texto):
        return False, "unittest no descubrió pruebas.\n" + texto
    return codigo == 0, f"unittest aislado · código {codigo}\n{texto}"
