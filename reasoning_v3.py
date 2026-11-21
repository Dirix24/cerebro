"""Train and evaluate Cerebro's own small advanced Transformer on CPU."""
import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import random
import tempfile
import time

from core.reasoning_v3 import (
    TOKENS, TOKEN_IDS, dataset, encoded_inputs, encoded_training, parse_problem,
)

FORMAT = "cerebro-reasoning-v3-experiment-1"
PROFILE = "diminuto"
FAMILIES = ("A", "L")
ROOT = Path(__file__).resolve().parent
LOGIC_TEST_LIMIT = 16
ARITHMETIC_TEST_LIMIT = 128


def create_model():
    from core.advanced_torch import construir_modelo_avanzado
    return construir_modelo_avanzado(PROFILE, len(TOKENS))


def tasks(split):
    return [item for family in FAMILIES for item in dataset(
        split, family, limit=ARITHMETIC_TEST_LIMIT if family == "A" else LOGIC_TEST_LIMIT,
    )]


def responses(model, problems):
    import torch
    if not problems:
        return []
    inputs = torch.tensor([encoded_inputs(p) for p in problems], dtype=torch.long)
    tokens = []
    with torch.inference_mode():
        for _ in range(4):
            next_token = model(inputs)[:, -1].argmax(dim=-1)
            tokens.append(next_token.tolist())
            inputs = torch.cat((inputs, next_token[:, None]), dim=1)
    output = []
    for row in zip(*tokens):
        answer = []
        for token in row:
            if token == TOKEN_IDS["<eos>"]:
                break
            answer.append(TOKENS[token])
        output.append("".join(answer))
    return output


def evaluate(model, problems):
    model.eval()
    return [answer for start in range(0, len(problems), 64)
            for answer in responses(model, problems[start:start + 64])]


def summary(problems, predictions):
    report = defaultdict(lambda: {"n": 0, "verified": 0, "final": 0, "empty": 0})
    for problem, prediction in zip(problems, predictions, strict=True):
        data = report[problem.family]
        data["n"] += 1
        data["verified"] += int(problem.verified(prediction))
        data["final"] += int(problem.final_correct(prediction))
        data["empty"] += int(not prediction.strip())
    return dict(report)


def atomic_save(path, state):
    import torch
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("No se admite un destino simbólico")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            torch.save(state, file)
            file.flush()
            os.fsync(file.fileno())
            file.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def load_state(path):
    import torch
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Checkpoint ausente o fuera de límites")
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state.get("format") != FORMAT or state.get("profile") != PROFILE or state.get("tokens") != TOKENS:
        raise ValueError("Checkpoint incompatible")
    return state


def peak_rss_mib():
    try:
        import resource
        import sys
    except ImportError:
        return None
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor, 1)


def train(output, steps, batch, seed, lr, every, resume=False):
    import torch
    import torch.nn.functional as F

    if not 1 <= batch <= 128 or not 1 <= steps <= 10000 or not 1 <= every <= 10000 or not 0 < lr <= 0.01:
        raise ValueError("Configuración fuera de límites del experimento CPU")
    output = Path(output)
    best_path = output.with_name(output.stem + ".best.pt")
    if not resume and (output.exists() or best_path.exists()):
        raise ValueError("El checkpoint existe. Usa --resume o elige otro destino.")
    torch.manual_seed(seed)
    sampler = random.Random(seed)
    training = [dataset("train", family) for family in FAMILIES]
    validation = tasks("validation")
    dataset_hash = hashlib.sha256("\n".join(p.question + p.trace for family in training for p in family).encode()).hexdigest()
    model = create_model()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    parameters = sum(p.numel() for p in model.parameters())
    settings = {"seed": seed, "batch": batch, "lr": lr, "dataset": dataset_hash, "every": every}
    start = 0
    best = -1
    history = []
    if resume:
        state = load_state(output)
        if state.get("settings") != settings or "optimizer" not in state:
            raise ValueError("Configuración de reanudación difiere del checkpoint")
        model.load_state_dict(state["weights"])
        optimizer.load_state_dict(state["optimizer"])
        sampler.setstate(state["sampler"])
        torch.set_rng_state(state["rng"])
        start, best, history = state["step"], state["best"], state["history"]
    started = time.perf_counter()
    model.train()
    for step in range(start + 1, start + steps + 1):
        examples = [sampler.choice(training[index % len(training)]) for index in range(batch)]
        x, y = zip(*(encoded_training(problem) for problem in examples))
        targets = torch.tensor(y)
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(model(torch.tensor(x)).flatten(0, 1), targets.flatten(), ignore_index=-100)
        if not torch.isfinite(loss):
            raise RuntimeError("Pérdida no finita")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        if step % every == 0 or step == start + steps:
            stats = summary(validation, evaluate(model, validation))
            score = sum(row["verified"] / row["n"] for row in stats.values()) / len(stats)
            row = {"step": step, "loss": round(loss.item(), 5), "validation": stats}
            history.append(row)
            print(json.dumps(row), flush=True)
            common = {"format": FORMAT, "profile": PROFILE, "tokens": TOKENS, "weights": model.state_dict(),
                      "step": step, "parameters": parameters, "settings": settings}
            if score > best:
                best = score
                atomic_save(best_path, common)
            atomic_save(output, {
                **common, "optimizer": optimizer.state_dict(), "sampler": sampler.getstate(),
                "rng": torch.get_rng_state(), "best": best, "history": history,
            })
            model.train()
    print(json.dumps({"seconds": round(time.perf_counter() - started, 2), "parameters": parameters,
                      "peak_rss_mib": peak_rss_mib(),
                      "input_tokens_total": (start + steps) * batch * len(x[0]),
                      "supervised_tokens_total": (start + steps) * batch * 4}), flush=True)


def paired_p_value(problems, before, after):
    wins = losses = 0
    for p, a, b in zip(problems, before, after, strict=True):
        wins += int(not p.verified(a) and p.verified(b))
        losses += int(p.verified(a) and not p.verified(b))
    n = wins + losses
    value = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(wins, losses) + 1)) / (2**n))
    return {"improved": wins, "regressed": losses, "two_sided_p": value}


@lru_cache(maxsize=1)
def load_model(path):
    model = create_model()
    model.load_state_dict(load_state(path)["weights"], strict=True)
    return model.eval()


def solve(text, checkpoint):
    problem = parse_problem(text)
    candidate = responses(load_model(str(checkpoint)), [problem])[0]
    if not problem.verified(candidate):
        return "Cerebro V3 se abstuvo: la propuesta neuronal no superó la verificación."
    first, final = candidate.split(":")
    return f"Cerebro V3 · propuesta neuronal verificada: paso intermedio {first}, resultado {final}."


def benchmark(path, original, seed):
    import torch
    from core.checkpoint import cargar_checkpoint

    problems = tasks("test")
    torch.manual_seed(seed)
    random_model = create_model()
    trained = load_model(str(path))
    start = time.perf_counter()
    before = evaluate(random_model, problems)
    random_ms = (time.perf_counter() - start) * 1000 / len(problems)
    start = time.perf_counter()
    after = evaluate(trained, problems)
    trained_ms = (time.perf_counter() - start) * 1000 / len(problems)
    baseline = cargar_checkpoint(original, con_optimizador=False)["modelo"]
    start = time.perf_counter()
    initial = [baseline.generar("usuario: " + problem.question + "\ncerebro:", max_nuevos=8,
                                temperatura=0, parar_en=("\n",), incluir_prompt=False)
               for problem in problems]
    initial_ms = (time.perf_counter() - start) * 1000 / len(problems)
    return {
        "original": summary(problems, initial), "random": summary(problems, before),
        "trained": summary(problems, after), "paired_vs_random": paired_p_value(problems, before, after),
        "paired_vs_original": paired_p_value(problems, initial, after),
        "average_ms_per_case": {"original_serial": initial_ms, "random_batched": random_ms,
                                "trained_batched": trained_ms},
    }


def main():
    import torch
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("train", "benchmark", "solve"))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--original", type=Path, default=ROOT / "checkpoints" / "best.npz")
    parser.add_argument("--problem")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--seed", type=int, default=3210)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--every", type=int, default=300)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--threads", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    if args.mode == "train":
        train(args.checkpoint, args.steps, args.batch, args.seed, args.lr, args.every, args.resume)
    elif args.mode == "benchmark":
        print(json.dumps(benchmark(args.checkpoint, args.original, args.seed), indent=2))
    elif args.problem:
        print(solve(args.problem, args.checkpoint))
    else:
        parser.error("solve requiere --problem")


if __name__ == "__main__":
    main()
