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
