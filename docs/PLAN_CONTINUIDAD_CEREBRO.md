# Continuidad de Cerebro

Cerebro debe convertir peticiones naturales en acciones locales verificables y compartir permisos, contexto y evidencias entre Terminal, Chat, Studio y esfera. El núcleo está en `universe/nucleo.py`. El control del escritorio vive en `universe/escritorio.py`; Qwen y el alumno tienen sus propios adaptadores. La entrada para el catálogo de herramientas se encuentra en `universe/herramientas.py`.

## Punto de partida

- Worktree `work/cerebro-demostracion`, rama `feature/demostracion-semantica`. La implementación de descarga está en `4a15e08`; el último commit se consulta con `git log -1 --oneline`.
- `main` local en `33459c8`. Mantenerlo intacto y conservar el worktree de `feature/mejoras-escritorio`.
- Auditoría completada. El equipo mostró 9,2 GiB de RAM, 5,4 GiB disponibles y 816 GiB libres en la partición del worktree. Verificar de nuevo antes de tareas intensivas.
- Fases 1 y 2 parciales. La primera herramienta reconoce órdenes como «Cerebro, clona https://github.com/octocat/Hello-World y explícame cómo funciona». Requiere internet y permisos READ/WRITE. Git verifica HEAD y lista la raíz; Cerebro muestra un extracto del README. La copia bare permanece en `universe-datos/repositorios` del hogar de Cerebro. La descarga tiene un plazo de 45 segundos.

## Matriz de capacidades

| Capacidad | Estado |
| --- | --- |
| Observación AT-SPI de casillas GTK, aprobación y reproducción | Implementado y probado en XFCE |
| Pausa, cancelación entre pasos y resumen en Universe | Implementado y probado |
| Clonación pública de GitHub, comprobación de commit y extracto | Implementado y probado en el núcleo con HTTPS real |
| Catálogo general, seguimiento de referencias y trabajo en segundo plano | Parcial |
| Explicación de componentes, apertura automática en Studio e historial de descargas | Pendiente |
| Voz y ratón para enseñar desde la esfera | Implementado, pendiente de prueba humana |
| Controles AT-SPI adicionales y Blender | Pendiente |
| Qwen local y alumno experimental | Parcial. Mejora neuronal generalizable aún pendiente |
| Cuentas y transferencias reales al clúster | Bloqueado para pruebas con datos y equipos reales hasta disponer de autorización y acceso |
| PWA y acceso remoto | Pendiente |

## Evidencias y próxima entrega

La petición al método `Nucleo.conversar` descargó `octocat/Hello-World` por HTTPS y verificó el commit `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d`, el archivo README y su contenido `Hello World!`. Se comprobó el rechazo del destino existente y del modo sin internet. GitHub rechazó un repositorio inexistente y el depósito temporal quedó vacío. La prueba no abrió el proyecto en Studio. La suite completa dio 406 pruebas y 3 subpruebas aprobadas, sin omisiones. Los dos hashes originales coincidieron.

Continúa revisando `core/proyecto_studio.py`, `universe/nucleo.py` y `universe/studio.py`. Primero añade descarga en segundo plano con cancelación y presupuesto de disco, registra el resultado por conversación y conserva el commit para resolver «ábrelo». Después prepara un árbol visible y de solo lectura para Studio a partir de archivos ordinarios y acotados del commit, sin ejecutar código del repositorio. Prueba la selección del proyecto desde Studio, permisos revocados, red fallida y cancelación. La ejecución de pruebas de un proyecto requiere la confirmación y el aislamiento existentes.

Para verificar regresiones, ejecuta `python -m pytest -q -rs` desde el worktree con el entorno virtual actual y acceso a loopback y Bubblewrap. Comprueba `checkpoints/best.npz` y `checkpoints/reasoning-v3.pt` con `sha256sum -c ../evaluacion-alumno/checkpoints-originales.sha256` en este entorno. Conserva ambos originales y los criterios de promoción. Usa commits locales y actualiza esta matriz al concluir cada entrega.

## Integración maestro–alumno sobre el main actual

Nueva rama `feature/integracion-maestro-alumno`, worktree `work/cerebro-integracion`, base `fc3701d`, integración `06f3449`. Los commits de `feature/maestro-alumno-zip` se usaron como referencia y se adaptaron al núcleo actual. Se conservan el especialista de escritorio, el flujo ANALIZAR existente, las demostraciones y la descarga Git. El profesor existente solo gana generación acotada para el alumno de hora y fecha.

En Terminal, Chat web y Studio, «Entrenar alumno» abre una autorización de dos minutos en esa conversación. «Confirma entrenar alumno» encola el trabajo. «Estado del alumno» muestra progreso, resultado y candidato activo. «Cancela entrenar alumno» detiene el ciclo en el siguiente límite seguro sin publicar un candidato cancelado. Qwen puede finalizar la consulta que está atendiendo. Configurar `CEREBRO_PROFESOR_MOTOR` y `CEREBRO_PROFESOR_MODELO` antes de iniciar el núcleo. La CLI `python entrenar_alumno_supervisado.py --retroceder` permite recuperar la versión previa. Los candidatos se guardan en `learning/alumno-supervisado`, fuera del explorador editable de Studio.

| Capacidad | Estado de verificación |
| --- | --- |
| Profesor real, entrenamiento autorizado, promoción y consulta de hora | Probados desde la Terminal real en MX Linux |
| Chat web | Consulta real de hora, solicitud, confirmación y cancelación comprobadas en Brave. Un candidato empatado se rechazó y la cancelación posterior dejó activo el mismo checkpoint |
| Studio | Ventana real en XFCE con respuesta visible de «Estado del alumno» |
| Universe | Nodo del candidato verificado por el endpoint local |
| Esfera y micrófono | Prueba visual y humana pendiente |
| Selección neuronal de archivos, red y estado del sistema | Pendiente |
| v0.1 estable | Pendiente de criterios de arranque, reinicio, recuperación y uso cotidiano |

El ciclo real aceptó 5 de 8 propuestas de Qwen y ajustó pesos con delta L2 10,40. Banco original de 16: 8 abstenciones correctas antes de entrenar, 14 aciertos después del control con semillas manuales, 16 tras incorporar las variantes Qwen con validador, 11 y 5 falsos positivos sin validador, 16 con reglas solas. En el banco diagnóstico adicional, sin duplicados con los ejemplos ni con la primera evaluación, las reglas y el sistema combinado acertaron 8/12. Ambos se abstuvieron ante cuatro consultas válidas, entre ellas «Por favor dime que hora es» y «Dme la ora local». Mantener ese resultado visible. No hay ventaja neuronal sobre las reglas en este dominio.

La suite completa dio 408 pruebas y 3 subpruebas aprobadas, sin omisiones. Los hashes originales de ambos checkpoints coincidieron. El siguiente trabajo es crear bancos separados por familias de solicitudes para búsqueda de archivos, apertura, búsqueda web y estado del sistema. Medir propuesta de etiquetas en modo observación primero. Reutilizar el registro de herramientas, sus validadores y permisos antes de habilitar cualquier acción.
