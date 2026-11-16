# Cerebro

## Aprendizaje diario desde Internet (opcional)

```bash
# Descargar unos pocos textos de Wikipedia y entrenar el motor NumPy pequeño
python3 aprendizaje_internet.py --entrenar

# Repetir cada día mientras el proceso esté abierto y el ordenador encendido
python3 aprendizaje_internet.py --cada-dia --entrenar

# Solo recopilar, sin modificar el modelo
python3 aprendizaje_internet.py
```

El sistema obtiene hasta 3 introducciones de artículos públicos de Wikipedia
en español por ciclo, guarda los enlaces de origen en
`data/aprendizaje_internet/fuentes.jsonl`, evita duplicados por ID y limita
el corpus acumulado a 20 MB. Requiere Internet para descargar datos, pero
**no usa ninguna API de IA**. El entrenamiento se realiza en el ordenador.
La fuente Wikipedia requiere respetar sus condiciones de reutilización y
atribución; se conservan URLs, no se otorgan licencias nuevas al contenido.

**Limitaciones:** es una función experimental y voluntaria, no un servicio que
se ejecute solo al encender el equipo. La terminal debe permanecer abierta.
El primer ciclo entrena desde cero si no hay checkpoint; los siguientes usan\n`--resume` para conservar los pesos y el optimizador del modelo NumPy.\nEl corpus descargado se convierte a pares `usuario:/cerebro:` compatibles\ncon la función de pérdida del entrenador.\n**Aviso:** el checkpoint original preexistente puede corresponder a otro corpus;\nla reanudación ajusta ese modelo con los nuevos textos, y un cambio de corpus\npuede empeorar respuestas antiguas.\nLos datos se añaden a un corpus acumulativo, pero no existe todavía un sistema\nde evaluación de regresiones que garantice conservar conocimientos anteriores.\nAntes de activar entrenamiento automático conviene guardar una copia de los\ncheckpoints.\nEl corpus de Internet,
no continúa automáticamente los pesos existentes; los textos previos del
corpus original no se mezclan en este proceso. El modelo PyTorch no reanuda
si cambia el corpus. La calidad del conocimiento no está garantizada; se
recomienda revisar los textos y medir el rendimiento antes de adoptar pesos.
No se ha verificado todavía la descarga ni el entrenamiento en el equipo del
usuario. El proceso puede consumir CPU y sobrescribir el checkpoint de
entrenamiento original según las reglas de `train.py`.


## Uso sencillo: un solo comando

No hace falta escribir `pip install torch` manualmente. Cerebro incorpora
`cerebro.py`, que prepara un entorno virtual privado `.cerebro-env` e instala
las bibliotecas del motor avanzado **automáticamente la primera vez**.
**Importante:** PyTorch no está empaquetado dentro del repositorio: es una
biblioteca grande y la primera preparación requiere Internet. Después, el
entrenamiento y la generación son locales, sin APIs ni modelos externos.

```bash
# Chat con el modelo original (NumPy)
python3 cerebro.py chat

# Entrenamiento del motor original (no requiere PyTorch)
python3 cerebro.py entrenar --pasos 100

# Entrenamiento avanzado: prepara PyTorch automáticamente si falta
python3 cerebro.py entrenar --motor avanzado --corpus data/corpus.txt --perfil diminuto --pasos 100

# Generación del motor avanzado ya entrenado
python3 cerebro.py generar --motor avanzado "Hola Cerebro"
```

Para evitar cualquier descarga automática, añade `--sin-instalar`. Para usar
la arquitectura clásica PyTorch, selecciona `--motor clasico`. El motor
original NumPy sigue siendo independiente y funciona sin PyTorch. El
lanzador requiere Python 3 con `venv` y `pip` disponibles; el motor NumPy
requiere además NumPy instalado. No hay instalación completamente sin
bibliotecas ni descarga inicial garantizada en todos los sistemas.


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
python3 cerebro.py entrenar --motor clasico --corpus data/corpus.txt --perfil grande --pasos 100 --dispositivo auto
python3 cerebro_torch.py --generar "Hola Cerebro"
```

Para entrenar en varias sesiones y guardar avances cada 50 pasos:

```bash
python3 cerebro_torch.py --corpus data/corpus.txt --perfil grande --pasos 100 --guardar-cada 50
python3 cerebro_torch.py --corpus data/corpus.txt --perfil grande --pasos 100 --resume --guardar-cada 50
```

`--resume` restaura pesos, optimizador, contador de pasos y estado aleatorio.
Comprueba la huella SHA-256 del corpus y rechaza cambios de datos o perfil.
El checkpoint se escribe mediante archivo temporal y reemplazo atómico.
**No cambies el corpus entre reanudaciones.** Checkpoints anteriores v1 pueden
utilizarse para generar, pero no para reanudar. Los checkpoints guardan también
el estado de AdamW, por lo que requieren más espacio.

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

## Nuevas capacidades experimentales (rama mejoras-cerebro-local)

Estas funciones se implementaron **sin Ollama, APIs ni modelos preentrenados**.
El motor NumPy y su checkpoint original permanecen disponibles.

### Arquitectura neuronal avanzada

`core/advanced_torch.py` implementa **RoPE, RMSNorm, SwiGLU y atención causal
SDPA**. Se selecciona con `--arquitectura avanzada`; sus pesos **no son
compatibles** con la arquitectura clásica. No se han entrenado los perfiles grandes.

```bash
python3 cerebro_torch.py --corpus data/corpus.txt --perfil diminuto --arquitectura avanzada --pasos 20 --acumulacion 2 --guardar-cada 10
python3 cerebro_torch.py --corpus data/corpus.txt --perfil diminuto --arquitectura avanzada --pasos 20 --acumulacion 2 --resume
```

La acumulación divide el gradiente entre microbatches y permite aumentar el
batch efectivo sin mantener todos los ejemplos simultáneamente en memoria.
El checkpoint guarda el optimizador y el estado aleatorio; reanudar con otra
acumulación o LR cambia la trayectoria del entrenamiento. No se ha añadido
precisión mixta ni optimizador cuantizado.

### Perfiles 250M, 500M y 1B (objetivos aproximados)

| Perfil | Capas | Dimensión | Cabezas | Contexto |
|---|---:|---:|---:|---:|
| `cerebro_250m` | 16 | 1024 | 16 | 1024 |
| `cerebro_500m` | 22 | 1280 | 20 | 1024 |
| `cerebro_1b` | 20 | 2048 | 32 | 2048 |

Son **perfiles experimentales**, no checkpoints ni recuentos exactos. El
número real de parámetros depende del vocabulario aprendido y la arquitectura.
Su entrenamiento puede requerir decenas de GB de RAM/VRAM, grandes conjuntos
de datos y tiempos largos. No se ha verificado su entrenamiento completo.

### Memoria por similitud local

`core/semantic_memory.py` calcula TF-IDF de palabras y trigramas de caracteres
sin descargar embeddings. `AdvancedMemoryManager.buscar_similar(texto)` busca
entre los recuerdos persistidos. **No es comprensión semántica profunda** y
no sustituye al método léxico `buscar` ya existente.

### Programación y herramientas seguras

`core/code_tools.py` analiza archivos Python mediante `ast`, sin ejecutarlos,
limitado a `data/workspace`. Informa funciones, clases, imports y líneas.

```bash
python3 herramientas_locales.py analizar ejemplo.py
```

`ejemplo.py` debe existir dentro de `data/workspace`. Esta herramienta es
independiente: no ejecuta código arbitrario ni concede nuevos permisos al agente.

### Voz local (funcionalidad parcial)

`core/local_voice.py` añade **síntesis de voz local opcional** mediante
`pyttsx3` y **grabación WAV** mediante `sounddevice`, utilizando los
dispositivos y voces disponibles en el sistema:

```bash
pip install pyttsx3 sounddevice
python3 herramientas_locales.py hablar "Hola, soy Cerebro"
python3 herramientas_locales.py grabar data/workspace/voz.wav --segundos 3
```

**No se ha implementado reconocimiento de voz ni transcripción**: grabar un
WAV no equivale a comprenderlo. La síntesis depende de un motor de voz instalado
en el sistema, no de un modelo de IA descargado por Cerebro.

### Pruebas

```bash
pip install pytest
python3 -m pytest -q tests/test_nuevas_capacidades.py tests/test_cerebro_torch.py
```

**Estado:** código subido a la rama, pero las pruebas y los entrenamientos
grandes no se han ejecutado ni verificado aquí.

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

Para el motor original, la dependencia principal es `numpy`; `psutil` es opcional.
PyTorch y pytest solo se necesitan para el motor nuevo y sus pruebas.

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
config.py               configuración central y perfiles
cerebro_torch.py         Transformer propio opcional en PyTorch
core/local_search.py    índice y búsqueda offline SQLite FTS5
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
tests/tests_final.py    pruebas originales
tests/test_cerebro_torch.py y tests/test_local_search.py    pruebas nuevas
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


