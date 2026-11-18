# -*- coding: utf-8 -*-
"""
Memoria de Cerebro.

  * Corto plazo: los últimos turnos de la conversación (en RAM). Se usan para
    construir el prompt, así el modelo "ve" lo que se acaba de decir.
  * Largo plazo: datos con nombre (clave -> valor + categoría, importancia y
    fecha) guardados en un JSON. Se escribe de forma atómica (archivo
    temporal + os.replace) para no corromper la memoria si se corta el
    programa a mitad de guardado.
"""

import datetime
import json
import math
import os

import config


def _ahora():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class AdvancedMemoryManager:
    def __init__(self, filepath=None, max_turnos=None):
        self.filepath = filepath or config.MEMORY_FILE
        self.max_turnos = config.MEMORIA_CORTO_PLAZO_TURNOS * 2 if max_turnos is None else max(0, int(max_turnos))
        self.short_term_context = []   # [{"rol": "usuario"|"ia", "contenido": str}]
        self.long_term_memory = {}
        self.cargar_memoria()

    # -- corto plazo ---------------------------------------------------------------

    def agregar_contexto(self, rol, contenido):
        self.short_term_context.append({"rol": rol, "contenido": contenido})
        exceso = len(self.short_term_context) - self.max_turnos
        if exceso > 0:
            del self.short_term_context[:exceso]

    def limpiar_corto_plazo(self):
        self.short_term_context = []

    # -- largo plazo ---------------------------------------------------------------

    def guardar_largo_plazo(self, clave, valor, categoria="general", importancia=1):
        anterior = self.long_term_memory.copy()
        self.long_term_memory[clave] = {
            "valor": valor, "categoria": categoria,
            "importancia": importancia, "fecha": _ahora(),
        }
        # Optimización conservadora: solo duplicados equivalentes al superar
        # el umbral. No elimina hechos únicos ni modifica pesos aprendidos.
        from memory.consolidacion import consolidar
        if len(self.long_term_memory) > 500:
            try:
                consolidar(self.long_term_memory, self.filepath)
                self.persistir()
            except (OSError, ValueError, TypeError):
                self.long_term_memory = anterior
                raise
        else:
            try:
                self.persistir()
            except Exception:
                self.long_term_memory = anterior
                raise

    def recuperar_largo_plazo(self, clave):
        entrada = self.long_term_memory.get(clave)
        return entrada.get("valor") if isinstance(entrada, dict) else None

    def actualizar_largo_plazo(self, clave, nuevo_valor):
        if clave in self.long_term_memory:
            anterior = self.long_term_memory[clave]
            actual = dict(anterior) if isinstance(anterior, dict) else {}
            actual["valor"] = nuevo_valor
            actual["fecha"] = _ahora()
            self.long_term_memory[clave] = actual
            try:
                self.persistir()
            except Exception:
                self.long_term_memory[clave] = anterior
                raise
            return True
        return False

    def eliminar_largo_plazo(self, clave):
        if clave in self.long_term_memory:
            anterior = self.long_term_memory.pop(clave)
            try:
                self.persistir()
            except Exception:
                self.long_term_memory[clave] = anterior
                raise
            return True
        return False

    def buscar(self, texto, limite=5):
        """Recuperación ligera por relevancia léxica. No requiere embeddings.
        Puntúa coincidencias de palabras en clave/valor/categoría y devuelve
        como máximo `limite` entradas, preservando la memoria explícita.
        """
        import re
        palabras = {p for p in re.findall(r"[\wáéíóúñü]+", str(texto).lower()) if len(p) > 2}
        resultados = []
        for clave, entrada in self.long_term_memory.items():
            if not isinstance(entrada, dict):
                continue
            campo = f"{clave} {entrada.get('valor', '')} {entrada.get('categoria', '')}".lower()
            score = sum(1 for p in palabras if p in campo)
            if score:
                try:
                    importancia = float(entrada.get("importancia", 1))
                    if not math.isfinite(importancia):
                        importancia = 1.0
                except (TypeError, ValueError, OverflowError):
                    importancia = 1.0
                score += 0.01 * importancia
                resultados.append((score, str(clave), entrada.get("valor")))
        resultados.sort(reverse=True)
        return {k: v for _, k, v in resultados[:max(0, limite)]}

    def buscar_similar(self, texto, limite=5):
        """Búsqueda TF-IDF de palabras y trigramas, sin modelos externos."""
        from core.semantic_memory import buscar_similares
        claves = [k for k, v in self.long_term_memory.items() if isinstance(v, dict)]
        documentos = [f"{k} {self.long_term_memory[k].get('valor', '')}" for k in claves]
        return {claves[i]: self.long_term_memory[claves[i]].get("valor")
                for i, _ in buscar_similares(texto, documentos, limite)}

    # -- persistencia ---------------------------------------------------------------

    def persistir(self):
        directorio = os.path.dirname(os.path.abspath(self.filepath))
        os.makedirs(directorio, exist_ok=True)
        tmp = self.filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"long_term": self.long_term_memory}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.filepath)

    def cargar_memoria(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    recuerdos = datos.get("long_term", {}) if isinstance(datos, dict) else {}
                    self.long_term_memory = recuerdos if isinstance(recuerdos, dict) else {}
            except (OSError, ValueError):
                self.long_term_memory = {}
