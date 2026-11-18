"""Planificación conservadora de entrenamiento; no reserva memoria ni crea pesos."""
import config
from core.entorno_portatil import ram_total_bytes


def plan_entrenamiento(tamano="mini", ram_bytes=None, fraccion=0.25):
    if tamano not in config.TAMANOS_NUCLEO:
        raise ValueError("Tamaño desconocido: " + str(tamano))
    if not 0 < fraccion <= 0.5:
        raise ValueError("La fracción de RAM debe estar entre 0 y 0.5.")
    perfil = config.perfil_por_tamano(tamano)
    parametros = config.estimar_parametros(perfil)
    # Estimación conservadora: pesos, gradientes, estados del optimizador
    # y margen de activaciones/implementación NumPy.
    minimo = parametros * 16
    presupuesto = minimo * 3
    ram = ram_total_bytes() if ram_bytes is None else ram_bytes
    cabe = None if not ram or ram <= 0 else presupuesto <= ram * fraccion
    return {"tamano": tamano, "perfil": perfil, "parametros_estimados": parametros,
            "minimo_pesos_gradientes_optimizador_bytes": minimo,
            "presupuesto_estimado_bytes": presupuesto, "ram_detectada_bytes": ram,
            "cabe_en_presupuesto": cabe,
            "advertencia": "Estimación, no garantía: batch/contexto y NumPy pueden consumir más."}
