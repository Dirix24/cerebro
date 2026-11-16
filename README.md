# Cerebro

Un modelo de lenguaje **local y construido desde cero**. El motor original usa
NumPy con retropropagación manual; esta rama añade un motor **PyTorch opcional**
para entrenar otra red propia desde cero, sin Ollama, sin APIs, sin modelos
preentrenados de terceros y sin necesidad de Internet.

```
python3 main.py        # habla con el modelo que ya viene entrenado
```

## Novedades de esta rama: más parámetros y tecnología local

Se incorporan perfiles de entrenamiento más grandes para el Transformer propio,
y un segundo motor opcional con PyTorch (CPU o CUDA). Los perfiles **no son
modelos ya entrenados**: indican tamaños de redes que puedes entrenar con tus
datos. Los parámetros de la tabla son **estimaciones para el vocabulario
objetivo completo**; si BPE aprende menos tokens, la cantidad real será menor.

| Perfil | Capas | Dimensión | Cabezas | Contexto | Parámetros estimados* |
|---|---:|---:|---:|---:|---:|
| grande | 6 | 256 | 8 | 256 | ~5,3 millones |
| experto | 8 | 384 | 8 | 384 | ~15,9 millones |
| gigante | 12 | 512 | 16 | 512 | ~42,3 millones |
| maximo | 16 | 768 | 16 | 768 | ~126,6 millones |

*Estimación para la arquitectura NumPy con embeddings compartidos y
vocabulario objetivo. Entrenar los perfiles `gigante` y `maximo` puede consumir
**muchos gigabytes de RAM/VRAM** y tardar considerablemente. Más parámetros
por sí solos no implican mejor calidad: se necesitan más datos y evaluación.
El modelo incluido de ~190 mil parámetros **no se convierte automáticamente**
en uno grande.

### Entrenamiento NumPy (motor original)

```bash
python3 train.py --perfil grande --pasos 100
python3 train.py --perfil experto --pasos 100
# gigante/maximo: solo con memoria y tiempo suficientes
```

### Entrenamiento PyTorch (motor propio opcional)

```bash
pip install torch
python3 cerebro_torch.py --corpus data/corpus.txt --perfil grande --pasos 100 --dispositivo auto
python3 cerebro_torch.py --generar "Hola Cerebro"
```

PyTorch es una biblioteca para cálculos y gradientes; **no se carga otra IA**.
Este motor guarda pesos independientes en `checkpoints/torch_cerebro.pt` y no
reemplaza el chat NumPy de `main.py`. La generación de PyTorch es experimental;
no hay resultados de calidad confirmados ni pruebas ejecutadas de este motor.
Consulta [CEREBRO_MOTORES.md](CEREBRO_MOTORES.md).

### Búsqueda offline del corpus

```bash
python3 -m core.local_search --indexar
python3 -m core.local_search --buscar "atención"
# En main.py: /buscar-corpus atención
```

Usa SQLite FTS5, sin servicios externos. Requiere crear el índice después de
cambiar el corpus. Más detalles en [MEJORAS_LOCALES.md](MEJORAS_LOCALES.md).

## Alcance honesto

Cerebro **no** es un LLM competitivo ni sabe cosas del mundo. El checkpoint original incluido tiene ~190 mil
parámetros y aprendió de un corpus propio de unos 80 mil tokens. Lo que sí hace bien:

- Contesta con fluidez las preguntas de su corpus y sus reformulaciones
  (incluida la escritura informal: «que es la atencion»).
- Ejecuta cuentas y consulta la hora con herramientas seguras, sin inventárselas.
- Recuerda datos entre sesiones (memoria de largo plazo).

Lo que **no** hace: responder sobre temas que no están en su corpus. Si le
preguntas algo desconocido contestará con la respuesta memorizada que más se
parezca, con total seguridad y sin sentido. Es el comportamiento esperable de un
modelo así de pequeño y `evaluate.py` lo mide (ver «Métricas»), no lo esconde.
Mejorarlo pasa por darle más texto (`data/corpus/`) y usar un perfil mayor.

## Qué hay dentro (todo real, todo verificado)

| Pieza | Dónde | Detalle |
|---|---|---|
| Transformer | `core/transformer/optimized_llm.py` | Pre-LayerNorm, atención multi-cabeza causal, MLP con GELU, embeddings de posición, dropout, pesos compartidos entrada/salida, entrenamiento por lotes |
| Retropropagación | mismo archivo | Derivada **a mano** con la regla de la cadena. Las pruebas la comparan con diferencias finitas (error ~1e-6) |
| Tokenizador BPE | `core/tokenizer.py` | Byte-level: nunca hay palabras desconocidas y decodifica tildes, ñ y emojis sin pérdida. Se conserva además el tokenizador por palabras original |
| Optimizadores | `core/optim.py` | AdamW (decaimiento desacoplado), SGD con momentum, recorte por norma global, learning rate con calentamiento + coseno |
| Muestreo | `core/sampling.py` | Temperatura, top-k, top-p, penalización de repetición, generación reproducible con semilla |
| Datos | `core/data.py` | Documentos separados por línea en blanco, validación aparte, **pérdida solo sobre las respuestas** (las líneas del usuario se enmascaran, como en el ajuste supervisado de un chatbot) |
| Checkpoints | `core/checkpoint.py` | Un `.npz` con pesos + arquitectura + tokenizador; escritura atómica; sin pickle |
| Entrenamiento | `train.py`, `trainer_engine.py` | Validación real, mejor checkpoint por bits/byte, `--resume`, no sobrescribe un modelo mejor |
| Evolución | `evolve.py` | Algoritmo evolutivo real: población, selección, cruce y mutación de hiperparámetros, con presupuesto de parámetros |
| Chat | `main.py`, `chat.py` | Comandos, memoria de corto plazo en el prompt, enrutador de herramientas |
| Agente | `agent/` | Límites de pasos y llamadas, **permisos por herramienta**, workspace cerrado |
| Memoria | `memory/advanced_memory.py` | Corto plazo + largo plazo persistente (JSON atómico) con búsqueda |
| Datos extra | `aumentar_corpus.py` | Reformulaciones, escritura informal y conversaciones multi-turno a partir del corpus |
| Reanudación reproducible | `trainer_engine.py`, `core/checkpoint.py` | Guarda RNG del modelo + muestreador de batches + AdamW; continuar produce los mismos pasos |
| Entrenamiento eficiente | `trainer_engine.py` | Acumulación de gradientes, scheduler basado en paso global y early stopping configurable |
| Evaluación | `data/test.txt`, `evaluate.py` | Conjunto TEST final que nunca selecciona checkpoints; huellas SHA-256 de train/validación |
| Pruebas | `tests/tests_final.py` | Pruebas originales sin frameworks; los nuevos tests opcionales usan pytest |
| Segundo motor propio | `cerebro_torch.py` | Transformer PyTorch desde cero, CPU/CUDA opcional, checkpoints separados |
| Búsqueda offline | `core/local_search.py` | Índice SQLite FTS5 del corpus, sin Internet |

## Instalación

```bash
git clone https://github.com/Dirix24/cerebro.git
cd cerebro
pip install -r requirements.txt      # solo numpy
python3 tests/tests_final.py         # comprueba que todo funciona
python3 main.py                      # a conversar
```

Para el motor original, la dependencia principal es `numpy`; `psutil` es opcional.\nPyTorch y pytest solo se necesitan para el motor nuevo y sus pruebas.

## Uso

### Conversar
```bash
python3 main.py                          # interactivo
python3 main.py --una-vez "hola"         # un mensaje, para scripts
python3 main.py --semilla 7              # respuestas reproducibles
```
Comandos: `/buscar-corpus texto /ayuda /estado /memoria /recordar clave = valor /olvidar clave /calc 12*7
/hora /archivos /leer f /escribir f texto /temp 0.5 /limpiar /salir`.
También entiende «cuánto es 12 por 7» y «qué hora es» (por reglas, no por el modelo).

### Entrenar
```bash
python3 train.py                     # 8000 pasos, perfil "pequeno"
CEREBRO_PERFIL=v2 python3 train.py   # perfil V2: 4 capas, dim 96, contexto 192, vocab 768
python3 train.py --perfil v2 --pasos 8000
python3 train.py --pasos 2000        # o --epocas 50
python3 train.py --resume            # continúa desde checkpoints/last.npz
python3 train.py --corpus mis_textos/    # tu propio corpus (archivo o carpeta)
CEREBRO_PERFIL=diminuto python3 train.py
python3 train.py --batch 8 --pasos 2000
```
Al terminar, `best.npz` solo se reemplaza si el modelo nuevo es **mejor** que el
existente (comparados hoy, sobre la misma validación, en bits por byte). Con
`--forzar` se sobrescribe sin comparar.

### Evolucionar hiperparámetros
```bash
python3 evolve.py --poblacion 6 --generaciones 3 --pasos-candidato 250 --pasos-final 3000
```

### Evaluar
```bash
python3 evaluate.py
```

### Añadir conocimiento
Cerebro solo sabe lo que hay en su corpus. Para enseñarle algo:

1. Escribe diálogos en `data/corpus/lo_que_sea.txt`, separados por una línea en blanco:
   ```
   usuario: ¿Qué es un byte?
   cerebro: Es un grupo de ocho bits.

   usuario: ¿Y un bit?
   cerebro: Es la unidad mínima de información.
   ```
   (La prosa suelta también vale.)
2. `python3 aumentar_corpus.py` (opcional, genera variantes de las preguntas).
3. `python3 train.py`.

## Datos y métricas: cómo leer los números

Hay tres conjuntos que **nunca se mezclan**:

- `data/corpus.txt` + `data/corpus/*.txt` — entrenamiento.
- `data/validacion.txt` — reformulaciones *nuevas* de cosas que el modelo sí debería
  saber. Con esto se elige el mejor checkpoint.
- `data/generalizacion.txt` — diálogos sobre temas que jamás vio. Mide conocimiento
  nuevo y, en un modelo de este tamaño, sale mal a propósito de mostrarlo.
- `data/test.txt` — conjunto final separado. Solo se informa; nunca decide qué checkpoint es mejor.

Cada checkpoint guarda además hashes SHA-256 de train/validación para detectar cambios de datos.

Métricas (las imprime `python3 evaluate.py`):

- **bits por byte (bpb)**: el error del modelo por cada byte de texto. Permite
  comparar modelos con tokenizadores distintos. Menor es mejor.
- **Respuestas exactas**: % de preguntas reformuladas que el modelo contesta idéntico
  al corpus con generación voraz. Es lo que se nota al chatear.

Resultado del modelo incluido (`checkpoints/best.npz`):

| Métrica | Valor |
|---|---|
| Parámetros | 190.528 (3 capas × 4 cabezas, dim 64, contexto 112, vocabulario BPE de 512) |
| Validación (reformulaciones nuevas) | 0,100 bits/byte (perplejidad 1,17) |
| Respuestas exactas a preguntas reformuladas | 47 % (similitud media 0,61) |
| Generalización (diálogos nunca vistos) | 4,51 bits/byte (perplejidad ~995): no sabe nada fuera de su corpus |
| Velocidad medida (CPU del sandbox, 1 núcleo) | ~26 000 tok/s entrenando, ~1 100 tok/s generando, ~46 MB de RAM |

Entrenamiento: `python3 train.py` (6000 pasos, ~6 min).

La validación es buena porque mide reformulaciones de lo aprendido; la
generalización es mala porque el modelo no sabe nada más. Los dos números son
verdad a la vez.

## Configuración (`config.py`)

| Qué | Dónde |
|---|---|
| Tamaño del modelo | `PERFILES` (`diminuto`, `pequeno`, `mediano`, `v2`, `grande`, `experto`, `gigante`, `maximo`) o `CEREBRO_PERFIL=...` |
| Entrenamiento | `BATCH_SIZE`, `TASA_APRENDIZAJE`, `WEIGHT_DECAY`, `GRAD_CLIP`, `OPTIMIZADOR`, `PASOS_POR_DEFECTO` |
| Generación | `GEN_TEMPERATURA`, `GEN_TOP_K`, `GEN_TOP_P`, `GEN_PENALIZACION_REPETICION` |
| Agente | `MAX_AGENT_STEPS`, `MAX_TOOL_CALLS`, `PERMISOS_AGENTE`, `MAX_FILE_BYTES`, `WORKSPACE_DIR` |

Para un agente de solo lectura quita `"WRITE"` de `PERMISOS_AGENTE`.

## Seguridad del agente

Todo esto lo comprueban las pruebas:

- La calculadora **no usa `eval`**: analiza la expresión como árbol y solo admite
  números, operadores y `sqrt/abs/sin/...`. Rechaza código, nombres, cadenas y
  bombas de cómputo (`9**9**9**9`, `10**100000`).
- Los archivos viven en `data/workspace/`. La ruta se resuelve con `realpath` y
  se comprueba con `commonpath`: bloquea `../`, rutas absolutas, carpetas
  vecinas con el mismo prefijo y enlaces simbólicos. Hay tope de tamaño.
- Cada herramienta exige un permiso (`READ`, `WRITE`, `CALCULATE`); sin él, no se ejecuta.
- Un plan que falla se detiene. Nada de archivos se activa por lenguaje natural:
  solo con `/leer` y `/escribir`.

## Estructura

```
config.py               configuración central y perfiles\ncerebro_torch.py         Transformer propio opcional en PyTorch\ncore/local_search.py    índice y búsqueda offline SQLite FTS5
main.py  chat.py        chat interactivo y su lógica
train.py                entrenamiento (CLI)
trainer_engine.py       bucle de entrenamiento y evaluación
evolve.py               búsqueda evolutiva de hiperparámetros
evaluate.py             informe de evaluación
aumentar_corpus.py      aumento de datos del corpus
core/
  tokenizer.py          BPE por bytes + tokenizador por palabras
  transformer/optimized_llm.py   el modelo (forward + backward a mano)
  optim.py  sampling.py  data.py  checkpoint.py
agent/                  agente, herramientas y enrutador de intenciones
memory/                 memoria de corto y largo plazo
benchmarks/             medición de velocidad y RAM
tests/tests_final.py    pruebas originales\ntests/test_cerebro_torch.py y tests/test_local_search.py    pruebas nuevas
data/                   corpus, validación, generalización, workspace
checkpoints/best.npz    modelo entrenado incluido
```

## Cómo seguir creciendo

El código está pensado para extenderse sin romper lo demás:

- **Nueva arquitectura**: un bloque son solo `_bloque_forward` y `_bloque_backward`
  en `optimized_llm.py`. `ModeloConfig` ignora campos desconocidos al cargar
  checkpoints, así que se pueden añadir opciones. **Regla de oro:** después de
  tocar el backward, ejecuta `python3 tests/tests_final.py -k gradientes`.
- **Nuevo tokenizador**: añádelo a `TOKENIZADORES` en `core/tokenizer.py`.
- **Nueva herramienta**: `ToolRegistry.registrar(nombre, desc, func, schema, permiso)`.
- **Modelo mayor**: crea un perfil en `config.py`. Más datos ayudan más que más parámetros.
- **Ideas siguientes**: caché de claves/valores para generar más rápido, RoPE en vez
  de posiciones aprendidas, muestreo por haces, recuperación de memoria por
  similitud de embeddings.


