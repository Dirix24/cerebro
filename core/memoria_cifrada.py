"""Copia cifrada de memoria privada para USB; nunca descifra sin clave.

Usa scrypt + AES-256-GCM de la biblioteca criptográfica (no modelos de IA).
No ejecuta contenido del respaldo. La restauración exige confirmación y
no sobrescribe una memoria existente.
"""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path

import config

FORMATO = "cerebro-memoria-privada-v1"
MAX_BYTES = 5_000_000


def _crypto():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        from cryptography.exceptions import InvalidTag
    except ImportError as exc:
        raise RuntimeError("Instala cryptography: python -m pip install cryptography") from exc
    return AESGCM, Scrypt, InvalidTag


def _clave(password, sal, Scrypt):
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")
    return Scrypt(salt=sal, length=32, n=2**15, r=8, p=1).derive(password.encode("utf-8"))


def _b64(data):
    return base64.b64encode(data).decode("ascii")


def _unb64(data):
    return base64.b64decode(data, validate=True)


def _validar_memoria(data):
    if not isinstance(data, dict) or not isinstance(data.get("long_term"), dict):
        raise ValueError("Memoria inválida")
    if len(data["long_term"]) > 10000:
        raise ValueError("Demasiadas entradas")
    for k, v in data["long_term"].items():
        if not isinstance(k, str) or len(k) > 200 or not isinstance(v, dict):
            raise ValueError("Entrada de memoria inválida")
        if not isinstance(v.get("valor"), (str, int, float, bool, type(None))):
            raise ValueError("Valor de memoria inválido")
    return data


def exportar(destino, password, origen=None):
    AESGCM, Scrypt, _ = _crypto()
    origen = Path(origen or config.MEMORY_FILE)
    if origen.stat().st_size > MAX_BYTES:
        raise ValueError("Memoria demasiado grande")
    datos = _validar_memoria(json.loads(origen.read_text(encoding="utf-8")))
    texto = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    if len(texto) > MAX_BYTES:
        raise ValueError("Memoria demasiado grande")
    sal, nonce = os.urandom(16), os.urandom(12)
    cifrado = AESGCM(_clave(password, sal, Scrypt)).encrypt(nonce, texto, FORMATO.encode())
    paquete = {"formato": FORMATO, "kdf": "scrypt-n32768-r8-p1",
               "cifrado": "aes-256-gcm", "sal": _b64(sal),
               "nonce": _b64(nonce), "datos": _b64(cifrado)}
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8") as f:
        json.dump(paquete, f)
    return {"ruta": str(ruta), "cifrado": True, "entradas": len(datos["long_term"])}


def _descifrar(archivo, password):
    AESGCM, Scrypt, InvalidTag = _crypto()
    ruta = Path(archivo)
    if ruta.stat().st_size > MAX_BYTES * 2:
        raise ValueError("Respaldo demasiado grande")
    paquete = json.loads(ruta.read_text(encoding="utf-8"))
    if (paquete.get("formato") != FORMATO or paquete.get("kdf") != "scrypt-n32768-r8-p1"
            or paquete.get("cifrado") != "aes-256-gcm"):
        raise ValueError("Formato de respaldo no compatible")
    sal, nonce, cifrado = map(_unb64, (paquete["sal"], paquete["nonce"], paquete["datos"]))
    if len(sal) != 16 or len(nonce) != 12 or len(cifrado) > MAX_BYTES + 16:
        raise ValueError("Respaldo inválido")
    try:
        texto = AESGCM(_clave(password, sal, Scrypt)).decrypt(nonce, cifrado, FORMATO.encode())
    except InvalidTag as exc:
        raise ValueError("Contraseña incorrecta o respaldo alterado") from exc
    return _validar_memoria(json.loads(texto.decode("utf-8")))


def examinar(archivo, password):
    datos = _descifrar(archivo, password)
    return {"entradas": len(datos["long_term"]), "restaurado": False,
            "nota": "No se muestran recuerdos privados en el resumen"}


def restaurar(archivo, password, *, confirmar=False, destino=None):
    if not confirmar:
        raise PermissionError("Restauración requiere confirmación explícita")
    datos = _descifrar(archivo, password)
    ruta = Path(destino or config.MEMORY_FILE)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Sin sobrescritura: protege la memoria de un nuevo portador.
    with ruta.open("x", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    return {"ruta": str(ruta), "restaurado": True, "entradas": len(datos["long_term"])}


def main():
    ap = argparse.ArgumentParser(description="Respaldo cifrado de memoria privada Cerebro")
    sub = ap.add_subparsers(dest="accion", required=True)
    for nombre in ("exportar", "examinar", "restaurar"):
        p = sub.add_parser(nombre)
        p.add_argument("archivo")
        if nombre == "restaurar":
            p.add_argument("--confirmar", action="store_true")
            p.add_argument("--destino", default=None)
        if nombre == "exportar":
            p.add_argument("--origen", default=None)
    args = ap.parse_args()
    password = getpass.getpass("Contraseña de memoria (no se guarda): ")
    if args.accion == "exportar":
        resultado = exportar(args.archivo, password, origen=args.origen)
    elif args.accion == "examinar":
        resultado = examinar(args.archivo, password)
    else:
        resultado = restaurar(args.archivo, password, confirmar=args.confirmar,
                             destino=args.destino)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
