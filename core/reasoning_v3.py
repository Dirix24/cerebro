"""Procedural exact-answer reasoning tasks with disjoint operator structures."""
from dataclasses import dataclass
from itertools import product
import operator
import random
import re


OPERATIONS = {
    "A": {"+": operator.add, "-": operator.sub, "*": operator.mul},
    "L": {"&": operator.and_, "|": operator.or_, "^": operator.xor},
}
VALIDATION = {"A": {("+", "*")}, "L": {("&", "^")}}
TEST = {"A": {("*", "+"), ("*", "-")}, "L": {("|", "^"), ("^", "&")}}
TOKENS = ("<bos>", "<eos>", "A", "L", *map(str, range(10)), "+", "-", "*", "&", "|", "^", "=", ":")
TOKEN_IDS = {token: index for index, token in enumerate(TOKENS)}
TASK = re.compile(r"([AL])([0-9])([+*\-&|^])([0-9])([+*\-&|^])([0-9])=?\Z")


@dataclass(frozen=True)
class Problem:
    family: str
    a: int
    op1: str
    b: int
    op2: str
    c: int

    @property
    def question(self):
        return f"{self.family}{self.a}{self.op1}{self.b}{self.op2}{self.c}="

    @property
    def trace(self):
        ops = OPERATIONS[self.family]
        first = ops[self.op1](self.a, self.b)
        if self.family == "A":
            first %= 10
        final = ops[self.op2](first, self.c)
        if self.family == "A":
            final %= 10
        return f"{first}:{final}"

    def verified(self, response):
        return response.strip() == self.trace

    def final_correct(self, response):
        return bool(re.fullmatch(r"[0-9]:[0-9]", response.strip())) and response.strip()[-1] == self.trace[-1]


def parse_problem(text):
    if len(text) > 64:
        raise ValueError("Problema demasiado largo")
    found = TASK.fullmatch("".join(text.upper().split()))
    if not found:
        raise ValueError("Formato esperado: A2+3*4 o L1&0|1")
    family, a, op1, b, op2, c = found.groups()
    values = tuple(map(int, (a, b, c)))
    ops = OPERATIONS[family]
    if op1 not in ops or op2 not in ops or (family == "L" and max(values) > 1):
        raise ValueError("Operandos u operaciones fuera del dominio")
    return Problem(family, values[0], op1, values[1], op2, values[2])


def dataset(split, family, *, limit=None, seed=3210):
    """Hold out ordered operation pairs, not just substitutions of operands."""
    if split not in {"train", "validation", "test"}:
        raise ValueError("Partición desconocida")
    ops = set(product(OPERATIONS[family], repeat=2))
    if split == "train":
        ops -= VALIDATION[family] | TEST[family]
    else:
        ops = (VALIDATION if split == "validation" else TEST)[family]
    values = range(10 if family == "A" else 2)
    examples = [Problem(family, a, op1, b, op2, c)
                for op1, op2 in sorted(ops) for a, b, c in product(values, repeat=3)]
    random.Random(seed).shuffle(examples)
    return examples if limit is None else examples[:limit]


def encoded_inputs(problem):
    return [TOKEN_IDS["<bos>"], *(TOKEN_IDS[token] for token in problem.question)]


def encoded_training(problem):
    prompt = encoded_inputs(problem)
    labels = [TOKEN_IDS[token] for token in problem.trace] + [TOKEN_IDS["<eos>"]]
    sequence = prompt + labels
    return sequence[:-1], [-100] * (len(prompt) - 1) + labels
