from fractions import Fraction
from types import SimpleNamespace

import pytest

from agent.controlled_agent import ControlledAgent
from chat import Conversacion
from core.habilidades import apply, teach


def test_learns_exact_rule_and_applies_new_values(tmp_path):
    db = tmp_path / "skills.db"
    teach(db, "doble-mas-uno", "0:1; 2:5; 3:7")
    assert apply(db, "DOBLE-MAS-UNO", "1,5") == (Fraction(4), 1, False)
    assert apply(db, "doble-mas-uno", "10") == (Fraction(21), 1, True)


def test_inconsistent_feedback_never_overwrites_skill(tmp_path):
    db = tmp_path / "skills.db"
    teach(db, "doble", "0:0; 1:2; 2:4")
    with pytest.raises(ValueError, match="contradicen"):
        teach(db, "doble", "0:0; 1:3; 2:4", revise=True)
    with pytest.raises(ValueError, match="ya existe"):
        teach(db, "doble", "0:0; 1:3; 2:6")
    assert apply(db, "doble", "3") == (Fraction(6), 1, True)
    teach(db, "doble", "0:0; 1:3; 2:6", revise=True)
    assert apply(db, "doble", "3") == (Fraction(9), 2, True)


def test_uses_chat_and_persists_across_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("config.raiz_datos", lambda: tmp_path)
    first = SimpleNamespace(agente=ControlledAgent())
    second = SimpleNamespace(agente=ControlledAgent())
    result, end = Conversacion._comando(first, "/enseñar-habilidad euros || 0:0; 2:3; 4:6")
    assert "Regla local guardada" in result and not end
    result, end = Conversacion._comando(second, "/usar-habilidad euros || 3")
    assert "9/2" in result and not end


def test_rejects_ambiguous_examples_and_code(tmp_path):
    db = tmp_path / "skills.db"
    for spec in ("0:1; 0:1; 2:5", "0:1; 2:5", "0:1; 1:2; 2:1+2"):
        with pytest.raises(ValueError):
            teach(db, "ejemplo", spec)
    assert not db.exists()


def test_composes_skills_on_a_combination_never_taught(tmp_path):
    from core.habilidades import chain

    db = tmp_path / "skills.db"
    teach(db, "doble", "0:0; 2:4; 4:8")
    teach(db, "suma-uno", "0:1; 4:5; 8:9")
    assert chain(db, ["doble", "suma-uno"], "3") == [
        ("doble", Fraction(6), 1, False),
        ("suma-uno", Fraction(7), 1, False),
    ]
