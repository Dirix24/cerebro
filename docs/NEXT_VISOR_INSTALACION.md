# Cerebro Next. Visor, instalación y GitHub

La base revisada es el merge de la PR #37, `7437cb9`. La suite de
referencia pasó 458 pruebas con 6 omitidas. Las PR #35 y #36 ya
aportaban visor paginado, recordatorios, diagnóstico y seguimiento
gestual. La generación revisable, modelos locales, coordinación,
memoria, Universe y el Acompañante ya estaban conectados al núcleo.

| Área | Cambios comprobables |
| --- | --- |
| Studio Tk y web | Rueda sin teclas modificadoras sobre el visor, anclaje al puntero, arrastre, ajuste y controles fuera de la superficie desplazable. PDF conserva la resolución real solicitada a Poppler. La escala de imagen en Tk usa el original y limita el área a 12 millones de píxeles. |
| Original | Las imágenes admiten la apertura en la aplicación asociada a XDG. Studio nativo admite también archivos individuales autorizados. Se exige confirmación explícita y se conserva el ámbito de acceso al escritorio. |
| Instalación | Diagnóstico del intérprete, importaciones reales, herramientas, permisos y motores. Las opciones de cámara instalan ruedas en el entorno virtual y permiten registrar un modelo .task existente. El instalador no abre la cámara. |
| Programación | Se conserva la propuesta revisable de la PR #37 y se puede seleccionar un modelo Ollama de código distinto del conversacional. Comparte el bloqueo de inferencia con Profesor y visión. |
| GitHub | Listado de cuenta mediante sesión de GitHub CLI y comparación pública mediante la API oficial. Cerebro no lee el token de GitHub CLI. El núcleo exige permiso READ e Internet. |
| Capacidades conservadas | Enrutamiento determinista y modelo local, visor documental y citas, voz, metadatos de X11 por consentimiento, recordatorios, CAZEL, DARAS y evaluaciones del Profesor. No se cambian repositorios externos ni pesos neuronales. |

## Validación

- Chromium verificó rueda sin modificadores, conservación aproximada
  del punto bajo el cursor, desplazamiento por arrastre, controles
  visibles y cambio de resolución del PDF.
- Studio nativo bajo Xvfb verificó rueda, anclaje, arrastre, PDF y el
  relevo al Acompañante.
- El diagnóstico se ejecutó en Linux sin webcam. Se probó una
  comparación pública real de `main` consigo mismo. El listado
  autenticado y la entrega a la aplicación externa usan dobles en las
  pruebas.
- Quedan pendientes cámara física y MediaPipe en el ASUS, modelos
  generativos y visuales reales, comparación Git local/remoto,
  publicaciones GitHub, observación de pantalla, OCR y mejora
  neuronal basada en tareas con evaluación independiente.

La suite final pasó 464 pruebas y 3 subpruebas. Se omitieron 6 pruebas
por falta de PyTorch o de soporte de aislamiento Bubblewrap.
