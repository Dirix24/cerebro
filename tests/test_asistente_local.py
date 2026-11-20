import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import cerebro


def test_iniciar_launches_local_chat_without_training_or_network():
    with patch.object(cerebro, "_ejecutar", return_value=0) as run:
        assert cerebro.iniciar_automatico() == 0
    command, = run.call_args.args
    assert command == [sys.executable, str(cerebro.RAIZ / "main.py"), "--local"]


def test_chat_cli_accepts_multiline_input_and_uses_learned_skills(tmp_path):
    root = Path(__file__).resolve().parents[1]
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    (tmp_path / ".cerebro_ssd").write_text("cerebro-ssd-v1\n")
    shutil.copyfile(root / "checkpoints" / "best.npz", checkpoints / "best.npz")
    result = subprocess.run(
        [sys.executable, "cerebro.py", "iniciar"], cwd=root,
        env={**os.environ, "CEREBRO_HOME": str(tmp_path), "OPENBLAS_NUM_THREADS": "1"},
        input=("ok\nAprende doble con estos ejemplos: 0:0; 2:4; 4:8\n"
               "Aprende suma-uno con estos ejemplos: 0:1; 4:5; 8:9\n"
               "Aplica doble y después suma-uno a 3\n"
               "Aprende esta respuesta: ¿Qué es el banco de pruebas? || Es nuestro entorno de simulación.\n"
               "Que es el banco de pruebas?\n"
               "¿Quién ganó la final de un evento que no está en mis datos?\n"),
        text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "De acuerdo" in result.stdout
    assert "doble (revisión 1) → 6" in result.stdout
    assert "suma-uno (revisión 1) → 7" in result.stdout
    assert "Fuente: Declarado por el usuario" in result.stdout
    assert "No tengo una respuesta fiable" in result.stdout
    assert not (checkpoints / "last.npz").exists()
