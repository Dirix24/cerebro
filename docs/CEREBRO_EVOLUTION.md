# CEREBRO Evolution y verificación para 1.0

La [auditoría final](AUDITORIA_FINAL_1_0.md) documenta la continuación, el banco ampliado y la generación modular.

El PR #43 sigue siendo un candidato a estabilización. Los controles del
núcleo, los checkpoints originales y el acceso local se conservan.
La evaluación de esta entrega detectó respuestas factuales erróneas del
modelo recomendado fuera del glosario. El control gestual en el ASUS y
el aislamiento de pruebas todavía requieren validación en destino.

## Cambios

- Entrenamiento corto, medio y largo con confirmación, un hilo de cómputo,
  prioridad reducida y límite de RAM ajustado a las mediciones. Se puede
  retomar una sesión sin volver a solicitar ejemplos a los adaptadores.
- Lecciones colectivas v1 con comprobación independiente y evidencia de
  procedencia. El historial y Universe muestran qué ejercicios aportó cada
  especialista y la decisión de la evaluación.
- Solicitudes JSON de llama.cpp ajustadas al esquema del servidor. Cuando
  se pide un único nombre de archivo compatible, ese nombre se restringe
  en el esquema. Antes de publicar siguen aplicándose los controles de rutas,
  tamaño, sintaxis y confirmación de Studio.
- Las definiciones del glosario local resisten respuestas incorrectas del
  modelo. Los seguimientos reciben la ficha y usan su texto de respaldo
  si la reformulación pierde el tema. La coincidencia léxica no certifica
  la veracidad de una reformulación.
- Arranque degradado ante un checkpoint ilegible, reemplazo atómico de
  checkpoints mediante temporales propios y actualización del servicio que
  espera al cierre del núcleo anterior. Universe también muestra RAM
  residente y CPU acumulada del núcleo en Linux.

## Uso y recuperación

Di «Prepara entrenamiento autónomo corto colectivo» y después
«Confirma entrenamiento autónomo». Puedes escoger corto, medio o largo.
Los presupuestos máximos de las tres opciones son 8, 64 y 256 pasos,
con guardados cada 4, 8 y 16 pasos. Las sesiones medianas y largas requieren
2 y 4 GiB de RAM disponible respectivamente. «Cancela entrenamiento
autónomo» detiene la sesión. Si hubo un guardado, usa «Reanuda entrenamiento
autónomo ensayo-ID» y confirma. El identificador aparece en el estado de
entrenamiento y en `learning/autonomo/`.

«Programa práctica colectiva cada 30 minutos» seguido de «Confirma
práctica programada» habilita sesiones cortas en el servicio de escritorio
abierto. El gestor espera al menos dos minutos sin actividad observada por
CEREBRO y comprueba carga, temperatura, batería y memoria disponibles. El
programa se desactiva al cerrar el servicio o al decir «Pausa práctica
programada». «¿Qué has aprendido hoy?» consulta los informes guardados.
«¿Por qué fallaste esta pregunta?» describe el fallo detectado en el último
turno del chat cuando hay evidencia de generación o validación.

Cada ensayo conserva un manifiesto v1 con huellas de datos y pesos, semilla,
presupuesto y lecciones. Mantiene pesos, optimizador y RNG en un checkpoint
NumPy v4 y registra métricas intermedias. Rechaza reanudar si cambian los
datos, el checkpoint base o el presupuesto. La restauración se comprobó
interrumpiendo tras el primer guardado y comparando los pesos finales con
una ejecución continua. El candidato se evalúa en un conjunto distinto
al de práctica. Tres revisiones sin mejora detienen el ensayo. Los
checkpoints activos v3/v4 se siguen leyendo, y la evaluación experimental
no escribe en ellos. Los informes completos permanecen en cada sesión.
Universe muestra el historial local reciente.

El protocolo colectivo usa una muestra Python sintética y coteja los
símbolos de CAZEL con el AST local. En DARAS comprueba dependencias y
orden del plan con las referencias del PROFESOR. Ejecuta los puntos de
entrada de DARAS en una copia temporal para mantener su SQLite fuera del
repositorio original. Las lecciones contienen datos canónicos. La sesión
no lee proyectos personales ni usa la red para las prácticas. El candidato
entrena los pesos de CEREBRO. Los especialistas v1 no exponen entrenamiento
de sus pesos a CEREBRO.

Si el modelo recomendado no completa una propuesta, reduce el alcance y
pide un archivo compatible concreto, como `calculadora.py`. Si un
checkpoint falla al cargar, revisa el diagnóstico y conserva la copia
anterior antes de sustituirlo. El lanzador intenta el respaldo local
antes de iniciar en modo de herramientas. Si MediaPipe informa que faltan
`libGLESv2` o EGL, vuelve a ejecutar `./instalar` y autoriza la
instalación de los paquetes que indica. El modo de prueba de cámara
permite comprobar el detector sin autorizar el puntero.

## Experimentos reales

**Hipótesis de retención.** Repetir 24 documentos anteriores puede
reducir la regresión del ajuste sobre ejercicios cortos. Se usó
`checkpoints/best.npz`, CPU Linux x86-64, un hilo, tasa inicial
`0.0001`, el mismo banco reservado de 32 reformulaciones y las semillas
17 y 29. El presupuesto fue de 32 pasos con revisión cada ocho. La
parada temprana terminó las cuatro sesiones tras 24 pasos.

| Semilla | Documentos de repaso | Bits por byte antes → después | Exactitud en validación | Decisión |
| --- | ---: | ---: | ---: | --- |
| 17 | 0 | 0,1000 → 0,1028 | 15/32 → 15/32 | Rechazado |
| 17 | 24 | 0,1000 → 0,1025 | 15/32 → 15/32 | Rechazado |
| 29 | 0 | 0,1000 → 0,1032 | 15/32 → 14/32 | Rechazado |
| 29 | 24 | 0,1000 → 0,1003 | 15/32 → 16/32 | Rechazado |

La muestra de repaso redujo la pérdida frente al control de su semilla.
Todos los candidatos empeoraron la pérdida de la referencia y mantuvieron
0/26 en generalización y 0/6 en el test final. Ninguna competencia
reservada ganó aciertos. Cada ejecución consumió unos cinco segundos de
CPU, incluida la evaluación. La discrepancia entre validación y test
hace necesario medir datos nuevos. Este ensayo no aísla el efecto de
tokenización, escala de datos o longitud de contexto.

El control de anchura existente entrenó dos Transformers desde cero con
el mismo tokenizador, 935 documentos de entrenamiento, las mismas 32
reformulaciones y ocho pasos. El ancho 32 terminó en 4,2745 y 4,2632
bits/byte en las semillas 17 y 29. El ancho 48 terminó en 4,1761 y
4,1534. El ancho mayor obtuvo menor pérdida en este presupuesto sin
alcanzar la referencia entrenada. Este control no justifica promover
pesos ni atribuye el problema del alumno a su anchura.

La práctica colectiva real ejecutó CAZEL `28bd14e` y DARAS
`a224fbb` sin red. Incorporó dos lecciones, entrenó ocho pasos y
terminó en 0,1014 bits/byte frente a 0,1000. El candidato fue rechazado.

Para recrear los controles en carpetas nuevas:

```sh
for semilla in 17 29; do
  for repaso in 0 24; do
    OPENBLAS_NUM_THREADS=1 python entrenar_competencias.py --ejecutar \
      --pasos 32 --intervalo 8 --semilla "$semilla" --repaso "$repaso" \
      --salida "learning/control-${semilla}-${repaso}"
  done
  OPENBLAS_NUM_THREADS=1 python comparar_anchos.py --semilla "$semilla" --pasos 8
done
```

## Evidencia de integración y límites

- La suite ejecutó 502 pruebas y tres subpruebas con éxito. Se omitieron seis,
  por PyTorch opcional y Bubblewrap. Se comprobó Studio web con Chromium y
  Studio nativo sobre X.Org virtual.

- Se verificó la descarga de Qwen2.5 0.5B Instruct Q4_K_M (491 400 032
  bytes) y se probó llama.cpp b7150 en CPU. Con el esquema corregido,
  Studio obtuvo un diff real de calculadora, publicó tras confirmación y
  las cuatro operaciones pasaron una comprobación externa después de
  revisar su AST. Bubblewrap no pudo iniciar el perfil de pruebas de
  proyectos en este entorno. El modelo respondió erróneamente a una
  pregunta abierta sobre una brújula, por lo que la calidad fuera de
  las rutas con respaldo sigue siendo una limitación.
- Se verificaron instalación local repetida, selección persistente,
  arranque, cambio de versión, recuperación del historial, cierre y
  desinstalación que conserva datos y pesos, en una copia temporal.
  La autorización de paquetes con privilegios queda para el equipo
  de destino.
- MediaPipe inicializó tras incorporar bibliotecas Debian en una
  carpeta temporal y devolvió 21 puntos de la mano con una imagen de
  prueba. Quedan pendientes cámara y micrófono físicos, cambio de
  pestañas y ventanas con gestos y pruebas de latencia en el ASUS.
- El control de arquitecturas y el entrenamiento de competencias prueban
  componentes distintos. La selección del núcleo aún depende de rutas
  con reglas y modelos opcionales. Quedan pendientes evaluación con
  bancos más amplios, promoción de un candidato superior, uso de GPU,
  propuesta de ejemplos a partir de recuerdos, OAuth y permisos
  centralizados para todos los dispositivos.

La calidad conversacional general, la prueba de proyectos con el
aislamiento habilitado y la validación del equipo de destino siguen
abiertas. Esta entrega no etiqueta una versión estable.
