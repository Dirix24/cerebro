# Mejoras locales de Cerebro

Esta rama mantiene el Transformer propio de NumPy, el entrenamiento manual y los
checkpoints existentes. No incorpora Ollama, llama.cpp, servicios externos,
modelos preentrenados ni dependencias obligatorias nuevas.

## Búsqueda local con SQLite FTS5

Se añade un índice de búsqueda de texto completo (SQLite, biblioteca estándar
de Python). Los resultados son fragmentos literales del corpus con su archivo
de origen: **no son respuestas generadas ni nuevos conocimientos aprendidos
por los pesos neuronales**.

```bash
python3 -m core.local_search --indexar
python3 -m core.local_search --buscar "atención"
python3 main.py
# En el chat: /buscar-corpus atención
```

El índice se guarda en `data/corpus_fts.sqlite3` y está excluido de Git.
Repite `--indexar` cuando cambien los textos de `data/corpus.txt` o
`data/corpus/*.txt`. El comando de chat solo lee el índice; nunca consulta
Internet. Si SQLite fue compilado sin FTS5, la indexación no estará disponible.

## Pruebas

```bash
python3 -m pytest -q tests/test_local_search.py
python3 tests/tests_final.py
```

La suite nueva usa pytest; el proyecto original continúa funcionando con
solo NumPy. **Las pruebas todavía no se han ejecutado en este entorno.**

## Próximos pasos sugeridos

- Mejorar el entrenamiento del Transformer NumPy sin cambiar el formato de
  los checkpoints.
- Medir mejoras con el conjunto de validación y el test independiente.
- Añadir pruebas automatizadas en CI y comparar rendimiento CPU/RAM.
