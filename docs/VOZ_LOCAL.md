# Voz y texto en Cerebro para MX Linux

El acompañante usa el mismo núcleo para una petición escrita y para una dictada.
Puedes escribir y pulsar Enter como siempre. **Dictar · 5 s** activa el
micrófono durante cinco segundos y deja la transcripción en el cuadro de texto.
Revísala o corrígela y pulsa Enter para enviarla. El audio permanece en memoria
mientras se transcribe. **Leer respuesta** reproduce el texto en español cuando
lo solicitas.

Prueba «Cerebro, abre YouTube» o «Abre el navegador» en cualquier interfaz
conectada mediante el lanzador local. El núcleo utiliza el navegador
predeterminado del escritorio y abre únicamente estas dos opciones fijas.
YouTube requiere que el acceso a internet esté habilitado. También puedes
dictar las consultas de memoria, matemáticas, investigación y documentos que
ya admite Cerebro.

## Activar el dictado opcional

La instalación habitual permite escribir. Para añadir voz:

```sh
cd ~/cerebro
sudo apt install alsa-utils espeak-ng unzip
.venv/bin/python -m pip install vosk
```

Descarga el ZIP español **vosk-model-small-es-0.42** desde el
[catálogo oficial de Vosk](https://alphacephei.com/vosk/models) y extrae la
carpeta con ese nombre dentro de
`${XDG_DATA_HOME:-$HOME/.local/share}/cerebro/voz/`. También puedes apuntar
`CEREBRO_MODELO_VOZ` a una ubicación local distinta antes de abrir el
acompañante. El catálogo indica que el ZIP tiene 39 MB y licencia Apache 2.0.
Vosk transcribe y eSpeak sintetiza. La conversación y las decisiones siguen en
el núcleo propio de Cerebro.

Cierra y vuelve a abrir el acompañante con
`~/.local/bin/cerebro escritorio`. Al dictar, el círculo indicará
**Escuchando**; durante la lectura indicará **Hablando**. Si la entrada de
micrófono falla, la caja de texto sigue disponible. Esta entrega incorpora
dictado y lectura por pulsación. Las órdenes compuestas de búsqueda y descarga,
el estudio autónomo y el sistema profesor–alumno pertenecen a fases posteriores.
