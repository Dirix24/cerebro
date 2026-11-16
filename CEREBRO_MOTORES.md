# Cerebro: más parámetros y segundo motor propio

Cerebro sigue siendo **una IA local propia**, sin Ollama, llama.cpp,
modelos de terceros, APIs ni descargas automáticas de pesos.

## Más parámetros neuronales

Se añadieron dos perfiles a `config.PERFILES`:

| Perfil | Dimensión | Capas | Cabezas | Contexto | FFN |
|---|---:|---:|---:|---:|---:|
| grande | 256 | 6 | 8 | 256 | 1024 |
| experto | 384 | 8 | 8 | 384 | 1536 |

Los parámetros exactos dependen del vocabulario realmente aprendido.
Un modelo más grande **no garantiza** mejores respuestas: requiere más
datos, RAM, tiempo y evaluación de calidad.

Entrenamiento NumPy original:

```bash
python3 train.py --perfil grande --pasos 100
```

## Motor propio PyTorch opcional

El nuevo archivo `cerebro_torch.py` construye desde cero un Transformer
causal con embeddings, atención multi-cabeza, GELU, LayerNorm y pesos de
salida compartidos. Usa **PyTorch como biblioteca de cálculo y autograd**,
no como servicio ni como otra IA. Puede utilizar CPU o CUDA si está
disponible. Sus checkpoints son independientes de los NumPy originales.

```bash
pip install torch
python3 cerebro_torch.py --corpus data/corpus.txt --perfil diminuto --pasos 10 --dispositivo cpu
python3 cerebro_torch.py --generar "Hola" --max-tokens 30
```

Para un equipo potente:

```bash
python3 cerebro_torch.py --corpus data/corpus.txt --perfil grande --pasos 1000 --dispositivo auto
```

**Advertencias importantes:**

- El motor PyTorch es experimental; no sustituye al chat NumPy de `main.py`.
- Se entrena desde cero con **tus textos**, no con pesos preentrenados.
- No convierte checkpoints NumPy a PyTorch ni viceversa.
- Esta primera implementación entrena con un archivo y guarda un checkpoint
  final, sin validación ni reanudación. No afirmar mejoras de calidad sin medir.
- La generación es greedy (argmax); modelos entrenados pocos pasos pueden
  producir texto sin sentido.
- `torch.load(weights_only=True)` requiere una versión de PyTorch compatible.
- **Las pruebas aún no se han ejecutado en este entorno.**

Pruebas:

```bash
python3 -m pytest -q tests/test_cerebro_torch.py tests/test_local_search.py
```
