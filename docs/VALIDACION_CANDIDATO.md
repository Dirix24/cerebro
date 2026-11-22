# Validación local del candidato Cerebro

Base principal `fc3701d`, integración recibida `680bcde`. Ambas ramas estaban limpias. Se crearon en el clon de trabajo las referencias locales `respaldo/main-fc3701d` y `respaldo/integracion-680bcde`. Las correcciones `c7715d8` y `04eeaa9` viven en `feature/auditoria-maestro-alumno`, worktree independiente. No se autorizó la integración por resultados incompletos frente a las condiciones solicitadas.

Los datos persistentes incluyen `data/` (conversaciones y registros), `memory/` (recuerdos), `universe-datos/` (espacio de Studio y copias Git), `learning/` (candidatos) y `checkpoints/` (modelos originales). Las verificaciones activas usaron hogares nuevos bajo `work/prueba-auditoria`. El archivo GGUF y llama.cpp ya estaban disponibles.

| Área | Estado | Evidencia |
| --- | --- | --- |
| Regresión, permisos, persistencia y aislamiento | Aprobado por suite | 412 pruebas y 3 subpruebas, 0 fallos y 0 omisiones en 23,95 s. Cuatro casos de PDF añadidos frente a las 408 pruebas de referencia. |
| Maestro Qwen real | Aprobado | 8 propuestas, 5 admitidas y 3 rechazadas. Carga 5,95 s; las dos generaciones tardaron 14,91 s y 11,96 s, con carga incluida en la primera. 43,59 s acumulados de CPU de llama-server, pico RSS 1.828.692 kB. Salida del proceso confirmada tras cerrarlo. |
| Alumno y reversión | Aprobado para hora y fecha | 450 pasos sobre 21 ejemplos, SHA de pesos cambiado, delta L2 10,40. Reapertura del núcleo y consulta de 3,21 ms sin levantar Qwen. Rollback de la primera promoción comprobado con conservación del candidato. |
| Terminal y ANALIZAR | Aprobado para el flujo probado | Lanzador real, estado, consulta y cierre. «Analiza el aprendizaje» produjo diagnóstico real en un perfil sin evaluaciones. |
| Studio | Aprobado para el ciclo de entrenamiento | Interfaz nativa XFCE. Inicio, autorización, progreso y resultado visible; ciclo en 16,36 s, candidato `0ab98a48037d425aa52bd08b7981270a`. Explorador, visualizadores y guardado de proyectos sin repetir visualmente en esta auditoría. |
| Universe | Aprobado por consulta del núcleo | Verificado nodo con versión activa, métricas y ejemplos aceptados. Vista gráfica sin repetir. |
| Chat en Brave | No probado visualmente en este commit | Hay prueba visual en el commit padre 680bcde y pruebas automatizadas. Falta repetir el flujo esencial y reinicio del navegador sobre el candidato corregido. |
| Esfera y voz | No probado | Falta una comprobación visual de la esfera y una persona que hable por el micrófono y confirme el audio recibido. |
| Escritorio AT-SPI | Aprobado para el flujo probado | Ventana GTK desechable, observación, aprobación, reproducción después de mover y redimensionar y rechazo sin efectos cuando falta la segunda casilla. |
| Git y PDF | Aprobado para el flujo probado, parcial en límites | Clonación HTTPS de `octocat/Hello-World`, commit `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d` y README verificado. Las URLs de PDF ya no activan Git. La descarga general, apertura automática del clon en Studio, cancelación y límite total de disco siguen pendientes. |
| Instalación limpia y reinicio del servicio completo | No probado | Se validó el arranque con el entorno virtual disponible. La recarga del alumno se probó en otra instancia del núcleo con los mismos datos. |
| Checkpoints originales | Aprobado | `best.npz`: `74bb8fefb5fb549342403b57d2d6becd9655955d1e8a810c5f077fb706c7f6fe`. `reasoning-v3.pt`: `25440710f5626735a6ba8430818b019a56f0e80a999e6300ee71c2cb099adc76`. |

## Generalización

En el banco de promoción, reglas solas 16/16, alumno entrenado con semillas y validador 14/16, alumno con Qwen y validador 16/16. Red sin validador 11/16 y cinco falsos positivos. La promoción experimental se acota a las dos consultas de solo lectura.

El banco separado en `BANCO_AUDITORIA_INTENCIONES.md` contiene 20 frases sin duplicados con el entrenamiento ni con el banco de promoción. Reglas y sistema combinado obtuvieron ambos 16/20 bajo el contrato vigente: 2 de 6 consultas válidas resueltas, cobertura positiva del 33 %, 14 abstenciones correctas y 0 falsos positivos. Las 14 abstenciones no representan competencia en búsquedas, apertura, web, estado ni otras intenciones. Ninguna predicción nueva se conectó a acciones. No se demuestra ventaja neuronal sobre las reglas.

## Puerta de integración

Queda pendiente validar en el commit candidato el Chat visual con reinicio, el uso cotidiano de archivos y proyectos en Studio, las pruebas manuales de esfera y voz, y la recuperación de errores en la instalación habitual. También quedan mediciones de RAM en reposo, Chat y Studio y pruebas de los límites de disco de la clonación. Mantener `main` en `fc3701d` hasta verificar las condiciones críticas.
