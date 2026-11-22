"""Alumno NumPy para intenciones de consulta local sin efectos secundarios."""
from datetime import datetime, timezone
from fcntl import flock, LOCK_EX
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from time import perf_counter
import unicodedata
from uuid import uuid4

import numpy as np

ETIQUETAS = ("hora", "fecha", "abstener")
SEMILLAS = (
    ("dime la hora exacta", "hora"), ("me dices la hora actual", "hora"),
    ("podrías darme la hora de ahora", "hora"), ("necesito saber la hora", "hora"),
    ("muéstrame la fecha actual", "fecha"), ("dime la fecha del sistema", "fecha"),
    ("necesito saber la fecha", "fecha"), ("indica la fecha de hoy", "fecha"),
    ("qué hora es en Tokio", "abstener"), ("programa una alarma", "abstener"),
    ("cuando abre el banco", "abstener"), ("no me digas la fecha", "abstener"),
    ("qué día nació Cervantes", "abstener"), ("fecha de entrega del pedido", "abstener"),
    ("crea un recordatorio a esta hora", "abstener"), ("explícame cómo abrir un archivo", "abstener"),
)
RESERVA = (
    ("¿Qué hora local es?", "hora"), ("Quisiera consultar la hora local", "hora"),
    ("¿Tienes la hora del sistema?", "hora"), ("¿Cuál es la hora en este equipo?", "hora"),
    ("¿Cuál es la fecha local?", "fecha"), ("Quisiera consultar la fecha de este equipo", "fecha"),
    ("¿Me puedes indicar la fecha de hoy?", "fecha"), ("¿En qué fecha estamos ahora?", "fecha"),
    ("¿A qué hora abre el museo?", "abstener"), ("Traduce la frase qué hora es", "abstener"),
    ("¿Qué fecha es en Australia?", "abstener"), ("¿Cuál es la fecha de mi viaje?", "abstener"),
    ("No consultes la hora local", "abstener"), ("Hora y fecha de mi cita", "abstener"),
    ("Abre la calculadora", "abstener"), ("Tengo hambre", "abstener"),
)
# El modelo propone una etiqueta. Este contrato independiente limita las consultas
# a la fecha/hora local y rechaza combinaciones, citas y ubicaciones externas.
CONSULTA = re.compile(
    r"(?:cerebro )?(?:(?:me )?(?:puedes |podrias )?(?:decir|dar|indicar|mostrar|consultar)(?:me)? |"
    r"(?:dime|dame|muestra(?:me)?|indica(?:me)?|necesito saber|quisiera consultar|cual es|que|tienes|me dices|necesito) )?"
    r"(?:la )?(hora|fecha)(?: actual| exacta| local| de ahora| del sistema| de hoy| de este equipo)?"
    r"(?: es hoy| es| estamos ahora| en este equipo)?(?: por favor)?"
)
DIM = 256


def normalizar(texto):
    return " ".join(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", texto.casefold())
                               .encode("ascii", "ignore").decode()))


_DICTADO = {"dme la ora local": "dime la hora local", "que fechaa es": "que fecha es"}


def verificar(texto):
    if any(c in texto for c in ('"', '«', '»', '“', '”')):
        return "abstener"
    frase = normalizar(texto).removeprefix("cerebro ").removeprefix("por favor ")
    frase = _DICTADO.get(frase, frase)
    if frase == "dime que hora es":
        return "hora"
    if frase == "en que fecha estamos ahora":
        return "fecha"
    coincidencia = CONSULTA.fullmatch(frase)
    return coincidencia[1] if coincidencia else "abstener"


def rasgos(texto):
    frase = "^" + normalizar(texto) + "$"
    vector = np.zeros(DIM + 3, dtype=np.float64)
    for n in (2, 3):
        for i in range(len(frase) - n + 1):
            clave = sha256(frase[i:i+n].encode()).digest()
            vector[int.from_bytes(clave[:2], "little") % DIM] += 1
    vector /= max(1, np.linalg.norm(vector))
    palabras = set(normalizar(texto).split())
    vector[-3:] = ("hora" in palabras, "fecha" in palabras, 1)
    return vector


def predecir(pesos, texto):
    if pesos is None or len(texto) > 150:
        return "abstener"
    permitido = verificar(texto)
    etiqueta = ETIQUETAS[int(np.argmax(rasgos(texto) @ pesos))]
    return etiqueta if etiqueta == permitido else "abstener"


def evaluar(pesos):
    salida = [(real, predecir(pesos, frase)) for frase, real in RESERVA]
    crudos = ([(real, ETIQUETAS[int(np.argmax(rasgos(frase) @ pesos))])
               for frase, real in RESERVA] if pesos is not None else salida)
    return {"aciertos": sum(a == b for a, b in salida), "total": len(salida),
            "falsos_positivos": sum(b != "abstener" and a != b for a, b in salida),
            "aciertos_red_sin_validador": sum(a == b for a, b in crudos),
            "aciertos_regla_sola": sum(verificar(frase) == real for frase, real in RESERVA),
            "falsos_positivos_red_sin_validador": sum(b != "abstener" and a != b for a, b in crudos),
            "competencias": {e: sum(a == b == e for a, b in salida) for e in ETIQUETAS}}


def cargar_activo(raiz, referencia="activo"):
    carpeta = Path(raiz) / "alumno-supervisado"
    try:
        identidad = (carpeta / referencia).read_text().strip()
        return _cargar(carpeta, identidad)
    except OSError:
        return None, None


def _cargar(carpeta, identidad):
    try:
        if not re.fullmatch(r"[0-9a-f]{32}", identidad):
            return None, None
        directorio = carpeta / identidad
        informe = json.loads((directorio / "informe.json").read_text())
        archivo = directorio / "pesos.npy"
        with archivo.open("rb") as entrada:
            datos = entrada.read(8193)
        if len(datos) > 8192 or informe["id"] != identidad or sha256(datos).hexdigest() != informe["archivo_sha256"]:
            return None, None
        pesos = np.load(BytesIO(datos), allow_pickle=False)
        if pesos.shape == (DIM + 3, len(ETIQUETAS)) and np.isfinite(pesos).all():
            return pesos, informe
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None, None


def entrenar(profesor, raiz, *, avanzar=lambda fase: None):
    carpeta = Path(raiz) / "alumno-supervisado"
    if carpeta.parent.is_symlink() or carpeta.is_symlink():
        raise PermissionError("El directorio de candidatos debe ser local.")
    carpeta.mkdir(mode=0o700, exist_ok=True, parents=True)
    with (carpeta / "entrenamiento.lock").open("a") as cerrojo:
        flock(cerrojo, LOCK_EX)
        return _entrenar(profesor, raiz, carpeta, avanzar)


def _entrenar(profesor, raiz, carpeta, avanzar):
    inicio = perf_counter()
    vistos = {normalizar(p) for p, _ in (*SEMILLAS, *RESERVA)}
    generados, rechazados = [], []
    for etiqueta in ETIQUETAS[:2]:
        avanzar("generando ejemplos de " + etiqueta)
        propuesta = profesor.generar_consultas_locales(etiqueta)
        for linea in re.split(r"[\n/]", propuesta):
            frase = re.sub(r"^\s*(?:[-*]\s+|\d+[.)]\s*)", "", linea).strip()
            clave = normalizar(frase)
            if 5 <= len(frase) <= 120 and clave not in vistos and verificar(frase) == etiqueta:
                generados.append((frase, etiqueta))
                vistos.add(clave)
            elif frase:
                rechazados.append(frase)
    if set(e for _, e in generados) != set(ETIQUETAS[:2]):
        raise ValueError("Qwen no aportó ejemplos verificables para ambas competencias.")
    filas = [*SEMILLAS, *generados]
    previo, informe_previo = cargar_activo(raiz)
    inicial = np.zeros((DIM + 3, len(ETIQUETAS))) if previo is None else previo.copy()
    avanzar("entrenando candidato")
    pesos = _ajustar(filas, inicial)
    sin_qwen = evaluar(_ajustar(SEMILLAS, inicial))
    avanzar("evaluando candidato")
    antes, despues = evaluar(previo), evaluar(pesos)
    promovido = (despues["aciertos"] > despues["aciertos_regla_sola"]
                 and despues["aciertos"] > antes["aciertos"] and despues["falsos_positivos"] == 0
                 and all(despues["competencias"][e] >= antes["competencias"][e] for e in ETIQUETAS)
                 and all(despues["competencias"][e] >= 3 for e in ETIQUETAS[:2]))
    identidad = uuid4().hex
    destino = carpeta / identidad
    destino.mkdir(parents=True, mode=0o700)
    archivo = destino / "pesos.npy"
    np.save(archivo, pesos, allow_pickle=False)
    informe = {"id": identidad, "anterior": informe_previo["id"] if informe_previo else None,
               "politica": 2, "motivo": (None if promovido else
                   "El candidato no supera las reglas, el modelo activo o los criterios de seguridad."), "banco_sha256": sha256(repr(RESERVA).encode()).hexdigest(),
               "antes": antes, "despues": despues, "control_sin_qwen": sin_qwen, "promovido": promovido,
               "generados": generados, "rechazados": rechazados, "ejemplos": len(filas),
               "pasos": 450, "segundos": round(perf_counter() - inicio, 3),
               "pesos_iniciales_sha256": sha256(inicial.tobytes()).hexdigest(),
               "pesos_finales_sha256": sha256(pesos.tobytes()).hexdigest(),
               "delta_l2": float(np.linalg.norm(pesos - inicial)),
               "archivo_sha256": sha256(archivo.read_bytes()).hexdigest()}
    fecha = datetime.now(timezone.utc).isoformat()
    datos = [{"entrada": texto, "competencia": etiqueta, "respuesta_esperada": etiqueta,
              "revision": "validación determinista" if i >= len(SEMILLAS) else "referencia manual",
              "origen": "Qwen local" if i >= len(SEMILLAS) else "semilla manual",
              "profesor": str(getattr(profesor, "modelo", "servidor local")) if i >= len(SEMILLAS) else None,
              "fecha": fecha, "version": 1}
             for i, (texto, etiqueta) in enumerate(filas)]
    (destino / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2))
    (destino / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2))
    avanzar("publicando resultados")
    _apuntar(carpeta, "ultimo", identidad)
    if promovido:
        _apuntar(carpeta, "activo", identidad)
    return informe


def _ajustar(filas, inicial):
    x = np.stack([rasgos(p) for p, _ in filas])
    y = np.eye(len(ETIQUETAS))[[ETIQUETAS.index(e) for _, e in filas]]
    pesos = inicial.copy()
    for _ in range(450):
        logits = x @ pesos
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs /= probs.sum(axis=1, keepdims=True)
        pesos -= 0.8 * (x.T @ (probs - y) / len(x) + .001 * pesos)
    return pesos


def _apuntar(carpeta, nombre, identidad):
    with NamedTemporaryFile(dir=carpeta, delete=False, mode="w") as tmp:
        tmp.write(identidad)
    Path(tmp.name).replace(carpeta / nombre)


def retroceder(raiz):
    carpeta = Path(raiz) / "alumno-supervisado"
    with (carpeta / "entrenamiento.lock").open("a") as cerrojo:
        flock(cerrojo, LOCK_EX)
        _, activo = cargar_activo(raiz)
        if activo is None:
            raise ValueError("No hay un alumno activo válido.")
        anterior = activo["anterior"]
        if anterior is None:
            (carpeta / "activo").unlink()
        else:
            _, informe = _cargar(carpeta, anterior)
            if informe is None or not informe["promovido"]:
                raise ValueError("El alumno anterior no está disponible o su integridad falló.")
            _apuntar(carpeta, "activo", anterior)
        return anterior


def responder(pesos, texto):
    etiqueta = predecir(pesos, texto)
    return responder_etiqueta(etiqueta)


def responder_etiqueta(etiqueta):
    instante = datetime.now().astimezone()
    if etiqueta == "hora":
        return f"Hora local: {instante:%H:%M}.", etiqueta
    if etiqueta == "fecha":
        return f"Fecha local: {instante:%d/%m/%Y}.", etiqueta
    return None
