# CEREBRO, candidato a estabilización

La [auditoría final](AUDITORIA_FINAL_1_0.md) documenta la continuación, el banco ampliado y la generación modular.

Comparación con `13c1afb`, en Debian Linux x86-64 sobre AMD EPYC con
3 CPU lógicas y aproximadamente 10 GiB de RAM visible. El ASUS X550LC
sigue pendiente de validación.

## Conversación con evidencia

Las consultas factuales reconocidas pasan por las herramientas deterministas,
las fichas exactas, el glosario, los temas y las definiciones del corpus.
La búsqueda pública requiere la configuración de red correspondiente.
Si hay una fuente pública, el generador puede elegir una oración. CEREBRO
solo publica la selección si coincide con una oración de la fuente y
conserva la atribución. Si falta evidencia, comunica la incertidumbre y
ofrece investigación pública cuando está disponible. Las conversaciones
abiertas, las propuestas y la ruta explícita de DARAS se conservan.

El banco offline incluye ciencia, tecnología, electrónica, programación,
historia, matemáticas, una consulta cotidiana, erratas, seguimiento,
ambigüedad y una pregunta ficticia. Sus respuestas esperadas no se añadieron
al glosario ni a los datos de entrenamiento. La rúbrica compara conceptos,
excluye errores conocidos y cuenta la abstención esperada en la pregunta
ficticia. Es una muestra pequeña y no certifica veracidad general.

| Qwen2.5 0.5B Instruct Q4_K_M, llama.cpp b7150 | Antes | Después |
| --- | ---: | ---: |
| Casos que cumplen la rúbrica | 5/11 | 5/11 |
| Respuestas o aclaraciones útiles según la rúbrica | 5/11 | 4/11 |
| Abstenciones | 0 | 7 |
| Latencia mediana | 2162 ms | Menos de 1 ms |

La nueva política evitó presentar afirmaciones sobre los casos sin
fuente y también dejó sin respuesta la pregunta histórica que el modelo
había acertado. La latencia baja corresponde sobre todo a la abstención
y al uso del conocimiento local. El seguimiento sobre fotosíntesis
mantuvo el tema y superó la rúbrica. No se descargaron modelos
conversacionales adicionales. Para repetir el banco y conservar las
salidas individuales:

```sh
OPENBLAS_NUM_THREADS=1 python -m benchmarks.conversacion_es \
  --motor /ruta/llama-server --modelo /ruta/modelo.gguf --salida resultados.json
```

## Aprendizaje y retención

Se repitió el control de semilla 29 con 24 documentos de repaso,
presupuesto de 32 pasos y tasa inicial `0.00003`. Al bajar la tasa,
el ajuste completó los 32 pasos y registró 0,0999 bits por byte frente
a 0,1000 del checkpoint base. La validación pasó de 15/32 a 16/32.
El control anterior con tasa `0.0001` había parado en el paso 24 y
terminó en 0,1003 bits por byte. El candidato nuevo obtuvo 0/26 en
generalización y 0/6 en test, y no mejoró ninguna competencia
reservada. La puerta lo rechazó. El resultado indica sensibilidad
a la tasa de ajuste en esta configuración y requiere más semillas
para generalizar. El entrenamiento y la evaluación consumieron
5,71 segundos de CPU en esta máquina.

```sh
OPENBLAS_NUM_THREADS=1 python entrenar_competencias.py --ejecutar \
  --pasos 32 --intervalo 8 --semilla 29 --repaso 24 --tasa .00003 \
  --salida learning/control-tasa-baja
```

El protocolo colectivo rota muestras de una a cuatro funciones y distintos
ejercicios de dependencias. Compara las respuestas de CAZEL con el AST
local y las de DARAS con el plan validado. Antes de entrenar descarta
lecciones que ya constan en el historial reciente. Dos sesiones reales
obtuvieron cuatro lecciones distintas verificadas. Los candidatos
subieron a 0,10069 y 0,10079 bits por byte. Ambos fueron rechazados.
Se preservaron los pesos activos y las particiones de evaluación.

## Ejecución de proyectos y rendimiento

La sonda comprueba Bubblewrap con código de confianza antes de leer el
proyecto. Bubblewrap está instalado y el límite de espacios de nombres
del kernel es positivo. El montaje de `/proc` es de solo lectura y la
creación del mapa UID falla con `Read-only file system`. La copia del
proyecto usa descriptores de directorio y excluye enlaces.

Existe una alternativa optativa con Docker rootless por socket Unix
local e imagen oficial fijada por digest. Reutiliza una copia de solo
lectura, sin red, sin privilegios y exige comprobar los límites
efectivos de CPU, RAM, swap y procesos antes de cargar el proyecto.
CEREBRO no descarga la imagen. Para preparar un daemon rootless
ya habilitado y probar la alternativa:

```sh
docker pull docker.io/library/python@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89
cerebro detener
CEREBRO_PRUEBAS_DOCKER=1 cerebro iniciar
```

Studio generó los cinco archivos con Qwen real, validó rutas y sintaxis,
mostró el diff y publicó cada caso tras confirmación en carpetas
temporales. Una prueba de diagnóstico previa en Docker rootless confirmó
usuario sin privilegios, red local aislada y montaje de solo lectura.
En ese perfil se ejecutaron las pruebas de los ejemplos revisados:

| Proyecto | Resultado funcional observado |
| --- | --- |
| Calculadora | Aprobado en el contenedor de diagnóstico |
| Gestor de tareas | Fallido. Mutó la lista y devolvió `None`. La corrección solicitada al modelo repitió el fallo |
| Conversor de unidades | Aprobado en el contenedor de diagnóstico |
| Lector UTF-8 | Aprobado en el contenedor de diagnóstico |
| Media de datos | Aprobado en el contenedor de diagnóstico |

El daemon de este entorno aceptó las opciones de recursos y aplicó los
límites del entorno padre. La sonda final lo rechaza. Los resultados
funcionales anteriores no certifican el perfil como apto para proyectos
arbitrarios. No quedaron contenedores de prueba.

En la prueba de generación el núcleo ocupó aproximadamente 34 MiB
de RSS pico, el motor alcanzó aproximadamente 630 MiB, y el archivo
GGUF pesó 491 400 032 bytes. Las propuestas tardaron 0,92–4,39 s.
Una inferencia en caliente empleó 3,49 s de CPU del motor en 2,69 s
de reloj. No se observó un incremento de CPU del motor en una
ventana de reposo de dos segundos. El proceso se cerró al terminar.
Estas cifras no sustituyen la medición en el portátil.

## Instalación e interfaces

El instalador ofrece Bubblewrap en Debian/MX Linux y comunica el
resultado de la sonda. El diagnóstico actualizado se ejecutó con
llama.cpp y el GGUF ya configurados. Las validaciones de instalación
limpia y repetida, actualización, conservación de datos y
desinstalación del PR están en [Evolution](CEREBRO_EVOLUTION.md).
Se volvió a probar Studio web en Chromium, con archivos, visores,
diffs y resultados verificados. La suite terminó con 506 pruebas y
3 subpruebas aprobadas. Se omitieron 6 por Bubblewrap y PyTorch opcional.

**Pendiente de prueba física en el ASUS.** En MX Linux XFCE,
confirma que la sesión es X11 y que el diagnóstico detecta OpenCV,
MediaPipe, `libGLESv2`, `xdotool` y la cámara. Abre **Probar cámara y
manos** y confirma la captura. Comprueba imagen continua, 21 puntos y
respuesta tras calibrar. Abre **Iniciar control gestual** y verifica
puntero, clic, arrastre y desplazamiento en una ventana de prueba.
Pulsa Esc durante un arrastre y comprueba que libera el botón y
detiene el control. Registra resolución, FPS, CPU y RAM, y verifica que
la cámara se libera al cerrar. El control físico de ventanas y pestañas
sigue pendiente.

**1.0 aún no cumple aceptación.** La utilidad factual general, el
aislamiento operativo con límites efectivos y el comportamiento físico
en el ASUS siguen abiertos. OAuth y la comparación de modelos
adicionales quedan pendientes.
