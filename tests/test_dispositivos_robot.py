from pathlib import Path
import pytest
from core.proyectos_robot import preparar_robot

def test_preparar_sin_flashear(tmp_path):
    r = preparar_robot("robot", "esp32", "print('hola')", raiz=tmp_path)
    assert r["flasheado"] is False
    assert (tmp_path / "robot" / "main.py").read_text() == "print('hola')"
    with pytest.raises(FileExistsError):
        preparar_robot("robot", "esp32", "otro", raiz=tmp_path)

def test_placa_incompatible(tmp_path):
    with pytest.raises(ValueError):
        preparar_robot("robot", "arduino", "void setup() {}", raiz=tmp_path)
