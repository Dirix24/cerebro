# Cerebro en MX Linux

Instala desde la carpeta del repositorio:

```sh
./instalar
```

La instalación inicial requiere Python 3 con soporte de entornos virtuales. En MX Linux, `python3-venv` aporta ese soporte y `python3-tk` permite abrir el acompañante. Para leer PDF con texto seleccionable, instala `poppler-utils`. Para consultar los formatos, pistas y duración de un vídeo, instala `ffmpeg`. Usa el gestor de paquetes de tu sistema para esas dependencias.

El acompañante se abre al terminar la instalación en una sesión gráfica y al iniciar sesión. También puedes abrirlo directamente desde **Cerebro Escritorio** en el menú de aplicaciones. La ventana y el núcleo se ejecutan por separado de la terminal, así que puedes cerrar la consola después de iniciarlo.

El menú de aplicaciones muestra **Cerebro Terminal**, **Cerebro Escritorio**, **Cerebro Chat** y **Cerebro Studio**. También puedes escribir `cerebro` en terminal o añadir `escritorio`, `chat` o `studio`. Si la terminal abierta todavía no encuentra el comando, ejecuta `export PATH="$HOME/.local/bin:$PATH"` una vez en esa sesión. `./instalar --sin-autoinicio` quita el autoinicio y omite la apertura al terminar la instalación.

- **Terminal** abre la conversación de texto dentro de la consola. Escribe «Salir» para volver al escritorio. Da prioridad a programación y revisión de archivos. Usa `/studio` para abrir el editor, `/web` para abrir el chat y `/historial` para consultar las últimas intervenciones. Las flechas recuperan las entradas de la sesión en consolas con Readline. Las acciones del usuario activan su interfaz. Los sondeos de fondo no se quedan con el foco.
- **Escritorio** muestra un acompañante de esquina con el núcleo circular inspirado en [NeuralCore de Arquitectura-Arus](https://github.com/Dirix24/Arquitectura-Arus/blob/9795ea0ae8168f0989096b0f90851fae38edc772/arus/interface/core_visual.py) (MIT, Dirix24 y colaboradores de Arquitectura ARUS). Pulsa **Recoger** para dejar a la vista solo el núcleo y su estado, y **Abrir chat** para recuperar la conversación. Escape recoge el panel y **Accesos → Copiar respuesta** copia la última respuesta. Usa **Enviar** o Enter para escribir, **Dictar** para hablar y **Accesos** para abrir otras interfaces o elegir el audio. Sus anillos y nodos son decorativos; el rótulo «Procesando» indica que hay una respuesta pendiente. Se oculta al abrir la terminal de Cerebro o una vista web de Cerebro, y vuelve cuando esas vistas se cierran o se ocultan. El relevo puede tardar hasta siete segundos si un proceso termina sin avisar. Abrir otra aplicación del equipo deja el acompañante disponible. También puedes dictar una petición o escuchar la respuesta con la [configuración de voz local](VOZ_LOCAL.md).
- **Chat** abre una página de conversación, investigación, historial, recuerdos y adjuntos. La barra lateral ofrece **Abrir terminal**, **Mostrar acompañante** y **Núcleo Universe**. Los dos primeros accesos usan el lanzador local. Enter envía el mensaje y Mayús+Enter añade otra línea. Si falla el envío, el borrador queda disponible. Al minimizar el navegador o cambiar de pestaña, Chat cede el foco al acompañante.
- **Studio** abre una aplicación nativa de escritorio con explorador, editor, validación de sintaxis, adjuntos y conversación. «Quiero programar» la abre desde el chat, la terminal o el acompañante. Al minimizar Studio aparece el acompañante. Su botón **Studio** restaura la misma ventana y conserva el trabajo que hay en el editor. Usa Ctrl+P para filtrar archivos y Ctrl+S para guardar. La pestaña **Universe** muestra el mapa nativo. El menú de MX Linux abre **Chat**. Su barra lateral permite cambiar a **Studio** en la web y volver a Chat con la misma sesión. Su acceso a **Núcleo Universe** abre la pestaña nativa de Studio. El servidor independiente de Universe conserva sus paneles para Canvas y Body. El HUD y la organización de herramientas están inspirados en [Arquitectura-Arus](https://github.com/Dirix24/Arquitectura-Arus). El servidor web independiente conserva un modo Studio para el navegador.

Las cuatro entradas se conectan al mismo servicio autenticado en loopback. Comparten los recuerdos y el historial local. Los comandos y las peticiones reconocidas de recuperación de datos privados quedan fuera del historial compartido. El perfil de servidor independiente se sigue iniciando como se indica en [la guía de Universe](UNIVERSE.md). El comando `cerebro apagar` detiene el servicio de escritorio. Si dejas abierto el acompañante, este puede volver a iniciarlo al enviarle otro mensaje.

## Qué puedes pedir

| Frase | Resultado |
| --- | --- |
| «Investiga la fotosíntesis» | Busca en Wikipedia en español y cita el artículo. |
| «¿Qué son los tardígrados?» | Primero intenta responder con recursos locales. Consulta Wikipedia si se queda sin respuesta y reconoce un tema público admisible. |
| «Noticias de hoy» o «Investiga» | Consulta titulares publicados en el feed de BBC Mundo y muestra la fecha y el enlace de cada uno. |
| «Escribe una función en Python para sumar dos números» | Genera una función de las operaciones aritméticas admitidas. |
| «Resume adjuntos/informe.pdf» | Resume de forma extractiva el texto disponible, hasta 12 páginas. Admite también texto, CSV y DOCX. |
| «Revisa adjuntos/prueba.py» | Identifica funciones, clases e importaciones sin ejecutar el archivo. |
| «Aprende de este modelo» | Guarda las medidas del último OBJ analizado y muestra una ficha vinculada en Universe. |
| «Analiza el vídeo adjuntos/clip.mp4» | Si FFprobe está instalado, muestra duración, resolución y pistas. Con `clip.srt` o `clip.vtt` adjunto, extrae los subtítulos. |

Al adjuntar desde Chat o Studio, Cerebro analiza el archivo automáticamente. Después puedes decir «Explícame» para ver los pasajes principales y los temas detectados. «Guarda lo aprendido de este archivo» guarda el análisis en la memoria compartida. El último archivo analizado se conserva en el núcleo mientras está en ejecución. El análisis admite adjuntos de hasta 16 MiB, dentro de la cuota del espacio de trabajo. El navegador reproduce localmente los vídeos compatibles con sus códecs. Están pendientes el OCR de documentos escaneados, la interpretación visual de escenas y la transcripción propia de audio. Las operaciones aritméticas y las deducciones usan reglas comprobables. El modelo propio sigue teniendo un rendimiento limitado en conversación y programación general.

### Modo táctil experimental y revisión de aprendizaje

«Cerebro, activa el modo táctil» abre un panel local. Elige una cámara, pulsa **Activar cámara** y confirma. El panel indica cuándo hay captura y permite detenerla con **Pausar** o Esc mientras está enfocado. La cámara se libera al detener el seguimiento. Las imágenes se procesan en memoria. **Ver cámara** muestra los puntos detectados y pausa el control del puntero. Con **Dibujar figura**, mantén la pinza mientras trazas un contorno y separa los dedos para terminar. **Convertir a 3D** da grosor al contorno y **Guardar OBJ** exporta la malla. **Usar puntero** vuelve al control del escritorio.

El adaptador experimental requiere Linux X11, `xdotool`, OpenCV, MediaPipe Tasks y un archivo local `hand_landmarker.task` indicado por `CEREBRO_MODELO_MANOS`. Comprueba la compatibilidad de estas dependencias con tu Python antes de instalarlas. La primera versión usa una zona central fija para mover el puntero, pinza breve para pulsar, pinza mantenida para arrastrar y una segunda mano para desplazar. La comprobación con una cámara y manos reales queda pendiente.

**Analizar** en Universe muestra el número de evaluaciones, correcciones y entrenamientos registrados, y genera propuestas a partir de esos datos. El entrenamiento de pesos sigue siendo una operación separada.

### Proyectos Python en Studio nativo

Pulsa **Abrir proyecto**, elige una carpeta de trabajo y confirma el acceso. El explorador muestra rutas relativas de archivos de texto y permite filtrarlas. Abre un archivo para editarlo. Studio pide confirmación al guardar en el proyecto y comprueba que el archivo siga coincidiendo con la versión que abriste.

Escribe «Cerebro, analiza este proyecto y corrige sus errores» o pulsa **Analizar**. Studio revisa la sintaxis de Python y muestra los diagnósticos. Puede proponer dos puntos ausentes o un delimitador final cuando el compilador acepta el archivo corregido. **Aplicar propuesta** requiere una confirmación por archivo. **Pruebas** ejecuta `unittest` en Bubblewrap sobre una copia de solo lectura, sin red del equipo ni acceso a la carpeta personal. Si el aislamiento no puede arrancar, Studio no ejecuta el proyecto. El resultado se muestra en **Validaciones**.

Para consultar un adjunto, adjúntalo y espera el análisis. Puedes preguntar «¿Qué dice el PDF adjunto sobre el presupuesto?». Cerebro devuelve pasajes del archivo con coincidencias y el alcance de la extracción. Los PDF escaneados necesitan OCR fuera de este flujo.

### Memoria y conversación compartidas

Prueba «Guarda esta memoria: proyecto = Atlas» en una interfaz y `/recuerdo proyecto` en otra. Las cuatro usan la misma memoria persistente. Si cambias de chat, el contexto inmediato pasa a la conversación elegida y los recuerdos guardados siguen disponibles. Chat web, Studio y la esfera se actualizan cuando otro cliente añade turnos al historial compartido. En Terminal, `/historial` muestra los intercambios guardados más recientes.

### Aplicaciones y ventanas

«Abre Blender» busca el nombre en las aplicaciones visibles de GIO. «Busca el archivo presupuesto» devuelve nombres de documentos en las carpetas habilitadas. «Abre el navegador e investiga la fotosíntesis» combina una consulta pública autorizada con la apertura del navegador.

En XFCE/X11, «Minimiza esta ventana» y «Cierra LibreOffice» consultan las ventanas reales mediante `wmctrl`, `xprop` y `xdotool`. Si hay varias coincidencias, elige por número. El cierre requiere «Confirmar cierre» en la misma sesión y deja que la aplicación gestione sus cambios sin guardar. En Wayland, Cerebro informa que necesita un adaptador del compositor.

### Búsquedas y combinaciones de herramientas

Prueba «Abre YouTube y busca un tutorial de Blender» para abrir los resultados en el navegador. «Abre este enlace» utiliza la última URL explícita del cliente. «Analiza este enlace» admite artículos públicos de Wikipedia en español. Estos pasos requieren conexión autorizada.

«Búscame todos mis PDF», «Encuentra las fotos de vacaciones» y «Busca los vídeos que descargué esta semana» consultan metadatos en Documentos y Descargas. Los filtros temporales usan la fecha de modificación. «Abre Blender y busca mi último proyecto» solicita la apertura del `.blend` más reciente a su aplicación asociada. La aplicación puede aceptar la solicitud aunque Cerebro todavía no haya confirmado la ventana o la reproducción.

Para generar un archivo, prueba «Busca mis PDF de física, abre el más reciente, hazme un resumen y guárdalo en una carpeta». Tras revisar el resultado, escribe **Confirmar guardar resumen** en la misma interfaz. El archivo se guarda en `resumenes/` dentro del espacio de Studio.

### Abrir y recordar documentos

1. Escribe o dicta «Cerebro, abre mi documento de matemáticas». Cerebro busca por nombre en Documentos y Descargas y pide elegir por número si hay varias coincidencias.
2. GIO identifica el formato por el nombre y solicita la apertura a la aplicación predeterminada de la sesión Linux. Este flujo requiere `python3-gi`. «¿Qué aplicaciones tengo instaladas?» muestra programas visibles y los tipos MIME que declaran.
3. Si ves el archivo en pantalla, responde «Sí, recuérdalo» para guardar la selección. Después de reiniciar, «Abre el documento de matemáticas otra vez» funciona en cualquiera de las interfaces. «Olvida el documento de matemáticas» elimina la selección.
4. Universe muestra un registro del formato y el programa confirmado. Tras guardar la selección, «Aprueba ejemplo de apertura» añade al banco del alumno una frase genérica sin nombres, rutas ni contenido del documento. El entrenamiento se ejecuta por separado con `entrenar_ejemplos_aprobados.py`.

Para desactivar la búsqueda y apertura de archivos personales, detén el servicio e inicia el lanzador con `CEREBRO_SIN_DOCUMENTOS=1`. Las acciones de apertura usan nombres y asociaciones del escritorio. **Nuevo chat** inicia una conversación vacía y conserva el historial anterior. **Eliminar chat** borra solo la conversación activa tras confirmar. Usa el selector de Chat web o Studio para volver a una conversación guardada. En Studio nativo, las comprobaciones de código aparecen en la pestaña **Validaciones** junto al editor. En Terminal usa `/nuevo-chat`, `/chats` y `/eliminar-chat`. Usa **Todos los chats** en la web o **Chats** en la esfera y Studio para marcar conversaciones y eliminarlas en grupo. En Terminal, escribe `/chats`, elige `borrar` e indica números separados por comas o `todos`. El núcleo conserva la selección al reiniciar y abre el historial anterior de la instalación como **Conversación anterior**. Los recuerdos guardados tienen su propio control de olvido.

### Aprender de modelos 3D

Adjunta un archivo Wavefront `.obj` en Chat o Studio y espera el análisis. Cerebro cuenta vértices y caras, mide la caja envolvente en X, Y y Z y señala caras con referencias repetidas. «Explícame» detalla qué significan esas medidas. «Aprende de este modelo» conserva los resultados y la huella SHA-256 en la memoria compartida. El mismo contenido se guarda una sola vez aunque lo adjuntes con otro nombre.

Abre la pestaña **Universe** de Studio y selecciona la ficha con el nombre del OBJ. Ahí se muestran sus medidas, procedencia y vínculo con el recuerdo persistente. Arrastra para girar el mapa y usa la rueda para ampliar. Las posiciones y la esfera son recursos visuales para explorar el grafo. El analizador mide geometría; la ficha se almacena como memoria estructurada. En esta fase se admite OBJ de hasta 16 MiB y el mapa representa el aprendizaje. La previsualización de mallas, otros formatos 3D y el entrenamiento neuronal con geometría quedan pendientes.

El lanzador para escritorio habilita las consultas a fuentes públicas. Cerebro prepara la consulta usando la petición actual. El historial, los recuerdos y los adjuntos se procesan localmente. Para iniciar el núcleo sin acceso web, detén el servicio y ejecuta `CEREBRO_SIN_INTERNET=1 cerebro`. La actualidad se consulta cuando la pides y queda atribuida a su fuente.

Para desinstalar, cierra el acompañante, ejecuta `cerebro apagar` y después `python3 cerebro.py desinstalar --confirmar` desde el repositorio. Se eliminan el entorno y las entradas que instaló este repositorio, y se conservan los recuerdos.
