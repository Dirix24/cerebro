"""Recordatorios persistentes con avisos mientras está activo el núcleo de escritorio."""
from contextlib import contextmanager
import fcntl
import json
from tempfile import NamedTemporaryFile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import config


def _ruta(ruta=None):
    return Path(ruta or (Path(config.CEREBRO_HOME) / "data" / "recordatorios.json"))


def listar(ruta=None, ahora=None):
    archivo = _ruta(ruta)
    if not archivo.is_file():
        return []
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    if not isinstance(datos, list):
        raise ValueError("Formato de recordatorios inválido")
    return datos


@contextmanager
def _bloquear(archivo):
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with archivo.with_suffix(".lock").open("a") as cerrojo:
        fcntl.flock(cerrojo, fcntl.LOCK_EX)
        yield


def _guardar(archivo, datos):
    temporal = None
    try:
        with NamedTemporaryFile(mode="w", dir=archivo.parent, encoding="utf-8", delete=False) as salida:
            temporal = Path(salida.name)
            json.dump(datos, salida, ensure_ascii=False, indent=2)
        temporal.replace(archivo)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def crear(fecha_iso, texto, ruta=None):
    if not isinstance(texto, str) or not 1 <= len(texto.strip()) <= 500:
        raise ValueError("Texto de 1 a 500 caracteres requerido")
    try:
        fecha = datetime.fromisoformat(fecha_iso)
    except ValueError as exc:
        raise ValueError("Usa fecha ISO con zona horaria: 2027-01-20T10:00:00+01:00") from exc
    if fecha.tzinfo is None or fecha.utcoffset() is None:
        raise ValueError("Incluye la zona horaria, por ejemplo +01:00")
    if fecha <= datetime.now(timezone.utc):
        raise ValueError("La fecha debe ser futura")
    archivo = _ruta(ruta)
    with _bloquear(archivo):
        datos = listar(archivo)
        if len(datos) >= 1000:
            raise ValueError("Límite de 1000 recordatorios")
        registro = {"id": uuid4().hex[:12], "fecha": fecha.isoformat(),
                    "texto": texto.strip(), "completado": False}
        datos.append(registro)
        _guardar(archivo, datos)
    return registro


def pendientes(ruta=None, ahora=None):
    instante = ahora or datetime.now(timezone.utc)
    return [x for x in listar(ruta) if not x["completado"]
            and datetime.fromisoformat(x["fecha"]) <= instante]


def interpretar(entrada, ahora=None):
    """Devuelve fecha ISO y texto si se reconocen los dos componentes."""
    import re
    from unicodedata import normalize
    from datetime import timedelta
    from core.documentos_usuario import _normalizar

    original = normalize("NFC", entrada.strip())
    orden = _normalizar(original)
    peticion = re.match(r"(?:(?:cerebro)[, ]+)?(?:recuerdame|avisame)(?: que)?\s+", orden)
    if not peticion:
        return None
    numeros = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
               "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "quince": 15, "treinta": 30}
    palabras = "|".join(numeros)
    relativo = re.search(rf"\b(?:dentro de|en) (\d{{1,4}}|{palabras}) (minutos?|horas?)\b", orden)
    dias = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
    calendario = re.search(rf"\b(manana|esta tarde|(?:el )?proximo ({'|'.join(dias)}))"
                           rf"(?: a (?:la|las) (\d{{1,2}}|{palabras})(?::(\d{{2}}))?)?\b", orden)
    instante = ahora or datetime.now().astimezone()
    if relativo:
        cantidad = int(relativo[1]) if relativo[1].isdecimal() else numeros[relativo[1]]
        segundos = cantidad * (3600 if relativo[2].startswith("hora") else 60)
        fecha = (instante.astimezone(timezone.utc) + timedelta(seconds=segundos)).astimezone(
            ahora.tzinfo if ahora else None)
        marca = relativo
    elif calendario:
        horas = calendario[3]
        hora = (int(horas) if horas.isdecimal() else numeros[horas]) if horas else (17 if calendario[1] == "esta tarde" else 9)
        retraso = ((dias.index(calendario[2]) - instante.weekday()) % 7 or 7) if calendario[2] else int(calendario[1] == "manana")
        fecha = (instante.replace(tzinfo=None) + timedelta(days=retraso)).replace(hour=hora,
                      minute=int(calendario[4] or 0), second=0, microsecond=0)
        fecha = fecha.replace(tzinfo=ahora.tzinfo) if ahora else fecha.astimezone()
        marca = calendario
    else:
        return None
    texto = (original[peticion.end():marca.start()] + " " + original[marca.end():]).strip(" ,.!?").strip()
    texto = re.sub(r"^que\s+", "", texto, flags=re.I)
    if not texto:
        return None
    if fecha <= instante:
        raise ValueError("La fecha resultante debe ser futura.")
    return fecha.isoformat(), texto


def cancelar(identificador, ruta=None):
    archivo = _ruta(ruta)
    with _bloquear(archivo):
        datos = listar(archivo)
        for item in datos:
            if item["id"] == identificador and not item["completado"]:
                item["completado"] = True
                item["cancelado"] = True
                _guardar(archivo, datos)
                return True
    return False


def notificar_locales(ruta=None):
    from html import escape
    from shutil import which
    from subprocess import DEVNULL, SubprocessError, run

    programa = which("notify-send")
    if not programa:
        return 0
    archivo = _ruta(ruta)
    if not archivo.is_file():
        return 0
    with _bloquear(archivo):
        datos = listar(archivo)
        instante = datetime.now(timezone.utc)
        for item in datos:
            if item["completado"] or datetime.fromisoformat(item["fecha"]) > instante:
                continue
            try:
                resultado = run([programa, "--", "Cerebro · Recordatorio", escape(item["texto"])],
                                timeout=1, stdout=DEVNULL, stderr=DEVNULL)
            except (OSError, SubprocessError):
                return 0
            if resultado.returncode:
                return 0
            item["completado"] = True
            item["notificado"] = True
            _guardar(archivo, datos)
            return 1
    return 0
