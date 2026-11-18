"""Identidad histórica pública y perfiles privados por portador.

No presupone conciencia, propiedad ni muerte de nadie. El creador se configura
explícitamente; las memorias privadas nunca se incluyen en el legado público.
"""
import hashlib
import json
import re
from pathlib import Path
import config

_NOMBRE = re.compile(r"^[\w áéíóúÁÉÍÓÚñÑ.-]{2,80}$", re.UNICODE)


def _base(raiz=None):
    return Path(raiz or config.CEREBRO_HOME) / "memory" / "legado"


def _escribir_nuevo(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def configurar_creador(nombre, raiz=None):
    if not isinstance(nombre, str) or not _NOMBRE.fullmatch(nombre):
        raise ValueError("Nombre de creador inválido")
    archivo = _base(raiz) / "origen.json"
    _escribir_nuevo(archivo, {"version": 1, "creador": nombre.strip(),
                             "descripcion": "Identidad histórica declarada por el creador",
                             "verificacion": "declarada_no_autenticada"})
    return leer_origen(raiz)


def leer_origen(raiz=None):
    archivo = _base(raiz) / "origen.json"
    if not archivo.is_file():
        return {"creador": None, "verificacion": "sin_configurar"}
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    return {"creador": datos["creador"], "verificacion": datos["verificacion"]}


def exportar_legado_publico(destino, raiz=None):
    """Exporta solo la identidad pública a un archivo elegido, sin secretos."""
    origen = leer_origen(raiz)
    if not origen["creador"]:
        raise ValueError("Primero configura la identidad del creador")
    carga = {"formato": "cerebro-legado-publico-v1", "origen": origen}
    bytes_carga = json.dumps(carga, sort_keys=True, ensure_ascii=False).encode("utf-8")
    paquete = {"contenido": carga, "sha256": hashlib.sha256(bytes_carga).hexdigest()}
    ruta = Path(destino)
    _escribir_nuevo(ruta, paquete)
    return {"ruta": str(ruta), "solo_datos_publicos": True}


def examinar_legado(ruta):
    """Valida integridad sin instalar ni importar memoria automáticamente."""
    archivo = Path(ruta)
    if archivo.stat().st_size > 100_000:
        raise ValueError("Paquete demasiado grande")
    paquete = json.loads(archivo.read_text(encoding="utf-8"))
    carga = paquete["contenido"]
    bytes_carga = json.dumps(carga, sort_keys=True, ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(bytes_carga).hexdigest() != paquete["sha256"]:
        raise ValueError("Integridad del legado no válida")
    if carga["formato"] != "cerebro-legado-publico-v1":
        raise ValueError("Formato desconocido")
    return {"origen": carga["origen"], "integridad": "sha256_correcto",
            "autenticidad": "no_verificada", "importado": False}
