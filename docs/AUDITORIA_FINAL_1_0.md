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
