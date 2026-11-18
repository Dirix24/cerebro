import json
import pytest
from core.legado_identidad import configurar_creador, leer_origen, exportar_legado_publico, examinar_legado


def test_identidad_no_se_sobrescribe(tmp_path):
    assert configurar_creador("Danny", tmp_path)["creador"] == "Danny"
    with pytest.raises(FileExistsError):
        configurar_creador("Otro", tmp_path)
    assert leer_origen(tmp_path)["creador"] == "Danny"


def test_legado_solo_publico_y_no_importa(tmp_path):
    configurar_creador("Danny", tmp_path)
    ruta = tmp_path / "usb" / "legado.json"
    exportar_legado_publico(ruta, tmp_path)
    assert "Danny" in ruta.read_text()
    assert "conversaciones" not in ruta.read_text()
    assert examinar_legado(ruta)["importado"] is False
    paquete = json.loads(ruta.read_text())
    paquete["contenido"]["origen"]["creador"] = "Falso"
    ruta.write_text(json.dumps(paquete))
    with pytest.raises(ValueError):
        examinar_legado(ruta)
