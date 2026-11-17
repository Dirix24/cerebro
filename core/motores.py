"""Registro de motores ya existentes: no implica pesos entrenados."""
import importlib.util


def disponibles():
    return [
        {"nombre": "neuronal_numpy", "tipo": "generacion", "integrado": True,
         "disponible": importlib.util.find_spec("numpy") is not None},
        {"nombre": "neuronal_torch_clasico", "tipo": "generacion_opcional",
         "integrado": True, "disponible": importlib.util.find_spec("torch") is not None},
        {"nombre": "neuronal_torch_avanzado", "tipo": "generacion_opcional",
         "integrado": True, "disponible": importlib.util.find_spec("torch") is not None},
        {"nombre": "memoria_semantica", "tipo": "recuperacion", "integrado": True,
         "disponible": True},
        {"nombre": "busqueda_fts5", "tipo": "recuperacion", "integrado": True,
         "disponible": True},
        {"nombre": "calculadora", "tipo": "razonamiento_determinista",
         "integrado": True, "disponible": True},
        {"nombre": "repaso_espaciado", "tipo": "aprendizaje", "integrado": True,
         "disponible": True},
        {"nombre": "autoevaluacion", "tipo": "evaluacion", "integrado": True,
         "disponible": True},
    ]
