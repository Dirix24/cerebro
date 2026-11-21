# Evolución de Cerebro

Cerebro, creado por Danny Jesús, se mantiene como proyecto MIT. Esta revisión parte de `main` en `9283881`. La integración se propone en `feature/investigacion-y-repositorios`.

## Diagnóstico

| Componente | Estado observado | Qué conservar o resolver |
| --- | --- | --- |
| Modelos y evaluación | Transformer NumPy propio, checkpoint base, Reasoning V3 en PyTorch y entrenamiento/evaluación reproducibles. El experimento V3 mide operaciones acotadas. | Conservar los pesos propios y comparar respuestas inéditas, exactitud y abstenciones antes de extender el uso del modelo. |
| Núcleo compartido | `universe/nucleo.py` reutiliza `chat.py`, el agente controlado y las herramientas locales. Terminal, Chat, Companion y Studio conectan al mismo proceso mediante una API local autenticada. Hay lanzadores antiguos que abren un chat separado. | Centralizar el enrutamiento de capacidades, conservar compatibilidad con el CLI y medir el aislamiento de fallos y la latencia. |
| Memoria y conocimiento | Recuerdos JSON, historial JSONL, conocimiento y habilidades en SQLite. Existen recuperación semántica, respaldo y fichero de ejemplos aprobados. | Diferenciar memoria personal, conocimiento con procedencia, reglas aprendidas y pesos entrenados. Probar concurrencia, corrección, borrado y recuperación. El historial y el contenido de un archivo requieren ámbitos claros. |
| Programación | Editor, inventario del espacio de trabajo, análisis AST y validación de sintaxis. El chat genera funciones aritméticas sencillas. | Preparar un flujo de proyecto, lectura, propuesta de diff, aprobación y validación reproducible. |
| Internet | Wikipedia, titulares de BBC Mundo y consultas básicas de GitHub. El acceso está condicionado por la configuración de red. | Reutilizar la política de conexión y ofrecer fuentes con enlaces verificables. La primera ampliación añade exploración de GitHub y búsqueda web general optativa. |
| Escritorio y voz | Companion nativo, relevo de interfaz, Studio nativo y utilidades experimentales de voz y escritorio. | Diseñar entrada por pulsación explícita y revocación. Verificar X11 y Wayland por separado. Medir antes de añadir captura continua. |
| Visualización | Universe representa registros, recuerdos, fichas y habilidades. Sus órbitas son una animación. | Registrar procedencia, tipo y cambios de vínculos. Para actividad matemática del modelo, definir mediciones explícitas y distinguirlas del grafo. |
| Instalación y pruebas | Lanzador para MX Linux, dependencias base NumPy y PyTorch opcional, licencia MIT y flujos de CI. | Resultado previo al cambio: 296 pruebas y 3 subpruebas aprobadas con el entorno completo. Conservar pruebas sin credenciales ni red externa obligatoria. |

## Arquitectura objetivo

Las cuatro interfaces serán clientes del mismo núcleo. Terminal priorizará el trabajo sobre proyectos y diffs. Web se centrará en investigar y conversar. Companion será la esfera azul flotante desde la que se puede conversar, actuar y enseñar procedimientos por voz o por escrito. Usará el mismo modelo alumno, memoria, permisos y herramientas que Terminal, Chat web y Studio. Studio ofrecerá una vista de proyectos, tareas, memoria y grafo. Cada interfaz puede abrirse por separado y compartir tareas y contexto por el API local.

En el núcleo, separar sesión e intención, políticas de permisos, herramientas tipadas, recuperación de memoria, inferencia propia y evaluación. Una solicitud debe identificar el ámbito del proyecto, las fuentes consultadas y si produjo cambios. Los clientes pueden mostrar los resultados sin volver a ejecutar la operación. El grafo y la telemetría se alimentan de los hechos registrados; la evaluación de modelos se ejecuta aparte.

Referencias iniciales: [permisos por operación en OpenCode](https://opencode.ai/docs/permissions), [modos de permisos en Claude Code](https://docs.anthropic.com/en/docs/claude-code/cli-usage), [control de cambios en Aider](https://aider.chat/docs/git.html) y [repositorio de Codex CLI](https://github.com/openai/codex). La propuesta es adoptar permisos acotados y cambios revisables. Las interfaces y los componentes de inferencia de Cerebro siguen siendo propios.

## Orden de trabajo

1. Inventario, diagnóstico y conectores públicos acotados. **Primera entrega de esta rama.**
2. Sesiones y ámbitos de proyecto en el núcleo. Unificar permisos, identidad, memoria y referencias entre los clientes.
3. Programación asistida. Primero exploración local, propuestas de cambios y comprobaciones autorizadas; después diffs más amplios y evaluación en repositorios de prueba.
4. Chat web y seguimiento. Mantener evidencia, archivos y conversación al cambiar de interfaz.
5. Companion. Integrar voz local bajo activación explícita y el flujo de búsqueda, apertura y aprendizaje de tareas de escritorio descrito abajo.
6. Studio y Universe. Hacer visibles cambios del grafo, fuentes, tareas y métricas observadas.
7. Aprendizaje y herramientas. Registrar resultados comprobados, recuperar procedimientos entre interfaces y evaluar ejemplos aprobados antes y después de entrenar el modelo alumno o incorporar una herramienta.
8. Medir arranque, RAM y tiempo de respuesta en equipos modestos. Documentar el despliegue y publicar evaluaciones reproducibles.

## Acompañante inteligente y aprendizaje continuo

Esta ampliación del plan maestro distribuye el trabajo entre comprensión del lenguaje, control del escritorio, núcleo compartido, voz, aprendizaje y validación.

| Fase del plan maestro | Entrega prevista |
| --- | --- |
| 1 y 4 · Comprensión y voz | Pasar texto y dictado por el mismo intérprete de intenciones. Admitir errores de escritura y transcripción. Si hay dudas que cambian el archivo o la operación, pedir una aclaración breve. |
| 2 · Control del escritorio | Buscar por nombre y formato dentro de carpetas autorizadas. Consultar las aplicaciones instaladas y sus asociaciones de archivo mediante adaptadores de cada sistema. Aprender qué funciones ofrecen a partir de metadatos, documentación y acciones comprobadas. Si hay varios documentos plausibles, mostrar opciones y esperar la elección. |
| 3 y 8 · Núcleo compartido y Universe | Usar el núcleo para resolver la intención, comprobar permisos, ejecutar la herramienta y registrar el resultado. Compartir preferencias, referencias, procedimientos y evidencias con Terminal, Chat web, Studio y Companion. Mostrar en Universe los resultados y su procedencia con el nivel de detalle permitido. |
| 5 y 7 · Aprendizaje por experiencia | Guardar la preferencia o el procedimiento cuando el usuario lo enseñe o confirme y registrar el resultado comprobado de las acciones autorizadas. Conservar condiciones, herramienta, evidencia y fecha. Permitir consultar, corregir y olvidar lo aprendido. Proponer automatizaciones a partir de tareas encomendadas que se repitan y pedir autorización antes de activarlas. |
| 6 y 11 · Investigación y comprobación | Si falta un procedimiento y la red está habilitada, consultar documentación pública con una consulta libre de datos privados. Probar el procedimiento con herramientas autorizadas en modo de solo lectura o sobre datos de prueba. Guardar los pasos reutilizables cuando el resultado confirme que funcionaron. |
| 12 y 13 · Portabilidad y validación | Verificar búsqueda, asociaciones, permisos y reapertura en Linux, Windows y macOS. Mantener las acciones sobre el ordenador limitadas al equipo y al ámbito autorizados. |

### Recuerdos, procedimientos y entrenamiento

Una referencia recordada ayuda a localizar un documento en el siguiente turno. El núcleo debe volver a verificar que existe y que la sesión conserva permiso para acceder al archivo. Si el documento se movió o la referencia es ambigua, ofrecer una nueva búsqueda en el ámbito autorizado. Una solicitud aceptada por el sistema operativo y una apertura confirmada son resultados distintos. Guardar y mostrar el grado de verificación disponible.

Los procedimientos comprobados se recuperan de la memoria y se reutilizan desde cualquier interfaz. Los ejemplos aprobados que sirvan para generalizar pueden alimentar el entrenamiento local del modelo alumno. Evaluar el candidato sobre tareas reservadas antes de sustituir el modelo activo, conservar el checkpoint anterior y comprobar que el aprendizaje respeta los permisos. Los documentos personales y sus extractos requieren autorización específica para incorporarse al conjunto de entrenamiento.

### Privacidad y criterios de aceptación

La esfera flotante acepta tareas escritas o dictadas mediante activación explícita. El aprendizaje se limita a solicitudes del usuario, interacciones autorizadas y resultados comprobados. La captura de pantalla, el micrófono y la lectura de archivos se usan solo para la tarea autorizada, sin grabación continua ni vigilancia de fondo. Antes de modificar, borrar o compartir un archivo, mostrar el archivo y el efecto de la acción y solicitar confirmación. Para compartir, identificar también el destino.

- Pedir por voz o por texto «abre mi documento de matemáticas», resolver una coincidencia única o preguntar cuando haya varias y abrir el archivo elegido con una aplicación compatible.
- Reiniciar Cerebro y pedir «abre el documento de matemáticas otra vez» desde Terminal, Chat web o Studio. Comprobar que se usa la referencia aprendida y que revocar el permiso impide abrirla.
- Consultar qué aprendió Cerebro y comprobar que puede mostrar la evidencia, corregir un recuerdo y explicar por qué no guardó como válido un procedimiento fallido.
- Repetir una tarea autorizada y comprobar que Cerebro propone una automatización, espera aprobación y conserva los límites de la tarea original.

## Descubrimiento y herramientas del escritorio

El núcleo recibe la orden de cualquiera de las cuatro interfaces y prepara pasos con argumentos tipados. Los adaptadores conservan las comprobaciones de permisos en la ejecución.

- Inventario de aplicaciones y compatibilidad MIME con GIO. Diagnóstico bajo demanda de aplicaciones, carpetas, extracción PDF y acceso a Internet.
- Búsqueda de PDF, fotos, vídeos y proyectos Blender por nombre, fecha de modificación y ubicación en las carpetas ya autorizadas. Las coincidencias ambiguas requieren elegir. La apertura se solicita a la aplicación asociada.
- Búsqueda de YouTube en el navegador predeterminado. Apertura de enlaces HTTP y HTTPS. El análisis de páginas usa el extracto de artículos públicos de Wikipedia en español. Los enlaces recientes se guardan solo en el contexto en memoria de cada cliente.
- Plan PDF comprobable: buscar el más reciente, solicitar su apertura y extraer un resumen. La autorización final permite escribir un archivo nuevo en el espacio de Studio. Cerebro vuelve a leerlo para comprobar el contenido.

Quedan pendientes el catálogo de paquetes y accesibilidad, la búsqueda por contenido, los resultados de YouTube dentro de Cerebro, el control de reproducción y la enseñanza supervisada por demostración. Los procedimientos futuros deberán registrar autorización, acciones, resultado observado y una forma de detenerse ante cambios de versión o interfaz.

## Primera entrega: repositorios e investigación pública

Escribe dentro de Terminal, Chat, Companion o Studio:

```text
Explora el repositorio https://github.com/Dirix24/cerebro
/github-explorar Dirix24/cerebro || universe
/github-leer Dirix24/cerebro
/github-leer Dirix24/cerebro || LICENSE
Busca en la web editores para MX Linux
```

GitHub consulta la rama predeterminada del repositorio público mediante la [REST API de contenido](https://docs.github.com/en/rest/repos/contents). Muestra hasta 45 entradas por listado y hasta 3 800 caracteres de texto por lectura. No necesita credenciales para el recorrido público. Las rutas se resuelven en GitHub, y una respuesta externa se presenta como texto citado. La implementación limita el tamaño de la respuesta, el tiempo por solicitud y los destinos permitidos. El modo sin conexión sigue bloqueando las solicitudes externas.

La búsqueda web general usa [Brave Search](https://api-dashboard.search.brave.com/app/documentation/web-search). Configura `CEREBRO_BRAVE_API_KEY` en el entorno del proceso que arranca el núcleo. Si ya está en marcha, reinícialo desde esa sesión. El proveedor recibe el tema público que escribas y devuelve hasta cinco referencias con extractos. Las referencias son resultados del buscador. Wikipedia y BBC Mundo siguen operativos sin esa clave. El proveedor de búsqueda aporta un índice web; la inferencia permanece local.

Este incremento cubre GitHub público y búsqueda pública a través de proveedores definidos. GitLab, repositorios privados, autenticación delegada y otros conectores se podrán incorporar por separado. La fase de agente de programación, la voz y la evolución del grafo quedan pendientes.

## Verificación de esta entrega

Pasaron 304 pruebas y 3 subpruebas con las dependencias opcionales instaladas. Se verificaron solicitudes reales para la raíz de Cerebro en GitHub, la carpeta `universe`, el README, la licencia y una definición en Wikipedia. La integración de Brave se comprobó con respuestas simuladas y sin una credencial real en el entorno de prueba.
