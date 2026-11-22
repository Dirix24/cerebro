import json

import pytest

from core import controles_accesibles as atspi


def test_selector_exige_identidad_y_transicion_booleana():
    clave = "a" * 64
    assert atspi.selector(json.dumps(["gtk.Clase", clave, False, True])) == ["gtk.Clase", clave, False, True]
    for valor in (["gtk.Clase", clave, True, True], ["gtk.Clase", "nombre en claro", False, True],
                  ["gtk.Clase", clave, 0, 1], ["", clave, False, True]):
        with pytest.raises(ValueError):
            atspi.selector(json.dumps(valor))
