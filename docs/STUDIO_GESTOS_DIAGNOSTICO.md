# Studio, gestos e inventario local

La base es el merge de la PR #35 en `main`. Antes de los cambios pasaron
443 pruebas y se omitieron 6. Se conservan los adaptadores v1 de CAZEL y
DARAS, las evaluaciones de PROFESOR, la memoria y los modelos neuronales.

- Studio conserva el panel de conversación y su separador. El menú del
  visor y el control gestual siguen disponibles. Se retiró el control de
  escalado táctil de Studio. La preferencia antigua permanece legible por
  clientes anteriores.
- El control gestual detecta dependencias sin abrir la cámara. MediaPipe
  conserva pinza, arrastre y desplazamiento. El marcador verde de OpenCV
  emite exclusivamente movimiento. El margen de calibración se aplica
  a los dos modos durante la sesión. La cámara permanece apagada hasta
  autorizarla en el diálogo local.
- El inventario consulta Ollama por HTTP en 127.0.0.1 y comprueba rutas
  concretas declaradas en el entorno. No inicia modelos ni ejecuta módulos
  de otros repositorios. La disponibilidad del archivo no garantiza que
  su motor pueda cargarlo.
- El diagnóstico de recursos lee métricas de Linux y traduce algunas
  observaciones en recomendaciones. No modifica el equipo. No se añade
  una inspección de servicios ni una vista detallada de procesos.
- La selección del motor continúa mediante configuración explícita.
  Queda pendiente seleccionar automáticamente por coste, latencia o
  evaluación, así como entrenar y comparar un candidato con experiencias
  conjuntas y ampliar la recuperación de tareas por proyecto.

La prueba de OpenCV usa una imagen sintética. Queda pendiente verificar
el puntero, la calibración y las pinzas con una cámara real en MX Linux.
La prueba del inventario sustituye la consulta a Ollama y verifica que
los adaptadores no se ejecutan durante el inventario.

La suite final con OpenCV y loopback disponibles pasó 449 pruebas y
3 subpruebas. Se omitieron 6 pruebas de Bubblewrap y PyTorch. Chromium
verificó los recorridos de Studio. En Xvfb, Studio nativo conservó el
menú gestual y la conversación, y se comprobó la retirada de los dos
controles. También se ejecutó una llamada HTTP a un servidor de prueba
en loopback con el contrato de Ollama.
