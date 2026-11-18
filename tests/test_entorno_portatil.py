"""El SSD portátil conserva rutas y el detector no necesita GPU."""
import config
from core.entorno_portatil import detectar_entorno, recomendar_tamano


def test_rutas_portatiles_respetan_home():
    assert config.CKPT_ULTIMO.startswith(config.CEREBRO_HOME)
    assert config.MEMORY_FILE.startswith(config.CEREBRO_HOME)
    assert config.CORPUS_FILE.startswith(config.CEREBRO_HOME)


def test_detectar_equipo_sin_efectos(tmp_path):
    info = detectar_entorno(tmp_path / "cerebro")
    assert info["disco_total_bytes"] >= info["disco_libre_bytes"] >= 0
    assert "NumPy" in info["motor"]
    assert info["disco_ruta"].endswith("cerebro")


def test_ram_pequena_recomienda_mini():
    assert recomendar_tamano(128 * 1024 * 1024) == "mini"


def test_mas_ram_no_reduce_capacidad():
    perfiles = list(config.TAMANOS_NUCLEO)
    bajo = recomendar_tamano(2 * 1024 ** 3)
    alto = recomendar_tamano(64 * 1024 ** 3)
    assert perfiles.index(alto) >= perfiles.index(bajo)
