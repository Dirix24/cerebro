"""Pruebas de capacidades robóticas sin conectar hardware."""
import pytest
from core.robotica_local import preparar_robot
from core.dispositivos_conectados import listar_puertos


def test_preparar_robot_sin_flashear(tmp_path):
    r = preparar_robot("robot1", "esp32", raiz=tmp_path)
    assert r["flasheado"] is False
    assert (tmp_path / "robot1" / "robot1.ino").exists()
    with pytest.raises(FileExistsError):
        preparar_robot("robot1", "esp32", raiz=tmp_path)


def test_rechaza_placa_o_nombre_desconocidos(tmp_path):
    with pytest.raises(ValueError):
        preparar_robot("../escape", "arduino", raiz=tmp_path)
    with pytest.raises(ValueError):
        preparar_robot("robot", "desconocida", raiz=tmp_path)


def test_inventario_tiene_formato_estable():
    inventario = listar_puertos()
    assert "puertos" in inventario
    assert isinstance(inventario["puertos"], list)
