"""Registro único de capacidades de Cerebro. No activa dispositivos ni redes."""
from importlib.util import find_spec

CAPACIDADES = {
    "nucleo": ("Transformer NumPy local", "numpy"),
    "proyectos": ("Creación de proyectos Python", None),
    "analisis_codigo": ("Análisis estático de Python", None),
    "ciberseguridad": ("Laboratorio defensivo local", None),
    "documentos": ("Creación de PDF", "reportlab"),
    "camara": ("Cámara: captura y visión propia aún no implementadas; apagada", "cv2"),
    "recordatorios": ("Recordatorios locales persistentes; consulta al abrir chat", None),
    "github": ("Consulta explícita de repositorios públicos, solo lectura", None),
    "voz": ("Voz: integración futura, apagada por defecto", None),
    "internet": ("Internet: sin acceso automático", None),
}


def capacidades():
    resultado = {}
    for clave, (descripcion, dependencia) in CAPACIDADES.items():
        instalado = dependencia is None or find_spec(dependencia) is not None
        resultado[clave] = {
            "descripcion": descripcion,
            "dependencia_disponible": instalado,
            "activo": clave in {"nucleo", "proyectos", "analisis_codigo", "ciberseguridad", "recordatorios", "github"}
            and instalado,
        }
    return resultado
