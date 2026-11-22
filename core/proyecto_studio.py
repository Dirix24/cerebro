"""Acceso acotado a una carpeta seleccionada y propuestas verificables de Python."""
import ast
import base64
from contextlib import contextmanager
import ctypes
import difflib
from io import StringIO
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import tokenize
from threading import RLock

FORMATOS = {".py", ".txt", ".md", ".json", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".css", ".js", ".html"}
OMITIR = {"__pycache__", "node_modules", "build", "dist", "venv"}
FORMATOS |= {".csv", ".tsv", ".xml", ".sql", ".sh", ".rs", ".java", ".c", ".h", ".cpp", ".ts"}
IMAGENES = {".png", ".gif", ".jpg", ".jpeg", ".webp"}
MAX_ARCHIVO = 512 * 1024
MAX_VISOR = 4 * 1024 * 1024
DOCUMENTOS_EXTERNOS = {".docx", ".odt", ".rtf", ".xlsx", ".ods", ".pptx", ".odp", ".pdf"}
_TRASH = ".cerebro-papelera"


def _renombrar_sin_reemplazar(fd_origen, nombre, fd_destino, destino):
    """MX Linux: cambio de nombre atómico que falla si el destino existe."""
    libc = ctypes.CDLL(None, use_errno=True)
    funcion = getattr(libc, "renameat2", None)
    if funcion is None:
        raise RuntimeError("Este equipo no admite mover archivos sin riesgo de reemplazo.")
    funcion.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    funcion.restype = ctypes.c_int
    if funcion(fd_origen, os.fsencode(nombre), fd_destino, os.fsencode(destino), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destino)



class ProyectoStudio:
    def __init__(self, carpeta, *, lectura_individual=False):
        if not isinstance(carpeta, str) or not Path(carpeta).is_absolute():
            raise ValueError("Selecciona una carpeta absoluta de proyecto.")
        self.raiz = Path(carpeta).resolve(strict=True)
        if (not self.raiz.is_dir() or (not lectura_individual and self.raiz == Path.home().resolve())
                or self.raiz == Path(self.raiz.anchor)):
            raise ValueError("Selecciona una carpeta concreta de proyecto.")
        self.propuestas = {}
        self.aplicadas = {}
        self.cerrojo = RLock()
        estado = self.raiz.stat()
        self.identidad = estado.st_dev, estado.st_ino

    def _partes(self, nombre):
        if not isinstance(nombre, str) or not nombre or len(nombre) > 240 or "\0" in nombre or "\\" in nombre:
            raise ValueError("Ruta de proyecto inválida.")
        partes = nombre.split("/")
        if any(not p or p.startswith(".") or p in OMITIR or any(ord(c) < 32 for c in p) for p in partes):
            raise ValueError("Selecciona una ruta relativa visible dentro del proyecto.")
        return partes

    @contextmanager
    def _directorio(self, partes=()):
        opciones = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open(self.raiz, opciones)
        try:
            estado = os.fstat(fd)
            if (estado.st_dev, estado.st_ino) != self.identidad:
                raise PermissionError("La carpeta autorizada fue reemplazada.")
            for parte in partes:
                nuevo = os.open(parte, opciones, dir_fd=fd)
                os.close(fd)
                fd = nuevo
            yield fd
        finally:
            os.close(fd)

    @contextmanager
    def _padre(self, nombre):
        partes = self._partes(nombre)
        with self._directorio(partes[:-1]) as fd:
            yield fd, partes[-1]

    @staticmethod
    def _tipo(fd, nombre):
        info = os.stat(nombre, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            return "carpeta", info
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PermissionError("Los enlaces y archivos especiales quedan fuera del proyecto.")
        return "archivo", info

    def ruta(self, nombre):
        if Path(nombre if isinstance(nombre, str) else "").suffix.lower() not in FORMATOS:
            raise ValueError("Selecciona un archivo de texto dentro del proyecto.")
        with self._padre(nombre) as (fd, hoja):
            if self._tipo(fd, hoja)[0] != "archivo":
                raise ValueError("Selecciona un archivo de texto dentro del proyecto.")
        return self.raiz.joinpath(*self._partes(nombre))

    def listar(self):
        archivos, entradas = [], []
        vistos = 0
        for base, directorios, nombres, fd in os.fwalk(self.raiz, follow_symlinks=False):
            if not entradas and Path(base) == self.raiz:
                estado = os.fstat(fd)
                if (estado.st_dev, estado.st_ino) != self.identidad:
                    raise PermissionError("La carpeta autorizada fue reemplazada.")
            directorios[:] = sorted(d for d in directorios if not d.startswith(".") and d not in OMITIR
                                    and not (Path(base) / d).is_symlink())
            vistos += 1 + len(nombres) + len(directorios)
            for nombre in [*directorios, *sorted(nombres)]:
                relativo = (Path(base) / nombre).relative_to(self.raiz).as_posix()
                try:
                    self._partes(relativo)
                    tipo, _ = self._tipo(fd, nombre)
                except (ValueError, OSError):
                    continue
                entradas.append({"ruta": relativo, "tipo": tipo})
                if tipo == "archivo" and Path(nombre).suffix.lower() in FORMATOS:
                    archivos.append(relativo)
                if len(entradas) >= 500:
                    return {"archivos": archivos, "entradas": entradas, "limitado": True}
            if vistos >= 10000:
                return {"archivos": archivos, "entradas": entradas, "limitado": True}
        return {"archivos": archivos, "entradas": entradas, "limitado": False}

    def _bytes(self, nombre, limite):
        with self._padre(nombre) as (fd, hoja):
            entrada = os.open(hoja, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(entrada, "rb") as lector:
                info = os.fstat(lector.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise PermissionError("Los enlaces y archivos especiales quedan fuera del proyecto.")
                datos = lector.read(limite + 1)
        if len(datos) > limite:
            raise ValueError(f"El archivo supera {limite // 1024} KiB.")
        return datos

    def leer(self, nombre):
        self.ruta(nombre)
        salida = self._bytes(nombre, MAX_ARCHIVO).decode("utf-8")
        if "\x00" in salida:
            raise ValueError("El archivo no es texto UTF-8.")
        return salida

    def inspeccionar(self, nombre, *, contenido=True, pagina=1, resolucion=980):
        extension = Path(nombre if isinstance(nombre, str) else "").suffix.lower()
        with self._padre(nombre) as (fd, hoja):
            tipo, info = self._tipo(fd, hoja)
        datos = {"archivo": nombre, "tipo": tipo, "extension": extension, "bytes": info.st_size,
                 "app_externa": tipo == "archivo" and extension in DOCUMENTOS_EXTERNOS,
                 "marca": [info.st_ino, info.st_mtime_ns, info.st_size]}
        if tipo != "archivo" or not contenido:
            return datos
        if extension in FORMATOS:
            try:
                texto = self.leer(nombre)
                respuesta = {**datos, "visor": "texto", "texto": texto}
                if extension == ".html":
                    from core.visores_studio import html_estatico
                    respuesta["fragmentos"] = html_estatico(texto)[:4000]
                elif extension in {".csv", ".tsv"}:
                    from csv import Error
                    from core.visores_studio import tabla
                    try:
                        respuesta["filas"] = tabla(texto, extension)
                    except Error as error:
                        respuesta["aviso"] = "Tabla inválida: " + str(error)
                return respuesta
            except (ValueError, UnicodeError) as error:
                return {**datos, "aviso": str(error)}
        if extension in IMAGENES | {".pdf", ".docx", ".odt"}:
            if info.st_size > MAX_VISOR:
                return {**datos, "aviso": "La vista previa admite archivos de hasta 4 MiB."}
            bruto = self._bytes(nombre, MAX_VISOR)
            if extension in {".docx", ".odt"}:
                from core.documentos_oficina import extraer_texto

                try:
                    texto = extraer_texto(bruto, extension)
                except ValueError as error:
                    return {**datos, "aviso": str(error)}
                return {**datos, "visor": "texto", "texto": texto, "solo_lectura": True,
                        "aviso": "Texto extraído en solo lectura." if texto else "El documento no contiene texto legible."}
            if extension == ".pdf":
                from core.visores_studio import pdf_vista

                try:
                    return {**datos, "visor": "pdf", **pdf_vista(bruto, pagina, resolucion)}
                except (OSError, ValueError) as error:
                    return {**datos, "aviso": str(error)}
            return {**datos, "visor": "imagen", "base64": base64.b64encode(bruto).decode("ascii")}
        return datos

    def buscar_pdf(self, nombre, consulta):
        if not isinstance(nombre, str) or Path(nombre).suffix.lower() != ".pdf":
            raise ValueError("Selecciona un archivo PDF.")
        from core.visores_studio import pdf_buscar

        return pdf_buscar(self._bytes(nombre, MAX_VISOR), consulta)

    def texto_pdf(self, nombre):
        from core.visores_studio import pdf_paginas, pdf_texto

        bruto = self._bytes(nombre, MAX_VISOR)
        total = pdf_paginas(bruto)
        revisadas = min(total, 50)
        texto = pdf_texto(bruto, 1, revisadas).decode("utf-8", "replace")
        paginas = [p.strip() for p in texto.split("\f")[:revisadas]]
        return paginas, total

    def gestionar(self, accion, nombre, destino=None, *, texto=""):
        with self.cerrojo, self._padre(nombre) as (fd, hoja):
            if accion == "carpeta":
                os.mkdir(hoja, 0o700, dir_fd=fd)
            elif accion == "crear":
                if Path(hoja).suffix.lower() not in FORMATOS:
                    raise ValueError("Selecciona una extensión de texto compatible.")
                if not isinstance(texto, str) or "\x00" in texto or len(texto.encode("utf-8")) > MAX_ARCHIVO:
                    raise ValueError("Usa texto UTF-8 de hasta 512 KiB.")
                self._publicar_nuevo(fd, hoja, texto.encode("utf-8"), 0o600)
            else:
                tipo, info = self._tipo(fd, hoja)
                if accion == "papelera":
                    with self._directorio() as raiz:
                        try:
                            os.mkdir(_TRASH, 0o700, dir_fd=raiz)
                        except FileExistsError:
                            pass
                        caja = os.open(_TRASH, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=raiz)
                        try:
                            etiqueta = secrets.token_hex(6) + "-" + hoja
                            _renombrar_sin_reemplazar(fd, hoja, caja, etiqueta)
                        finally:
                            os.close(caja)
                    return {"archivo": nombre, "papelera": _TRASH + "/" + etiqueta}
                with self._padre(destino) as (otro, nueva):
                    if accion == "mover":
                        _renombrar_sin_reemplazar(fd, hoja, otro, nueva)
                    elif accion == "copiar":
                        if tipo == "carpeta":
                            if destino.startswith(nombre + "/"):
                                raise ValueError("La copia no puede quedar dentro de la carpeta de origen.")
                            self._copiar_carpeta(fd, hoja, otro, nueva)
                        else:
                            bruto = self._bytes(nombre, MAX_VISOR)
                            self._publicar_nuevo(otro, nueva, bruto, stat.S_IMODE(info.st_mode) & 0o666)
                return {"archivo": destino}
        return {"archivo": nombre}

    def _copiar_carpeta(self, padre, origen, destino, nombre):
        opciones = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        temporal = ".cerebro-" + secrets.token_hex(8)
        os.mkdir(temporal, 0o700, dir_fd=destino)
        contador, restante = 0, 16 * 1024 * 1024

        def copiar(entrada, salida, nivel):
            nonlocal contador, restante
            if nivel > 30:
                raise ValueError("La carpeta supera la profundidad de copia.")
            with os.scandir(entrada) as items:
                for item in items:
                    hoja = item.name
                    self._partes(hoja)
                    contador += 1
                    if contador > 500:
                        raise ValueError("La carpeta supera 500 entradas.")
                    tipo, info = self._tipo(entrada, hoja)
                    if tipo == "carpeta":
                        os.mkdir(hoja, 0o700, dir_fd=salida)
                        fuente = os.open(hoja, opciones, dir_fd=entrada)
                        try:
                            copia = os.open(hoja, opciones, dir_fd=salida)
                            try:
                                copiar(fuente, copia, nivel + 1)
                            finally:
                                os.close(copia)
                        finally:
                            os.close(fuente)
                    else:
                        fd = os.open(hoja, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=entrada)
                        with os.fdopen(fd, "rb") as archivo:
                            actual = os.fstat(archivo.fileno())
                            if not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1:
                                raise PermissionError("La carpeta contiene un enlace o archivo especial.")
                            bruto = archivo.read(restante + 1)
                        restante -= len(bruto)
                        if restante < 0:
                            raise ValueError("La carpeta supera 16 MiB.")
                        self._publicar_nuevo(salida, hoja, bruto, stat.S_IMODE(info.st_mode) & 0o666)

        publicado = False
        try:
            entrada = os.open(origen, opciones, dir_fd=padre)
            try:
                salida = os.open(temporal, opciones, dir_fd=destino)
                try:
                    copiar(entrada, salida, 0)
                finally:
                    os.close(salida)
            finally:
                os.close(entrada)
            _renombrar_sin_reemplazar(destino, temporal, destino, nombre)
            publicado = True
        finally:
            if not publicado:
                shutil.rmtree(temporal, dir_fd=destino)

    @staticmethod
    def _publicar_nuevo(fd, hoja, bruto, modo):
        temporal = ".cerebro-" + secrets.token_hex(8)
        creado = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, modo, dir_fd=fd)
        try:
            with os.fdopen(creado, "wb") as archivo:
                archivo.write(bruto)
                archivo.flush()
                os.fsync(archivo.fileno())
            _renombrar_sin_reemplazar(fd, temporal, fd, hoja)
        finally:
            try:
                os.unlink(temporal, dir_fd=fd)
            except FileNotFoundError:
                pass

    def guardar(self, nombre, texto, original):
        if not isinstance(texto, str) or "\x00" in texto or len(texto.encode("utf-8")) > MAX_ARCHIVO:
            raise ValueError("Guarda texto UTF-8 de hasta 512 KiB.")
        with self.cerrojo, self._padre(nombre) as (fd, hoja):
            if self.leer(nombre) != original:
                raise ValueError("El archivo cambió en disco. Vuelve a abrirlo antes de guardar.")
            _, info = self._tipo(fd, hoja)
            temporal = ".cerebro-" + secrets.token_hex(8)
            creado = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             stat.S_IMODE(info.st_mode) & 0o777, dir_fd=fd)
            try:
                with os.fdopen(creado, "wb") as archivo:
                    archivo.write(texto.encode("utf-8"))
                    archivo.flush()
                    os.fsync(archivo.fileno())
                _, actual = self._tipo(fd, hoja)
                if (actual.st_ino, actual.st_mtime_ns, actual.st_size) != (info.st_ino, info.st_mtime_ns, info.st_size):
                    raise ValueError("El archivo cambió en disco. Vuelve a abrirlo antes de guardar.")
                os.replace(temporal, hoja, src_dir_fd=fd, dst_dir_fd=fd)
            finally:
                try:
                    os.unlink(temporal, dir_fd=fd)
                except FileNotFoundError:
                    pass

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

    def cambiar_propuesta(self, accion, identificador):
        with self.cerrojo:
            cambios = self.aplicadas if accion == "revertir" else self.propuestas
            if not isinstance(identificador, str) or identificador not in cambios:
                raise ValueError("El cambio ya no está disponible en esta sesión.")
            nombre, original, candidato = cambios[identificador]
            if accion == "aplicar":
                self.guardar(nombre, candidato, original)
                if len(self.aplicadas) >= 20:
                    self.aplicadas.pop(next(iter(self.aplicadas)))
                self.aplicadas[identificador] = nombre, original, candidato
            elif accion == "revertir":
                self.guardar(nombre, original, candidato)
            del cambios[identificador]
            return {"archivo": nombre}

    def aplicar(self, identificador):
        return self.cambiar_propuesta("aplicar", identificador)


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
