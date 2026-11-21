# Cerebro: más parámetros y segundo motor propio

Cerebro incluye un modelo alumno propio. El núcleo de escritorio también puede consultar un profesor de lenguaje en un servidor local autorizado. La integración está desactivada por defecto y carece de descargas automáticas de motores y pesos.

## Profesor local opcional

Di «Estado del profesor» para ver la recomendación según la RAM disponible y el disco del directorio de datos. Para el i7-4500U observado y unos 5 GiB de RAM libre, el primer candidato es Qwen2.5-1.5B-Instruct GGUF Q4_K_M, con licencia Apache-2.0. El archivo oficial ocupa 1,12 GB. La disponibilidad de memoria y la compatibilidad del formato permiten proponer la prueba en CPU. Hace falta medir latencia y calidad en español en este equipo. [Ficha y licencia de Qwen](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)

Una vez instalados y autorizados el motor y los pesos, puedes iniciar un servidor compatible usando el GGUF ya guardado:

```sh
llama-server -m /ruta/al/modelo.gguf --host 127.0.0.1 --port 8080 -c 1024 -t 2 -ngl 0
```

Arranca una nueva sesión del núcleo de Cerebro con `CEREBRO_PROFESOR_PUERTO=8080`. Si las rutas locales no resuelven «Explícame …», Cerebro puede enviar el tema al profesor. La respuesta indica su origen. El adaptador limita cada consulta a una explicación de 96 tokens y una conexión de hasta 18 segundos de espera de socket. Envía solo el tema y recibe texto. El profesor carece de acceso a las herramientas y las solicitudes de herramientas en su salida se rechazan. [Documentación del servidor de llama.cpp](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)

## Entrenamiento y evaluación del alumno

`entrenamiento_guiado.py` puede arrancar desde `best.npz` cuando todavía no existe `last.npz`. Entrena en una copia con un hilo de BLAS y un límite configurable de tiempo. La validación fija exige que baje la pérdida en bits por byte y comprueba que el acierto exacto no empeore cuando hay preguntas reformuladas. Los pesos activos permanecen en su ubicación. `evaluate.py --ckpt RUTA --rapido` permite medir un candidato en el test reservado.

La prueba aislada de tres pasos con el alumno de 190.528 parámetros pasó de 47 % a 44 % de respuestas exactas en 32 reformulaciones. El test final quedó en 0 de 6 y la pérdida de validación pasó de 0,100 a 0,101 bits por byte. El candidato quedó fuera de promoción. No se usaron respuestas de un profesor ni conversaciones privadas para entrenar.

## Más parámetros neuronales

Se añadieron dos perfiles a `config.PERFILES`:

| Perfil | Dimensión | Capas | Cabezas | Contexto | FFN |
|---|---:|---:|---:|---:|---:|
| grande | 256 | 6 | 8 | 256 | 1024 |
| experto | 384 | 8 | 8 | 384 | 1536 |
| gigante | 512 | 12 | 16 | 512 | 2048 |
| maximo | 768 | 16 | 16 | 768 | 3072 |

Estimaciones de parámetros NumPy con vocabulario objetivo: grande ~5,3 M; experto ~15,9 M; gigante ~42,3 M; maximo ~126,6 M. Los parámetros exactos dependen del vocabulario realmente aprendido. Los perfiles mayores pueden requerir muchos gigabytes de memoria.
Un modelo más grande **no garantiza** mejores respuestas: requiere más
datos, RAM, tiempo y evaluación de calidad.

Entrenamiento NumPy original:

```bash
python3 train.py --perfil grande --pasos 100
```

## Motor propio PyTorch opcional

El nuevo archivo `cerebro_torch.py` construye desde cero un Transformer
causal con embeddings, atención multi-cabeza, GELU, LayerNorm y pesos de
salida compartidos. Usa **PyTorch como biblioteca de cálculo y autograd**,
no como servicio ni como otra IA. Puede utilizar CPU o CUDA si está
disponible. Sus checkpoints son independientes de los NumPy originales.

```bash
pip install torch
python3 cerebro_torch.py --corpus data/corpus.txt --perfil diminuto --pasos 10 --dispositivo cpu
python3 cerebro_torch.py --generar "Hola" --max-tokens 30
```

Para un equipo potente:

```bash
python3 cerebro_torch.py --corpus data/corpus.txt --perfil grande --pasos 1000 --dispositivo auto
```

**Advertencias importantes:**

- El motor PyTorch es experimental; no sustituye al chat NumPy de `main.py`.
- Se entrena desde cero con **tus textos**, no con pesos preentrenados.
- No convierte checkpoints NumPy a PyTorch ni viceversa.
- Esta primera implementación entrena con un archivo y guarda un checkpoint
  final, sin validación ni reanudación. No afirmar mejoras de calidad sin medir.
- La generación es greedy (argmax); modelos entrenados pocos pasos pueden
  producir texto sin sentido.
- `torch.load(weights_only=True)` requiere una versión de PyTorch compatible.
- **Las pruebas aún no se han ejecutado en este entorno.**

Pruebas:

```bash
python3 -m pytest -q tests/test_cerebro_torch.py tests/test_local_search.py
```
