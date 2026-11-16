# Cerebro 🧠

**Inteligencia artificial local y desarrollada desde cero.** Cerebro utiliza un Transformer propio entrenado con datos del proyecto. No utiliza Ollama, ChatGPT, servicios de inferencia ni modelos preentrenados de terceros. El motor original está implementado en NumPy; existe además un Transformer propio opcional implementado con PyTorch (biblioteca de cálculo, **no** un modelo externo).

> **Estado:** proyecto experimental. El modelo original es pequeño; disponer de Internet, memoria y perfiles grandes no equivale a una IA con conocimiento general. Las nuevas funciones automáticas aún necesitan pruebas de extremo a extremo en el equipo de destino.

## Inicio rápido: un solo comando

Requisitos: Python 3, NumPy instalado y conexión a Internet **solo** si quieres recopilar artículos. Desde la carpeta del proyecto:

```bash
python3 -m pip install -r requirements.txt
python3 cerebro.py todo
```

**`python3 cerebro.py todo` activa en una sesión:**
1. Reconstruye el índice de búsqueda local SQLite FTS5.
2. Abre el chat original de Cerebro, con sus herramientas y memoria.
3. Inicia en segundo plano el recopilador diario de Wikipedia en español y su entrenamiento NumPy, con evaluación y recuperación de checkpoints.

**Para detenerlo:** escribe `/salir` en el chat. El lanzador intenta detener el proceso de aprendizaje. **No es un servicio permanente:** no arranca con el sistema operativo y la terminal debe seguir abierta. El primer ciclo puede empezar inmediatamente. El entrenamiento consume CPU y puede afectar a la fluidez del chat; el chat ya abierto no recarga automáticamente los pesos nuevos. **Haz copia de `checkpoints/` antes de activar el aprendizaje automático.** No ejecutes varias instancias de `todo` a la vez.

La memoria de conocimientos se guarda localmente. El chat consulta automáticamente **solo preguntas exactas** y muestra la fuente; si existen respuestas distintas para esa pregunta, se abstiene y deja responder al modelo. Para buscar coincidencias aproximadas utiliza `/conocimiento palabras`. El motor PyTorch avanzado **no** se activa ni se entrena con `todo`, para evitar descargas pesadas y consumo de recursos inesperado.

## Comandos disponibles

| Comando | Función |
|---|---|
| `python3 cerebro.py todo` | Chat + índice local + aprendizaje diario |
| `python3 cerebro.py chat` | Solo chat NumPy, sin aprendizaje en segundo plano |
| `python3 cerebro.py aprender --cada-dia --entrenar` | Solo aprendizaje diario |
| `python3 cerebro.py aprender` | Descargar textos una vez, sin entrenar |
| `python3 cerebro.py conocimiento buscar "Luna"` | Consultar la base local con fuentes |
| `python3 cerebro.py conocimiento guardar "¿Qué es la Luna?" "Un satélite" --fuente "manual"` | Guardar conocimiento |
| `python3 cerebro.py entrenar --pasos 100` | Entrenar motor NumPy |
| `python3 cerebro.py entrenar --motor avanzado --corpus data/corpus.txt --perfil diminuto --pasos 100` | Entrenar Transformer PyTorch propio |
| `python3 cerebro.py generar --motor avanzado "Hola"` | Generar con un checkpoint PyTorch existente |
| `python3 tests/tests_final.py` | Pruebas originales |

En Windows, sustituye `python3` por `python` si corresponde.

## ¿Qué tecnología incluye?

- **Motor neuronal NumPy:** Transformer causal, atención multi-cabeza, BPE por bytes, retropropagación manual, AdamW, gradientes acumulados, validación y checkpoints `.npz`.
- **Motor PyTorch opcional:** Transformer clásico o avanzado con RoPE, RMSNorm, SwiGLU y atención SDPA. Sus checkpoints `.pt` son independientes e incompatibles con el motor NumPy. PyTorch se instala automáticamente en `.cerebro-env` la primera vez que lo necesites (requiere Internet para descargar la biblioteca).
- **Aprendizaje diario experimental:** recopila hasta 3 artículos de Wikipedia por ciclo, conserva las URLs, evita IDs duplicados y limita el corpus a 20 MB por defecto. Utiliza Internet como **fuente de texto**, nunca como IA externa.
- **Protección del aprendizaje NumPy:** intenta continuar desde `last.npz`, hace respaldos temporales de `last.npz` y `best.npz`, evalúa `best.npz` contra `data/validacion.txt` y restaura ambos checkpoints ante errores o un empeoramiento superior al 2% en bits por byte, evaluando tanto `best.npz` como `last.npz` sobre la misma validación fija. Esto **no garantiza ausencia de olvido**.
- **Conocimiento local:** SQLite con preguntas, respuestas y fuentes, búsqueda estadística TF-IDF de palabras/trigramas, y alertas heurísticas de contradicción. Las alertas pueden tener falsos positivos.
- **Herramientas:** búsqueda local FTS5, análisis estático de Python, calculadora, archivos limitados a `data/workspace`, memoria persistente y voz opcional (síntesis/grabación; **no** reconocimiento de voz).

## Modelos y entrenamiento

```bash
# Motor NumPy: retomar entrenamiento existente
python3 train.py --resume --pasos 100

# Motor PyTorch avanzado: entrenar red propia
python3 cerebro.py entrenar --motor avanzado --corpus data/corpus.txt --perfil diminuto --pasos 100

# Probar chat original
python3 cerebro.py chat

# Evaluación local
python3 evaluate.py
```

Perfiles NumPy/PyTorch disponibles en `config.py`: `diminuto`, `pequeno`, `mediano`, `v2`, `grande`, `experto`, `gigante`, `maximo`, `cerebro_250m`, `cerebro_500m` y `cerebro_1b`. Los perfiles grandes son **configuraciones experimentales, no modelos ya entrenados**; requieren mucha memoria, datos y tiempo. No cambies el corpus al reanudar un checkpoint PyTorch: el motor comprueba su SHA-256.

## Seguridad, privacidad y límites

- Sin modelos preentrenados, Ollama ni APIs de IA de terceros.
- Las peticiones a Wikipedia sí envían tráfico de red a Wikimedia. Revisa las condiciones de reutilización y atribución del contenido.
- La base personal `data/conocimiento.sqlite3` y los textos descargados se excluyen de Git.
- La protección de checkpoints es experimental: no garantiza conservar todos los conocimientos, ni recuperarse de un apagón durante cualquier escritura. Mantén copias externas.
- El chat original puede utilizar un checkpoint anterior mientras el aprendizaje actualiza archivos en disco; reinicia el chat para cargar pesos aceptados.
- No se ha verificado aquí el funcionamiento integral del modo `todo` ni la calidad del entrenamiento autónomo.

## Pruebas antes de integrar en main

```bash
python3 tests/tests_final.py
python3 -m unittest tests.test_conocimiento tests.test_aprendizaje_internet
python3 cerebro.py chat --una-vez "hola"
```

Comprueba también manualmente `python3 cerebro.py todo` en tu sistema: indexación, chat, descarga, entrenamiento, interrupción, recuperación y cierre de procesos. **No fusionar solo porque el código esté subido**; revisar los resultados y los posibles conflictos del PR.

## Estructura del proyecto

| Archivo | Responsabilidad |
|---|---|
| `cerebro.py` | Lanzador único y modo `todo` |
| `main.py`, `chat.py` | Chat original |
| `train.py`, `trainer_engine.py` | Entrenamiento y evaluación NumPy |
| `cerebro_torch.py`, `core/advanced_torch.py` | Transformer propio opcional |
| `aprendizaje_internet.py` | Recopilación y entrenamiento diario |
| `core/seguridad_aprendizaje.py` | Respaldo, restauración y evaluación fija |
| `core/conocimiento.py` | Base de conocimientos y fuentes |
| `core/local_search.py`, `core/semantic_memory.py` | Recuperación local |
| `data/corpus.txt`, `data/validacion.txt` | Entrenamiento y validación |
| `checkpoints/` | Pesos del modelo |

Más detalles técnicos: [CEREBRO_MOTORES.md](CEREBRO_MOTORES.md) y [MEJORAS_LOCALES.md](MEJORAS_LOCALES.md).

## Contribuciones

Desarrolla primero en una rama, ejecuta pruebas y revisa los cambios antes de fusionar con `main`. El objetivo es mejorar **una IA propia y auditable**, sin depender de modelos de terceros.

## Correcciones para la siguiente fusión

- El aprendizaje evalúa **best y last** en el mismo conjunto fijo, y revierte ambos ante regresiones superiores al 2%.
- Al cerrar `todo` se envía una señal al recopilador, que detiene el entrenamiento hijo antes de restaurar checkpoints si se interrumpe.
- El chat muestra respuestas almacenadas con fuente para coincidencias exactas y no elige arbitrariamente entre fuentes contradictorias.
- GitHub Actions ejecuta pruebas al abrir un PR hacia `main` y al actualizar `main`. La ejecución completa de CI debe comprobarse antes de fusionar.

**Precaución:** la recuperación de checkpoints y el cierre de procesos no equivalen a una garantía frente a cortes de luz o fallos de disco. El aprendizaje automático sigue siendo experimental.

## Entrenamiento neuronal guiado (experimental)

Se incorpora un pequeño currículo **original** en `data/corpus/entrenamiento_guiado.txt` con ejemplos de cálculo, lógica, lenguaje y reconocimiento de incertidumbre. No utiliza modelos preentrenados ni APIs de IA.

Para continuar entrenando las neuronas NumPy ya existentes:

```bash
python3 entrenamiento_guiado.py --pasos 100 --lr 0.0003
```

Este comando **no se ejecuta automáticamente**. Requiere `checkpoints/last.npz` y `data/validacion.txt`. Realiza una copia temporal de `last.npz` y `best.npz`, reanuda los pesos, evalúa ambos en la misma validación fija y restaura los checkpoints si hay un error o la pérdida empeora más del 2 %. No garantiza que el modelo aprenda razonamiento general ni evita todos los tipos de olvido. Guarda una copia externa de tus checkpoints importantes antes de entrenar.

Para probar el código sin iniciar entrenamiento:

```bash
python3 -m pytest -q tests/test_entrenamiento_guiado.py
```

## Capacidades locales adicionales (integración experimental)

Estas herramientas son **prototipos funcionales**, no sustituyen un modelo conversacional entrenado:

- `core/razonamiento_local.py`: aritmética con AST restringido y un silogismo simple.
- `core/biblioteca_local.py`: lectura y búsqueda de TXT/Markdown dentro de una carpeta.
- `core/planificador_local.py`: planes con aprobación explícita; no ejecuta acciones.
- `core/analizador_codigo_local.py`: inspección AST de Python sin ejecutar código.
- `core/investigador_local.py`: normalización y deduplicación de fuentes HTTPS; la descarga existente sigue en `aprendizaje_internet.py`.
- `core/laboratorio_local.py`: registro JSONL de métricas y experimentos.
- `panel_cerebro.py`: interfaz Tkinter para cálculo, búsqueda, análisis de código e historial; no es todavía un chat gráfico.

Ejemplos:

```bash
python3 panel_cerebro.py
python3 panel_cerebro.py --accion calcular --texto "12 / 4 + 2"
python3 panel_cerebro.py --accion biblioteca --texto "Luna"
python3 -m pytest -q tests/test_capacidades_locales.py
```

El currículo de entrenamiento y el respaldo de checkpoints se desarrollan en la rama previa `integracion-entrenamiento-neuronal`. **Pendiente de desarrollar:** lectura de PDF, razonamiento avanzado, aprendizaje curricular automático, comparación experimental de modelos y conexión de todas las herramientas con el chat principal. Ninguna herramienta nueva toma el control del ordenador de forma autónoma.

### Voz avanzada: pospuesta

La nueva implementación de voz queda **fuera de esta integración** y se reserva para una versión futura. Las funciones de audio anteriores del proyecto no se modifican.

### Nuevos comandos del chat

`/biblioteca Luna`, `/calcular-local 2+3*4`, `/analizar-codigo def f(): return 1` y `/experimentos` permiten acceder a varias herramientas desde el chat original. No requieren modelos externos.

### Utilidades nuevas de estudio

`/resumir texto` selecciona frases del texto original y `/palabras-clave texto` extrae términos frecuentes. También están disponibles en `panel_cerebro.py`. Son funciones deterministas y no generan conocimientos nuevos; el resumen puede omitir detalles importantes.

### Herramientas educativas adicionales

- `/estadisticas Hola mundo.` cuenta palabras, frases, caracteres y líneas.
- `/comparar hola mundo || hola luna` muestra similitud y cambios de palabras.
- `/fichas Luna: satélite natural ; Marte: planeta` crea tarjetas de estudio a partir de definiciones explícitas.

Las tres opciones también están en el panel Tkinter. Son algoritmos locales, no aprendizaje neuronal. La voz avanzada sigue aplazada.

### Repaso y limpieza de textos

- `/preguntas La Luna es un satélite. Marte es un planeta.` genera preguntas literales con respuestas basadas en frases explícitas.
- `/duplicados La Luna es blanca || la luna es blanca` compara textos y señala similitudes por palabras.

Ambas funciones también están disponibles en `panel_cerebro.py` mediante interfaz gráfica o `--accion`. No utilizan modelos externos ni modifican los datos.

### Fase 1: historial local explícito

`/guardar-turno usuario Hola` y `/guardar-turno cerebro Hola` guardan entradas JSONL en `data/historial_cerebro.jsonl`. `/historial` consulta las últimas 20. Por ahora el guardado es **manual**, no automático; no debe confundirse con memoria neuronal ni entrenamiento. Los límites de tamaño y las pruebas se encuentran en `core/historial_local.py` y `tests/test_historial_local.py`.
