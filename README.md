# CEREBRO

CEREBRO es un asistente personal de software libre para Linux, pensado para MX Linux con XFCE y X11. Reúne conversación en español, memoria local y herramientas de escritorio en un núcleo compartido por Studio, el chat web, la Terminal y el Acompañante.

## Qué puedes hacer

- **Conversar y recordar.** Haz cálculos exactos, consulta referencias en español y guarda, exporta o recupera recuerdos. Estas funciones básicas pueden usarse sin internet. Para conversación generativa, configura un modelo local con Ollama o llama.cpp.
- **Trabajar en Studio.** Autoriza una carpeta para abrir código, imágenes y PDF. Puedes pedir una propuesta de código, revisar las diferencias y confirmar antes de publicar. Universe muestra la actividad registrada del núcleo y sus herramientas.
- **Investigar y coordinar especialistas.** Autoriza las consultas públicas cuando las necesites. Los adaptadores opcionales CAZEL y DARAS aportan análisis de código e investigación. PROFESOR participa en explicaciones, ejercicios y evaluaciones.

Prueba con «Calcula el 15 % de 240», «¿Qué es un diodo?» o «Recuerda que mi proyecto se llama Mimbre».

## Instalar y arrancar

Desde la carpeta del repositorio, con Python 3 instalado:

```sh
./instalar
~/.local/bin/cerebro iniciar
```

También puedes abrir **Cerebro Studio** desde el menú de aplicaciones. Usa `./instalar --sin-autoinicio` para arrancarlo manualmente o `./instalar --sin-red` para usar las dependencias locales. Para una instalación limpia sin conexión, añade `--ruedas=/ruta/a/ruedas`.

## Estado del proyecto

En `main` se han verificado el servicio y la conversación con un modelo local, la recuperación de memoria tras reiniciar y la instalación con la red IP bloqueada. La ejecución de proyectos generados requiere un aislamiento validado. La generación de proyectos Python con varios módulos y el control gestual con cámara siguen en validación.

## Autoría y licencia

La idea y la dirección del proyecto son de **Dirix24**. El software, la documentación y las pruebas se han desarrollado en gran medida con asistencia de IA, incluidos ChatGPT y Codex.

El código es software libre bajo la [licencia MIT](LICENSE). Los extractos de Wikipedia incluidos en el [catálogo de referencias](data/referencias_publicas.json) se distribuyen bajo [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) y conservan la atribución por artículo y revisión.

## Documentación

- [Instalación, escritorio y Studio](docs/INTERFACES_MX.md)
- [Conversación y configuración de modelos](docs/CONVERSACION_MODELO_LOCAL.md)
- [Auditoría, pruebas reproducibles y limitaciones](docs/AUDITORIA_FINAL_1_0.md)
