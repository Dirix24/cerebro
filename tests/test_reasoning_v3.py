from pathlib import Path

import pytest

from core.reasoning_v3 import TOKEN_IDS, dataset, encoded_inputs, encoded_training, parse_problem
import reasoning_v3 as experiment


def test_splits_exclude_entire_operator_pairs():
    for family in ("A", "L"):
        groups = [dataset(split, family) for split in ("train", "validation", "test")]
        keys = [{(item.op1, item.op2) for item in group} for group in groups]
        assert all(groups)
        assert all(not keys[i] & keys[j] for i in range(3) for j in range(i))
        assert groups[0] == dataset("train", family)


def test_verifier_checks_both_steps_and_domain():
    arithmetic = parse_problem(" A8 + 3 * 4 ")
    assert arithmetic.trace == "1:4"
    assert arithmetic.final_correct("0:4") and not arithmetic.verified("0:4")
    assert parse_problem("L1&0|1=").verified("0:1")
    with pytest.raises(ValueError):
        parse_problem("L2&0|1=")
    with pytest.raises(ValueError):
        parse_problem("A2&0|1=")


def test_supervision_masks_entire_prompt():
    problem = parse_problem("A8+3*4")
    x, y = encoded_training(problem)
    assert x[: len(encoded_inputs(problem))] == encoded_inputs(problem)
    assert y[:-4] == [-100] * (len(encoded_inputs(problem)) - 1)
    assert y[-4:] == [TOKEN_IDS[token] for token in ("1", ":", "4", "<eos>")]


def test_advanced_transformer_is_causal_and_gradients_are_finite():
    torch = pytest.importorskip("torch")
    torch.set_num_threads(1)
    model = experiment.create_model()
    tokens = torch.tensor([[0, 1, 2, 3, 4], [0, 1, 2, 9, 8]])
    logits = model(tokens)
    torch.testing.assert_close(logits[0, :3], logits[1, :3])
    logits.square().mean().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())


def test_exact_cpu_resume_matches_uninterrupted_training(tmp_path):
    torch = pytest.importorskip("torch")
    torch.set_num_threads(1)
    full = tmp_path / "full.pt"
    split = tmp_path / "split.pt"
    experiment.train(full, 4, 4, 3210, 0.001, 2)
    experiment.train(split, 2, 4, 3210, 0.001, 2)
    experiment.train(split, 2, 4, 3210, 0.001, 2, resume=True)
    expected = experiment.load_state(full)
    resumed = experiment.load_state(split)
    assert expected["history"] == resumed["history"]
    for name, weights in expected["weights"].items():
        torch.testing.assert_close(weights, resumed["weights"][name], atol=0, rtol=0)
    with pytest.raises(ValueError, match="difiere"):
        experiment.train(split, 1, 6, 3210, 0.001, 2, resume=True)


def test_solver_abstains_when_neuron_trace_is_invalid(monkeypatch):
    monkeypatch.setattr(experiment, "load_model", lambda _: None)
    monkeypatch.setattr(experiment, "responses", lambda *_: ["0:4"])
    assert "se abstuvo" in experiment.solve("A8+3*4", Path("unused.pt"))


def test_chat_uses_shipped_neural_weights_and_keeps_numpy_model():
    torch = pytest.importorskip("torch")
    from types import SimpleNamespace
    from chat import Conversacion

    torch.set_num_threads(1)
    legacy = object()
    chat = SimpleNamespace(agente=None, modelo=legacy)
    result, stop = Conversacion._comando(chat, "/razonar L1|0^1")
    assert "propuesta neuronal verificada" in result
    assert "paso intermedio 1, resultado 0" in result
    assert not stop and chat.modelo is legacy
