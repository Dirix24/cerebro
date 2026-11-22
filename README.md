# 🧠 Cerebro — Asistente personal de IA local y de código abierto

**Cerebro** es un asistente personal experimental construido en Python. **Por el momento, está desarrollado principalmente para Linux**, en especial **MX Linux con XFCE y X11**. El soporte para otros sistemas operativos es una posibilidad futura, **no una función disponible actualmente**. Une conversación, memoria, archivos, proyectos, navegación, herramientas del escritorio y aprendizaje neuronal supervisado en un núcleo local compartido.

**Repositorio:** https://github.com/Dirix24/cerebro · **Licencia:** [MIT](LICENSE) · **Estado:** desarrollo activo / experimental

> **Creación con IA, sin ocultarlo:** la idea, los objetivos y la dirección del proyecto corresponden a **Dirix24**. El software se ha desarrollado en gran medida **con asistencia de inteligencia artificial**, incluidos ChatGPT y Codex, para diseño, programación, documentación y pruebas. El código asistido por IA requiere revisión y verificación como cualquier otro código.
>
> **No es una IA general ni un sustituto de los grandes modelos comerciales.** Muchas funciones son específicas, otras experimentales y algunas siguen pendientes de pruebas reales.

## Índice

1. [Qué es Cerebro](#qué-es-cerebro)
2. [Instalación, desinstalación y comandos](#instalación-desinstalación-y-comandos)
3. [Las cuatro interfaces](#las-cuatro-interfaces)
4. [Ejemplos de cosas que puedes pedirle](#ejemplos-de-cosas-que-puedes-pedirle)
5. [Maestro Qwen y alumno neuronal](#maestro-qwen-y-alumno-neuronal)
6. [Memoria, Universe y ANALIZAR](#memoria-universe-y-analizar)
7. [Studio y programación](#studio-y-programación)
8. [Escritorio, demostraciones y voz](#escritorio-demostraciones-y-voz)
9. [Internet, descargas y GitHub](#internet-descargas-y-github)
10. [Arquitectura y seguridad](#arquitectura-y-seguridad)
11. [Pruebas y estado real](#pruebas-y-estado-real)
12. [Cómo colaborar y licencia](#cómo-colaborar-y-licencia)

## Qué es Cerebro

La idea de Cerebro es tener **un asistente propio, local y extensible** que pueda entender órdenes habituales y usar herramientas reales con permisos, en lugar de limitarse a producir texto. Su diseño conecta cuatro interfaces a un servicio local y a las mismas herramientas, recuerdos y registros.

Cerebro puede realizar tareas acotadas como buscar documentos autorizados, abrir aplicaciones, consultar fuentes públicas, inspeccionar proyectos, ejecutar verificaciones controladas y registrar demostraciones de escritorio. Cuando una acción necesita autorización, el sistema debe pedirla y verificar el resultado.

**Local por diseño:** los modelos, recuerdos y proyectos pueden permanecer en el equipo. Las consultas web y las descargas sí usan internet. El maestro Qwen es opcional y requiere tener instalados por separado llama.cpp y los pesos GGUF; Cerebro no los descarga automáticamente.

## Instalación, desinstalación y comandos

### Requisitos

Proyecto orientado a **MX Linux / Debian con XFCE y X11**. Se necesita Python 3. Las capacidades de escritorio dependen de herramientas como `wmctrl`, `xdotool`, `xprop` y AT-SPI; la ejecución aislada de pruebas requiere Bubblewrap y namespaces disponibles. Para PDF de texto se usa `pdftotext` de Poppler. Algunas funciones utilizan Pillow, Vosk, OpenCV, MediaPipe o PyTorch opcionalmente.

Desde la carpeta del repositorio:

```bash
# Instalar Cerebro para tu usuario
./instalar

# Hacer disponible el comando en esta terminal
export PATH="$HOME/.local/bin:$PATH"

# Arrancar Cerebro
cerebro iniciar

# Consultar estado
cerebro estado
```

Instalar sin activar el inicio automático:

```bash
./instalar --sin-autoinicio
```

### Comandos principales

| Acción | Comando |
| --- | --- |
| Instalar | `./instalar` |
| Instalar sin autoinicio | `./instalar --sin-autoinicio` |
| Iniciar Cerebro con Studio como ventana principal | `cerebro iniciar` |
| Detener servicio y tareas | `cerebro detener` |
| Ver estado | `cerebro estado` |
| Abrir Studio | `cerebro studio` |
| Abrir Chat web | `cerebro chat` |
| Abrir Terminal de Cerebro | `cerebro terminal` |
| Abrir esfera de escritorio | `cerebro escritorio` |
| Activar autoinicio en XFCE | `cerebro autoinicio activar` |
| Desactivar autoinicio | `cerebro autoinicio desactivar` |
| Desinstalar conservando datos | `./desinstalar` |
| Desinstalar y solicitar borrado de datos conocidos | `./desinstalar --borrar-datos` |

El **autoinicio** se registra para la siguiente entrada en tu sesión de XFCE, no antes de iniciar sesión. Studio actúa como ventana principal; su **X** solicita apagar el servicio compartido, avisando si hay cambios sin guardar. Cerrar una ventana secundaria no siempre significa cerrar todo Cerebro.

**La desinstalación normal conserva** repositorio, proyectos, recuerdos, modelos y datos. La variante `--borrar-datos` exige escribir la frase de confirmación `BORRAR MIS DATOS` y solo afecta a las ubicaciones reconocidas por el desinstalador. Haz copias de seguridad antes de usarla.

El comando `cerebro` se instala en `~/.local/bin/`. Si tu shell no lo encuentra, añade esa carpeta al `PATH` o abre una terminal nueva tras configurarlo.

### Herramientas CLI adicionales del proyecto

El repositorio conserva también comandos del sistema clásico de Cerebro. No todos equivalen al núcleo compartido de Studio:

```bash
python3 cerebro.py --help
python3 cerebro.py diagnostico
python3 cerebro.py motores
python3 evaluate.py --rapido
python3 -m pytest -q -ra
```

Para entrenamientos especializados consulta [la guía de motores](CEREBRO_MOTORES.md). No ejecutes entrenamientos largos sobre checkpoints importantes sin respaldos.

## Las cuatro interfaces

| Interfaz | Uso principal |
| --- | --- |
| **Terminal** | Conversación y comandos locales; puede tener chat separado o sincronizarse con el chat activo |
| **Chat web** | Conversación desde el navegador local, adjuntos y herramientas |
| **Cerebro Studio** | Explorador de proyectos, editor, revisiones, pruebas, chat contextual y Universe |
| **Esfera azul** | Acompañante flotante, interacción por texto y opciones experimentales de voz |

El servicio se comunica por **loopback** (`127.0.0.1`) y usa una clave de sesión. Las interfaces comparten un núcleo y pueden compartir el chat activo, según el modo elegido.

### Conversaciones y memoria

- `/nuevo-chat`: abrir conversación nueva.
- `/chats`: consultar conversaciones.
- `/historial`: ver historial disponible.
- `/sincronizar` o **«sincronízate»**: usar en Terminal el chat activo de Studio, Chat web y esfera.
- `/separar`: volver al ámbito separado de Terminal.
- `/guardar-en-studio` o **«guarda esto en Studio»**: guardar la última respuesta como nota TXT.
- `/recordar proyecto = Atlas`: guardar un dato explícito.
- `/recuerdo proyecto`: recuperar ese dato.

La memoria persistente y el historial son funciones distintas del entrenamiento neuronal.

## Ejemplos de cosas que puedes pedirle

Los ejemplos muestran rutas concretas del proyecto. Su resultado depende de permisos, aplicaciones instaladas, datos disponibles y compatibilidad del sistema.

| Petición | Qué intenta hacer |
| --- | --- |
| «¿Qué hora es?» | Consultar la hora local |
| «¿Cuánto es dos más dos?» | Usar cálculo determinista |
| «Búscame todos mis PDF» | Buscar en carpetas autorizadas |
| «Busca los vídeos que descargué esta semana» | Filtrar archivos por tipo y fecha |
| «Busca en mis documentos: presupuesto» | Buscar texto en archivos compatibles y acotados |
| «Abre Blender» | Localizar y abrir la aplicación disponible |
| «Enfoca el navegador» | Seleccionar la ventana real en X11 |
| «Maximiza Blender» | Cambiar la ventana y verificar el resultado |
| «Cierra LibreOffice» | Solicitar confirmación y enviar cierre normal |
| «Muéstrame todas las ventanas abiertas» | Consultar ventanas X11 |
| «Abre YouTube y busca un tutorial de Blender» | Abrir resultados en el navegador |
| «Analiza este enlace de Wikipedia» | Consultar la introducción de un artículo público |
| «Estado del profesor» | Consultar disponibilidad y configuración del maestro |
| «Estado del alumno» | Consultar modelo activo y evaluación |
| «Entrenar alumno» | Solicitar un ciclo supervisado, con confirmación |
| «Estado de descarga Git» | Consultar una clonación en segundo plano |
| «Cancela descarga Git» | Cancelar una clonación iniciada desde ese chat |

**Ejemplo con confirmación:** «Cierra LibreOffice» no debe cerrar inmediatamente una ventana sin comprobar la autorización correspondiente. **Ejemplo con contexto:** después de buscar documentos, puedes seleccionar un resultado por número cuando haya varias coincidencias.

## Maestro Qwen y alumno neuronal

Una de las líneas de investigación de Cerebro es un **ciclo maestro–alumno local**:

1. **Maestro:** Qwen2.5-1.5B-Instruct en GGUF Q4_K_M, ejecutado mediante llama.cpp en CPU, propone ejemplos para una tarea concreta.
2. **Validador independiente:** filtra propuestas incorrectas o que no cumplen el contrato.
3. **Alumno:** un clasificador neuronal pequeño en NumPy entrena con ejemplos aprobados y **modifica pesos reales**.
4. **Evaluación:** compara el candidato con bancos separados, reglas y criterios de abstención.
5. **Promoción o rechazo:** conserva el candidato anterior si el nuevo no mejora lo necesario; admite reversión.
6. **Uso local:** el núcleo puede consultar un alumno aprobado sin mantener Qwen cargado continuamente.

### Comandos del ciclo supervisado

| Escribe en una interfaz compatible | Función |
| --- | --- |
| `Entrenar alumno` | Preparar solicitud de entrenamiento |
| `Confirma entrenar alumno` | Autorizar desde la conversación de origen |
| `Estado del alumno` | Consultar progreso, evaluación y candidato activo |
| `Cancela entrenar alumno` | Solicitar cancelación segura |
| `Estado del profesor` | Consultar el profesor local |

Para configurar Qwen bajo demanda, después de instalar llama.cpp y descargar legalmente el GGUF de forma separada:

```bash
export CEREBRO_PROFESOR_MOTOR="/ruta/a/llama-server"
export CEREBRO_PROFESOR_MODELO="/ruta/a/qwen.gguf"
cerebro iniciar
```

También existe la opción de un servidor local previamente autorizado mediante `CEREBRO_PROFESOR_PUERTO`; consulta [CEREBRO_MOTORES.md](CEREBRO_MOTORES.md). **No incluyas pesos GGUF en un pull request** sin revisar su licencia y tamaño.

### Resultados y límites

Los informes del proyecto documentan inferencia real de Qwen, generación y filtrado de ejemplos, cambios de pesos, uso de un candidato desde el núcleo y rollback. Las pruebas se han centrado en **hora y fecha**. **No se ha demostrado una ventaja neuronal general frente a las reglas**; algunos bancos pequeños dieron resultados equivalentes. Por eso las nuevas clases de intención se prueban primero en observación y no ejecutan automáticamente acciones.

Cerebro también contiene otros motores y experimentos de entrenamiento NumPy/PyTorch, evaluación de competencias y análisis. **No son todos el mismo alumno ni están necesariamente integrados en el chat habitual.** Consulta [Motores](CEREBRO_MOTORES.md) y [validación](docs/VALIDACION_CANDIDATO.md).

## Memoria, Universe y ANALIZAR

**Memoria** conserva información explícita y permite recuperarla entre sesiones. **Universe** representa conocimientos, relaciones, procedimientos, candidatos y evidencias; un nodo de Universe **no es** por sí mismo una neurona ni una prueba de aprendizaje de pesos.

**ANALIZAR** examina registros y resultados, señala debilidades y permite preparar ciclos controlados de entrenamiento. Las propuestas no deben considerarse mejoras hasta superar validación.

Se distinguen tres cosas:

- **Recordar:** almacenar un dato.
- **Aprender un procedimiento:** registrar una secuencia autorizada y verificable.
- **Entrenar un modelo:** cambiar pesos y medir su rendimiento fuera del entrenamiento.

## Studio y programación

Studio es el entorno de trabajo de Cerebro. Su objetivo es reunir **explorador, editor, visualizadores, chat contextual, revisión de cambios, pruebas y Universe**.

Flujo típico:

1. Abre Studio con `cerebro studio`.
2. Selecciona **Abrir proyecto** y autoriza una carpeta.
3. Explora y abre archivos compatibles.
4. Pide analizar un proyecto Python.
5. Revisa errores y propuestas en **Cambios**.
6. Confirma las modificaciones que quieras aplicar.
7. Ejecuta pruebas compatibles desde **Pruebas** y revisa **Validaciones**.

El análisis estático puede compilar Python sin ejecutarlo y proponer correcciones acotadas. No es un programador general capaz de reparar cualquier proyecto.

### Documentos

Cerebro puede trabajar con TXT, Markdown, código, DOCX y PDF con texto extraíble según la ruta utilizada. Los PDF escaneados necesitan OCR. Los visores y la apertura externa dependen del formato y de las aplicaciones instaladas.

### Ejecución segura de pruebas

La ruta de `unittest` desde Studio utiliza **Bubblewrap** cuando el sistema lo permite, con copia de trabajo acotada, límites de recursos y red aislada. Si el aislamiento no está disponible, la ejecución se rechaza. El aislamiento no equivale a una garantía absoluta frente a todo código malicioso.

## Escritorio, demostraciones y voz

En **XFCE/X11**, Cerebro usa utilidades del sistema para localizar, enfocar, minimizar, maximizar, mover y solicitar el cierre de ventanas. Verifica estados cuando la operación lo permite. Wayland necesita adaptadores específicos.

### Enseñar una demostración

Ejemplo de rutina autorizada:

1. «Empezar demostración Diseño».
2. Ejecuta las acciones compatibles una a una.
3. «Guardar demostración».
4. «Repite la demostración Diseño».

En los flujos de observación semántica con **AT-SPI**, Cerebro puede detectar cambios de casillas accesibles de una ventana autorizada, guardar un borrador, solicitar revisión y reproducir los pasos con comprobaciones. No equivale a grabar toda la pantalla ni a aprender libremente cualquier interfaz.

El sistema también tiene un **modo táctil experimental** basado en cámara y detección de manos, sujeto a dependencias y compatibilidad. No debe presentarse como una función universal ya verificada.

### Esfera y voz

La esfera puede mostrar estados e interactuar por **texto**. El dictado y la respuesta hablada son opcionales y necesitan micrófono, configuración y pruebas humanas. **Cerebro puede utilizarse sin micrófono.** La falta de una prueba de voz no debe ocultarse ni convertirse en una afirmación de que la voz ya está verificada.

## Internet, descargas y GitHub

Las funciones públicas son **acotadas**: por ejemplo, consultas a Wikipedia, fuentes de noticias, búsquedas abiertas en navegador y algunas descargas desde fuentes verificadas. No es un navegador autónomo universal.

### Clonar repositorios

Ejemplo:

```text
Clona https://github.com/octocat/Hello-World
Estado de descarga Git
Cancela descarga Git
```

La clonación HTTPS se ejecuta en segundo plano, valida el repositorio y comprueba el commit y el README. La cancelación se vincula a la conversación que inició el trabajo. El depósito utiliza un presupuesto agregado documentado de **128 MiB** con comprobaciones durante la operación y almacenamiento temporal controlado; los límites exactos dependen del sistema de archivos y la versión. No debe prometerse una cuota instantánea universal sin verificarla.

Una URL de PDF no debe enviarse al clonador Git. Los repositorios descargados son **contenido no confiable**: leerlos o inspeccionarlos no implica ejecutar su código.

## Arquitectura y seguridad

Componentes principales del repositorio:

| Área | Papel |
| --- | --- |
| `universe/nucleo.py` | Núcleo de conversación, memoria, herramientas y coordinación |
| `universe/lanzador.py` | Arranque y conexión de interfaces al servicio local |
| `universe/instalar_escritorio.py` | Comandos, accesos y autoinicio de XFCE |
| `universe/herramientas.py` | Catálogo y ejecución de herramientas, incluida descarga Git |
| `universe/` | Studio, esfera, servidor y adaptadores |
| `core/` | Utilidades, modelos, validadores, seguridad y componentes |
| `agent/` | Orquestación y agentes auxiliares |
| `memory/` | Memoria y recuperación |
| `checkpoints/` | Pesos y checkpoints del proyecto |
| `tests/` | Pruebas automatizadas |
| `docs/` | Guías técnicas y continuidad |

La estructura exacta puede evolucionar; usa el árbol del repositorio como referencia para tu commit.

### Principios de seguridad

- Permisos **READ/WRITE** para operaciones relevantes.
- Confirmaciones vinculadas a la conversación para acciones sensibles.
- Validación de rutas, destinos y parámetros.
- Comprobación del resultado cuando sea posible.
- Cancelación y límites de recursos para trabajos prolongados.
- Copias y candidatos separados para proteger checkpoints.
- Servicio local limitado a loopback con token de sesión.
- No ejecutar automáticamente código descargado.

Los datos persistentes pueden incluir `data/`, `memory/`, `universe-datos/`, `learning/` y `checkpoints/`. **No publiques datos personales, tokens, conversaciones ni modelos privados** al colaborar.

## Pruebas y estado real

Comando habitual:

```bash
python3 -m pytest -q -ra
```

También hay herramientas de diagnóstico y evaluación específicas. Algunas pruebas requieren acceso a loopback, Bubblewrap, XFCE/X11, cámara o micrófono. Un entorno sin esos recursos puede dejar verificaciones manuales pendientes.

Los informes de auditoría han registrado **entrenamiento real del maestro y alumno, pruebas de Studio y Chat, regresiones, protección de checkpoints y validación de clonación Git**. Los resultados corresponden a commits concretos y **no garantizan automáticamente cualquier versión posterior**.

Para detalles y evidencias: [validación del candidato](docs/VALIDACION_CANDIDATO.md), [continuidad](docs/PLAN_CONTINUIDAD_CEREBRO.md), [interfaces MX Linux](docs/INTERFACES_MX.md), [motores](CEREBRO_MOTORES.md).

### Futuras funciones que se espera desarrollar

> **Planes y objetivos, no funciones ya terminadas.** Esta lista expresa la dirección deseada del proyecto; no implica fechas de entrega ni garantiza que todas las ideas lleguen a implementarse.

**Primero: hacer más sólido Cerebro en Linux**
- Facilitar la instalación, actualización, diagnóstico y recuperación de errores.
- Completar las pruebas de voz con micrófono y altavoces reales, y mejorar la conversación en español.
- Mejorar la estabilidad de Studio, Chat web, Terminal y esfera, incluidos sus arranques y cierres.
- Ampliar la compatibilidad con otros escritorios y distribuciones Linux; estudiar Wayland y sus permisos específicos.

**Después: ampliar la utilidad diaria**
- Mejorar la comprensión de peticiones en lenguaje natural, el contexto entre conversaciones y la búsqueda de documentos.
- Desarrollar un Studio más capaz para revisar proyectos, proponer cambios, navegar por archivos y ayudar a programar, siempre con confirmación.
- Añadir más automatizaciones locales y rutinas enseñables con comprobaciones, límites y posibilidad de detenerlas.
- Ampliar la investigación web y el uso de fuentes públicas, con enlaces verificables y control del acceso a internet.
- Explorar integraciones opcionales con correo, calendario y otros servicios mediante autorización expresa.

**Investigación en IA local**
- Entrenar y evaluar alumnos para más tipos de tareas, con bancos independientes y comparación frente a reglas.
- Mejorar la colaboración entre modelos locales pequeños y maestros opcionales, reduciendo el consumo de memoria y CPU.
- Investigar aprendizaje a partir de ejemplos y correcciones aprobados por el usuario, sin ejecutar acciones nuevas sin validación.

**Ideas a más largo plazo**
- Estudiar una versión móvil o PWA y acceso remoto seguro, sin exponer directamente el servicio local.
- Explorar colaboración entre varios equipos autorizados (por ejemplo, un pequeño clúster doméstico).
- Evaluar compatibilidad con otros sistemas operativos **solo cuando la base Linux sea estable**.

La prioridad es una versión cotidiana fiable en Linux antes de extender Cerebro a nuevas plataformas.

## Cómo colaborar y licencia

**Cerebro está abierto a colaboradores.** Se agradecen informes de errores, pruebas en Linux, documentación, traducciones, mejoras de accesibilidad, diseño, seguridad y experimentos de aprendizaje reproducibles.

1. Revisa los [Issues](https://github.com/Dirix24/cerebro/issues) o abre uno con los pasos para reproducir el problema.
2. Haz un fork y crea una rama con un cambio acotado.
3. Añade pruebas cuando cambies el comportamiento.
4. Indica qué comprobaste realmente y qué quedó pendiente.
5. Envía un Pull Request con la explicación del cambio.

No hace falta contribuir con una función enorme: corregir un fallo pequeño o mejorar una guía también ayuda.

### Licencia MIT

El código y la documentación de Cerebro se ofrecen bajo la **[licencia MIT](LICENSE)**. Se permite utilizar, copiar, estudiar, modificar, distribuir y vender software derivado, conservando los avisos de copyright y licencia exigidos. Las dependencias, modelos de terceros y otros recursos pueden tener licencias diferentes.

**Cerebro es una idea humana desarrollada con ayuda de IA y abierta a que la comunidad la mejore.** 🧠💙

## Coordinación local de CEREBRO, DARAS, CAZEL y PROFESOR

Con los tres repositorios en ramas que incluyen el contrato v1:

```sh
export CEREBRO_DARAS_RAIZ=/ruta/a/Daras-IA
export CEREBRO_CAZEL_RAIZ=/ruta/a/CAZEL_IA
export CEREBRO_CAZEL_PROYECTO=/ruta/al/proyecto/autorizado
cerebro terminal
```

Dile «Investiga cómo construir un robot, planifica el proyecto, revisa el código
y comprueba lo aprendido». DARAS consulta su biblioteca local, CAZEL analiza
el proyecto y PROFESOR formula un ejercicio verificable sobre el plan. La
Terminal y el universo muestran la misma experiencia. Con internet permitido
en la sesión, añade «en internet» a la petición de investigación para usar las
fuentes públicas de DARAS.

`CEREBRO_CAZEL_PROPUESTAS=1` habilita propuestas en peticiones de desarrollo
cuando CAZEL tiene un modelo local activo. CEREBRO muestra la sesión de CAZEL
Studio donde se revisan los cambios. Si usas una carpeta de ajustes y sesiones
alternativa, configura `CEREBRO_CAZEL_DATOS` con esa ruta.
`CEREBRO_CAZEL_PRUEBAS=1` autoriza pruebas aisladas cuando se piden
expresamente. Ctrl+C cancela la coordinación desde Terminal.

Consulta [el contrato, sus pruebas y sus límites](docs/COORDINACION_V1.md).

### Trabajar con un proyecto en Studio

Usa **Abrir proyecto** y autoriza una carpeta concreta. El explorador de
Studio navega carpetas, busca por nombre y filtra tipos. Permite crear,
mover y copiar, y envía lo eliminado a `.cerebro-papelera` dentro del
proyecto. La reapertura del último proyecto requiere autorización.

El centro dispone de editor, visor, validaciones, cambios y resultados.
HTML se previsualiza como contenido estático. El visor PDF dibuja la primera
página y extrae texto de hasta ocho páginas con `poppler-utils` y `prlimit`. Pillow es opcional para ampliar
los formatos de imagen del Studio nativo. El navegador permite operar sobre
proyectos al entrar desde el núcleo del lanzador de escritorio.

En el chat de Studio, «Planifica un robot simulado, revisa el código y
comprueba lo aprendido» presenta una respuesta de CEREBRO y abre las
evidencias en **Resultados**. «Quiero ver qué aprendiste» abre **Universe**.
«Crea una página web» ofrece crear una plantilla local con confirmación.
Las propuestas del agente CAZEL se revisan en la sesión indicada de CAZEL
Studio. Los arreglos sintácticos del proyecto abierto se previsualizan y
se aprueban en CEREBRO Studio.

La prueba reproducible de navegador usa los repositorios hermanos de DARAS y
CAZEL, Playwright, Pillow y Chromium:

```sh
PYTHONPATH=. python3 tests/manual/verificar_studio.py
```

Para documentos de oficina sin visor interno, **Abrir en aplicación local**
solicita confirmación y usa la aplicación predeterminada del escritorio.
Esa acción excluye HTML y los archivos ejecutables.
