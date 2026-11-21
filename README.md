# Cerebro

Cerebro es un asistente local de código abierto para MX Linux. Cuatro interfaces comparten un núcleo, conversaciones, recuerdos y herramientas. El proyecto combina modelos propios en NumPy y PyTorch con herramientas verificables para documentos, proyectos Python, escritorio y consulta de fuentes públicas.

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

Las cuatro conservan el diseño negro con acentos azules y el núcleo escucha en loopback con autenticación. **Nuevo chat** conserva los chats anteriores. Desde **Chats** puedes recuperarlos o seleccionar cuáles eliminar. En Terminal están `/nuevo-chat`, `/chats` y `/historial`. Guarda un dato con `/recordar proyecto = Atlas` y recupéralo con `/recuerdo proyecto` desde otra interfaz.

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

## Escritorio y control por manos

«Abre Blender» busca aplicaciones en GIO. «Abre mi documento de matemáticas» busca el archivo por nombre en Documentos y Descargas. Si hay varias coincidencias, elige una. Cerebro solo guarda la selección cuando la confirmas. Con `CEREBRO_SIN_DOCUMENTOS=1` puedes desactivar esa capacidad al arrancar.

En X11, «Minimiza esta ventana» y «Cierra LibreOffice» usan `wmctrl`, `xdotool` y `xprop`. Cerrar requiere confirmación. En Wayland falta un adaptador del compositor.

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

## Contribuir y licencia

Crea una rama, añade pruebas para los cambios de comportamiento y señala qué verificaste en MX Linux y qué sigue pendiente. Conserva los datos personales, modelos externos y dependencias locales fuera del repositorio.

Cerebro se distribuye bajo [MIT](LICENSE). La esfera incorpora ideas visuales atribuidas en [la guía de interfaces](docs/INTERFACES_MX.md). El código del proyecto, los modelos opcionales y sus dependencias tienen sus propias licencias.
