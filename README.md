# Cerebro 🧠

**Asistente personal de IA local, de código abierto y desarrollado con ayuda de inteligencia artificial.**

Cerebro es un proyecto experimental para **MX Linux con XFCE/X11** que reúne conversación, archivos, proyectos, herramientas de escritorio y un sistema de aprendizaje **maestro–alumno**. Su objetivo es que puedas pedir acciones en lenguaje natural, revisar qué hará el asistente y trabajar desde varias interfaces conectadas a un mismo núcleo.

> **Transparencia:** Cerebro fue ideado y dirigido por su creador, **Dirix24**, y gran parte de su código, documentación y pruebas se ha desarrollado con asistencia de herramientas de IA, como ChatGPT y Codex. El código generado por IA se revisa y prueba; no se presenta como escrito enteramente a mano.
>
> **Estado:** proyecto en desarrollo. No es una IA general ni todas las funciones están completas. Las capacidades y pruebas descritas dependen de la versión y del equipo.

## ¿Qué puede hacer?

- **Cuatro interfaces:** Terminal, Chat web, Cerebro Studio y esfera de escritorio, conectadas al núcleo local.
- **Cerebro Studio:** explorar proyectos y archivos autorizados, leer y editar texto, revisar cambios y ejecutar pruebas de Python en un entorno aislado cuando esté disponible.
- **Herramientas locales:** búsqueda de documentos, lectura de PDF de texto, apertura de aplicaciones y control autorizado de ventanas en XFCE/X11.
- **Memoria y Universe:** guardar y consultar recuerdos, relaciones y evidencias de acciones y evaluaciones.
- **Git y web:** consultar fuentes públicas y clonar repositorios HTTPS con comprobación de resultados, progreso, cancelación y presupuesto de almacenamiento.
- **Maestro–alumno experimental:** Qwen local mediante llama.cpp puede proponer ejemplos; un alumno pequeño entrena pesos reales, se evalúa y solo se promociona si cumple los criterios. Hay opción de cancelar y revertir.
- **Voz opcional:** la esfera admite interacción por texto; dictado y respuesta hablada requieren hardware y pruebas manuales adicionales.

**Límites importantes:** el alumno se ha probado en competencias acotadas, especialmente consultas de hora y fecha. **No se ha demostrado que supere a las reglas tradicionales ni que aprenda cualquier tarea.** Las predicciones experimentales para archivos, web y estado del sistema no deben confundirse con acciones autónomas ya habilitadas. El funcionamiento sin micrófono es válido.

## Instalación en MX Linux

Requisitos principales: MX Linux con XFCE/X11, Python 3 y las dependencias indicadas en el proyecto. Algunas funciones requieren programas adicionales; consulta [la guía de interfaces](docs/INTERFACES_MX.md).

Desde una copia del repositorio:

```bash
./instalar
export PATH="$HOME/.local/bin:$PATH"
```

Para instalar **sin autoinicio**:

```bash
./instalar --sin-autoinicio
```

### Comandos de uso

| Acción | Comando |
| --- | --- |
| Iniciar Cerebro | `cerebro iniciar` |
| Detener Cerebro y sus tareas | `cerebro detener` |
| Consultar estado | `cerebro estado` |
| Abrir Studio | `cerebro studio` |
| Abrir Chat web | `cerebro chat` |
| Abrir Terminal de Cerebro | `cerebro terminal` |
| Abrir esfera | `cerebro escritorio` |
| Activar autoinicio en XFCE | `cerebro autoinicio activar` |
| Desactivar autoinicio | `cerebro autoinicio desactivar` |
| Desinstalar | `./desinstalar` |

El autoinicio se realiza al **entrar en la sesión de XFCE**. La X de la ventana principal de Studio solicita el cierre del servicio compartido y avisa si hay cambios sin guardar. El cierre de ventanas secundarias tiene un comportamiento diferente para evitar pérdidas de trabajo.

La desinstalación normal **conserva proyectos, recuerdos, modelos y datos**. La opción `./desinstalar --borrar-datos` solicita una confirmación explícita y solo debe usarse si deseas eliminar los datos que gestiona el instalador. Haz una copia de seguridad antes.

## Maestro y alumno: qué significa «aprender»

El ciclo experimental sigue esta secuencia:

1. **Maestro:** Qwen ejecutado localmente propone ejemplos para una habilidad acotada.
2. **Validación:** se filtran ejemplos incorrectos o inseguros.
3. **Alumno:** un modelo pequeño se entrena y modifica sus pesos.
4. **Evaluación:** se compara el candidato con el modelo anterior y con reglas, usando bancos separados.
5. **Promoción o rechazo:** solo se activa el candidato cuando cumple la política de evaluación; se conserva la posibilidad de revertir.

En las interfaces compatibles puedes usar **«Entrenar alumno»**, **«Confirma entrenar alumno»**, **«Estado del alumno»** y **«Cancela entrenar alumno»**. El entrenamiento requiere confirmación en la conversación que lo inició y se ejecuta en segundo plano.

Este mecanismo **sí entrena parámetros neuronales**, pero no convierte automáticamente a Cerebro en una inteligencia general. Consulta [el informe de validación](docs/VALIDACION_CANDIDATO.md) para conocer las pruebas y sus limitaciones.

## Seguridad y privacidad

Cerebro prioriza la ejecución local y los permisos explícitos. Las operaciones sensibles pueden requerir autorización, los cambios en Studio se revisan y las pruebas de código usan aislamiento con Bubblewrap cuando está disponible. Si el aislamiento requerido no funciona, esa ejecución se rechaza.

**Local no significa infalible:** revisa las acciones propuestas, evita abrir proyectos no confiables con permisos amplios y mantén copias de seguridad. Las búsquedas públicas y descargas sí necesitan conexión a internet. Los modelos y bibliotecas de terceros tienen sus propias condiciones de licencia.

## Pruebas y desarrollo

Desde el repositorio, con las dependencias de desarrollo instaladas:

```bash
python3 -m pytest -q -ra
```

Algunas pruebas requieren loopback, Bubblewrap, X11 o intervención manual. Un resultado positivo de la suite no sustituye la prueba real de las interfaces. Consulta la [documentación de continuidad](docs/PLAN_CONTINUIDAD_CEREBRO.md) y la [validación del candidato](docs/VALIDACION_CANDIDATO.md). Las cifras de pruebas de informes antiguos no garantizan el estado de cada nueva revisión.

## Cómo colaborar 🤝

**¡Se aceptan contribuciones!** Puedes ayudar con Python, Linux, interfaces, accesibilidad, documentación, pruebas, traducciones, seguridad y evaluación del aprendizaje.

1. Abre un **Issue** para describir un error o proponer una mejora.
2. Haz un **fork** del repositorio y crea una rama.
3. Añade pruebas o explica cómo verificaste el cambio.
4. Envía un **Pull Request** con una descripción clara.

Las contribuciones pequeñas son bienvenidas. Si una función todavía es experimental, indícalo con claridad. No incluyas credenciales, datos personales ni pesos de modelos de terceros sin comprobar sus licencias.

**Repositorio:** https://github.com/Dirix24/cerebro

## Licencia abierta: MIT

Cerebro se distribuye bajo la **[licencia MIT](LICENSE)**. Puedes usar, estudiar, modificar y redistribuir el código, incluso con fines comerciales, siempre que conserves el aviso de copyright y el texto de la licencia. Los componentes y modelos externos mantienen sus licencias independientes.

---

**Cerebro es un proyecto abierto creado a partir de una idea humana y desarrollado con ayuda de IA.** Su propósito es aprender, experimentar y construir un asistente personal útil que otras personas también puedan estudiar y mejorar.
