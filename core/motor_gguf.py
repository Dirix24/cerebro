"""Motor GGUF opcional mediante llama-cpp-python, totalmente local.

No descarga modelos, no abre servidores ni ejecuta herramientas. El usuario
proporciona un archivo GGUF existente y autoriza su uso explícitamente.
"""
from pathlib import Path


def cargar_gguf(ruta, n_ctx=2048, n_gpu_layers=0):
    if not 128 <= n_ctx <= 32768:
        raise ValueError("n_ctx fuera de límites")
    if not 0 <= n_gpu_layers <= 200:
        raise ValueError("n_gpu_layers fuera de límites")
    archivo = Path(ruta).expanduser().resolve(strict=True)
    if not archivo.is_file() or archivo.suffix.lower() != ".gguf":
        raise ValueError("Se requiere un archivo .gguf local")
    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError("Instala el motor opcional: pip install llama-cpp-python") from exc
    return Llama(model_path=str(archivo), n_ctx=n_ctx, n_gpu_layers=n_gpu_layers,
                 verbose=False)


def responder_gguf(motor, mensajes, max_tokens=256):
    if not 1 <= max_tokens <= 2048:
        raise ValueError("max_tokens fuera de límites")
    if not mensajes or any(m.get("role") not in ("system", "user", "assistant")
                          or not isinstance(m.get("content"), str) for m in mensajes):
        raise ValueError("Historial inválido")
    respuesta = motor.create_chat_completion(messages=mensajes, max_tokens=max_tokens,
                                             temperature=0.6)
    return respuesta["choices"][0]["message"]["content"].strip()
