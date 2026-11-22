# Evolución de Cerebro Studio

Base auditada `918b54c` de `main`. Los cambios se limitan a `Dirix24/cerebro`.

| Área revisada | Implementación y alcance |
| --- | --- |
| Conversación | El núcleo común autentica Studio, Terminal, chat web y acompañante. Conserva las herramientas y el planificador híbrido existente. Se incorpora una ruta local de cálculo exacto y otra de contexto documental de Studio. La comprensión libre de tareas compuestas sigue dependiendo de las capacidades del planificador y de los adaptadores. |
| Modelos y Profesor | El Transformer propio, los entrenamientos NumPy y PyTorch, el maestro bajo demanda, las evaluaciones y el flujo de candidatos conservan sus contratos. El mismo cliente local de Profesor admite Ollama además de la API compatible con llama.cpp. No se cambian los pesos ni se promueven candidatos. El ejercicio en Studio usa texto del archivo y una respuesta verificable. |
| Colaboración y memoria | Se conservan los adaptadores de CAZEL y DARAS y el contrato de coordinación existente. La memoria de conversaciones, experiencias y Universe sigue disponible. Los nodos de Universe representan registros y relaciones. Los parámetros entrenables viven en checkpoints aparte. |
| Archivos y escritorio | Studio conserva las autorizaciones por cliente y los controles de guardado, cambios y pruebas. DOCX y ODT comparten extractor local limitado con ambos visores. La orden de carpeta personal usa las entradas XDG de Studio nativo y pasa por la autorización habitual. |
| Cámara, voz y multimedia | Se reutiliza MediaPipe y el controlador de gestos de X11, con un lanzador visible en Studio y un perfil de procesamiento ligero. Se conserva el sistema Vosk de voz. El análisis semántico de vídeo, de audio de archivos y de imágenes con un modelo visual sigue pendiente. |
| Instalación y recursos | Se conservan los lanzadores, instalador y desinstalador. El diagnóstico usa datos observados del host y nunca activa una cámara ni un modelo. El conteo de nodos expuestos no garantiza que la cámara pueda abrirse, y la disponibilidad de dependencias no verifica el aislamiento de Bubblewrap. |

## Comprobaciones reproducibles

```bash
python3 -m pytest -q tests -rs
PYTHONPATH=. python3 tests/manual/verificar_studio.py
```

- La referencia anterior al cambio registró 407 pruebas aprobadas, 22 omitidas y 3 subpruebas. La ejecución final con loopback registró 435 aprobadas, 6 omitidas y 3 subpruebas. Las omisiones finales corresponden a PyTorch no instalado y a Bubblewrap sin soporte de aislamiento en el entorno. Las pruebas añadidas cubren cálculo exacto, permisos del contexto, ODT y DOCX, límites XML, evaluación, diagnóstico y el contrato HTTP de Ollama.
- Chromium recorrió el flujo de edición, visor DOCX, resumen contextual, respuesta a un ejercicio, aplicación de un diff, simulación y evidencias de colaboradores, actualización del explorador y recuperación del proyecto. El script utiliza Chromium, Playwright, Pillow y repositorios hermanos accesibles.
- Tk y Xvfb comprobaron edición, visores, apertura real de Thunar y entrega a la ventana del acompañante. La comprobación de arrastre invocó el callback con una URI local.
- La integración de Ollama se verificó al nivel del contrato de transporte con un doble HTTP. Queda pendiente cargar un modelo real, medir recursos y verificar respuestas con el equipo desconectado.
- Quedan pendientes el seguimiento de mano y la calibración con cámara física, el arrastre físico desde Thunar en MX Linux y la medición de rendimiento en un ASUS X550LC. La lógica de gestos se comprueba con secuencias de puntos simuladas.
- La aceptación completa de la misión requiere ampliar las tareas compuestas desde lenguaje libre, la generación y verificación de proyectos, la coordinación conjunta, las evaluaciones de competencias y el análisis multimedia con motores reales.
