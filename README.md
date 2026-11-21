### Ojos animados y expresiones (sin cámara)

```bash
python3 main.py --ojos
```

**Solo ojos, sin boca**: dos pantallas oculares en la terminal, sin navegador ni modelo entrenado. Incluye 18 expresiones visuales (atento, feliz, curioso, pensando, sorprendido, dormido, analizando, aprendiendo, investigando, asociando, observando, consolidando, error, concentrado, dudando, esperando, saludando y descansando). Parpadea, alterna la mirada y realiza microgestos breves: guiño al saludar, destello al aprender y exploración visual al analizar o investigar. Es una interpretación original de ojos robóticos expresivos, no una reproducción exacta de un personaje cinematográfico. Usa flechas izquierda/derecha para recorrer expresiones, 1-9 para las primeras nueve, `a` para alternar entre modo manual y automático, `q` para salir. El modo automático está **apagado al inicio** y refleja únicamente eventos recientes de la telemetría local; no interpreta sentimientos, no lee mensajes privados ni usa cámara. Requiere terminal interactiva con curses (en Windows puede requerir `pip install windows-curses`).

**Privacidad:** los ojos son solo una animación. No abren ni solicitan acceso a ninguna cámara, micrófono o red. Si en el futuro se conecta la visión a las expresiones, deberá ser opcional y requerir autorización explícita; la herramienta existente `camara_local.py --confirmar` sigue siendo una captura independiente y puntual.

# 🧠 Cerebro — IA local, memoria y aprendizaje experimental

> **Diseñado y desarrollado con asistencia de inteligencia artificial (IA).** Cerebro es un proyecto experimental impulsado por su creador, con colaboración de IA en el diseño de la arquitectura, programación, documentación y pruebas. Esta declaración describe el proceso de desarrollo, **no** significa que Cerebro sea una IA general ni que se haya diseñado a sí mismo.

**Cerebro** es un proyecto de inteligencia artificial local en Python: combina un Transformer propio NumPy, motores Transformer opcionales basados en PyTorch, búsqueda de información, memoria, herramientas deterministas y entrenamiento experimental. **No utiliza modelos preentrenados de terceros, Ollama, GGUF de otras IA ni APIs de IA para generar respuestas.** Wikipedia se utiliza como fuente de textos, no como motor de IA.

**Estado:** versión **experimental**, desarrollada en una rama de integración. Algunas pruebas automáticas han pasado, pero el arranque integral, la desinstalación en el equipo de destino, la calidad de las respuestas y el entrenamiento de larga duración **todavía requieren verificación**. No se debe confundir «módulo integrado en el repositorio» con «motor entrenado y disponible automáticamente dentro del chat».

## 🚀 Instalación y primer arranque

Requisitos: Linux (orientado a MX Linux / Debian), Python 3 y acceso a Internet para descargar dependencias o artículos. Desde la carpeta del repositorio:

```bash
# Instala las dependencias básicas en un entorno local aislado
python3 cerebro.py instalar

# Inicia el chat con herramientas locales, incluso sin checkpoint
python3 cerebro.py iniciar
```

Para añadir también la biblioteca PyTorch, **sin instalar otra aplicación de IA**:

```bash
python3 cerebro.py instalar --avanzado
```

PyTorch es una biblioteca de cálculo; **no es otro asistente ni un modelo descargado**. Puede ocupar bastante espacio y tardar en instalarse. El chat normal sigue utilizando el motor NumPy: los motores PyTorch se entrenan y generan por sus comandos específicos, **no** se alternan automáticamente dentro del chat.

La instalación no crea un servicio del sistema. La acción `todo` ejecuta el aprendizaje diario mientras el chat permanece abierto. Cierra el chat con `/salir` para detener la sesión.

### Razonamiento, recuerdos e internet

Cerebro ejecuta su modelo NumPy y sus herramientas de razonamiento en tu equipo. El asistente local verifica cálculos y deducciones dentro de los formatos admitidos. La generación experimental con los pesos propios está disponible con `python3 cerebro.py chat`. Su alcance es más limitado que el de un modelo generalista.

Estos ejemplos se escriben dentro del chat:

```text
Deduce: Ada es ave; ave implica animal; animal implica ser vivo ? ser vivo
Inserta un recuerdo: proyecto = Atlas
¿Qué recuerdas sobre el proyecto?
Extrae recuerdos
/insertar-recuerdo {"proyecto": "Atlas"}
Busca en internet fotosíntesis
```

Los recuerdos se conservan entre sesiones. Copia el JSON de `/extraer-recuerdos` para restaurar los valores con `/insertar-recuerdo` en otra instalación. Si una clave ya contiene un valor distinto, Cerebro rechaza la importación completa. Para extraer una sola clave, usa `/extraer-recuerdos proyecto`.

`/internet` y «Busca en internet…» envían el tema que escribas a Wikipedia en español y devuelven un extracto con su enlace. Escribe solo temas públicos en ese comando. Para usar el asistente local desde un script, ejecuta `python3 cerebro.py iniciar --una-vez '/recuerdo proyecto'`.

## Cerebro Universe

```bash
python3 cerebro.py universe
```

Abre la dirección que aparece en la terminal para usar Studio, Universe, Canvas y Body con el mismo núcleo. Consulta los [perfiles, la auditoría de integración y las pruebas](docs/UNIVERSE.md).

## 🧩 Todos los comandos de la aplicación

| Comando | Qué hace |
|---|---|
| `python3 cerebro.py instalar` | Instala dependencias básicas de Cerebro |
| `python3 cerebro.py instalar --avanzado` | Instala también PyTorch opcional |
| `python3 cerebro.py iniciar` | Asistente local con los pesos existentes, sin entrenamiento automático |
| `python3 cerebro.py todo` | Inicia chat, índice y aprendizaje usando dependencias ya disponibles |
| `python3 cerebro.py chat` | Abre solo el chat NumPy |
| `python3 cerebro.py diagnostico` | Consulta estado de checkpoints, índice y batería |
| `python3 cerebro.py motores` | Enumera motores y módulos, con disponibilidad de bibliotecas |
| `python3 cerebro.py laboratorio` | Genera un panel HTML local de progreso, checkpoints y simulaciones |
| `python3 cerebro.py automejora` | Analiza progreso y errores; genera propuestas seguras de mejora |
| `python3 cerebro.py aprender` | Ejecuta recopilación de textos una vez |
| `python3 cerebro.py aprender --cada-dia --entrenar` | Recopilación y entrenamiento diario experimental |
| `python3 cerebro.py conocimiento buscar "Luna"` | Busca conocimiento local y fuentes |
| `python3 cerebro.py entrenar --pasos 100` | Entrena el motor NumPy |
| `python3 cerebro.py entrenar --motor avanzado --corpus data/corpus.txt --perfil diminuto --pasos 100` | Entrena Transformer PyTorch propio |
| `python3 cerebro.py generar --motor avanzado "Hola"` | Genera con pesos PyTorch existentes |
| `python3 cerebro.py desinstalar --confirmar` | Elimina entornos de dependencias de Cerebro y **conserva los datos y el código** |
| `python3 cerebro.py desinstalar --confirmar --borrar-datos` | Solicita una frase adicional antes de borrar datos locales reconocidos |

### 🧹 Desinstalación con un comando

```bash
python3 cerebro.py desinstalar --confirmar
```

**Importante:** elimina los entornos locales `.venv` y `.cerebro-env`, pero **no borra el repositorio ni los archivos personales**. Si se añade `--borrar-datos`, solicita escribir exactamente `BORRAR MIS DATOS` antes de eliminar las carpetas de datos y checkpoints conocidas. **No elimina paquetes del sistema, instalaciones externas, copias de seguridad ni el propio código fuente.** Para quitar absolutamente toda la carpeta del proyecto, el usuario debe hacerlo aparte, tras revisar qué contiene. No existe una desinstalación automática programada para ninguna fecha.

## 💬 Comandos dentro del chat

Escribe `/ayuda` para consultar la ayuda incorporada.

| Comando | Función |
|---|---|
| `/estado` | Arquitectura, parámetros y memoria del modelo |
| `/memoria` | Consulta memoria persistente |
| `/recordar clave = valor` | Guarda un dato indicado explícitamente |
| `/olvidar clave` | Elimina un dato de la memoria |
| `/buscar-corpus Luna` | Busca documentos en el índice local |
| `/conocimiento Luna` | Busca conocimientos con fuentes |
| `/biblioteca Luna` | Busca en biblioteca local |
| `/calc 12 * (3 + 4)` | Calculadora segura |
| `/calcular-local 2+3*4` | Cálculo local |
| `/analizar-codigo def f(): return 1` | Análisis estático de Python |
| `/resumir texto` | Resumen extractivo, no generativo |
| `/palabras-clave texto` | Extrae palabras frecuentes |
| `/estadisticas texto` | Estadísticas de texto |
| `/comparar A || B` | Comparación de textos |
| `/fichas concepto: definición` | Crea fichas a partir de definiciones |
| `/preguntas texto` | Genera preguntas literales de repaso |
| `/duplicados A || B` | Detecta textos parecidos |
| `/aprender-ficha pregunta || respuesta` | Guarda ficha aprobada para repaso |
| `/repasar` | Presenta una ficha pendiente |
| `/calificar bien` / `/calificar mal` | Programa el próximo repaso |
| `/autoevaluar` | Compara respuestas del modelo con fichas aprobadas |
| `/progreso` | Registra precisión exacta y variación histórica |
| `/motor-para ¿Qué es Marte?` | Explica el motor que seleccionaría el orquestador |
| `/registrar-error pregunta || respuesta correcta` | Guarda corrección **pendiente de revisión** |
| `/errores-pendientes` | Lista correcciones pendientes |
| `/aprobar-ejemplo pregunta || respuesta` | Guarda un ejemplo aprobado |
| `/ejemplos-aprobados` | Consulta ejemplos aprobados |
| `/experimentos` | Consulta registros de experimentos |
| `/historial` | Consulta turnos guardados |
| `/guardar-turno usuario Hola` | Guarda explícitamente un turno |
| `/hora` | Consulta hora local |
| `/archivos` | Lista archivos permitidos del espacio de trabajo |
| `/leer nombre.txt` | Lee archivo permitido |
| `/escribir nombre.txt texto` | Escribe archivo permitido |
| `/temp 0.7` | Ajusta temperatura de generación |
| `/limpiar` | Limpia conversación a corto plazo |
| `/salir` | Cierra el chat |

Los comandos con `||` utilizan ese separador literalmente. Las herramientas de escritura no se ejecutan a partir de texto libre: requieren un comando explícito y los permisos correspondientes.

## 🧠 Motores y tecnologías

| Componente | Tecnología | Estado |
|---|---|---|
| Generador neuronal principal | Transformer causal propio en **NumPy**, tokenizador, atención, entrenamiento y checkpoints `.npz` | Integrado en chat |
| Motor neuronal clásico | Transformer propio con **PyTorch** y checkpoints `.pt` | Opcional, acceso mediante CLI |
| Motor neuronal avanzado | RoPE, RMSNorm, SwiGLU y atención SDPA mediante PyTorch | Opcional, acceso mediante CLI |
| Memoria persistente | Almacenamiento local y recuperación | Integrado |
| Recuperación de documentos | SQLite **FTS5** y búsqueda léxica | Integrado |
| Conocimiento con procedencia | Respuestas guardadas y URLs de fuentes | Integrado |
| Razonamiento determinista | Calculadora, análisis de código y utilidades | Integrado para tareas concretas |
| Repaso espaciado | Fichas aprobadas y calendario de revisión | Integrado |
| Autoevaluación | Coincidencia normalizada de respuestas y métricas históricas | Integrado; métrica limitada |
| Control de aprendizaje | Validación fija, respaldo, restauración y control de recursos | Experimental |

**Más motores no equivale automáticamente a más inteligencia.** El orquestador actual es **determinista**: identifica ciertos tipos de peticiones y elige rutas existentes. No es un sistema de razonamiento general ni un comité de modelos neuronales votando respuestas.

## 🌱 Cómo evoluciona Cerebro

1. **Adquiere textos:** puede consultar artículos de Wikipedia en español, con límites de cantidad y almacenamiento.
2. **Guarda procedencia:** conserva URLs y registra conocimiento local, evitando duplicados conocidos.
3. **Recupera información:** busca fuentes antes de recurrir a generación en ciertos tipos de preguntas.
4. **Recuerda y repasa:** utiliza memoria local, fichas aprobadas y repaso espaciado.
5. **Aprende de correcciones:** `/registrar-error` almacena una corrección **sin asumir que sea verdadera ni modificar pesos automáticamente**.
6. **Mide progreso:** `/autoevaluar` y `/progreso` comparan respuestas con fichas aprobadas. La comparación es estricta y **no mide razonamiento profundo**.
7. **Entrena con límites:** el ciclo incremental ajusta pasos y evita iniciar nuevos entrenamientos con batería baja, poca RAM disponible o temperatura elevada, si hay sensores.
8. **Protege checkpoints:** guarda respaldos y rechaza nuevos pesos si las métricas de validación son inválidas o empeoran más del umbral permitido.

**Limitaciones:** la validación fija mide pérdida en textos, no garantiza que Cerebro haya aprendido hechos correctos. Las respuestas generadas no se consideran automáticamente conocimientos aprobados. Los pesos nuevos se cargan al reiniciar el chat; la sesión abierta no se actualiza automáticamente.

## 🧪 Pruebas y verificación

```bash
python3 -m pip install -r requirements.txt pytest
python3 -m compileall -q .
python3 -m pytest -q tests
python3 tests/tests_final.py
python3 cerebro.py diagnostico
python3 cerebro.py motores
```

GitHub Actions ejecuta comprobaciones de sintaxis y pruebas automatizadas en la rama de integración. **Una ejecución anterior** de la suite principal terminó con **68 pruebas superadas y 2 omitidas**, pero ese resultado **no valida los cambios posteriores** ni sustituye pruebas en MX Linux. El entrenamiento PyTorch, la instalación, el primer arranque y la desinstalación real requieren verificación separada. Consulta la pestaña **Actions** del repositorio para el resultado más reciente.


## 🤖 Modo simbionte: USB y robótica experimental

Cerebro puede **enumerar puertos serie** conectados al ordenador anfitrión (solo metadatos), con permiso READ y la biblioteca opcional `pyserial`. Enumerar un puerto **no** identifica de forma infalible el tipo de placa, no abre el dispositivo y no inspecciona todo tipo de USB.

```bash
python3 -m pip install pyserial
python3 main.py
```

Dentro del chat:

```text
/descubrir-i2c 0x3c 0x68
/analizar-robot codigo_robot.py
/usb
/crear-robot mi_robot arduino
/crear-robot robot_esp esp32
```

`/crear-robot` requiere WRITE y genera en el workspace un proyecto nuevo con archivo `.ino` y README. Es una plantilla de parpadeo de LED: **no compila, no instala, no flashea ni controla físicamente la placa**. Revisa el pin LED, las tensiones y el circuito para cada placa. No se incluyen controladores para motores, baterías, servos ni sensores. El usuario decide si quiere compilar y cargar firmware mediante sus herramientas habituales.

**Diseño futuro:** vincular de forma explícita una placa concreta; importar y analizar el código que proporcione el usuario; generar un protocolo de comunicación limitado entre Cerebro y un microcontrolador; probar en simulación; y solicitar confirmación específica antes de cada carga de firmware. Nada de propagarse a dispositivos USB, buscar equipos ajenos ni instalar código automáticamente. El «fragmento de Cerebro» para una placa es firmware especializado, no una copia de la red neuronal completa.

## 🧠 Cerebro V2: entrenamiento, motores y SSD portátil

**Política de motores propios:** NumPy y PyTorch se usan como bibliotecas matemáticas para construir y entrenar arquitecturas originales de Cerebro desde cero. No se cargan modelos de lenguaje preentrenados ajenos, ni se depende de APIs de otros asistentes. La calidad del modelo depende de los datos, entrenamiento y evaluación; los pesos propios todavía son experimentales.


Estos comandos están implementados en la rama de integración `fix/nucleo-validacion-2026`. Los tamaños mayores son **arquitecturas disponibles, no modelos ya entrenados**. La ruta de entrenamiento NumPy utiliza CPU; la presencia de una GPU no activa aceleración automáticamente.

### Entrenamiento del núcleo NumPy

```bash
python3 train.py --listar-tamanos
python3 train.py --detectar-equipo
python3 train.py --tamano mini --plan-entrenamiento
python3 train.py --tamano auto --pasos 1000
python3 train.py --tamano mini --pasos 300 --batch 2 --semilla 1234
python3 train.py --resume --pasos 300
python3 -m pytest -q tests
```

- `--tamano` acepta `mini`, `normal`, `grande`, `potente`, `extra`, `maximo`, `experimental` y `auto`. El tamaño `auto` es una estimación basada en RAM.
- `--plan-entrenamiento` calcula una **estimación** del presupuesto de memoria; no entrena. Si se elige un tamaño que supera el presupuesto, el entrenamiento exige una aceptación explícita con `--permitir-riesgo-memoria`. No se recomienda usar esa opción sin verificar la RAM.
- `--resume` conserva la arquitectura del checkpoint y continúa desde pesos anteriores; **no** agranda automáticamente sus capas.
- El entrenamiento separa documentos de validación y guarda `checkpoints/last.npz`; solo reemplaza `best.npz` si la validación lo justifica, salvo que se use `--forzar`. La métrica de pérdida no demuestra inteligencia general.
- No hay un número universal de pasos que signifique «entrenamiento completo»: depende de corpus, hardware, pérdida de validación y calidad de respuestas.

**Entrenamiento en GitHub Actions:** el flujo [Cerebro - entrenamiento local de prueba](.github/workflows/entrenamiento-cerebro.yml) conserva las pruebas PyTorch de dos pasos y añade un trabajo NumPy **manual** (30, 100 o 300 pasos, perfil mini) que guarda los checkpoints como artefactos descargables durante 14 días. Desde **Actions**, selecciona el flujo, **Run workflow**, la rama de integración y los pasos deseados. Los pesos del runner **no se instalan automáticamente en el SSD**; hay que descargarlos, revisarlos y copiarlos al directorio de checkpoints. No se promete que el entrenamiento termine dentro del límite de tiempo del runner.

### Preparar y usar el SSD externo

Configura `CEREBRO_HOME` **antes de iniciar Python**, apuntando a la unidad externa realmente montada:

```bash
export CEREBRO_HOME="/ruta/real/del/SSD/Cerebro"
python3 train.py --preparar-ssd
python3 train.py --detectar-equipo
python3 main.py --huesped estado
python3 main.py --huesped vincular --confirmar
python3 main.py --huesped desvincular
```

En Windows, define `CEREBRO_HOME` en el entorno de PowerShell antes de ejecutar los comandos. **Comprueba la unidad montada**: crear el marcador de SSD no demuestra que la ruta pertenezca a un disco externo. La vinculación de huésped compara datos generales del equipo, no proporciona autenticación criptográfica.

### Comandos V2 dentro del chat

Inicia `python3 main.py` cuando tengas un checkpoint NumPy compatible. Los comandos siguientes requieren el chat abierto:

| Comando | Función y límites |
|---|---|
| `/motores` | Inventario de capacidades y dependencias; no activa cámara, voz ni Internet |
| `/motor-especializado Quiero programar Python` | Propone motor para la petición, sin ejecutarla |
| `/motor-para ¿Qué es Marte?` | Explica el enrutamiento básico |
| `/criterio /crear-proyecto demo cli` | Revisa permisos y riesgos sin actuar |
| `/materias` | Lista materias disponibles |
| `/estudiar ciberseguridad` | Muestra guía educativa defensiva |
| `/crear-proyecto demo cli` | Crea un proyecto local en el workspace con permiso WRITE |
| `/crear-proyecto utilidades biblioteca` | Crea una biblioteca Python local |
| `/laboratorio demo/main.py` | Inspecciona un archivo del workspace, sin ejecutarlo; requiere READ |
| `/crear-pdf informe Texto del informe` | Genera PDF sencillo; requiere WRITE y `reportlab` |
| `/analizar-codigo def f(): return 1` | Análisis estático de código |
| `/progreso` | Evalúa fichas aprobadas con una métrica limitada |

Para PDF instala `python3 -m pip install reportlab` en el entorno de Cerebro. Los documentos y proyectos se escriben en el workspace configurado. La inspección del laboratorio es **estática**, no equivale a un antivirus ni a una auditoría completa. La cámara, el reconocimiento visual, el micrófono y la conversación hablada son **integraciones futuras** y no se activan por este registro.

## 🤖 Cerebro Simbionte: USB y robots programables

La detección es **voluntaria y local**, no busca dispositivos por red ni instala firmware.

```bash
python3 -m pip install pyserial   # opcional: solo para listar puertos serie
python3 main.py
```

Dentro del chat:

```text
/usb
/preparar-robot mi_robot esp32 codigo_robot.py
/preparar-robot mi_robot_pico rp2040 codigo_robot.py
```

`/usb` lista los puertos serie visibles para el ordenador, sin abrirlos ni conectarse a ellos. VID/PID y fabricante son pistas, **no prueban el modelo de placa**. Requiere permiso READ.

`/preparar-robot` lee un archivo de código existente en el workspace, y crea un proyecto nuevo `main.py` y `README.md` para **MicroPython ESP32 o RP2040**. Requiere permisos READ y WRITE; no sobrescribe proyectos, no convierte automáticamente código Arduino/C++, no valida pines ni controla motores. El código se copia sin ejecutarse. El usuario debe revisar compatibilidad y seguridad física antes de cualquier carga.

**Descubrimiento pasivo:** `/descubrir-i2c` interpreta direcciones I²C que tú proporciones (no consulta el bus); `/analizar-robot` revisa el código del workspace e identifica interfaces como I²C, SPI, GPIO o PWM sin ejecutarlo. Ninguno demuestra el modelo exacto del componente, ni activa motores. La detección real en placa requerirá firmware de diagnóstico autorizado y específico para ese hardware.\n\n**Todavía no se programa ninguna placa desde Cerebro.** El flasheo o comunicación serie deberá ser un paso posterior, explícitamente confirmado y probado con el hardware exacto. Una Raspberry Pi con Linux y un Arduino Uno usan flujos distintos a MicroPython.

## 🧬 Identidad, portadores y legado público

Cerebro puede conservar la **identidad histórica declarada** de su creador en `CEREBRO_HOME/memory/legado/origen.json`. La identidad se configura una sola vez; no está pregrabado ningún nombre.

```text
/configurar-creador Danny
/origen
/exportar-legado /ruta/al/usb/legado.json
/examinar-legado /ruta/al/usb/legado.json
```

También entiende «¿Quién te creó?» después de configurar la identidad. La exportación solo incluye información pública sobre el origen; **nunca conversaciones, contraseñas ni memorias privadas**. El archivo SHA-256 detecta alteraciones accidentales, **no demuestra autenticidad ni autoriza a revelar datos**. Examinar un respaldo no lo instala ni cambia el estado de Cerebro.

**Pendiente:** perfiles aislados de varios usuarios, cifrado autenticado con clave del portador, recuperación privada voluntaria y mecanismo de sucesión/transferencia. No se deben desbloquear recuerdos privados solo porque alguien encuentre un USB. No existe detección automática de fallecimiento ni recuperación de una conciencia.

### Recuperación cifrada de recuerdos privados desde USB

```bash
python3 -m pip install cryptography
python3 -m core.memoria_cifrada exportar /ruta/usb/recuerdos.cerebro
python3 -m core.memoria_cifrada examinar /ruta/usb/recuerdos.cerebro
python3 -m core.memoria_cifrada restaurar /ruta/usb/recuerdos.cerebro --confirmar --destino /ruta/nueva/memoria.json
```

Cada operación solicita una **contraseña oculta** en la terminal. El respaldo de la memoria de largo plazo usa scrypt para derivar la clave y AES-256-GCM para cifrado autenticado; `cryptography` es una biblioteca criptográfica, **no un modelo de IA externo**. Se puede llevar el archivo en un USB. Sin la contraseña correcta no se puede descifrar. `examinar` solo muestra cuántas entradas hay; no imprime los recuerdos. `restaurar` exige `--confirmar` y **no sobrescribe** una memoria existente; usa un destino nuevo para impedir mezclar portadores accidentalmente. No se descifran pesos del modelo ni archivos arbitrarios: solo `long_term` de la memoria JSON.

**Precauciones:** el USB no se detecta ni abre automáticamente, la contraseña no se guarda y, si se pierde, los datos cifrados pueden ser irrecuperables. No coloques contraseñas en comandos, chats o GitHub. No recupera memorias que nunca se guardaron, ni supone una continuidad de conciencia. La migración selectiva entre perfiles y el flujo conversacional de recuperación están pendientes.

## 🧠 Recuerdos y mapa de conexiones

En el chat puedes decir «Cerebro, recuerda que mi robot usa un sensor de distancia». Cerebro lo guarda como **declaración del usuario**, no como verdad verificada, en su memoria local de largo plazo.

`/mapa-recuerdos` crea un archivo SVG local en `CEREBRO_HOME/data/mapa_recuerdos.svg`. Puedes abrirlo en un navegador. Los círculos azules son recuerdos guardados; las líneas muestran coincidencias de palabras entre recuerdos. La leyenda reserva amarillo para **analizando** y naranja para **investigando**, pero **esta primera versión no monitoriza en vivo esos estados**. No muestra las neuronas reales ni las conexiones de pesos del Transformer. Es un mapa de memoria, no una medición de actividad neuronal.

El mapa contiene texto de recuerdos privados: no lo compartas ni lo subas a GitHub. Para regenerarlo, mueve o elimina el SVG anterior. Pendiente: visualización dinámica de estados, filtros por usuario y relaciones semánticas aprendidas.

### Estación neuronal explorable

En el chat: «Cerebro, abre la estación neuronal», «visualiza tus neuronas» o el comando avanzado `/estacion-neuronal`. Se genera `CEREBRO_HOME/data/estacion_neuronal.html`, una página **local y autónoma** que puedes abrir en el navegador, sin servidor, CDN ni IA externa.

Incluye núcleo central animado, recuerdos alrededor, conexiones y pulsos decorativos; puedes arrastrar, acercar, alejar, pausar y seleccionar un recuerdo para consultar su contenido. Colores: amarillo (analizando), azul (aprendido), naranja (investigando), verde (consolidado), violeta (asociando), cian (observando), rojo (error). **Actualmente los recuerdos se muestran azules; los demás colores están preparados para eventos, pero todavía no se conectan a una telemetría en tiempo real.** Los enlaces reflejan palabras compartidas, no sinapsis ni pesos reales. Los puntos se animan visualmente; no son neuronas nuevas creadas al entrenar.

**Privacidad:** el HTML incluye recuerdos privados en texto para poder explorarlos sin red. No lo compartas ni lo subas a repositorios públicos. Para actualizarlo, mueve o elimina el archivo anterior y vuelve a solicitarlo.

### Estación neuronal en vivo (procesos reales)

Con Cerebro en funcionamiento, abre **otra terminal** en el proyecto y ejecuta:

```bash
python3 estacion_neuronal_live.py
```

Visita `http://127.0.0.1:8765/`. La estación actualiza cada 1,5 segundos el mapa de recuerdos y los eventos registrados por el chat: amarillo al recibir mensajes (analizando), azul cuando se guarda memoria (aprendido), naranja al iniciar búsqueda local (investigando), verde tras respuesta generativa (consolidado). El visor dispone también de violeta (asociando), cian (observando) y rojo (error), que se usarán cuando los procesos correspondientes emitan eventos reales. Los eventos **no contienen el texto de las conversaciones**; solo estado, etiqueta fija y fecha. Los recuerdos sí aparecen en el visor y pueden ser privados.

El servidor escucha **solo en 127.0.0.1** y no requiere internet ni modelos externos. **Advertencia de privacidad:** cualquier proceso local capaz de acceder al puerto puede consultar los recuerdos mientras el servidor esté abierto; úsalo solo en un equipo de confianza y ciérralo al terminar (Ctrl+C). No expongas ni reenvíes el puerto a la red.

Las partículas y los movimientos de los nodos son efectos gráficos; **los cambios de estado del chat y la incorporación de recuerdos son eventos reales**. No equivale a observar neuronas biológicas ni pesos individuales del modelo.

### Estación neuronal integrada en la terminal (sin navegador)

**Dentro del chat** (`python3 main.py`), escribe «Cerebro, abre la estación neuronal» o `/estacion-terminal`. Se abre una pantalla a color dentro de la **misma terminal**, sin navegador ni servidor. Pulsa **q** para volver a hablar con Cerebro. Si todavía no tienes checkpoint de IA, también puedes abrirla de manera independiente:

```bash
python3 main.py --estacion-terminal
# o:
python3 -m core.estacion_terminal
```

**Controles:** flechas para seleccionar recuerdos; `+` y `-` para acercar y alejar; espacio para pausar el movimiento; `q` para salir. Los recuerdos y eventos se actualizan periódicamente desde el disco o la memoria del chat. El visor limita el grafo a 120 recuerdos para mantener la fluidez; no borra recuerdos de la memoria. El núcleo cambia de color según el **último evento registrado**. Los puntos y conexiones son una **visualización de recuerdos y coincidencias de palabras**, no las neuronas ni sinapsis físicas del modelo. La animación es decorativa.

Utiliza la biblioteca estándar `curses` (habitualmente incluida en Linux/macOS; en Windows requiere `pip install windows-curses` si Python no incluye `curses`). Necesita una terminal interactiva de al menos 52×15. Los recuerdos privados pueden verse en pantalla: úsala en un entorno de confianza.

**Diagnóstico y recuperación sin iniciar el modelo:**

```bash
python3 main.py --diagnostico-memoria
python3 main.py --archivados
python3 main.py --restaurar-recuerdo "CLAVE" --confirmar
```

El diagnóstico muestra cantidades y tamaños, sin valores privados. El listado muestra **claves** de recuerdos archivados, que pueden ser sensibles. Restaurar exige confirmación explícita, no sobrescribe una clave existente y requiere que el respaldo siga disponible. La recuperación examina los últimos 2 MB del archivo de respaldo; no es un sistema de copia de seguridad completo.

### Consolidación segura de recuerdos (sin perder lo aprendido)

Cuando la memoria de largo plazo supera **500 entradas**, Cerebro busca únicamente duplicados equivalentes: la misma clave normalizada, el mismo valor y la misma categoría. Conserva la versión con mayor importancia y guarda las variantes redundantes en `memory_store.json.duplicados.jsonl` junto al archivo de memoria, **antes** de retirarlas del índice activo. No descarta conocimientos únicos ni toca checkpoints, pesos del modelo o datos de entrenamiento.

El respaldo contiene información privada **en texto claro** y permanece en disco: esta consolidación reduce el tamaño de la memoria activa, pero **no garantiza liberar espacio de disco** mientras se conserve el respaldo. La memoria de conversación a corto plazo ya tiene un límite independiente. No se usa ninguna IA externa ni se envían datos a internet.

## 💬 Hablar con Cerebro sin comandos

El chat reconoce **algunas peticiones habituales en español** y selecciona una herramienta segura sin necesidad de escribir una barra:

- «Cerebro, mira si tengo una placa conectada» → consulta puertos serie (no abre dispositivos)
- «Revisa errores del repositorio GitHub Dirix24/cerebro» → consulta incidencias públicas
- «Consulta GitHub Dirix24/cerebro» → estado público
- «¿Qué tengo pendiente?» → lista recordatorios
- «Mira con la cámara» → pide autorización y explica el procedimiento, **no la activa**
- «Recuérdame revisar el robot» → solicita fecha/hora, **todavía no interpreta ni guarda el siguiente turno automáticamente**

Es un **enrutador por reglas**, no comprensión general comparable a un asistente grande. Las acciones peligrosas o de escritura no se ejecutan automáticamente. Los comandos siguen disponibles para tareas avanzadas. La conversación de varios pasos y el aprendizaje de nuevas intenciones están pendientes.

## 📅 Recordatorios, GitHub y futura visión

Cerebro incluye recordatorios **guardados localmente** en `CEREBRO_HOME/data/recordatorios.json` y una consulta **optativa de solo lectura** a la API pública de GitHub. GitHub no se usa para generar respuestas de IA ni para entrenar el modelo.

```text
/recordar-tarea 2027-01-20T10:00:00+01:00 revisar el proyecto del robot
/recordatorios
/github-estado Dirix24/cerebro
```

Las fechas deben incluir zona horaria y ser futuras. **Los recordatorios no generan notificaciones por sí solos ni funcionan con Cerebro cerrado**; el comando `/recordatorios` muestra cuáles han vencido. Para avisos automáticos habrá que integrar posteriormente un planificador local autorizado. `/github-estado` y `/github-errores` requieren Internet y acceso al repositorio público; no leen repositorios privados, no piden credenciales, no hacen commits y no abren pull requests.

**Avisos locales automáticos mientras se ejecuta el planificador:**

```bash
python3 recordatorios_daemon.py --una-vez
python3 recordatorios_daemon.py --intervalo 30
```

El segundo comando mantiene el proceso activo y muestra en su terminal los recordatorios vencidos una sola vez. Para avisos al cerrar esa terminal será necesario configurar un servicio local de usuario con consentimiento; no se instala automáticamente. Los avisos aún no son notificaciones gráficas.

**GitHub (consulta de incidencias):**

```text
/github-errores Dirix24/cerebro
```

**Cámara (captura voluntaria y análisis geométrico básico):**

```bash
python3 -m pip install opencv-python
python3 camara_local.py --confirmar
python3 camara_local.py --confirmar --guardar imagen_robot.png
```

No se abre la cámara sin `--confirmar`. Se libera tras una captura; por defecto no se guarda ninguna foto. El número de contornos **no equivale a identificar objetos**. No hay reconocimiento semántico ni modelo de visión entrenado todavía.

**Plan para la cámara:** incorporar captura local con permiso explícito, detección de objetos con un modelo de visión **propio** entrenado desde cero, almacenamiento de imágenes opcional y una política que prohíba encender la cámara sin autorización. Instalar OpenCV u otra biblioteca de imágenes no proporciona por sí solo un detector entrenado. La cámara y el reconocimiento de objetos **todavía no funcionan**.

**Arquitectura:** aumentar parámetros solo tras medir RAM, tiempo y calidad; separar motor neuronal, memoria, herramientas, dispositivos y permisos. No se incorporan pesos ni APIs de otras IA.

## 🔒 Privacidad, recursos y seguridad

- Los datos personales, el corpus y los checkpoints permanecen localmente salvo las peticiones explícitas a Wikipedia.
- La descarga de Wikipedia necesita Internet y está sujeta a las condiciones de Wikimedia y atribución de fuentes.
- El entrenamiento puede consumir CPU, RAM y batería. Los controles de temperatura, memoria y batería **no sustituyen** la vigilancia del sistema y no interrumpen todos los procesos ya iniciados.
- La desinstalación no elimina información personal por defecto.
- Antes de entrenamientos importantes, guarda una copia externa de `checkpoints/` y `data/`.
- Las funciones de voz existentes son limitadas; no se promete reconocimiento de voz ni conversación hablada completa.
- Los perfiles grandes son configuraciones disponibles, **no pesos ya entrenados**.

## 🗂️ Archivos importantes

| Ruta | Contenido |
|---|---|
| `cerebro.py` | Instalación, inicio, diagnóstico, motores y desinstalación |
| `chat.py`, `main.py` | Chat y comandos |
| `agent/orquestador.py` | Selección y explicación de rutas |
| `core/motores.py` | Inventario de motores |
| `core/instalacion.py` | Instalación y limpieza controlada |
| `core/errores_aprendizaje.py` | Registro de correcciones pendientes |
| `core/medicion_progreso.py` | Historial de evaluaciones |
| `core/puerta_checkpoint.py` | Regla de aceptación de checkpoints |
| `core/repaso_espaciado.py` | Fichas y calendario de repaso |
| `core/autoevaluacion.py` | Comparación de respuestas |
| `aprendizaje_internet.py` | Adquisición y entrenamiento diario |
| `train.py`, `cerebro_torch.py` | Entrenamiento NumPy y PyTorch |
| `core/local_search.py`, `core/conocimiento.py` | Búsqueda y fuentes |
| `data/`, `checkpoints/` | Datos y pesos locales |

Más información: [Motores de Cerebro](CEREBRO_MOTORES.md) · [Mejoras locales](MEJORAS_LOCALES.md).

## 🛣️ Próximos objetivos

- Integrar de verdad la selección del motor PyTorch dentro del chat sin perder compatibilidad con NumPy.
- Añadir evaluaciones de conocimiento, razonamiento y regresión con conjuntos separados del entrenamiento.
- Mejorar la recuperación de fuentes, la abstención ante dudas y la gestión de contradicciones.
- Comprobar arranque, instalación, desinstalación y reanudación en MX Linux.
- Medir memoria, temperatura, consumo y tiempos reales del portátil antes de activar perfiles mayores.
- Desarrollar mejoras incrementales solo cuando las pruebas y la validación justifiquen el cambio.

## 🤝 Créditos y desarrollo asistido por IA

**Cerebro es un proyecto diseñado y desarrollado con asistencia de inteligencia artificial.** Su creador define los objetivos y las decisiones de uso; una IA ha colaborado en propuestas técnicas, implementación, documentación y diseño de pruebas. El código debe revisarse y probarse: **haber sido generado o revisado por IA no demuestra su corrección**.

El objetivo es construir una IA local, transparente y ampliable, que mejore con datos y evaluaciones verificables, sin vender capacidades futuras como si ya existieran.


## 🖥️ Laboratorio visual: progreso, versiones y simulaciones

```bash
python3 cerebro.py laboratorio
```

El comando genera el archivo **`data/laboratorio_cerebro.html`**. Ábrelo con tu navegador de archivos o navegador web. Es un archivo HTML local y estático, sin servidor ni servicios externos.

El panel permite ver:
- **Progreso registrado:** historial de precisión de `/progreso`, cuando existan evaluaciones.
- **Versiones de pesos:** presencia, tamaño y fecha de modificación de los checkpoints `best.npz` y `last.npz`. No representa un historial completo de versiones.
- **Experimentos:** últimos registros de `learning/evolution/experimentos.jsonl`.
- **Red neuronal animada:** representación conceptual en movimiento, **no** activaciones neuronales reales.
- **Simulación de tareas del ordenador:** muestra pasos hipotéticos para organizar archivos sin leerlos ni cambiarlos.

Para actualizar los datos, vuelve a ejecutar el comando y recarga el HTML. **No hay monitorización en tiempo real**, ni control remoto del ordenador. Cerebro tiene herramientas de lectura y escritura restringidas, pero **no** debe recibir control autónomo del sistema sin límites, permisos explícitos, simulación y registro de acciones. El aprendizaje neuronal sigue requiriendo validación independiente.

Prueba del laboratorio:

```bash
python3 -m pytest -q tests/test_laboratorio_visual.py
```


## 🔁 Automejora guiada por evidencias

```bash
python3 cerebro.py automejora
```

El comando analiza el historial de evaluaciones, las correcciones pendientes y los resultados de entrenamiento. Genera **`data/informe_automejora.json`** con prioridades y propuestas de mejora. No requiere otro asistente ni servicio externo.

**Qué puede hacer automáticamente:** recopilar datos mediante el ciclo existente, adaptar moderadamente el número de pasos, entrenar el motor NumPy bajo sus controles de recursos, validar métricas y revertir checkpoints cuando falla la validación. Estas capacidades siguen siendo experimentales.

**Qué NO hace:** reescribir su código fuente, instalar programas por iniciativa propia, controlar libremente el ordenador, aceptar correcciones no verificadas, cambiar arquitectura sin pruebas ni garantizar que cada entrenamiento lo vuelva más inteligente. Las propuestas del informe requieren revisión; el comando `automejora` **no entrena ni modifica pesos**.

Pruebas específicas: `python3 -m pytest -q tests/test_automejora.py`.


## 🌐 Consulta automática y respuestas claras (PR pendiente)

En preguntas como `¿Qué es la robótica?`, Cerebro primero consulta su biblioteca local. Si falta una definición respaldada, **intenta automáticamente** obtener el artículo correspondiente de la API pública de Wikipedia en español. Guarda la definición con su fuente para consultas posteriores y muestra hasta dos frases en vez de cortar arbitrariamente a mitad de palabra.

**Privacidad:** solo se envía el nombre del concepto, no el historial, recuerdos o archivos. No introduzcas información privada en una pregunta de definición si no quieres que su concepto se consulte en Wikipedia. La consulta automática solo se activa para definiciones sin respuesta local; otras preguntas siguen funcionando localmente. Si la conexión falla o Wikipedia devuelve HTTP 403, Cerebro informa de que no encontró una fuente fiable. No se utilizan APIs de IA externa ni se reentrenan pesos automáticamente.

Pruebas: `python3 -m pytest -q tests/test_respuestas_claras_internet.py`. Estas funciones se encuentran en una PR pendiente de fusión, no necesariamente en `main`.


## 🔄 Exploración autónoma local e Internet (experimental)

Este modo **requiere activación explícita**. Puedes dejarlo funcionando en una terminal; cada ciclo indexa documentos de texto de tu carpeta personal, identifica relaciones por términos compartidos y consulta hasta dos artículos aleatorios de Wikipedia. No utiliza modelos de IA de terceros ni envía tus archivos a Internet.

```bash
# Una pasada de lectura y aprendizaje (sin entrenamiento de pesos):
python3 exploracion_autonoma.py --autorizar-hogar

# Repetir cada seis horas; entrenar NumPy con el ciclo seguro existente cuando corresponda:
python3 exploracion_autonoma.py --autorizar-hogar --cada-horas 6 --entrenar

# Leer solo textos locales, sin consultar Wikipedia:
python3 exploracion_autonoma.py --autorizar-hogar --solo-local
```

**Alcance y límites:** «hogar» significa tu carpeta personal (normalmente `/home/usuario`), **no** todo el disco, otros usuarios ni dispositivos externos. Solo lee archivos `.txt`, `.md` y `.rst`; omite carpetas ocultas, enlaces simbólicos, rutas de credenciales y otras carpetas sensibles. Límite por ciclo: 300 archivos, 64 KiB por archivo y 3 MiB en total. **No garantiza detectar todos los secretos**: revisa el contenido de tus carpetas antes de autorizarlo. Los textos se guardan en una base SQLite local `data/exploracion_local.sqlite3`, que puede contener datos personales y no debes subir a GitHub.

**Importante:** el índice local autónomo está separado de la búsqueda conversacional; por ahora **no alimenta automáticamente al chat ni al entrenador neuronal**. La comparación es léxica, no verifica contradicciones ni aprende relaciones semánticas. La parte web usa el ciclo diario ya existente: si ya recopiló artículos hoy, no repetirá la descarga. `--entrenar` solicita el entrenamiento existente con control de recursos, validación y restauración de checkpoints; no promete que entrene en cada pasada. El proceso funciona mientras la terminal esté abierta y se detiene con Ctrl+C. No hay servicio persistente instalado.

Prueba sin conexión: `python3 -m pytest -q tests/test_exploracion_autonoma.py`.


## 🔎 Consultar los documentos de la exploración autónoma

Después de ejecutar `python3 exploracion_autonoma.py --autorizar-hogar`, inicia el chat con `python3 cerebro.py iniciar` y pregunta:

```text
/mis-documentos robótica
busca en mis documentos sensores
consulta mis documentos inteligencia artificial
```

La consulta se hace **exclusivamente en el índice privado local** `data/exploracion_local.sqlite3`; no se envían consultas ni archivos a Internet. Muestra fragmentos de los documentos y la ruta de origen, marcados como coincidencias **no verificadas**. El índice se actualiza en cada exploración y puede quedar desactualizado si cambian los archivos. Para evitar divulgar información personal por accidente, la búsqueda se activa únicamente con estas expresiones o con el comando explícito, no en cualquier pregunta. Este cambio **no** conecta todavía esos textos al entrenamiento de pesos ni comprueba contradicciones.

Pruebas: `python3 -m pytest -q tests/test_consulta_exploracion.py`.

## Reasoning V3 experimental

La rama `feature/cerebro-reasoning-v3` incluye un Transformer propio entrenado
desde cero y un checkpoint optativo para el comando `/razonar` con PyTorch
local. Prueba `/razonar L1|0^1` para lógica booleana o `/razonar A2+3*4`
para aritmética módulo 10. Las operaciones se aplican de izquierda a derecha.
Cerebro comprueba la propuesta y se abstiene si algún paso falla.

El experimento verificó ambos pasos en 16/16 casos de lógica y 11/128 de
aritmética con combinaciones reservadas. Consulta los [resultados y comandos
reproducibles](docs/REASONING_BASELINE.md).

## Licencia

El código original de Cerebro y los pesos procedimentales de Reasoning V3
se distribuyen bajo la [licencia MIT](LICENSE). Los materiales y dependencias
de terceros conservan sus condiciones y atribuciones.

### Aprendizaje local de habilidades

Puedes enseñar una regla numérica a Cerebro durante una conversación. Los dos
primeros ejemplos determinan una regla afín y los demás deben confirmarla.
Cerebro conserva la regla entre sesiones, acepta correcciones explícitas y
marca cuándo aplica una regla fuera del rango observado.

```text
/enseñar-habilidad doble || 0:0; 2:4; 4:8
/enseñar-habilidad suma-uno || 0:1; 4:5; 8:9
/usar-habilidad doble || 3
/encadenar-habilidades doble, suma-uno || 3
/corregir-habilidad doble || 0:0; 2:4; 5:10
```

El encadenamiento del ejemplo produce 6 y luego 7. Se usan fracciones
exactas. El alcance es una familia de reglas numéricas, almacenadas
localmente en SQLite. Este modo no modifica los pesos neuronales ni convierte
conversaciones o páginas externas en instrucciones de entrenamiento.

En el modo local puedes decir `Aprende doble con estos ejemplos: 0:0; 2:4; 4:8`
y después `Usa doble con 3`. Con dos habilidades enseñadas, prueba
`Aplica doble y después suma-uno a 3`. El chat indica cuando una respuesta
carece de respaldo local. `cerebro.py todo` sigue siendo la acción explícita
para el flujo experimental de investigación y entrenamiento en segundo plano.

También puedes escribir `Aprende esta respuesta: ¿Qué es mi laboratorio? ||
Es mi espacio de pruebas.` y preguntar `Que es mi laboratorio?`. Cerebro
muestra la atribución al usuario y se abstiene si hay respuestas guardadas
que discrepan para la misma consulta.

### Conversación local con contexto

En `cerebro.py iniciar`, prueba `2mas 2`, `dos más dos` o `cuánto es 2 por 6`.
Para probar el catálogo inicial, escribe `que es japon` y en el siguiente
turno `¿y su capital?`. El modo local cita la fuente y también reconoce
preguntas básicas sobre Portugal. Este catálogo es pequeño y el tema solo se
conserva durante la sesión. Las consultas ajenas al catálogo siguen usando el
conocimiento local existente o una respuesta de incertidumbre.
