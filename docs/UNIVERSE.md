# Cerebro Universe

Primera versión multiinterfaz para un propietario. Las cuatro vistas usan el mismo proceso Python, gestor de memoria, identidad, agente de herramientas y registro de actividad de Cerebro. El navegador utiliza HTML, CSS y JavaScript incluidos en el repositorio. La inferencia y los archivos permanecen en el equipo que ejecuta el núcleo. El uso de Wikipedia requiere habilitar internet expresamente.

## Arranque

```bash
python3 cerebro.py instalar
python3 cerebro.py universe
```

Abre la URL que imprime la terminal. La clave aleatoria viaja en el fragmento y se retira de la barra de direcciones al cargar la página. Si abres la dirección sin fragmento, puedes introducir la clave manualmente. Cierra el servidor con Ctrl+C. Para detener la visualización 3D, cambia el interruptor de Universe. La lista, los filtros y el inspector siguen disponibles.

- **Studio.** Prueba «¿Qué sabes hacer?», «Guarda esta memoria: proyecto = Atlas» y «¿Qué recuerdas del proyecto?». Usa el editor dentro de `universe-datos/`. La terminal controlada ejecuta dos tareas predefinidas: medir el estado y validar sintaxis de Python con el analizador AST. El código del editor no se ejecuta. Los estados y el resultado aparecen en la cola de tareas.
- **Universe.** Consulta recuerdos, categorías registradas, habilidades, fichas y eventos. Los vínculos unen recuerdos que comparten una categoría almacenada. El color verde identifica fichas aprobadas y su registro de aprobación, con la procedencia visible. Las fichas con una fuente registrada que carecen de esa aprobación aparecen en gris. El registro compartido `data/actividad_neuronal.jsonl` transporta etiquetas y marcas de tiempo entre el chat, los procesos existentes y la visualización. Las posiciones, la silueta de dos lóbulos, la órbita y el núcleo son una representación gráfica. Cada elemento seleccionable apunta a un dato real.
- **Canvas.** Dibuja trazos, cajas, conectores y etiquetas. Puedes alinear figuras, deshacer la última figura, guardar el dibujo localmente y exportar SVG. El formato vectorial JSON admite un proveedor futuro de visión o generación de imágenes propio. Ese proveedor deberá aceptar entradas autorizadas localmente, producir artefactos en el espacio de trabajo y registrar el resultado en el bus. La automatización gráfica actual se limita a organizar figuras del lienzo.
- **Body.** El simulador valida órdenes CAZEL-1 y arranca detenido. Al armarlo, acepta avances de hasta 50 cm y giros entre −180 y 180 grados por operación. **Parada de emergencia** bloquea las órdenes simuladas hasta un nuevo armado. La consulta de puertos necesita instalar `pyserial` en el entorno de Cerebro. El cliente de telemetría acepta lecturas numéricas de un programa local de sensores. El transporte físico CAZEL-1, el control de motores y la captura de cámara desde el panel quedan pendientes de una integración y validación por dispositivo.

El chat puede seguir funcionando con herramientas locales sin cargar pesos. Añade `--modelo` y usa `/modelo pregunta` para probar el checkpoint propio. Añade `--internet` para habilitar «Busca en internet…». Las métricas muestran CPU lógica, RAM total detectada, dispositivos DRM visibles en Linux, espacio libre, latencia mediana reciente y los datos de validación del checkpoint cuando están disponibles. La inferencia integrada se ejecuta en CPU.

## Perfiles y almacenamiento

| Perfil | Uso | Cuota inicial de Studio y Canvas |
| --- | --- | ---: |
| `--perfil usb` | USB de 8 GB. Ejecuta las herramientas sin pesos por defecto. | 32 MiB |
| `--perfil local` | Ordenador de uso diario. Pesos propios bajo petición. | 256 MiB |
| `--perfil servidor` | Núcleo en equipo propio, con token estable y proxy HTTPS para acceso remoto. | 512 MiB |
| `--perfil robot` | Instalación ligera de banco. Admite publicar lecturas desde el cliente desacoplado. | 16 MiB |

`--cuota-mib N` cambia la cuota. El contador del panel mide los archivos del espacio de trabajo y del lienzo. También verifica espacio libre antes de guardar, para permitir el reemplazo atómico. Los recuerdos, las bases de conocimiento y los pesos mantienen sus rutas y quedan fuera de la limpieza de caché. «Limpiar historial» retira resultados de tareas terminadas de la sesión y conserva las tareas activas. El presupuesto de un USB debe considerar aparte el entorno Python, los pesos y el espacio de datos.

Para mover los datos a un USB, configura `CEREBRO_HOME` con su ruta, prepara el almacenamiento con `python3 train.py --preparar-ssd` desde el entorno de Cerebro e inicia Universe con el perfil USB. Studio exporta los recuerdos activos con categoría, fecha e importancia, y rechaza un respaldo entero si una clave entra en conflicto. El respaldo de Studio cubre el almacén de largo plazo. Conversaciones, habilidades, corpus, identidad, archivos del editor y pesos se conservan por separado. Para cifrar una copia privada, usa el flujo existente de `core.memoria_cifrada`.

## Servidor y telemetría

El servidor enlaza a `127.0.0.1`. Para acceso remoto, usa un túnel SSH o un proxy HTTPS propio que reenvíe la cabecera `Authorization` al puerto local. Configura `CEREBRO_UNIVERSE_TOKEN` con un secreto aleatorio de al menos 32 caracteres y añádelo a la configuración privada del servicio. El token da acceso al espacio de un propietario. Usa `--solo-lectura` para desactivar chat y escritura desde el panel. Se recomienda limitar el acceso por red privada, VPN o túnel.

Puedes configurar `CEREBRO_ROBOT_TOKEN` como secreto distinto, de al menos 32 caracteres. Ese token permite publicar telemetría en una ruta independiente. Se aceptan hasta 16 identificadores por sesión, con hasta 16 lecturas finitas por identificador. Se muestran la última lectura y su hora de recepción. Para verificar el transporte desde un cliente:

```bash
python3 -m universe.cliente_robot http://127.0.0.1:8765 banco '{"distancia_cm": 12}'
```

Fuera de loopback, el cliente exige HTTPS y comprueba los certificados mediante la biblioteca estándar. Para conectar sensores, el programa del cuerpo puede llamar a `publicar_lecturas` con las lecturas de su adaptador. El canal permanece dedicado a telemetría. El control de movimiento remoto requerirá autorización por dispositivo, validación de tiempos y límites físicos, y una parada independiente del servidor.

## Auditoría de integración

| Repositorio | Referencias examinadas | Decisión |
| --- | --- | --- |
| Cerebro | Rama de desarrollo, base de `main`, README, arquitectura, motores, memoria, entrenamiento, estación neuronal y pruebas | Mantener el núcleo y los comandos. Reutilizar el registro JSONL, las bases existentes y el gestor de memoria. |
| Daras-IA | `main` 12fbf11, `release/daras-1.0-stable` f6c6677, `mejoras/auditoria-2026-11-19` 01e581b, auditoría de estabilidad y aplicación | Adaptar el patrón de respuestas conversacionales explícitas en `agent/dialogo_local.py` y reutilizar la decisión de separar consentimiento web, historial y caché. Conservar una única memoria. |
| CAZEL_IA | `main` 075b633, `release/cazel-1.0-stable` ad6eccf, `mejoras/auditoria-2026-11-19` 4b236c8, protocolo, seguridad, servidor y espacio | Adaptar la parte de descripción y validación de órdenes de CAZEL-1 a `universe/cazel.py`. El simulador es el único consumidor de órdenes. Se mantienen los pesos propios de Cerebro. |

Los componentes adaptados vienen de [Daras-IA](https://github.com/Dirix24/Daras-IA/tree/12fbf11c3fac2c6829ce0e4ab536893aaa062e07) y [CAZEL_IA](https://github.com/Dirix24/CAZEL_IA/tree/075b63321ac0d17ede96e61d7132853c77638156), ambos con licencia MIT, copyright © 2026 Dirix24. Se conserva el aviso MIT en `LICENSE`.

## Verificación de esta entrega

- Cerebro: 283 pruebas pasaron, 8 se omitieron y pasaron 3 subpruebas. Se incluyeron pruebas HTTP para autenticación, memoria, archivos, cuotas, Canvas, tareas y Body.
- Copia limpia en Linux: se instaló desde el lanzador, se arrancó Universe, se guardó un recuerdo y se desinstaló el entorno virtual. El archivo de recuerdos permaneció en su sitio.
- Brave 158 en Linux, en modo sin ventana: verificados el acceso al panel, mensaje en Studio, recuerdo visible con 3D desactivado, dibujo guardado y secuencia simulada de armado, avance y parada. Desde el arranque del navegador hasta el acceso transcurrieron 1660 ms en esa ejecución.
- Perfil USB, Linux, un hilo de BLAS, herramientas locales sin checkpoint: 100 llamadas basadas en cuatro casos repetidos (cálculo, deducción, capacidades y aclaración de una errata). Los 100 casos coincidieron con lo esperado. Latencia mediana de 0,27 ms en el núcleo, inicialización de 177,07 ms y RSS máximo del proceso de 36,1 MiB. La prueba mide esos cuatro recorridos locales. La evaluación de generalización neuronal se documenta por separado en [Reasoning V3](REASONING_BASELINE.md).

Daras-IA aprobó 9 pruebas y CAZEL_IA aprobó 83 en las revisiones auditadas.

La validación con un USB físico de 8 GB, despliegue HTTPS público, hardware conectado y pruebas en otros sistemas sigue pendiente. La selección automática de pesos según el equipo, las preferencias persistentes de personalidad, el control de aplicaciones y la recuperación automática de versiones tras fallos están fuera de esta primera versión.
