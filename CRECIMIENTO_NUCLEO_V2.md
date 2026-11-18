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
