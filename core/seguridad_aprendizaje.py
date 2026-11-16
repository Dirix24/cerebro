"""Protección de checkpoints durante aprendizaje autónomo (NumPy local)."""
from pathlib import Path
import shutil
import tempfile

def respaldar(rutas):
    """Copias en directorio temporal; no modifica el checkpoint activo."""
    carpeta = Path(tempfile.mkdtemp(prefix="cerebro-seguro-"))
    existentes = {}
    for ruta in map(Path, rutas):
        if ruta.is_file() and not ruta.is_symlink():
            destino = carpeta / ruta.name
            shutil.copy2(ruta, destino)
            existentes[ruta] = destino
        else:
            existentes[ruta] = None
    return carpeta, existentes

def restaurar(existentes):
    """Restaura pesos y optimizador, incluidos checkpoints nuevos fallidos."""
    for ruta, copia in existentes.items():
        if copia is None:
            if ruta.exists() and not ruta.is_symlink():
                ruta.unlink()
        else:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(copia, ruta)

def evaluar_fijo(ruta, corpus_validacion):
    """Métrica comparable: mismo conjunto de validación, en bits por byte."""
    from core.checkpoint import cargar_checkpoint
    from trainer_engine import evaluar_modelo_en_docs
    from core.data import cargar_datos
    if not Path(ruta).is_file():
        return None
    docs_train, docs_val, _ = cargar_datos(str(corpus_validacion), 0.20)
    if not docs_val:
        raise ValueError("No hay documentos para validación fija")
    modelo = cargar_checkpoint(str(ruta), con_optimizador=False)["modelo"]
    return evaluar_modelo_en_docs(modelo, docs_val)["bpb"]
