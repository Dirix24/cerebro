# Cerebro: más parámetros y segundo motor propio

Cerebro incluye un modelo alumno propio. El núcleo de escritorio también puede consultar un profesor de lenguaje en un servidor local autorizado. La integración está desactivada por defecto y carece de descargas automáticas de motores y pesos.

## Profesor local opcional

Di «Estado del profesor» para ver la recomendación según la RAM disponible y el disco del directorio de datos. Para el i7-4500U observado y unos 5 GiB de RAM libre, el primer candidato es Qwen2.5-1.5B-Instruct GGUF Q4_K_M, con licencia Apache-2.0. El archivo oficial ocupa 1,12 GB. La disponibilidad de memoria y la compatibilidad del formato permiten proponer la prueba en CPU. Hace falta medir latencia y calidad en español en este equipo. [Ficha y licencia de Qwen](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)

Una vez instalados y autorizados el motor y los pesos, puedes iniciar un servidor compatible usando el GGUF ya guardado:

```sh
llama-server -m /ruta/al/modelo.gguf --host 127.0.0.1 --port 8080 -c 1024 -t 2 -ngl 0
```

Arranca una nueva sesión del núcleo de Cerebro con `CEREBRO_PROFESOR_PUERTO=8080`. Si las rutas locales no resuelven «Explícame …», Cerebro puede enviar el tema al profesor. La respuesta indica su origen. El adaptador limita cada consulta a una explicación de 96 tokens y una conexión de hasta 18 segundos de espera de socket. Envía solo el tema y recibe texto. El profesor carece de acceso a las herramientas y las solicitudes de herramientas en su salida se rechazan. [Documentación del servidor de llama.cpp](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)

## Coordinación híbrida

Las órdenes conocidas y las herramientas deterministas tienen prioridad. Un profesor local configurado se ocupa de la conversación que queda sin resolver y de las solicitudes expresas. Solo mantiene hasta dos turnos recientes de esa conversación. Los textos del modelo se muestran como respuesta. Un plan de escritorio solo se prepara mediante una petición expresa, pasa por un esquema de acciones de escritorio y necesita «Confirmar plan de escritorio». El agente vuelve a comprobar permisos, nombres y resultados. Un cierre conserva la confirmación independiente. [Esquemas JSON del servidor llama.cpp](https://github.com/ggml-org/llama.cpp/blob/b12600/tools/server/README.md)

Para iniciar el motor bajo demanda, usa `CEREBRO_PROFESOR_MOTOR=/ruta/llama-server` y `CEREBRO_PROFESOR_MODELO=/ruta/qwen.gguf` en una sesión nueva. El agente arranca el motor existente en CPU con dos hilos y contexto 1.024, y lo cierra a los 45 segundos de inactividad. El puerto fijo de un servidor previamente autorizado sigue admitiéndose mediante `CEREBRO_PROFESOR_PUERTO`. Ninguna modalidad descarga componentes.

`entrenar_especialista.py --salida HOGAR/learning/especialista.npz --ejecutar` genera un cabezal separado vinculado por SHA-256 a los pesos del alumno. Usa embeddings congelados y rasgos de caracteres. El cabezal solo sugiere una acción admitida en validación y en el banco reservado. En el piloto, búsqueda obtuvo 4/12 casos cubiertos, sin falsos positivos. El sistema se abstuvo en 72/76 casos, incluidos los 16 fuera de dominio. Las demás clases quedaron deshabilitadas. Los permisos provienen del registro de acciones, nunca de la predicción. La sugerencia se puede consultar con «Clasifica la intención de: …».

«¿Qué puedo hacer?» consulta disponibilidad de GIO, X11, carpetas y navegador, con permisos vigentes. «Revisa la demostración NOMBRE» muestra pasos guardados. «Genera ejercicios de la demostración NOMBRE» prepara ejemplos para revisión omitiendo los objetivos originales. Universe distingue las competencias neuronales, las fichas de conocimiento y los procedimientos autorizados.

## Competencias y ejercicios verificables

- «Ejercicio de matemáticas» propone una práctica. También admite español, programación, razonamiento y herramientas. El profesor elige una variante numérica y Cerebro construye el ejercicio y su referencia de forma determinista.
- «Explica ejercicio de matemáticas» y «Revisa al alumno en matemáticas» usan el último ejercicio de esa materia en la conversación, cuando existe. La nota usa la referencia local. El comentario del profesor se muestra como explicación y puede contener errores.
- «Evalúa competencias» guarda las métricas del alumno con su huella. «Competencias del alumno», «Ponte a analizar» y Universe muestran aciertos y fallos. El banco reservado incluye dos preguntas por materia.
- `entrenar_competencias.py --salida RUTA --ejecutar` entrena una copia. Puedes añadir `--variantes RUTA_JSON` con variantes numéricas revisadas y `--registrar` para incorporar el resultado al registro del hogar que esté activo. El informe distingue pérdida, acierto en validación y preguntas reservadas. El comando no promueve candidatos ni modifica los pesos activos.

En la prueba autorizada, llama.cpp b12600 ejecutó Qwen2.5-1.5B-Instruct Q4_K_M en MX Linux con dos hilos, contexto 1.024 y una red Bubblewrap aislada. El modelo cargó en 2,87 s y alcanzó un pico de 1.796 MiB de RAM. Produjo cinco variantes verificables. Acertó un caso de orden lógico y dio una explicación de fotosíntesis con los conceptos pedidos y errores gramaticales. Resolvió 7 + 5 pero ignoró el formato exacto de dos líneas. [Versión del motor](https://github.com/ggml-org/llama.cpp/releases/tag/b12600)

### Resultado del piloto

| Prueba del profesor | Resultado | Latencia |
|---|---|---:|
| Explicación en español | Mencionó luz y oxígeno. Hubo errores gramaticales. | 10,92 s |
| Instrucción compuesta | Obtuvo 12, pero devolvió una sola línea con puntuación añadida. | 5,04 s |
| Orden lógico | Identificó al cocinero como último. | 2,96 s |

El proceso del profesor consumió 101,04 segundos de CPU acumulados en la serie completa. En una revisión del alumno señaló la referencia correcta y dio una justificación parcialmente errónea. La calificación independiente siguió usando el valor verificado.

El alumno entrenó tres pasos con cinco ejercicios parametrizados por el profesor. En las diez preguntas reservadas obtuvo 0/10 antes y después. Conservó 46,9 % de acierto en validación y su pérdida pasó de 0,1000 a 0,1001 bits por byte. El candidato se rechazó. Las huellas de los pesos originales se conservaron.

Las 15 omisiones previas se debían al sandbox exterior. Catorce pruebas requerían escuchar en loopback y una requería que Bubblewrap pudiera iniciar su aislamiento. Todas pasaron al ejecutar la suite con esos permisos locales.

## Currículo progresivo y mediciones

El experimento previo de cinco ejercicios proporcionaba 228 tokens de corpus y 31 tokens objetivo, incluidos separadores y prefijos del asistente. El Transformer de 190.528 parámetros tiene 3 capas, dimensión 64, vocabulario BPE de 512 y contexto 112. El generador de lotes toma ventanas sobre el corpus concatenado. Con solo tres actualizaciones de AdamW, los documentos se repiten y se observan pocas variantes. La pérdida cruzada evalúa los tokens objetivo, mientras que el acierto exacto exige que la secuencia completa cumpla la instrucción. La versión inicial de los diálogos del currículo necesitaba hasta 131 tokens. Al acortar las instrucciones, el máximo del currículo principal quedó en 106.

Qwen propuso 35 semillas sin conexión. El currículo verificó referencias con plantillas deterministas y produjo 779 ejemplos únicos en tres etapas: fundamentos, reformulaciones e instrucciones compuestas, y continuación de diálogos. La continuación recibe el turno previo con su respuesta de referencia. No mide una conversación autónoma completa. Se mezcló repaso del corpus anterior sin incluir sus validaciones ni las preguntas inéditas. La inferencia de prueba usa solo los pesos del alumno y separa ejercicios incluidos en el corpus de los dos conjuntos inéditos.

| Medición | Base | Candidato A, 255 pasos | Candidato B, 435 pasos |
|---|---:|---:|---:|
| Banco reservado, tras repetir con el mismo decodificador | 0/90 | 8/90 | 4/90 |
| Segundo banco reservado | 0/90 | 12/90 | 4/90 |
| Retención anterior, acierto exacto en 32 reformulaciones | 46,9 % | 28,1 % | 46,9 % |
| Pérdida en la validación anterior, bits por byte | 0,1000 | 0,1433 | 0,1110 |

El segundo banco confirma una mejora acotada en programación y selección de herramientas. Matemáticas, español y razonamiento siguieron en cero en estos bancos. Ambos candidatos quedaron rechazados. A utilizó 120 documentos de repaso, LR 0,0006 y tardó 38,1 s. B utilizó 480, LR 0,00032 y tardó 55,5 s. Los dos entrenamientos usaron un hilo de BLAS y dejaron los checkpoints de origen intactos. Como siguiente escalón de arquitectura queda el perfil `v2` ya previsto en el repositorio: aproximadamente 540.480 parámetros, contexto 192 y objetivo BPE de 768. Todavía falta entrenarlo y compararlo con el perfil actual.

Ejecuta el currículo de forma aislada con `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout 220 python entrenar_curriculo.py --semillas RUTA_JSON --salida CARPETA --ejecutar`. El JSON debe incluir semillas numéricas por materia. Usa `--registrar HOGAR` para que Universe y ANALIZAR muestren la comparación entre el modelo de referencia y el candidato. Ningún resultado se promueve de forma automática.

## Comparación controlada de arquitectura y repaso

`comparar_arquitecturas.py` entrena `pequeno` y `v2` desde cero con un BPE compartido de 768 tokens para aislar el cambio de arquitectura. Para cada semilla se emparejan documentos, objetivos y pasos, con un lote de dos documentos. En el ajuste mixto se alterna un documento nuevo con un ejemplo anterior, recorriendo el búfer antiguo barajado sin reemplazo. Un ensayo separado parte del alumno activo y compara ajuste mixto con ajuste sobre ejemplos nuevos solamente. Esta es una variante de *experience replay*. [Trabajo original sobre repaso episódico](https://arxiv.org/abs/1902.10486)

El banco nuevo incluye 40 preguntas con estructuras distintas al currículo. Se mide el acierto exacto y el éxito de una respuesta ignorando mayúsculas y puntuación final. El ensayo de contexto contiene ocho pares contrafactuales de diálogo. Cambia la clave al principio de cada par, mientras el sufijo que puede ver el modelo con contexto 112 es idéntico. Se informa cuántas entradas caben completas y cuántos pares se resuelven por entero, incluyendo una ablación de `v2` recortada a 112.

Para reproducir una corrida, usa `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout 220 python comparar_arquitecturas.py --perfil v2 --semilla 17 --semillas SEMILLAS.json --salida CARPETA --ejecutar`. Se necesitan los informes de ambos perfiles por semilla para que `informar_comparacion.py` valide la equivalencia y pueda guardarlos con `--registrar HOGAR`. Los controles desde cero y las copias de adaptación se guardan en carpetas nuevas. El mecanismo carece de promoción automática.

### Mediciones de arquitectura en MX Linux

Los cuatro controles desde cero usaron 100 actualizaciones de base y 140 de ajuste. Se verificaron las mismas huellas de pares y de tokens objetivo por semilla. El BPE compartido hizo que el control `pequeno` tuviera 207.168 parámetros; el checkpoint activo mantiene su BPE de 512 y 190.528 parámetros. `v2` tuvo 540.480 parámetros.

| Perfil, semilla | Pérdida final (bpb) | Banco nuevo | Entrenamiento | Pico RSS | Latencia mediana del banco |
|---|---:|---:|---:|---:|---:|
| pequeño, 17 | 2,6555 | 0/40 | 8,79 s | 98,6 MiB | 21,4 ms |
| pequeño, 29 | 2,6604 | 0/40 | 7,21 s | 99,2 MiB | 35,3 ms |
| v2, 17 | 2,5570 | 0/40 | 17,29 s | 147,7 MiB | 27,1 ms |
| v2, 29 | 2,5807 | 0/40 | 12,52 s | 145,4 MiB | 57,7 ms |

Las cinco materias tuvieron 0/8 de éxito y acierto exacto en el banco nuevo. El contexto de `v2` conservó las 16 entradas largas completas; el de `pequeno` conservó 0. Ambos resolvieron 0/8 pares. Recortar `v2` a 112 tampoco produjo aciertos. La menor pérdida de `v2` se repitió en ambas semillas. Este presupuesto de entrenamiento desde cero no produjo comprensión conversacional verificable.

| Ajuste del alumno activo, 140 pasos | Retención en 32 preguntas | Pérdida final (bpb) | Currículo reservado, programación / herramientas |
|---|---:|---:|---:|
| Base | 46,9 % | 0,1000 | 0/18 / 0/18 |
| Solo ejemplos nuevos | 15,6 % | 0,2229 | 5/18 / 7/18 |
| Mixto con repaso | 37,5 % | 0,1322 | 6/18 / 6/18 |

Las otras tres materias quedaron en 0/18 en el currículo para ambos ajustes. Los dos ajustes quedaron en 0/40 en el banco nuevo. La ablación de repaso mantuvo los pasos y el número de documentos por lote. Los documentos anteriores elevaron los tokens objetivo de 2.709 a 8.835, así que la diferencia mide la estrategia completa. Ambos candidatos se rechazaron por regresión frente al alumno activo.

Con la evidencia disponible, el alumno pequeño es apropiado para ensayos de competencias acotadas verificables. Las tareas lingüísticas complejas pueden seguir usando el profesor local, atendiendo a los fallos ya medidos del profesor cuando se requiere precisión. El experimento no establece un límite general para `v2` con más entrenamiento.

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
