# Auditoría de estabilización de CEREBRO

Base comparada: `c08e707`. Esta entrega conserva la denominación de
candidato a estabilización. La sesión de prueba tiene CPU AMD EPYC 9V74
sobre KVM y no expone una cámara V4L2. La autorización de uso del
portátil no proporciona un canal hacia el ASUS X550LC.

## Matriz de fallos

| ID | Componente y gravedad | Esperado | Observado y causa | Archivos y corrección | Regresión y evidencia | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| INT-01 | Núcleo y conversación · Alto | Respuesta exacta a consultas calculables | Ante `len` de un literal, el modelo podía describir la operación sin dar el resultado. Faltaba una ruta determinista | `core/comprension_conversacional.py`, `universe/nucleo.py`. Analizar literales con AST y calcular su longitud | Pruebas de contenedores, expresiones rechazadas y banco antes/después con Qwen real | Corregido para los literales compatibles |
| INT-02 | Cobertura factual y selección de modelo · Alto | Referencias útiles en dominios diversos | 56 abstenciones en casos con respuesta conocida. Fuentes locales escasas y evidencia insuficiente, con un único modelo real disponible | `benchmarks/conversacion_es.py`, `benchmarks/banco_es_reservado.py`. Medición ampliada y separada por categoría | 101 casos con resultados individuales. Qwen2.5 0.5B Instruct Q4_K_M, llama.cpp b7150 | Parcial. Faltan fuentes y comparación con otros modelos autorizados |
| GEN-01 | Studio · Alto | Añadir una tarea devolviendo una lista nueva | Qwen volvió a generar `tareas.append(titulo)`, que muta la lista y no devuelve la nueva | `core/generacion_proyecto.py`, `universe/nucleo.py`. Reparación AST condicionada al contrato explícito y al patrón inequívoco | Regresión AST. Con Qwen real se reprodujo el patrón, se corrigió antes del diff y se publicó en una carpeta temporal autorizada | Corrección estática comprobada. Ejecución aislada pendiente |
| GEN-02 | Studio y publicación · Alto | Proyecto mayor de seis archivos y subcarpetas | El formato anterior solo admitía propuestas pequeñas planas | `core/generacion_proyecto.py`, `core/proyecto_studio.py`. Plan de rutas explícito, generación secuencial y publicación atómica por descriptores, sin reemplazar | Prueba de siete módulos con doble. Traversal, colisiones y publicación sin confirmación rechazados. Lista de importaciones externas revisable | Integrado. Límite de calidad del modelo en módulos complejos |
| GEN-03 | Generación modular · Alto | Rechazar módulos con nombres usados sin definir | Qwen produjo `print(VALOR)`; el primer reintento lo envolvió en una función. Analizar sintaxis sola no lo detectaba | Tabla de símbolos del módulo y sus bloques con un reintento acotado. Falla antes del diff publicable si el nombre sigue sin definir | Pruebas de nombres libres y reintento. Qwen real aún dejó VALOR indefinido y Studio rechazó el plan | Regresión cubierta. No certifica toda la lógica de un proyecto |
| ISO-01 | Pruebas de proyectos · Crítico para 1.0 | Aislamiento con red, montajes y recursos controlados | Bubblewrap no puede crear el mapa UID en el montaje de solo lectura. Docker rootless del entorno no aplica los límites pedidos | `core/aislamiento_proyecto.py`, `core/proyecto_studio.py`. Se conservan las sondas y el bloqueo antes de cargar código | Solicitud real para los proyectos generados termina en diagnóstico. La suite omite la prueba Bubblewrap física del entorno | Bloqueado por el entorno. Se conserva análisis y revisión |
| INS-01 | Instalador · Medio | Comprobar realmente el servicio | El diagnóstico importaba módulos, pero una importación correcta no acredita que funcione el servicio | `universe/diagnostico_instalacion.py`. Servicio HTTP aislado con datos temporales, consulta aritmética, lectura del historial y cierre | Sonda real superada por loopback | Corregido para el núcleo. La reinstalación completa y MX Linux físico conservan el alcance de validaciones previas |
| APR-01 | Aprendizaje neuronal · Alto | Ganancia en datos reservados, protección de pesos | El control anterior conservó 0/6 en test. Ningún candidato reciente cumplió la puerta | `entrenar_competencias.py`, `trainer_engine.py`. Se conservan particiones, reanudación, evaluación y rechazo | Resultados reproducibles de tasa, repaso y arquitectura en [Evolution](CEREBRO_EVOLUTION.md). Suite de reanudación y checkpoints ejecutada | Pendiente de mejora generalizable. Dos candidatos nuevos rechazados y pesos activos conservados |
| COL-01 | CAZEL, DARAS y PROFESOR · Medio | Verificación de más de un tipo de ejercicio | La rotación de CAZEL se limitaba a recuento de funciones | `core/lecciones_colectivas.py`. Ejercicio de localizar un error de sintaxis, cotejado con Python antes de admitirlo al contrato v1 | Adaptadores reales devolvieron línea 2 y dependencia T2 en una práctica separada. Los archivos de los repositorios independientes se conservaron | Ampliado. Pendientes más competencias y evaluación de ganancias |
| MEM-01 | Memoria y permisos · Alto | Procedencia, revocación y contradicciones fiables | Las contradicciones se limitan a negaciones casi literales. Los permisos persistentes de carpetas no constituyen una política común para cámara y micrófono | `core/recuerdo_portable.py`, `universe/dialogo_recuerdos.py`, `universe/nucleo.py`. Se mantienen los controles existentes | Suite de confirmación, duplicados, no ejecución de citas, persistencia y revocación | Parcial. Semántica y permisos centralizados pendientes |
| DES-01 | Acompañante y Universe · Medio | Sugerencias con contexto de proyecto y estado observable | El Acompañante aprende contadores de aplicaciones X11. Universe tiene estados reales y recursos del núcleo, con mediciones incompletas por proceso | `core/habitos_escritorio.py`, `universe/lanzador.py`, `universe/mapa_studio.py`. Se mantienen pausa, borrado y filtros | Regresiones existentes ejecutadas. Sin prueba de Acompañante físico nueva | Parcial |
| FIS-01 | Cámara y ASUS · Alto | Gestos, consumo y cierre comprobados en el equipo de destino | En la sesión KVM no hay dispositivo V4L2 visible. MediaPipe se verificó anteriormente con imagen | `universe/tactil.py`, `core/gestos_tactiles.py`, `universe/diagnostico_instalacion.py`. Dos acciones principales y ruta de pausa conservadas | Pruebas automatizadas de estados. Procedimiento físico en [Estabilización](ESTABILIZACION_1_0.md) | Pendiente de prueba física |

## Conversación reproducible

Se fijó antes de comparar una ganancia mínima de 8 respuestas útiles
sobre 101 casos, conservación de abstenciones esperadas, seguimiento
correcto y ausencia de nuevos errores factuales graves observados.
Se usaron los mismos modelos, entradas y rúbrica para el control y el
candidato. Los casos reservados no se usaron para entrenar. Las
categorías principales tienen alrededor de diez casos. Erratas,
ambigüedad y seguimiento conservan un solo caso cada una, por lo que
no hay equilibrio completo ni validación estadística general.

| Métrica de rúbrica offline, 101 casos | `c08e707` | Candidato |
| --- | ---: | ---: |
| Casos que cumplen | 37 | 45 |
| Respuestas útiles | 26 | 34 |
| Abstenciones esperadas | 11 | 11 |
| Otras abstenciones | 56 | 56 |
| Seguimiento | 1/1 | 1/1 |
| Razonamiento con conclusión explícita | 10/10 | 10/10 |
| Latencia mediana | 0,3 ms | 0,3 ms |

La mejora observada se concentra en ocho casos con resultados de
`len`. El subconjunto cambiado devuelve enteros obtenidos con Python
sobre literales y no introdujo afirmaciones factuales nuevas de otros
dominios. El umbral de utilidad de este banco se alcanzó. Esto no valida
la cobertura general ni sustituye una evaluación de los casos abiertos.
Las latencias medianas son del banco offline, dominado por rutas
locales y abstenciones.

```sh
OPENBLAS_NUM_THREADS=1 python -m benchmarks.conversacion_es --ampliado \
  --motor /ruta/llama-server --modelo /ruta/modelo.gguf --salida resultados.json
```

Para comparar, ejecuta el mismo evaluador y los mismos casos contra el
código de cada versión desde su directorio. El JSON conserva respuestas,
orígenes, tiempos y resultado de la rúbrica.

## Integración y aceptación

- **Conversación.** Aprobado el recorrido de evidencia, errata,
  cálculo y seguimiento en el banco. Cobertura factual abierta parcial.
- **Investigación.** Adaptador DARAS probado con su plan local.
  Contraste exhaustivo en red pendiente.
- **Programación.** Chromium volvió a recorrer Studio web, diffs y
  coordinación. Qwen real reprodujo el fallo del gestor y el diff
  reparado devolvió una lista nueva según AST. La prueba funcional
  de estos proyectos se bloqueó al fallar la sonda.
- **Aprendizaje.** Dos lecciones v1 reales verificadas. Se compararon
  16 pasos con y sin esas lecciones, semilla 29, 24 documentos de repaso
  y tasa 0,00003. Desde 0,100032 bits/byte, el control terminó en
  0,100007 y retuvo 15/32. El colectivo terminó en 0,100246 y bajó a
  14/32. Ambos obtuvieron 0/26 en generalización y 0/6 en test y
  fueron rechazados. Cada ajuste y evaluación consumió unos 5 s de CPU.
  La suite incluye reanudación y protección de pesos.
- **Memoria y escritorio.** Pruebas existentes de persistencia,
  confirmación, pausa y revocación ejecutadas. Sin nueva sesión
  física de escritorio.
- **Instalación.** Sonda HTTP local aprobada. Se conservan instalador
  guiado y comprobaciones previas de actualización y desinstalación.
- **Gestos.** Cámara física no disponible. Se conservan los resultados
  previos con MediaPipe sobre una imagen.
- **Rendimiento.** Banco offline medido en KVM. Las cifras de RAM y
  CPU de inferencia previas están en el informe de estabilización.
  Consumo y latencia del portátil siguen pendientes.

La ejecución final aprobó **514 pruebas y 3 subpruebas**, con 6 omitidas
por Bubblewrap y PyTorch opcional.

El aislamiento efectivo del equipo de destino, la cobertura factual
y la validación física impiden recomendar 1.0 estable.

## Ciclo de corrección posterior a `8edfcb6`

### Conversación

La mayor causa de abstención sigue siendo la falta de una referencia que
responda a la pregunta. También se reproducen dos problemas de enrutamiento.
Las conversiones y porcentajes iban al generador, que llegó a convertir
mililitros en centímetros. Algunas peticiones coloquiales de definiciones no
llegaban al buscador factual y recibían afirmaciones sin fuentes.

El núcleo usa aritmética racional para porcentajes y conversiones de longitud,
masa, volumen y tiempo. Reconoce abreviaturas, plurales y decimales con coma,
y pide una unidad compatible si las dimensiones difieren. Las definiciones
con fórmulas coloquiales se redirigen a las rutas de hechos. Con investigación
automática autorizada, la búsqueda adicional en Wikipedia acepta un título
coincidente o una corrección muy cercana y única, conserva la URL y descarta
páginas de desambiguación. Se verificó una recuperación real de «máquina
virtual». El extracto correcto recibió cero puntos en la rúbrica porque no
incluía la palabra obligatoria «sistema». Se mantuvo la rúbrica predefinida
para ambas versiones. Sin evidencia se conserva la abstención y el siguiente
seguimiento ya no se desvía a un tema anterior.

| Banco y sesión | Útiles | Cobertura | Precisión de respuestas por rúbrica | Abstenciones esperadas / otras | Mediana | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 101 sin red, `8edfcb6` | 34/101 | 34/101 | 34/34 | 11 / 56 | 0,3 ms | 0,6 ms |
| 101 sin red, este ciclo | 34/101 | 34/101 | 34/34 | 11 / 56 | 0,3 ms | 0,8 ms |
| 15 nuevos sin red, `8edfcb6` | 2/15 | 9/15 | 2/9 | 2 / 4 | 1944,6 ms | 3030,4 ms |
| 15 nuevos sin red, este ciclo | 8/15 | 9/15 | 8/9 | 2 / 4 | 0,3 ms | 1453,4 ms |
| 15 nuevos con red, `8edfcb6` | 3/15 | 11/15 | 3/11 | 2 / 2 | 1192,7 ms | 4431,2 ms |
| 15 nuevos con red, este ciclo | 9/15 | 11/15 | 9/11 | 2 / 2 | 0,6 ms | 2846,1 ms |

Cobertura es la proporción de turnos que reciben una respuesta o aclaración
en vez de una abstención. La precisión usa la coincidencia de palabras y
vetos entre respuestas emitidas. La utilidad penaliza también las abstenciones
y usa todos los turnos como denominador. Cada sesión se ejecutó en CPU con
Qwen2.5 0.5B Instruct GGUF y llama.cpp b7150. El muestreo y la red introducen
variación. La cohorte nueva tiene seis peticiones de cálculo o unidades, cinco
de conocimiento o programación, dos turnos de errata y seguimiento y dos
hechos ficticios. No se utilizó para entrenar. Los resultados muestran mejoras
en las medidas y la conversación contextual, sin aumento de cobertura. Quedan
pendientes recuperación factual más amplia y evaluación semántica independiente.

Para reproducir, usa `python -m benchmarks.conversacion_es` con
`--motor`, `--modelo` y `--salida`. Usa `--ampliado` para los 101
casos o `--ciclo-correccion` para los 15 adicionales. La opción
`--investigacion-publica` envía los temas del banco a las fuentes públicas.
Para reproducir el control, usa el mismo banco y evaluador con el núcleo de
`8edfcb6`. Los JSON incluyen cada respuesta, origen y latencia.

### Studio, aprendizaje y aceptación

| Área | Causa y cambio | Prueba y estado |
| --- | --- | --- |
| Studio, importaciones | Parsear módulos de forma aislada aceptaba rutas internas inexistentes. Ahora se contrasta el árbol completo y se señala archivo y línea. | Regresiones para importaciones absolutas y relativas. **Corregido y probado** para rutas del árbol propuesto. |
| Studio, comportamiento | El AST aceptaba una función que mutaba la lista y devolvía `None`. La reparación acotada se aplica a una firma explícita, con contrato de lista nueva y una única llamada a `append`. | Tres módulos de prueba escritos para la suite. `unittest` observa el fallo y pasa después de aplicar la reparación real, incluyendo la comprobación de la lista original. La confirmación previa a publicar sigue cubierta. Los proyectos generados continúan **bloqueados por el entorno** para pruebas dinámicas. |
| Aislamiento | La sonda Bubblewrap comprobaba el arranque, no los controles. Ahora verifica montaje de solo lectura, UID no privilegiado, ausencia de la carpeta personal, interfaces y límites por proceso. | El host devolvió `uid map: Read-only file system` con loopback habilitado. No hay daemon Docker rootless listo. **Bloqueado por el entorno**. CPU, RAM y procesos agregados requieren el perfil con cgroups y se mantienen pendientes de una comprobación real. |
| Especialistas | El ejercicio DARAS solo cubría dependencias. Una práctica rotativa añade recuperación y contraste de dos fuentes sintéticas discrepantes, en una base efímera. | CAZEL real analizó AST y error de sintaxis. DARAS real devolvió las dos fuentes y PROFESOR comprobó el contraste y el contrato. La prueba rechaza una sola fuente. **Mejorado parcialmente**. Corrección de errores por CAZEL e investigación contrastada de fuentes externas siguen pendientes. |
| Memoria, permisos, Universe y Acompañante | El contexto conversacional omitía el último turno sin evidencia. Se añade al diálogo y el seguimiento pide precisar o aportar fuente. | Regresión sobre cambio de tema y suite de persistencia, autorización, eventos y hábitos. **Corregido y probado** para este seguimiento. Sin cambios adicionales en Universe y Acompañante. |
| Instalación, cámara y gestos | No hay cámara física ni sesión ASUS XFCE/X11 conectada. | Se ejecutaron las pruebas automatizadas de instalación, diagnóstico gestual y controles. La prueba física sigue **pendiente**. |

El diagnóstico neuronal `OPENBLAS_NUM_THREADS=1 python -m benchmarks.diagnostico_neuronal`
compara cuatro entrenamientos desde cero de 24 pasos, semilla 29, lote 2
y tasa 0,001. Usa diálogos de entrenamiento distintos de los prompts exactos
reservados. Se compara un control BPE de 384 con una ventana mayor, un
vocabulario de 260 sin fusiones y la mitad de los diálogos. Cada ejecución
consumió 1,5–2,4 s de CPU. Los pesos activos permanecieron intactos.

| Configuración | Diálogos | Ventana | Bits/byte generalización | Bits/byte test | Exactas generalización / test |
| --- | ---: | ---: | ---: | ---: | ---: |
| Checkpoint activo, 190 528 parámetros | — | 112 | 4,510 | 3,732 | 0/26 · 0/6 |
| Control BPE | 96 | 96 | 4,348 | 4,141 | 0/26 · 0/6 |
| Ventana mayor | 96 | 144 | 4,344 | 4,135 | 0/26 · 0/6 |
| Bytes sin fusiones | 96 | 96 | 7,045 | 7,042 | 0/26 · 0/6 |
| Mitad de los datos | 48 | 96 | 4,424 | 4,406 | 0/26 · 0/6 |

Los prompts reservados caben en el checkpoint activo. La similitud textual
media de ese checkpoint fue 0,301 y 0,418 en los dos bancos, con 0 coincidencias
exactas. Ni ampliar la ventana ni reducir el vocabulario resolvió el fallo
con ese presupuesto. Una pequeña mejora de pérdida tampoco se tradujo en
respuestas correctas. La alternativa implementable es usar el modelo propio
para competencias que superen un banco reservado de comportamiento y
combinarlo con recuperación, herramientas y un generador local para consultas
abiertas. El umbral de promoción sigue intacto. Queda pendiente ensayar un
objetivo supervisado por competencia con más pares verificados y varias semillas.

Suite completa con loopback habilitado: **524 aprobadas, 6 omitidas y 3 subpruebas**.
Las omisiones corresponden a Bubblewrap y PyTorch opcional. El PR continúa
como candidato a revisión.
