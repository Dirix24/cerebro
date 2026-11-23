# CEREBRO

Asistente personal de código abierto para Linux, orientado a MX Linux con XFCE/X11. Comparte conversación en español, memoria local y herramientas entre Studio, el chat web, la Terminal y el Acompañante. Proyecto experimental de Dirix24, desarrollado con asistencia de IA.

## Instalar y empezar

Desde la carpeta del repositorio, con Python 3 instalado:

```sh
./instalar
export PATH="$HOME/.local/bin:$PATH"
cerebro iniciar
```

Usa `./instalar --sin-autoinicio` si prefieres abrirlo tú. Sin internet, usa `./instalar --sin-red` si ya tienes las dependencias, o añade `--ruedas=/ruta/a/ruedas` para una instalación limpia. Puedes abrir **Cerebro Studio** desde el menú de aplicaciones, consultar el servicio con `cerebro estado` y apagarlo con `cerebro detener`. La desinstalación normal con `./desinstalar` conserva tus datos.

## Qué puedes hacer

- **Consultar y recordar.** Prueba «Calcula el 15 % de 240», «¿Qué es un diodo?» o «Recuerda que mi proyecto se llama Mimbre». Puedes exportar e importar recuerdos.
- **Trabajar en Studio.** Autoriza una carpeta para abrir código, imágenes o PDF. Pide una propuesta, revisa el diff y confirma antes de publicar. Universe muestra eventos, memoria y actividad registrada.
- **Ampliar capacidades.** Ollama o llama.cpp permiten conversación generativa local. CAZEL y DARAS son adaptadores opcionales de programación e investigación. La investigación pública requiere autorización.

El cálculo, la memoria y el catálogo de referencias funcionan sin internet. La conversación generativa requiere un modelo local instalado. La ejecución de proyectos generados exige un perfil de aislamiento validado. La generación modular y los gestos con cámara siguen en validación.

## Documentación

- [Conversación y modelos locales](docs/CONVERSACION_MODELO_LOCAL.md)
- [Studio, escritorio y gestos](docs/INTERFACES_MX.md)
- [Coordinación de especialistas](docs/COORDINACION_V1.md)
- [Auditoría y pruebas reproducibles](docs/AUDITORIA_FINAL_1_0.md)

Código bajo licencia [MIT](LICENSE).
