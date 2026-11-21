# Cerebro en MX Linux

Instala desde la carpeta del repositorio:

```sh
./instalar
```

La instalación inicial requiere Python 3 con soporte de entornos virtuales. En MX Linux, `python3-venv` aporta ese soporte y `python3-tk` permite abrir el acompañante. Para leer PDF con texto seleccionable, instala `poppler-utils`. Para consultar los formatos, pistas y duración de un vídeo, instala `ffmpeg`. Usa el gestor de paquetes de tu sistema para esas dependencias.

El menú de aplicaciones muestra **Cerebro Terminal**, **Cerebro Escritorio**, **Cerebro Chat** y **Cerebro Studio**. También puedes escribir `cerebro` en terminal o añadir `escritorio`, `chat` o `studio`. Si la terminal abierta todavía no encuentra el comando, ejecuta `export PATH="$HOME/.local/bin:$PATH"` una vez en esa sesión. `./instalar --sin-autoinicio` desactiva el acompañante al iniciar sesión.

- **Terminal** abre la conversación de texto dentro de la consola. Escribe «Salir» para volver al escritorio. Da prioridad a programación y revisión de archivos. Las acciones del usuario activan su interfaz. Los sondeos de fondo no se quedan con el foco.
- **Escritorio** muestra un acompañante de esquina con el núcleo circular inspirado en [NeuralCore de Arquitectura-Arus](https://github.com/Dirix24/Arquitectura-Arus/blob/9795ea0ae8168f0989096b0f90851fae38edc772/arus/interface/core_visual.py) (MIT, Dirix24 y colaboradores de Arquitectura ARUS). Sus anillos y nodos son decorativos; el rótulo «Procesando» indica que hay una respuesta pendiente. Se oculta al abrir la terminal de Cerebro o una vista web de Cerebro, y vuelve cuando esas vistas se cierran o se ocultan. El relevo puede tardar hasta siete segundos si un proceso termina sin avisar. Abrir otra aplicación del equipo deja el acompañante disponible.
- **Chat** abre una página de conversación, investigación, historial, recuerdos y adjuntos. **Núcleo Universe** abre el mapa 3D directamente.
- **Studio** abre una aplicación nativa de escritorio con explorador, editor, validación de sintaxis, adjuntos y conversación. «Quiero programar» la abre desde el chat, la terminal o el acompañante. El botón **Universe** abre el mapa y da acceso a Canvas y Body. El HUD y la organización de herramientas están inspirados en [Arquitectura-Arus](https://github.com/Dirix24/Arquitectura-Arus). El servidor web independiente conserva un modo Studio para el navegador.

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
| «Analiza el vídeo adjuntos/clip.mp4» | Si FFprobe está instalado, muestra duración, resolución y pistas. Con `clip.srt` o `clip.vtt` adjunto, extrae los subtítulos. |

Al adjuntar desde Chat o Studio, Cerebro analiza el archivo automáticamente. Después puedes decir «Explícame» para ver los pasajes principales y los temas detectados. «Guarda lo aprendido de este archivo» guarda el análisis en la memoria compartida. El último archivo analizado se conserva en el núcleo mientras está en ejecución. El análisis admite adjuntos de hasta 16 MiB, dentro de la cuota del espacio de trabajo. El navegador reproduce localmente los vídeos compatibles con sus códecs. Están pendientes el OCR de documentos escaneados, la interpretación visual de escenas y la transcripción propia de audio. Las operaciones aritméticas y las deducciones usan reglas comprobables. El modelo propio sigue teniendo un rendimiento limitado en conversación y programación general.

El lanzador para escritorio habilita las consultas a fuentes públicas. Cerebro prepara la consulta usando la petición actual. El historial, los recuerdos y los adjuntos se procesan localmente. Para iniciar el núcleo sin acceso web, detén el servicio y ejecuta `CEREBRO_SIN_INTERNET=1 cerebro`. La actualidad se consulta cuando la pides y queda atribuida a su fuente.

Para desinstalar, cierra el acompañante, ejecuta `cerebro apagar` y después `python3 cerebro.py desinstalar --confirmar` desde el repositorio. Se eliminan el entorno y las entradas que instaló este repositorio, y se conservan los recuerdos.
