# Arquitectura objetivo de Cerebro

> Documento de diseño. No implica que todas las garantías descritas estén implementadas.

## Rama de integración

La rama `fix/nucleo-validacion-2026` parte de `mejora-nucleo-2026`, que a su vez parte de `main`. El trabajo de `fix/aprendizaje-checkpoint-descartado` es ancestro de `main`; no hay commits exclusivos de esa rama pendientes de incorporar.

**No borrar ni fusionar ramas hasta verificar CI y revisar la solicitud de cambios.**

## Separación de responsabilidades

1. **Interfaz:** `chat.py`, `chat_grafico.py`, `main.py`. Parsean comandos, gestionan sesión y presentan respuestas. No deben implementar cálculos del modelo.
2. **Orquestación:** `agent/`, `core/motores.py`. Deciden si responder con modelo, memoria o herramientas; mantienen trazabilidad del origen.
3. **Modelo:** `core/transformer/optimized_llm.py`, `core/sampling.py`. Forward, backward, pérdida y generación; sin efectos de disco ni red.
4. **Datos y tokenización:** `core/data.py`, `core/tokenizer.py`. Formatos versionados, divisiones train/validación/test sin filtraciones.
5. **Entrenamiento:** `trainer_engine.py`, `core/optim.py`, `train.py`. Plan de pasos global, reproducibilidad, clipping y evaluación.
6. **Persistencia:** `core/checkpoint.py`, `memory/`. Escrituras atómicas, compatibilidad y validación de metadatos.
7. **Evaluación:** `evaluate.py`, `benchmarks/`, `tests/`. Métricas de pérdida, gradientes, respuestas y pruebas de regresión.

## Contratos y límites

- El modelo devuelve logits o tokens; la interfaz decide cómo mostrarlos.
- El entrenamiento solo guarda el mejor modelo tras evaluar datos no vistos.
- Reanudar desde checkpoint debe conservar optimizador, generadores aleatorios y calendario de LR.
- La memoria recuperada no debe confundirse con parámetros aprendidos por el Transformer.
- Las herramientas locales deben tener permisos y límites explícitos.
- Los datos de prueba no deben alimentar entrenamiento, tokenizer ni selección de hiperparámetros.

## Plan verificable

### Fase 1: fiabilidad
- [x] Consolidar historial de ramas en una rama de integración.
- [x] Añadir validaciones básicas de datos y configuración y pruebas de regresión.
- [ ] Ejecutar pytest y registrar resultados.
- [ ] Probar diferencias finitas para atención, LayerNorm, MLP y embeddings.
- [ ] Probar checkpoint guardar/cargar/reanudar con estados idénticos.

### Fase 2: aprendizaje
- [ ] Definir horizonte global de LR persistente al reanudar.
- [ ] Medir pérdida y bits por byte en conjuntos separados.
- [ ] Añadir prueba de sobreajuste de un minibatch diminuto.
- [ ] Evaluar generalización sin coincidencias exactas con el entrenamiento.

### Fase 3: experiencia
- [ ] Establecer política de selección modelo/memoria/herramientas.
- [ ] Evitar que respuestas de repaso pasen por generación libre.
- [ ] Crear conjunto de preguntas y salidas esperadas, con métricas reproducibles.

## Criterios para integrar en main

CI verde; ninguna regresión crítica; checkpoint restaurable; mejora o estabilidad de métricas de validación; y revisión humana del diff. No afirmar que el modelo «aprende mejor» solo por aprobar tests.
