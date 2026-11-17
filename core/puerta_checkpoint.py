"""Reglas transparentes para aceptar o revertir pesos tras validación."""
import math


def aceptar_checkpoint(bpb_previo, bpb_nuevo, tolerancia=0.02):
    """Menor bpb es mejor; rechazar valores no finitos y regresiones >2%."""
    if bpb_nuevo is None or not math.isfinite(bpb_nuevo) or bpb_nuevo < 0:
        return False
    if bpb_previo is None:
        return True
    if not math.isfinite(bpb_previo) or bpb_previo < 0:
        return False
    return bpb_nuevo <= bpb_previo * (1 + tolerancia)
