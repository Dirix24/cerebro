# Coordinación local v1

CEREBRO recibe el objetivo en su interfaz habitual y utiliza adaptadores
independientes. DARAS ejecuta `python -m especialista`; CAZEL ejecuta
`python -m cazel.especialista`. PROFESOR es el módulo
`core/profesor_local.py` de este repositorio. Su evaluación del primer
ejercicio de dependencias compara la respuesta con el plan guardado y
funciona con el motor generativo de Profesor apagado.

## Mensajes y control

Los adaptadores reciben un objeto JSON UTF-8 por entrada estándar.
La solicitud incluye `version: 1`, `accion`, `objetivo` y, si corresponde,
`red`. El repositorio y el proyecto local se eligen por configuración.
Cada respuesta incluye versión, especialista y estado (`ok`, `parcial`,
`no_disponible` o `error`). Los resultados pueden contener fuentes,
análisis, planes, simulaciones, ejercicios o el ID de una sesión CAZEL
con diffs pendientes. CAPACIDADES se consulta con la acción `capacidades`.

CEREBRO limita la coordinación a una tarea activa y dos especialistas
externos simultáneos. Cada ejecución tiene un plazo y puede cancelarse.
La ruta elegida debe apuntar a una instalación de confianza. Las tareas
de propuesta son locales y cada edición queda bajo el permiso normal de
Studio. El puente carece de una acción de robótica física.

El SQLite `universe-datos/experiencias-v1.sqlite3` conserva objetivos,
resultados estructurados, fecha y procedencia. Una firma del contenido
evita duplicados y los resultados distintos se conservan. El universo
carga las veinte coordinaciones más recientes y representa los informes
de cada región como nodos conectados a la tarea. Son acciones registradas
del sistema. Las neuronas se visualizan en los componentes existentes
de evaluación neuronal.

## Prueba conjunta

En Linux, DARAS consultó Wikipedia para «robots móviles» y devolvió cinco
referencias. Su simulación triangular con semilla 0 y 1000 muestras dio p50
21,92 h y p90 25,66 h con duraciones de referencia del plan. Qwen2.5-Coder-1.5B
Q4_K_M, a través de CAZEL, propuso `robot_simulado.py` desde una carpeta
vacía. CEREBRO registró la propuesta, los informes y la evaluación de
PROFESOR. El operador revisó el diff, lo aceptó en CAZEL y añadió dos casos
independientes de `unittest` para verificar avance y retroceso. Ambos pasaron
en el perfil de proyecto confiable. No se conectó hardware.

## Auditoría de límites y experimento neuronal

Los plazos y el tamaño de mensaje del puente son límites de estabilidad.
Los topes de archivos y permisos son controles de seguridad. La ventana de
veinte coordinaciones es de presentación. SQLite conserva las experiencias
anteriores. Los perfiles del Transformer se configuran según recursos. El
tamaño del mapa visual y el número de neuronas entrenables son métricas
independientes.

```sh
OPENBLAS_NUM_THREADS=1 python3 comparar_anchos.py --semilla 17 --pasos 4
```

Con 935 documentos de entrenamiento y 32 de validación, el control entrenó
dos modelos desde cero. El de ancho 32 pasó de 4,498 a 4,367 bits por byte
(41.728 parámetros). El de ancho 48 pasó de 4,506 a 4,300 (80.832 parámetros).
El ensayo usó una sola semilla y un presupuesto breve. Aún faltan comparaciones
de retención y generalización con varias semillas y migración de pesos.
`evolve.py` guarda candidatos aislados salvo promoción explícita.

Después de revisar y probar una propuesta en CAZEL, di «Muéstrame las
pruebas de CAZEL de la sesión ID». La acción `evidencia` importa el
resultado histórico para el proyecto autorizado y lo muestra en Universe.
La salida detallada del proceso permanece en CAZEL.
