# Cerebro portátil en SSD de 120 GB

Cerebro puede usar un directorio externo como hogar de sus datos sin mover
el código fuente. Configura la variable `CEREBRO_HOME` con la ruta **real**
de tu SSD montado. Nunca se escribe en el disco externo si no está conectado
o si la ruta es incorrecta; comprueba el destino antes de entrenar.

Linux/macOS:

```bash
export CEREBRO_HOME="/ruta/real/del/SSD/Cerebro"
python train.py --preparar-ssd  # solo la primera vez, con el SSD conectado
python train.py --detectar-equipo
python train.py --listar-tamanos
python train.py --tamano auto --pasos 100
python main.py
```

Windows PowerShell:

```powershell
$env:CEREBRO_HOME = "E:\Cerebro"
python train.py --detectar-equipo
python train.py --tamano auto --pasos 100
python main.py
```

Las rutas de corpus, checkpoints, memoria principal, conocimiento y varios
historiales se basan en `CEREBRO_HOME`. Otras herramientas del proyecto pueden
seguir usando rutas propias: audítalas antes de considerar una migración
completa. Para conservar datos antiguos, **copia** manualmente `data/`,
`memory/` y `checkpoints/` al SSD con Cerebro detenido; verifica los
archivos antes de borrar originales. No hay migración automática.

`--detectar-equipo` informa CPU lógica, RAM física estimada y espacio libre.
`--tamano auto` selecciona una arquitectura **al iniciar un entrenamiento
nuevo**, con margen conservador para AdamW. No convierte checkpoints existentes
ni cambia el tamaño del modelo en caliente. Los modelos NumPy actuales
ejecutan cálculo en CPU; detectar una GPU no significa poder usarla.

Un SSD de 120 GB es **almacenamiento**, no 120 GB de RAM. La RAM del equipo
determina qué modelos se pueden entrenar; el espacio libre del SSD determina
cuántos modelos y datos caben. Para migrar entre ordenadores, instala Python,
NumPy y las dependencias del proyecto en cada uno y utiliza el mismo
`CEREBRO_HOME`. Expulsa el SSD de forma segura tras cerrar Cerebro.

## Protección contra desconexiones

Antes de usar el SSD por primera vez, define `CEREBRO_HOME` y ejecuta
`python train.py --preparar-ssd`. Se crea un marcador `.cerebro_ssd` y
las carpetas de datos. Cuando `CEREBRO_HOME` está definido, `train.py`
y `main.py` rechazan arrancar si no encuentran ese marcador, evitando
crear una nueva carpeta en el disco interno al faltar la unidad.

**Precaución:** comprueba la ruta y el volumen montado antes de preparar;
el marcador no puede detectar todos los casos de sustitución o montaje de
otra unidad. No desconectes el SSD mientras Cerebro esté ejecutándose.
