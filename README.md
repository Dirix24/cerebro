# 🧠 Cerebro — IA local, memoria y aprendizaje experimental

> **Diseñado y desarrollado con asistencia de inteligencia artificial (IA).** Cerebro es un proyecto experimental impulsado por su creador, con colaboración de IA en el diseño de la arquitectura, programación, documentación y pruebas. Esta declaración describe el proceso de desarrollo, **no** significa que Cerebro sea una IA general ni que se haya diseñado a sí mismo.

**Cerebro** es un proyecto de inteligencia artificial local en Python: combina un Transformer propio NumPy, motores Transformer opcionales basados en PyTorch, búsqueda de información, memoria, herramientas deterministas y entrenamiento experimental. **No utiliza modelos preentrenados de terceros, Ollama ni APIs de IA para generar respuestas.** Wikipedia se utiliza como fuente de textos, no como motor de IA.

**Estado:** versión **experimental**, desarrollada en una rama de integración. Algunas pruebas automáticas han pasado, pero el arranque integral, la desinstalación en el equipo de destino, la calidad de las respuestas y el entrenamiento de larga duración **todavía requieren verificación**. No se debe confundir «módulo integrado en el repositorio» con «motor entrenado y disponible automáticamente dentro del chat».

## 🚀 Instalación y primer arranque

Requisitos: Linux (orientado a MX Linux / Debian), Python 3 y acceso a Internet para descargar dependencias o artículos. Desde la carpeta del repositorio:

```bash
# Instala las dependencias básicas en un entorno local aislado
python3 cerebro.py instalar

# Inicia el chat, prepara el modelo inicial si hace falta,
# indexa documentos y arranca el ciclo de aprendizaje mientras el chat esté abierto
python3 cerebro.py iniciar
```

Para añadir también la biblioteca PyTorch, **sin instalar otra aplicación de IA**:

```bash
python3 cerebro.py instalar --avanzado
```

PyTorch es una biblioteca de cálculo; **no es otro asistente ni un modelo descargado**. Puede ocupar bastante espacio y tardar en instalarse. El chat normal sigue utilizando el motor NumPy: los motores PyTorch se entrenan y generan por sus comandos específicos, **no** se alternan automáticamente dentro del chat.

La instalación no crea un servicio del sistema. El proceso de aprendizaje diario funciona mientras el lanzador permanece abierto. Cierra el chat con `/salir` para detener la sesión.

## 🧩 Todos los comandos de la aplicación

| Comando | Qué hace |
|---|---|
| `python3 cerebro.py instalar` | Instala dependencias básicas de Cerebro |
| `python3 cerebro.py instalar --avanzado` | Instala también PyTorch opcional |
| `python3 cerebro.py iniciar` | Arranque integrado con chat y aprendizaje |
| `python3 cerebro.py todo` | Inicia chat, índice y aprendizaje usando dependencias ya disponibles |
| `python3 cerebro.py chat` | Abre solo el chat NumPy |
| `python3 cerebro.py diagnostico` | Consulta estado de checkpoints, índice y batería |
| `python3 cerebro.py motores` | Enumera motores y módulos, con disponibilidad de bibliotecas |
| `python3 cerebro.py laboratorio` | Genera un panel HTML local de progreso, checkpoints y simulaciones |
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
