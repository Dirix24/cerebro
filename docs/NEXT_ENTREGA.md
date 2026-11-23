# CEREBRO Next

Entrega incremental basada en `main` en `107c80f60499799b8a8d58cf322ea1a1c1bd0dff` (PR #42).

## Auditoría del punto de partida

| Área | Estado en la base y rutas examinadas |
| --- | --- |
| Conversación y coordinación | Implementadas en el núcleo de Universe, `chat.py` y las rutas deterministas de escritorio. El modelo conversacional intervenía temprano en definiciones reconocidas. El contexto generativo se mantenía en RAM. |
| Modelo propio | `checkpoints/best.npz` contiene un Transformer NumPy operativo. `reasoning-v3.pt` y el motor PyTorch son experimentales y requieren la dependencia opcional. |
| Entrenamiento y PROFESOR | Existen evaluación por fichas verificadas, bancos aprobados, entrenamiento de candidatos, promoción condicionada y reversión. La evaluación de dependencias funciona localmente. La generación de ejemplos y las explicaciones del profesor generativo requieren motor. |
| CAZEL y DARAS | Adaptadores v1 independientes con permisos, validación de contrato y plazos. Requieren repositorios de confianza configurados y, en CAZEL, un proyecto autorizado. La red de DARAS depende del permiso y de la solicitud. |
| Memoria e historial | Memoria local, JSONL por conversación, respaldo JSON y comandos `/extraer-recuerdos` y `/insertar-recuerdo`. Faltaba convertir una selección de mensajes en un recuerdo portable con vista previa. |
| Studio y visores | Proyecto confinado, visor raster/PDF, texto, HTML estático, editor, validaciones, pruebas, diferencias y generación con revisión. El centro mostraba todas las pestañas desde el inicio. |
| Universe | Mapa conceptual de memoria, eventos, conocimiento, ejercicios y experiencias. Separado de la estación de activaciones y pesos. La eliminación de recuerdos existentes exige confirmación. |
| Terminal y herramientas de código | Terminal con ámbito de conversación propio, análisis de Python, herramientas de GitHub y acciones de proyecto sujetas a revisión o permisos. Las pruebas de proyecto dependen del perfil de aislamiento. |
| Acompañante | Esfera con chat, voz opcional y consulta puntual de metadatos X11 tras autorización. Las rutinas autorizadas ya existen. El aprendizaje pasivo y las sugerencias personalizadas permanecen pendientes. |
| Gestos | Función experimental. Detección MediaPipe con dependencias compatibles y marcador verde como respaldo. Diagnóstico y permisos de cámara existentes. |
| Instalador y modelos | Detección de entorno, dependencias, recursos, Ollama y llama.cpp. El instalador ya probaba candidatos ligeros de Ollama. llama.cpp requería configuración manual. |
| Internet y privacidad | Consultas públicas, repositorios, ramas, commits, issues y PR. Los proyectos y las acciones tienen permisos específicos. OAuth de Google queda pendiente. |

## Arquitectura y cambios

- Studio y Acompañante utilizan el servicio local autenticado. El núcleo resuelve primero las rutas deterministas, incluida la competencia supervisada de hora y fecha. El motor local redacta respuestas a consultas informativas y continuaciones reconocidas. Puede recuperar hasta seis pares del historial persistido. Los intercambios temporales de escritorio quedan fuera de esa recuperación. Ante un fallo conserva las rutas de respaldo existentes.
- El instalador compara la RAM disponible con los candidatos conocidos de Ollama. Si no logra activar uno, prueba GGUF locales en `models/` con `llama-server` en CPU, con un solo proceso y en loopback. Guarda la elección después de recibir texto. El inventario distingue una selección guardada de un motor disponible. Las configuraciones explícitas mantienen prioridad.
- «Investiga sobre electrónica» puede seleccionar DARAS y «Analiza el proyecto» puede seleccionar CAZEL cuando sus rutas están autorizadas. La ruta implícita de CAZEL usa análisis sobre el proyecto configurado. El registro de experiencia incluye estado, operación y duración. Las rutas de colaboración y evaluación de PROFESOR permanecen disponibles.
- Studio nativo abre un centro vacío. Revela las vistas al abrir contenido o al haber una operación que mostrar. Los visores, la generación con diff y el chat a la derecha usan las rutas existentes. La versión web conserva su distribución anterior. Studio nativo permite recordar el acceso a carpetas concretas. El permiso está ligado a la ruta y a la identidad de la carpeta en el sistema de archivos. Revocarlo invalida las sesiones de proyecto y sus propuestas pendientes. Las operaciones que ya empezaron pueden terminar.
- Universe nativo añade leyenda y filtros de categoría, grupo, estado y proceso. Los filtros se aplican a los nodos disponibles y la ficha muestra los metadatos registrados de adaptadores.

## Recuerdos portables

El diálogo de Studio y Acompañante permite exportar la selección o todos los
mensajes visibles, hasta 60. JSON `cerebro-recuerdo-v1` contiene `formato`,
`id`, `tema`, `procedencia` y `mensajes`. Cada mensaje tiene `rol`,
`texto` y `fecha` ISO 8601. El ID es SHA-256 de la lista de mensajes
serializada por Python con `json.dumps(ensure_ascii=True, sort_keys=True)`
y codificada en UTF-8. Identifica el fragmento y permite detectar cambios.
La procedencia declarada en el archivo carece de autenticación externa.
Markdown exporta una copia legible.

La importación valida el formato y el tamaño, muestra las citas y consulta
si el ID ya existe. Un conflicto de metadatos para el mismo fragmento se
bloquea y se conserva la copia existente. La confirmación escribe en la
memoria local. `/recuerdo recuerdo_ID` muestra el contenido y
`/contexto-recuerdo recuerdo_ID pregunta` selecciona citas para una consulta.
Con un motor configurado, la explicación recibe las citas como datos no
confiables. Sin motor muestra las citas. Las instrucciones de archivos
importados nunca se despachan como órdenes y la importación no inicia
entrenamiento. La detección de contradicciones entre fragmentos distintos,
la clasificación de hechos y opiniones y los metadatos de referencias
externas quedan pendientes.

## Validación y pendientes

- `python -m pytest -q tests -rs`: 489 pruebas aprobadas, 6 omitidas y 3 subpruebas aprobadas. Compilación sintáctica y `git diff --check` correctos. El entorno ejecutó loopback, pruebas PDF, OpenCV y cifrado. Se omitió el aislamiento de Bubblewrap y las pruebas opcionales de PyTorch.
- `python evaluate.py --rapido` ejecutó el checkpoint incluido en CPU. Tiene 190 528 parámetros, 47 % de respuestas exactas en 32 reformulaciones y 0 % en seis preguntas del test final. Generalización de 4,510 bits/byte. La suite entrenó pesos reales de un candidato de hora/fecha, comprobó rechazo y ejercitó promoción y reversión con una referencia de promoción controlada. La entrega conserva los checkpoints distribuidos.
- Se ejecutaron copias temporales de CAZEL (`28bd14e`) y DARAS (`a224fbb`) a través del núcleo. CAZEL analizó Python y DARAS devolvió un plan en modo sin red. PROFESOR preparó y evaluó un ejercicio de dependencias. La consulta de fuentes en vivo de DARAS queda sin verificar en esta ejecución.
- Studio nativo se probó sobre X.Org virtual con el servicio HTTP real. Se comprobó el centro vacío, las tres columnas, la recepción por el manejador de soltar, la renderización de imagen y PDF y la apertura de proyecto y Python. La propuesta de calculadora usó un doble del generador y se publicó tras la aprobación. Se comprobó también el flujo para recordar, reabrir y revocar permisos desde el menú.
- Las pruebas de selección generativa usaron dobles de motor. No había un servicio Ollama ni una instalación con GGUF disponible para verificar una inferencia generativa externa real. El instalador puede usar modelos ya presentes y conserva la opción de descarga explícita del modelo ligero.
- La cámara física, MediaPipe con manos reales, el control de ventanas en MX Linux XFCE del ASUS, los hábitos persistentes del Acompañante, el entrenamiento colaborativo programado, los recursos por proceso en Universe y las integraciones OAuth siguen pendientes de implementación o validación física según el área. La Terminal conserva su ámbito privado y capacidades existentes.
