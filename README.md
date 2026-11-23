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

El **autoinicio** se registra para la siguiente entrada en tu sesión de XFCE, no antes de iniciar sesión. Studio actúa como ventana principal. Su **X** avisa si hay ediciones sin guardar y deja el núcleo activo. Si no queda otra interfaz activa, vuelve el acompañante. Para apagar el núcleo y sus tareas usa `cerebro detener`.

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

El sistema también tiene un **modo gestual experimental** basado en cámara y detección de manos, sujeto a dependencias y compatibilidad. No debe presentarse como una función universal ya verificada.

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


### Studio como escritorio de trabajo en MX Linux

- El selector del explorador detecta carpetas XDG existentes y admite
  favoritas. Cada carpeta se autoriza antes de explorarla. **Abrir en
  Thunar** abre la subcarpeta visible y usa el gestor predeterminado si
  Thunar no está disponible.
- Arrastra un archivo local desde Thunar o la lista de Studio al editor,
  visor o panel de resultados. `./instalar` instala `tkinterdnd2` en
  Linux. **Archivos → Abrir archivo en visor** ofrece la misma lectura
  si arrastrar y soltar no está disponible. Un archivo externo se lee
  tras confirmación y permanece en su ubicación. **Actualizar visor**
  vuelve a leerlo si se detecta un cambio externo.
- Prueba «Resume esto», «Analiza este documento», «Valida este archivo»
  o «Profesor, evalúame sobre este PDF» después de abrirlo. El resumen
  actual es extractivo. PROFESOR propone completar un término de un
  pasaje concreto y guarda el resultado solo si lo autorizas. Las
  imágenes muestran el visor y metadatos; el reconocimiento visual
  necesita un modelo compatible.
- **Validaciones** comprueba Python, JSON, CSV/TSV o que el visor pueda
  extraer contenido de HTML. Las pruebas del proyecto conservan su
  aislamiento. Los arreglos sintácticos de **Cambios** se pueden
  rechazar o revertir en la sesión, siempre que el archivo no haya
  cambiado en disco desde la aplicación.
- **Web** en Studio para navegador acepta direcciones HTTPS con
  Internet habilitado. La vista bloquea scripts, formularios y acceso
  a las APIs internas. Algunos sitios bloquean la inclusión en marcos.
  El historial recoge las direcciones introducidas en Studio. En la
  aplicación Tk, **Abrir web** usa el navegador predeterminado.

El registro de herramientas de documentos está en
[`core/escritorio_studio.py`](core/escritorio_studio.py). Las operaciones
de archivo siguen usando el registro y los permisos del proyecto.
Las órdenes como «Abre Thunar» o «Abre la calculadora» conservan la
resolución por aplicaciones del escritorio, sin intérprete de shell.

### Trabajo contextual y modo gestual

En Studio nativo, «Abre mis descargas» selecciona la carpeta XDG real y
solicita autorización antes de cargarla como proyecto. Tras abrir un
documento, puedes escribir «Resúmelo», «Analízalo» o «Profesor,
evalúame». Studio para navegador admite estas peticiones con un
documento de un proyecto autorizado. El resumen toma frases del
documento y el ejercicio se basa en un pasaje del mismo archivo.

Los visores de DOCX y ODT extraen texto en solo lectura. Conservan el
archivo original y omiten estilos, imágenes incrustadas y macros.
Admiten hasta 4 MiB de archivo y 2 MiB de XML. Para el documento
completo usa la aplicación predeterminada desde el proyecto autorizado.

El chat compartido admite «Calcula 0.1 + 0.2» y «Resuelve la ecuación
2x + 3 = 11». Devuelve fracciones exactas y verifica la raíz por
sustitución. «Diagnóstico del equipo» muestra la RAM, CPU lógicas,
espacio libre, GPU PCI con controlador visible, nodos de cámara y
dependencias que el proceso puede encontrar. En MX Linux, estas
medidas ayudan a escoger un perfil para el ASUS X550LC.

Para usar la cámara ve a **Opciones → Modo gestual por cámara** en Studio nativo o
ejecuta `cerebro tactil`. Elige el dispositivo y confirma su uso en el
diálogo local. El seguimiento existente usa el índice para mover el
puntero, una pinza para seleccionar o arrastrar y una segunda mano para
desplazar. Usa **Pausar** o Escape con la ventana gestual enfocada para
apagar la cámara. Los fotogramas de este control se procesan en memoria.
Requiere X11, `xdotool`, OpenCV, MediaPipe y
`CEREBRO_MODELO_MANOS` con la ruta del modelo instalado localmente.
Define `CEREBRO_CAMARA_PERFIL=ligero` antes de abrir Studio para limitar
la inferencia a 320 × 240 y 10 cuadros por segundo. El perfil por defecto
utiliza hasta 640 × 480 y 20 cuadros por segundo. Queda pendiente probar
la precisión y el consumo con la webcam física del ASUS.

### Modelo local opcional con Ollama

El backend existente de llama.cpp se conserva. También puedes usar
Ollama previamente instalado con un modelo local ya preparado. Para
ejecutarlo sin servicios externos, inicia el servidor Ollama con
`OLLAMA_NO_CLOUD=1`. Configura el nombre y, si corresponde, el puerto
antes de iniciar Cerebro, por ejemplo:

```bash
export CEREBRO_OLLAMA_MODELO=qwen2.5:0.5b
export CEREBRO_OLLAMA_PUERTO=11434
cerebro iniciar
```

Establecer `CEREBRO_OLLAMA_MODELO` selecciona Ollama para el Profesor
local y para los flujos que ya lo consultan. Cerebro llama a
`127.0.0.1`, envía solicitudes limitadas y pide liberar el modelo tras la
respuesta. Cerebro no instala Ollama ni descarga pesos. El modelo puede
redactar sugerencias. Las herramientas y sus permisos se siguen
validando en el núcleo.

Consulta la [auditoría y matriz de validación de esta evolución](docs/VALIDACION_EVOLUCION_STUDIO.md).

### PDF paginado, preguntas sobre archivos y recordatorios

En Studio abre un PDF y usa el indicador de página, las flechas y
**Buscar**. **Ctrl + rueda** cambia el zoom. También puedes ajustar el
ancho, encajar la página o volver al tamaño inicial con **100 %**. El
zoom de PDF vuelve a renderizar la página con Poppler. La información y
el texto extraído se consultan desde el diálogo o panel de información.
Las imágenes mantienen sus proporciones y tienen zoom independiente.
En Studio nativo, el menú **Opciones** permite ocultar o mostrar los
panel de archivos. Puedes redimensionar la conversación.

- «Explícame la página cuatro» muestra un extracto de esa página.
- «Según el PDF, ¿qué dice de la energía solar?» recupera pasajes y
  cita las páginas donde aparecen.
- «Resúmelo» sobre un PDF muestra extractos por página. La búsqueda y
  el resumen revisan como máximo las primeras 50 páginas, e indican el
  alcance. Las páginas individuales se pueden abrir más allá de ese
  límite. Los PDF escaneados pueden requerir OCR. El visor necesita
  `pdfinfo`, `pdftotext`, `pdftoppm` y `prlimit`. Para el zoom nativo
  instala Pillow mediante el instalador del repositorio.
- En Terminal, pega un fragmento Python o un bloque Markdown marcado
  como `python`. Cerebro inspecciona la sintaxis y señala funciones,
  clases, importaciones o dónde falla el análisis. Las pruebas
  siguen siendo una operación separada y autorizada.

Los recordatorios se guardan en el equipo con la zona horaria local.
Por ejemplo, «Recuérdame que en cinco minutos tengo examen» devuelve
la fecha programada y un identificador. Usa `/recordatorios` para
consultarlos y `/cancelar-recordatorio ID` para cancelar uno. «Esta
tarde» corresponde a las 17:00 y «el próximo lunes» a las 09:00 salvo
que indiques otra hora. El núcleo de escritorio usa `notify-send`
(`libnotify-bin` en MX Linux) y el servicio de notificaciones de XFCE.
Deja Cerebro abierto para recibir el aviso a tiempo. Si estaba cerrado,
los avisos pendientes se revisan al arrancarlo.

Consulta las [pruebas y límites del visor y los recordatorios](docs/STUDIO_PAGINADO.md).

### Cámara opcional e inventario local

En el chat escribe **«Detecta inteligencias instaladas»**. Cerebro
consulta únicamente el servicio Ollama en loopback y las rutas de
adaptadores configuradas explícitamente. La presencia de un adaptador
indica que se encontró su módulo. Puedes seguir escogiendo un modelo
mediante las variables del motor. **«Analiza mi ordenador»** muestra
RAM, swap, carga, procesos visibles, disco y temperaturas disponibles,
junto con recomendaciones que requieren intervención del usuario.

Para el modo gestual, comprueba el intérprete tras instalar Cerebro.
Desde el directorio del repositorio ejecuta estas órdenes solo si
deseas instalar los paquetes en el entorno virtual del proyecto:

```bash
.venv/bin/python --version
.venv/bin/python -m pip install --only-binary=:all: opencv-python mediapipe
.venv/bin/python -c 'import cv2, mediapipe; print(cv2.__version__, mediapipe.__version__)'
```

Si no hay una rueda compatible de MediaPipe, instala solo OpenCV con
`.venv/bin/python -m pip install --only-binary=:all: opencv-python`.
Elige **Marcador verde · solo puntero** y usa una pequeña marca
verde saturada con fondo neutro. Esta alternativa mueve el puntero.
Para hacer clic o cambiar de pestaña usa el ratón o el teclado. En
modo MediaPipe puedes usar la pinza sobre los controles de Studio.
**Calibrar** ajusta el margen antes de iniciar la cámara.

### Proyectos revisables, documentos y visión local

Para programar en Studio abre y autoriza una carpeta, configura el
modelo local de Ollama o llama.cpp y pide **«Haz una calculadora»** o
**«Diseña una web»**. Revisa las diferencias en Resultados y pulsa
**Guardar propuesta revisada**. Cerebro publica los archivos juntos en
una carpeta nueva. Si ya existe, pide otro nombre. Los archivos
generados se abren sin ejecutar su contenido. Para ejecutar las pruebas
Python, abre la carpeta generada como proyecto y usa **Pruebas** con
Bubblewrap habilitado.

En un archivo abierto prueba **«Según el documento, ¿qué dice de la
energía solar?»** o **«Explica este PDF»**. Cerebro cita los fragmentos
recuperados y, con un modelo local de texto configurado, añade una
interpretación separada. La explicación depende de los fragmentos
seleccionados. Los PDF escaneados todavía pueden requerir OCR externo.

Para **«Analiza esta imagen»**, configura `CEREBRO_OLLAMA_VISION` con
el nombre de un modelo visual que ya tengas en Ollama y reinicia
Cerebro. La imagen autorizada se envía a Ollama en el propio equipo.
Para mantener el servicio en modo local, inicia Ollama con
`OLLAMA_NO_CLOUD=1`. El análisis de imágenes y el de texto comparten
el límite de una consulta a la vez.

En el Acompañante, **«Mira esta ventana»** pide permiso para consultar
una vez el título y la clase de la ventana activa al recoger la esfera.
El resultado se muestra en la ventana del Acompañante. El análisis de
capturas de pantalla queda pendiente.

El diálogo del modo gestual incluye **Diagnóstico** para ver el nodo
de cámara, los permisos y cada dependencia. Las instrucciones de
instalación opcional anteriores se aplican al entorno virtual de
Cerebro. Puedes comprobar el rendimiento con **«Analiza mi rendimiento»**
y contar las aplicaciones visibles en el menú con **«Cuántos programas
tengo instalados»**.

Consulta [la validación de Cerebro Next](docs/CEREBRO_NEXT.md).

### Visor con rueda y diagnóstico de instalación

En el visor de una imagen o un PDF, gira la rueda para ampliar o
reducir alrededor del puntero. Arrastra con el botón izquierdo para
mover el contenido ampliado. El doble clic encaja la imagen y otro
doble clic recupera su escala anterior. En PDF, el doble clic encaja
la página. Los botones de ajuste y de tamaño real quedan fuera de la
zona desplazable. **100 %** muestra los píxeles originales de una
imagen, sujetos al límite de memoria, y equivale a 96 ppp en PDF
dentro de los límites del renderizado. **Información** despliega los
metadatos. **Abrir en aplicación local** solicita confirmación antes
de entregar el original a la aplicación predeterminada de XDG.

`./instalar --sin-autoinicio` crea el entorno virtual de Cerebro,
instala la base y comprueba importaciones, herramientas PDF/X11,
permisos de cámara y motores locales. Para autorizar la instalación
opcional de los paquetes de gestos en ese mismo entorno:

```bash
./instalar --sin-autoinicio --gestos manos --modelo-manos /ruta/hand_landmarker.task
```

Usa `--gestos marcador` si MediaPipe no tiene una rueda compatible.
El modo marcador no necesita el archivo de manos. Los modelos se
seleccionan de archivos existentes. Si quieres un modelo de código
distinto del de conversación, define `CEREBRO_OLLAMA_CODIGO` con el
nombre ya instalado y reinicia Cerebro.

Con Internet habilitado, **«Muéstrame mis repositorios de GitHub»**
consulta hasta 20 repositorios con la sesión ya configurada en
`gh auth login`. Para una comparación pública, escribe
**«Compara GitHub Dirix24/cerebro main con otra-rama»** y sustituye
`otra-rama` por una referencia existente. Esta ruta compara referencias
remotas. Consulta [la auditoría, las pruebas y los límites](docs/NEXT_VISOR_INSTALACION.md).

### Lecciones verificadas del Profesor

Configura un modelo local como Profesor (Ollama o llama.cpp). En Studio,
Terminal, chat web o el Acompañante escribe **«Profesor, prepara una
lección de matemáticas»**. También están disponibles programación,
español, razonamiento y herramientas. El modelo elige una variante y
la resuelve. Cerebro comprueba el resultado con la respuesta de su
banco de competencias. Si coincide, puedes guardar el ejemplo con
**«Aprueba lección del Profesor»** desde la misma conversación.

Desde el repositorio, utiliza el mismo `CEREBRO_HOME` con el que
arrancas Cerebro, si lo personalizaste:

```bash
.venv/bin/python entrenar_ejemplos_aprobados.py
.venv/bin/python entrenar_ejemplos_aprobados.py --aplicar --entrenar
.venv/bin/python entrenar_ejemplos_aprobados.py --alumno DARAS --aplicar
.venv/bin/python entrenar_ejemplos_aprobados.py --alumno CAZEL --aplicar
```

El primer comando muestra cuántos ejemplos hay. El segundo prepara el
corpus y entrena un candidato aislado de Cerebro usando el checkpoint y
la validación fija existentes. Si supera los criterios, queda para
revisión. Los dos últimos exportan JSONL en
`data/lecciones-profesor/` para una futura importación en cada
especialista. La exportación conserva el origen y el criterio de
verificación. No inicia entrenamiento en los repositorios hermanos.

En la verificación de este flujo se usó un doble del Profesor para
crear una lección y se entrenó un candidato NumPy real durante tres
pasos en un directorio temporal. La pérdida bajó de 0,100032 a
0,099936 bits por byte y el acierto exacto en 32 reformulaciones bajó
del 46,9 % al 43,8 %. El control de regresión descartó el candidato.

**«Consulta al equipo: [pregunta]»** pide aportes a DARAS y CAZEL.
CEREBRO añade una comprobación local cuando reconoce una operación
matemática o código Python. Si PROFESOR está configurado, el modelo
local prepara una conclusión y un paso para practicar. Al repetir
la misma pregunta recibe también un extracto de la revisión previa
para contrastarlo con los resultados nuevos. Esa revisión se conserva
como experiencia, separada del banco de lecciones verificadas.

**«Consulta al equipo en internet: [pregunta]»** permite a DARAS usar
la red si la sesión la tiene habilitada. CAZEL conserva sus límites de
proyecto y PROFESOR usa el motor local configurado.

El instalador informa el perfil de cámara recomendado. El control
gestual elige el perfil ligero con menos de 4 GiB de RAM disponible o
menos de cuatro CPU lógicas. Puedes fijarlo con
`CEREBRO_CAMARA_PERFIL=ligero` o `CEREBRO_CAMARA_PERFIL=normal`.

En el Acompañante, **Accesos → Rutinas de escritorio** permite elegir
una ventana para enseñar, autorizar la observación, revisar y aprobar
los pasos, y repetir una rutina guardada. La observación dura hasta
90 segundos y registra estados compatibles de la ventana elegida
con un indicador visible. Funciona con permisos de escritorio y
herramientas X11/GTK. El menú no activa la observación al abrirse.

Universe enlaza las lecciones aprobadas con el banco de PROFESOR.
Cada nodo representa un ejemplo comprobado con su referencia.
Cuando falta una respuesta local y la investigación automática está
habilitada, las consultas de definición pública admitidas pueden
aportar una fuente a la explicación de PROFESOR. La fuente se
muestra junto a la respuesta.
