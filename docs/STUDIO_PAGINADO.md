# Studio paginado y herramientas locales

La revisión parte de `main` en `e29dee5`. El núcleo autenticado, los
proyectos con exploración acotada y las cuatro interfaces se conservan.
El visor, la consulta sobre un archivo y el análisis de código pasan por
la autorización de lectura existente. Los recordatorios requieren
permiso de escritura para crear y cancelar, y se publican mediante el
servicio local de escritorio.

## Implementación y límites

| Área | Comportamiento |
| --- | --- |
| PDF | Poppler lee a través de la entrada estándar. Se obtiene el número de páginas y se renderiza solo la solicitada, con límites de tiempo, memoria, salida y resolución de 320 a 2200 píxeles. Cada cliente conserva la página visible y descarta respuestas de navegación atrasadas. El control «100 %» restaura la resolución inicial de 980 píxeles. |
| Documentos | El resumen PDF recorre hasta 50 páginas. Las preguntas explícitas recuperan hasta cuatro pasajes por coincidencia léxica. La cita señala su página o nombre del archivo. HTML se convierte en texto inerte. La síntesis semántica, OCR y análisis de imágenes incrustadas requieren otra etapa. |
| Programación | El analizador Python usa AST y señala sintaxis y símbolos. El código pegado no se ejecuta. Se conservan las propuestas y las pruebas aisladas de proyecto. Sigue pendiente ampliar la detección y validación a otros lenguajes y la creación autónoma de proyectos. |
| Persistencia | Los recordatorios manuales y naturales comparten el almacén JSON existente. Las mutaciones se serializan y se reemplaza el archivo de forma atómica. El servicio local verifica recordatorios vencidos cada cinco segundos. Si el servicio gráfico rechaza el aviso, este sigue pendiente. |
| Modelos y especialistas | Se conserva la infraestructura de llama.cpp, Ollama, Profesor, los modelos propios y los adaptadores de CAZEL y DARAS. Esta entrega no cambia checkpoints, mediciones neuronales ni protocolos de los repositorios hermanos. |
| Resto de interfaces | Se conservan memoria, Universe, ANALIZAR, acompañante, voz, cámara, instalador y permisos. El análisis sintáctico y las operaciones de visor son rutas deterministas. La coordinación autónoma y el análisis multimedia completo siguen pendientes. |

## Verificación y pruebas pendientes

- Suite original de `main` antes de los cambios: 435 aprobadas, 6 omitidas. Suite final: 443 aprobadas, 6 omitidas y 3 subpruebas. Las omisiones corresponden a PyTorch y a un entorno que no permite iniciar Bubblewrap.
- Pruebas añadidas para horas relativas, calendario, persistencia, cancelación, entrega al programa de avisos, recuperación de pasajes y código pegado sin ejecución.
- Verificación de navegador mediante `PYTHONPATH=. python3 tests/manual/verificar_studio.py`, con un PDF real de dos páginas, navegación, cambio medido de resolución, búsqueda y cita. El script usa Chromium, Playwright, Poppler y los adaptadores disponibles.
- Studio nativo bajo Xvfb verificó el PDF de dos páginas, el cambio de resolución, la apertura de Thunar y el relevo al acompañante.
- Queda pendiente ver una notificación real en el escritorio XFCE del usuario, probar con la cámara y dependencias de su ASUS X550LC, y medir el rendimiento durante sesiones largas. La prueba automatizada de aviso comprueba la invocación del ejecutable y la transición persistente con un doble del proceso.
