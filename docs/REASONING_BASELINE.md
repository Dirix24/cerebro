# Referencia y experimento Reasoning V3

En la revisión base `fe98aa6`, `python evaluate.py --rapido` midió 47 %
de respuestas exactas en 32 reformulaciones y 0 de 6 en el test de diálogo.
El checkpoint original tiene 190 528 parámetros. La suite inicial obtuvo
262 aprobadas y 3 omitidas con el entorno NumPy. El checkpoint original se
conserva y se usa para los flujos habituales del chat.

## Prueba de razonamiento estructurado

Se reservaron combinaciones ordenadas completas de operadores. Cada caso
exige proponer el resultado intermedio y el resultado final. Se seleccionó el
checkpoint por la media de exactitud de lógica y aritmética en validación,
antes de evaluar la prueba.

| Modelo | Aritmética modular | Lógica booleana |
| --- | ---: | ---: |
| Cerebro NumPy original | 0/128 | 0/16 |
| Transformer diminuto sin entrenar | 0/128 | 0/16 |
| Transformer diminuto entrenado | 11/128 | 16/16 |

El modelo entrenado acertó solo el resultado final en 14/128 casos en
aritmética, contando también los 11 con ambos pasos correctos. El comparador
original no fue entrenado para el formato de dos valores. El control
aleatorio comparte arquitectura y formato con el modelo entrenado. El
análisis pareado es descriptivo para este conjunto: los ejemplos comparten
estructuras y la lógica solo cubre dos pares de operadores. No se estima
rendimiento en razonamiento general a partir de estos datos.

La prueba usa generación neuronal directa. `/razonar` verifica esa misma
propuesta con un algoritmo independiente y se abstiene ante errores. En la
prueba esto equivale a 27 resultados verificados y 117 abstenciones.
La generación entrenada promedió 0,21 ms por ejemplo procesado por lotes.
La medición del modelo original se hizo en serie y no es directamente comparable.
El [JSON de resultados](reasoning-v3-results.json) incluye las mediciones y
la huella SHA-256 de los pesos publicados.

## Entrenamiento

Transformer avanzado propio con 33 632 parámetros, inicialización aleatoria,
datos procedimentales y supervisión exclusiva de la respuesta. Se ejecutaron
2400 pasos, 844 800 tokens de entrada y 307 200 tokens supervisados en 26,87 s.
Pico observado de 332,4 MiB de RSS en CPU Intel Core i7-4500U con dos hilos,
Python 3.13 y PyTorch 2.15.0+cpu. No se utilizaron pesos ni APIs de otros
modelos. La suite con PyTorch aprobó 269 pruebas y omitió 3.

## Reproducción

Instala NumPy y PyTorch 2.6 o superior para CPU y ejecuta desde el repositorio:

```bash
python reasoning_v3.py train --checkpoint runs/v3.pt --steps 2400 --batch 32 --every 300 --threads 2
python reasoning_v3.py benchmark --checkpoint runs/v3.best.pt --threads 2
python reasoning_v3.py solve --checkpoint checkpoints/reasoning-v3.pt --problem 'L1|0^1'
python reasoning_v3.py train --checkpoint runs/v3.pt --resume --steps 300 --batch 32 --every 300 --threads 2
python -m pytest -q tests
```

El archivo principal de entrenamiento guarda también estado de optimizador y
muestreo. El archivo `.best.pt` solo contiene los pesos seleccionados y sus
metadatos para inferencia. No se incluyeron currículum, varios candidatos,
programación ni problemas narrativos en este primer experimento.
