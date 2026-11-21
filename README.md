# Cerebro

Cerebro es un asistente local de software libre para MX Linux, publicado bajo la licencia MIT. Cuatro interfaces comparten el servicio local, recuerdos y herramientas. Studio, Chat web y la esfera comparten el chat activo. Terminal puede incorporarse cuando tú lo pidas. El proyecto combina modelos propios en NumPy y PyTorch con herramientas verificables para documentos, proyectos Python, escritorio y consulta de fuentes públicas.

**Estado experimental.** El flujo habitual funciona en MX Linux con XFCE/X11. La comprensión general, el seguimiento de manos con diferentes cámaras, Wayland y el agente de programación de propósito general siguen en desarrollo.

## Arranque en MX Linux

Desde la carpeta del repositorio:

```bash
./instalar
```

| Interfaz | Comando | Para qué sirve |
| --- | --- | --- |
| Terminal | `cerebro terminal` | Conversación y comandos locales, con cabecera CEREBRO en azul. |
| Chat web | `cerebro chat` | Conversaciones, adjuntos y consultas públicas. |
| Acompañante | `cerebro escritorio` | Esfera flotante, texto, dictado y lectura opcionales. |
| Studio | `cerebro studio` | Explorador, editor, revisión de cambios, pruebas y Universe. |

Las interfaces conservan el diseño negro con acentos azules. El núcleo de escritorio escucha únicamente en loopback y requiere una clave de sesión. **Nuevo chat** conserva los chats anteriores. Desde **Chats** puedes recuperarlos o seleccionar cuáles eliminar. Terminal abre un chat separado para programación. Escribe **sincronízate** o `/sincronizar` para ver y usar el chat activo de Studio, la web y la esfera. Usa `/separar` para volver al chat de Terminal. El cambio afecta a esa sesión y no copia mensajes anteriores. Siguen disponibles `/nuevo-chat`, `/chats` y `/historial`. Con **guarda esto en Studio** o `/guardar-en-studio` puedes guardar la última respuesta como TXT en `notas/`. Guarda un dato con `/recordar proyecto = Atlas` y recupéralo con `/recuerdo proyecto` desde otra interfaz.

Para arrancar el asistente de consola anterior o preparar los motores opcionales, ejecuta `python3 cerebro.py --help`. Consulta [las interfaces y sus dependencias](docs/INTERFACES_MX.md) y [la configuración de voz local](docs/VOZ_LOCAL.md).

## Studio y documentos

1. En Studio nativo, pulsa **Abrir proyecto**, elige una carpeta y autoriza el acceso.
2. Usa el explorador para filtrar y abrir archivos. El editor resalta Python y comprueba si el original cambió antes de guardar en la carpeta autorizada.
3. Escribe «Cerebro, analiza este proyecto y corrige sus errores». Studio compila archivos Python sin ejecutarlos, señala errores y claves literales repetidas, y puede proponer correcciones acotadas, como dos puntos o un delimitador final ausentes.
4. Revisa el diff en **Cambios** y confirma cada propuesta que quieras aplicar. Usa **Pruebas** para ejecutar `unittest` aislado y ver su salida en **Validaciones**.

Adjunta PDF de texto, TXT, Markdown, DOCX o código. Puedes preguntar «¿Qué dice el PDF adjunto sobre el presupuesto?». Cerebro muestra pasajes y el alcance de la lectura. La extracción de PDF usa `pdftotext` de `poppler-utils`; los escaneados requieren OCR.

## Permisos e aislamiento

- `READ` controla el acceso a archivos, recuerdos, historial y otros datos locales. `WRITE` controla los cambios persistentes y operaciones concretas del escritorio. Las herramientas de cálculo conservan su permiso propio. Studio revalida los permisos al ejecutar las operaciones.
- **Pruebas** requiere Bubblewrap (`bwrap`) con espacios de usuario habilitados y el Python del sistema. Se ejecuta con una copia de solo lectura, sin directorio personal, sin variables heredadas y en un espacio de red separado. `/tmp` es temporal y tiene un máximo de 64 MiB.
- La copia omite archivos ocultos, enlaces, llaves con extensiones conocidas y directorios de dependencias o compilación. Tiene límites de entradas y tamaño. La ejecución limita tiempo, memoria por proceso y salida. Los archivos visibles de la copia quedan accesibles a las pruebas, así que guarda los secretos fuera de los proyectos que quieras ejecutar.
- Si Bubblewrap falta o no puede crear el entorno, la ejecución se rechaza. El aislamiento cubre el flujo de `unittest` de Studio y usa un subconjunto de bibliotecas del sistema.

## Búsqueda y herramientas del escritorio

| Puedes decir | Resultado |
| --- | --- |
| «Búscame todos mis PDF» | Busca por tipo en carpetas autorizadas. Si hay varias coincidencias, puedes elegir un archivo por número. |
| «Busca los vídeos que descargué esta semana» | Busca en Descargas y filtra por fecha de modificación. |
| «Busca en el contenido de mis documentos: presupuesto» | Busca texto de forma local en hasta doce archivos TXT o Markdown, con un límite de 64 KiB por archivo. |
| «Abre Blender y busca mi último proyecto» | Localiza el archivo `.blend` más reciente y solicita su apertura mediante la asociación del escritorio. |
| «Abre YouTube y busca un tutorial de Blender» | Abre los resultados en el navegador. |
| «Analiza este enlace https://es.wikipedia.org/wiki/Fotos%C3%ADntesis» | Resume la introducción del artículo público e indica su fuente. |
| «¿Qué puedes hacer en mi ordenador?» | Comprueba aplicaciones visibles en GIO, carpetas autorizadas, extractor de PDF y estado de la conexión. |

Una solicitud de apertura aceptada por el escritorio puede requerir que confirmes que apareció la ventana. Las búsquedas de YouTube se muestran en el navegador. El análisis directo de enlaces admite artículos de Wikipedia en español.

### Guardar un resumen en Studio

Prueba «Busca mis PDF de física, abre el más reciente, hazme un resumen y guárdalo en una carpeta». Cuando revises el resumen, responde **Confirmar guardar resumen** desde la interfaz que inició la operación. Cerebro escribe un TXT en `resumenes/` dentro del espacio de Studio y comprueba el contenido guardado. [Guía de búsquedas y adjuntos](docs/INTERFACES_MX.md)

## Escritorio y control por manos

«Abre Blender» busca aplicaciones en GIO. «Abre mi documento de matemáticas» busca el archivo por nombre en Documentos y Descargas. Si hay varias coincidencias, elige una. Cerebro solo guarda la selección cuando la confirmas. Con `CEREBRO_SIN_DOCUMENTOS=1` puedes desactivar esa capacidad al arrancar.

En X11 puedes decir «Enfócame el navegador», «Maximiza Blender», «Minimiza esta ventana», «Restaura esa ventana» o «Muéstrame todas las ventanas abiertas». Cerebro consulta el estado de X11 después de cada acción. Para enfocar el navegador usa la asociación HTTPS y, cuando esta apunta al lanzador de XFCE, consulta la preferencia de XFCE.

«Cierra LibreOffice» y «Cierra todas las ventanas de LibreOffice» requieren **Confirmar cierre** desde la conversación que inició la operación. Se envía una solicitud de cierre normal. Si una ventana sigue abierta, revisa si la aplicación pide guardar cambios. Puedes encadenar órdenes de aplicaciones y ventanas, como «Enfoca Blender, minimiza el navegador y pon LibreOffice delante». La secuencia pausa ante una selección o confirmación y se detiene si un paso falla.

El control de ventanas requiere X11, `wmctrl`, `xdotool` y `xprop`. En Wayland se necesita un adaptador del compositor.

**Modo táctil experimental.** En el panel local selecciona tu cámara y autorízala. **Ver cámara** muestra los puntos detectados y pausa el puntero. **Dibujar figura** permite trazar un contorno con una pinza. **Convertir a 3D** le da grosor y **Guardar OBJ** exporta la malla. **Pausar** libera la cámara.

Requiere X11, `xdotool`, Tk, OpenCV y MediaPipe. Se comprobó MediaPipe 0.10.32 con Python 3.13. Para preparar un entorno propio:

```bash
python3 -m venv .cerebro-env/tactil
.cerebro-env/tactil/bin/python -m pip install 'mediapipe==0.10.32'
CEREBRO_MODELO_MANOS=/ruta/absoluta/hand_landmarker.task \
  .cerebro-env/tactil/bin/python -m universe.lanzador tactil
```

[Guía de escritorio y modo táctil](docs/INTERFACES_MX.md) · [Modelo Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker#models)

## Conversación, Internet y aprendizaje

- Pregunta «¿Qué hora es? ¿Cuánto es dos más dos?» para ver la separación de preguntas y la ruta de cálculo local. La comprensión de dictado y preguntas generales sigue siendo limitada.
- «Noticias de hoy» usa el feed de BBC Mundo. Las consultas a Wikipedia y GitHub indican su fuente. Inicia con `CEREBRO_SIN_INTERNET=1` para bloquear las consultas públicas.
- **Universe** presenta recuerdos y relaciones. **Analizar** revisa registros y propone próximos pasos. **Evaluar alumno** mide coincidencia exacta sobre un pequeño conjunto de fichas locales aprobadas, sin mezclar el contexto del chat con la prueba.
- Guardar memoria, enseñar una habilidad y entrenar el modelo son procesos separados. `python3 entrenamiento_guiado.py --pasos 100` entrena copias en un espacio de candidatos y conserva un candidato si reduce la pérdida en validación fija. Ese flujo deja intactos los checkpoints activos. Comprueba también generalización y diálogo antes de decidir una promoción.
- NumPy es el motor base. PyTorch, Vosk y MediaPipe aportan funciones opcionales. [Arquitectura](ARQUITECTURA_CEREBRO_V2.md) · [Motores](CEREBRO_MOTORES.md) · [Evaluación V3](docs/REASONING_BASELINE.md) · [Plan maestro](docs/EVOLUCION_CEREBRO.md)

## Datos y pruebas

Los datos y checkpoints pueden residir en un SSD configurado con `CEREBRO_HOME`. [Preparación y uso del SSD](CEREBRO_SSD_PORTATIL.md)

```bash
python3 -m pip install -r requirements.txt pytest
python3 -m pytest -q -ra
python3 evaluate.py --rapido
```

Las pruebas de integración de la API necesitan loopback. Las pruebas reales de aislamiento necesitan Bubblewrap y namespaces. Los resultados de reconocimiento físico dependen de la cámara y las condiciones de captura.

## Contribuir

Crea una rama, añade pruebas para los cambios de comportamiento y señala qué verificaste en MX Linux y qué sigue pendiente. Conserva los datos personales, modelos externos y dependencias locales fuera del repositorio.

## Licencia de software libre

El código y la documentación de Cerebro se distribuyen bajo la [licencia MIT](LICENSE). Puedes usar, estudiar, copiar, modificar y redistribuir el proyecto, incluso con fines comerciales. Al redistribuir copias o partes sustanciales, conserva el aviso de copyright y el texto de la licencia.

La esfera incorpora ideas visuales atribuidas en [la guía de interfaces](docs/INTERFACES_MX.md). Las bibliotecas y los modelos opcionales de terceros se rigen por sus respectivas licencias.
