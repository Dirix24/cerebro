# Cerebro Next

La base revisada incluye el visor PDF y los recordatorios de la PR #35,
y la simplificación, los gestos y el diagnóstico de la PR #36.
La referencia anterior a los cambios pasó 448 pruebas con 7 omitidas.

| Área | Cambio y comprobación |
| --- | --- |
| Proyecto de código | Studio dirige peticiones de creación acotadas al cliente de modelo local existente. El JSON acepta hasta seis archivos de primer nivel, comprueba nombres y sintaxis Python, presenta un diff y exige una aprobación separada. La escritura usa publicación atómica de una carpeta nueva sin reemplazar. El código generado requiere revisión y pruebas aparte. |
| Documentos | Se reutilizan las páginas y los extractos del visor. El motor local recibe fragmentos etiquetados y añade una interpretación separada del texto verificable. Cuando el motor falla se conservan los pasajes. |
| Imágenes | El adaptador opcional habla con Ollama en loopback con el campo de imágenes de su API. Solo se usa al pedir el análisis de una imagen autorizada en Studio. No se implementó OCR ni captura de pantalla. |
| Acompañante | El diálogo de identificación consulta una vez título y clase de X11 tras la aprobación. Los metadatos se muestran localmente, sin incorporarlos al historial compartido. Se conservan la conversación y memoria que ya comparte con Studio. |
| Escritorio y cámara | Se reutiliza GIO para el conteo de identificadores de aplicaciones visibles. El diagnóstico gestual separa nodo, permisos, motor y dependencias. Detectar permisos no garantiza que el dispositivo pueda abrirse. |
| Recordatorios | Se conserva el servicio compartido y se amplía la interpretación a expresiones como «el lunes por la tarde». |
| Colaboración y aprendizaje | Se conservan los contratos con CAZEL, DARAS y PROFESOR, la evaluación y la memoria. Esta entrega no reemplaza modelos ni promueve nuevos pesos. |

## Cómo verificar

Desde el repositorio ejecuta `python3 -m pytest -q tests -rs`. El
recorrido de Studio Web se puede repetir con Chromium y Playwright
mediante `PYTHONPATH=. python3 tests/manual/verificar_studio.py`.

La generación y la interpretación de documentos usan un doble del
modelo en las pruebas. El transporte de visión se comprueba con un
doble HTTP. Las pruebas de escritura ejercitan el sistema de archivos
real. Quedan pendientes un modelo generativo y un modelo visual reales,
la ayuda visual de pantalla, el reconocimiento robusto de instrucciones
libres, las tareas largas con corrección automática y la cámara física
del ASUS X550LC.

La suite final pasó 458 pruebas y 3 subpruebas. Se omitieron 6
por PyTorch y por el aislamiento de Bubblewrap del entorno.
Chromium verificó navegación PDF, edición, coordinación con
especialistas y creación de HTML/CSS con el doble de modelo. Antes
de aprobar la propuesta se comprobó que la carpeta no existía.
