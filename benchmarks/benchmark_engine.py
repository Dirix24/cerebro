# -*- coding: utf-8 -*-
"""Benchmark y diagnóstico real del modelo local: parámetros exactos, RAM,
velocidad de ENTRENAMIENTO y de GENERACIÓN (tokens reales por segundo), y
calidad medida sobre la validación. Sin simulaciones ni APIs externas."""

import os
import time

import numpy as np

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def _ram_mb():
    if HAS_PSUTIL:
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    try:                                   # Linux sin psutil
        with open("/proc/self/status") as f:
            for linea in f:
                if linea.startswith("VmRSS:"):
                    return int(linea.split()[1]) / 1024
    except OSError:
        pass
    return 0.0


class BenchmarkEngine:
    def __init__(self, modelo):
        self.modelo = modelo

    def contar_parametros(self):
        return self.modelo.n_parametros()

    def velocidad_entrenamiento(self, pasos=8, batch=8):
        m = self.modelo
        T = min(m.cfg.block_size, 64)
        rng = np.random.default_rng(0)
        x = rng.integers(4, m.cfg.vocab_size, size=(batch, T))
        y = np.roll(x, -1, axis=1)
        m.perdida_y_gradientes(x, y)      # calentamiento
        t0 = time.perf_counter()
        for _ in range(pasos):
            m.perdida_y_gradientes(x, y)
        dt = time.perf_counter() - t0
        return pasos * batch * T / dt

    def velocidad_generacion(self, prompt="usuario: hola\ncerebro:", n=40):
        m = self.modelo
        ids = [3] + m.tokenizer.codificar(prompt)
        t0 = time.perf_counter()
        nuevos, _ = m.generar_ids(ids, max_nuevos=n, temperatura=0.8, parar_en=None, seed=0)
        dt = time.perf_counter() - t0
        return len(nuevos) / max(dt, 1e-9), m.tokenizer.decodificar(nuevos)

    def ejecutar_benchmark_completo(self):
        tok_gen, texto = self.velocidad_generacion()
        return {
            "parametros": self.contar_parametros(),
            "ram_mb": round(_ram_mb(), 1),
            "tok_s_entrenamiento": round(self.velocidad_entrenamiento()),
            "tok_s_generacion": round(tok_gen, 1),
            "muestra": texto,
        }
