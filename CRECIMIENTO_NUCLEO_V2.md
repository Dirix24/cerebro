# Crecimiento seguro del núcleo Cerebro V2

El núcleo admite varios tamaños mediante `CEREBRO_PERFIL`. El nuevo perfil
`v2_plus` aumenta el ancho, la profundidad y el contexto respecto a `v2`.
No sustituye el perfil por defecto ni modifica checkpoints existentes.

## Cómo entrenar el perfil ampliado

```bash
CEREBRO_PERFIL=v2_plus python train.py
```

El perfil ampliado necesita más memoria y tiempo de CPU. **Elegir un perfil
más grande crea un modelo nuevo con pesos iniciales**, no expande de manera
automática los pesos de un checkpoint pequeño. No se debe afirmar que un
modelo ampliado conserva lo aprendido sin implementar y probar una migración
de pesos.

## Datos aislados

Al usar el corpus predeterminado, `cargar_datos` excluye los documentos
idénticos a los conjuntos de test y generalización antes de dividir. Rechaza
solapamientos explícitos entre validación y dichos conjuntos. La comparación
actual es por texto exacto: las paráfrasis y duplicados casi idénticos requieren
una auditoría adicional.

## Reanudación y tasa de aprendizaje

Para un calendario fijo y reproducible, crea `ConfigEntrenamiento(total_pasos=N)`
antes de entrenar y utiliza la misma configuración al reanudar. El horizonte
se almacena en el checkpoint. En el modo tradicional sin `total_pasos`, se
permite ampliar sesiones por compatibilidad, pero la curva de aprendizaje
puede variar al cambiar la duración prevista.

## Pendientes para crecimiento real

- Migración de pesos entre arquitecturas de distinto tamaño.
- Presupuesto automático de RAM y tiempo antes de elegir perfil.
- Evaluación independiente de generalización, con control de paráfrasis.
- Pruebas integrales de checkpoint con horizonte fijo y dropout.

## Perfiles NumPy de mayor capacidad

Se han añadido dos escalones opcionales, sin cambiar el perfil predeterminado:

| Perfil | Parámetros teóricos con vocabulario objetivo | Capas | Dimensión | Contexto |
| --- | ---: | ---: | ---: | ---: |
| `v2_6m` | 6.910.464 | 8 | 256 | 256 |
| `v2_16m` | 15.920.896 | 8 | 384 | 384 |

```bash
CEREBRO_PERFIL=v2_6m python train.py
# Para equipos con suficiente memoria y paciencia:
CEREBRO_PERFIL=v2_16m python train.py
```

Las cifras son teóricas para vocabularios completos; el tokenizador puede
aprender menos tokens. El entrenamiento AdamW reserva momentos adicionales
para los parámetros y el contexto consume memoria cuadrática por cabeza.
Estos perfiles **no están preentrenados** y no aumentan automáticamente la
calidad: requieren datos y evaluación. Los checkpoints pequeños no pueden
cargarse directamente como arquitectura mayor sin migración de pesos.

## Selector único de tamaño (NumPy)

Para no configurar dimensiones, capas y cabezas por separado, usa `--tamano`:

```bash
python train.py --listar-tamanos
python train.py --tamano grande --pasos 1000
```

Opciones: `mini`, `normal`, `grande`, `potente`, `extra`, `maximo`, `experimental`.
Corresponden a `v2`, `v2_plus`, `v2_6m`, `v2_16m`, `v2_30m`,
`v2_60m`, `v2_120m`. El último escalón es experimental y puede requerir
mucha RAM y tiempo. `--listar-tamanos` estima un mínimo de memoria para
pesos, gradientes y dos momentos AdamW en float32; no incluye activaciones,
corpus ni memoria adicional de Python/NumPy.

El selector se aplica al entrenamiento **desde cero**. `--resume` carga la
arquitectura del checkpoint existente y no la convierte a otro tamaño.
