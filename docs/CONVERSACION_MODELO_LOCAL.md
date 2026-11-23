# Conversación con modelo local

Base de partida: PR #41, `2839ccd`. La ruta anterior reconocía
herramientas y acciones primero, y consultaba al Profesor cuando
el corpus devolvía un fallo o en peticiones explícitas. En consecuencia
una definición encontrada en el corpus podía saltarse el motor.

La nueva ruta consulta al Profesor en preguntas informativas reconocidas,
después de resolver herramientas y antes de llamar al corpus. Si esta
primera consulta falla, mantiene la búsqueda tradicional y evita un
segundo intento idéntico. Las consultas documentales autorizadas, la
aritmética local y los comandos conservan prioridad. Las búsquedas
públicas de respaldo muestran el extracto y la fuente cuando hay enlace.

El selector usa Ollama en loopback, verifica que el modelo está listado
y que devuelve texto antes de escribir una configuración local.
Las variables anteriores siguen permitiendo configurar un modelo de
código, uno visual, un servidor llama.cpp o un maestro GGUF bajo demanda.
Las respuestas del modelo no se ejecutan como comandos de escritorio.

El checkpoint NumPy de Cerebro se conserva. Universe distingue la
presencia del modelo propio en memoria y la configuración del Profesor.
La evaluación, los entrenamientos y la aprobación de lecciones siguen
siendo rutas separadas. Esta entrega no modifica arquitectura ni pesos.
El estado «configurado» no acredita que el servicio siga respondiendo.

Los adaptadores v1 se detectan en sus rutas configuradas o en repositorios
hermanos estándar. Detectar un archivo no ejecuta el adaptador. El envío
de tareas sigue utilizando el contrato y los permisos de coordinación
existentes.

Quedan pendientes la instalación guiada de Ollama y la descarga con
estimación de recursos, la configuración gráfica, la selección dinámica
de motor, las pruebas de inferencia con un modelo generativo real y
una nueva evaluación neuronal medida en el ASUS.

Pruebas locales: 483 aprobadas y 6 omitidas, con 3 subpruebas.
La configuración, el enrutamiento generativo y el historial se
comprobaron con dobles de motor. El recorrido de Chromium comprobó los
visores, el zoom, la generación revisable y las evidencias de
coordinación que presenta Studio.
