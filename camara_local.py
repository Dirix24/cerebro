"""Captura puntual de cámara con autorización explícita.

OpenCV realiza detección geométrica básica, NO reconocimiento semántico de
objetos ni inferencia con modelos de terceros. Sin streaming ni red.
"""
import argparse
import json
from pathlib import Path


def inspeccionar_camara(indice=0, *, confirmar=False, salida=None):
    if not confirmar:
        raise PermissionError("La cámara requiere --confirmar en cada captura")
    if not 0 <= indice <= 16:
        raise ValueError("Índice de cámara fuera de rango")
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Instala OpenCV opcional: pip install opencv-python") from exc
    camara = cv2.VideoCapture(indice)
    try:
        if not camara.isOpened():
            raise RuntimeError("No se pudo abrir la cámara")
        correcto, fotograma = camara.read()
        if not correcto or fotograma is None:
            raise RuntimeError("No se pudo capturar la imagen")
    finally:
        camara.release()
    gris = cv2.cvtColor(fotograma, cv2.COLOR_BGR2GRAY)
    bordes = cv2.Canny(gris, 80, 160)
    contornos, _ = cv2.findContours(bordes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    alto, ancho = gris.shape
    resultado = {"ancho": ancho, "alto": alto, "contornos_aproximados": len(contornos),
                 "reconocimiento_objetos": False, "modelo_ia_externo": False,
                 "imagen_guardada": False}
    if salida is not None:
        destino = Path(salida).expanduser()
        if destino.suffix.lower() != ".png":
            raise ValueError("La imagen de salida debe ser .png")
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            raise FileExistsError("No se sobrescriben imágenes existentes")
        if not cv2.imwrite(str(destino), fotograma):
            raise RuntimeError("No se pudo guardar la imagen")
        resultado["imagen_guardada"] = True
        resultado["ruta"] = str(destino)
    return resultado


def main():
    ap = argparse.ArgumentParser(description="Captura puntual local autorizada")
    ap.add_argument("--confirmar", action="store_true")
    ap.add_argument("--indice", type=int, default=0)
    ap.add_argument("--guardar", default=None)
    args = ap.parse_args()
    print(json.dumps(inspeccionar_camara(args.indice, confirmar=args.confirmar,
                                         salida=args.guardar), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
