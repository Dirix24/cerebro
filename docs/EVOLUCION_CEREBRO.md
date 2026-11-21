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

Las cuatro interfaces serán clientes del mismo núcleo. Terminal priorizará el trabajo sobre proyectos y diffs. Web se centrará en investigar y conversar. Companion será un acceso breve a voz y acciones autorizadas. Studio ofrecerá una vista de proyectos, tareas, memoria y grafo. Cada interfaz puede abrirse por separado y compartir tareas y contexto por el API local.

En el núcleo, separar sesión e intención, políticas de permisos, herramientas tipadas, recuperación de memoria, inferencia propia y evaluación. Una solicitud debe identificar el ámbito del proyecto, las fuentes consultadas y si produjo cambios. Los clientes pueden mostrar los resultados sin volver a ejecutar la operación. El grafo y la telemetría se alimentan de los hechos registrados; la evaluación de modelos se ejecuta aparte.

Referencias iniciales: [permisos por operación en OpenCode](https://opencode.ai/docs/permissions), [modos de permisos en Claude Code](https://docs.anthropic.com/en/docs/claude-code/cli-usage), [control de cambios en Aider](https://aider.chat/docs/git.html) y [repositorio de Codex CLI](https://github.com/openai/codex). La propuesta es adoptar permisos acotados y cambios revisables. Las interfaces y los componentes de inferencia de Cerebro siguen siendo propios.

## Orden de trabajo

1. Inventario, diagnóstico y conectores públicos acotados. **Primera entrega de esta rama.**
2. Sesiones y ámbitos de proyecto en el núcleo. Unificar permisos, identidad, memoria y referencias entre los clientes.
3. Programación asistida. Primero exploración local, propuestas de cambios y comprobaciones autorizadas; después diffs más amplios y evaluación en repositorios de prueba.
4. Chat web y seguimiento. Mantener evidencia, archivos y conversación al cambiar de interfaz.
5. Companion. Probar voz local bajo activación explícita y controles de permiso para acciones de escritorio.
6. Studio y Universe. Hacer visibles cambios del grafo, fuentes, tareas y métricas observadas.
7. Aprendizaje y herramientas. Separar corrección, memoria y entrenamiento. Evaluar ejemplos aprobados antes y después de cambiar pesos o incorporar una herramienta.
8. Medir arranque, RAM y tiempo de respuesta en equipos modestos. Documentar el despliegue y publicar evaluaciones reproducibles.

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
