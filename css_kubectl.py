#!/usr/bin/python3.9
import pdb
import subprocess
import sys
import time
from collections import defaultdict
from typing import Any, Callable

import yaml
from tinycss2 import ast, parse_stylesheet


def split_semicolons(
    l: list[ast.Node], cond: Callable[[ast.Node], bool]
) -> list[list[ast.Node]]:
    res = []
    collected = []
    items = list(l) + [...]
    for item in items:
        split = not (
            isinstance(item, ast.LiteralToken) and item.value == ";" or item == ...
        )
        if split:
            collected.append(item)
        else:
            res.append(collected)
            collected = []

    return res


def strip_whitespace(toks: list[ast.Node]) -> list[ast.Node]:
    return [tok for tok in toks if not isinstance(tok, ast.WhitespaceToken)]


def recursive_dd() -> defaultdict:
    return defaultdict(recursive_dd)


def normal_dict(d: Any) -> dict:
    if isinstance(d, defaultdict):
        return {k: normal_dict(v) for k, v in d.items()}
    if isinstance(d, list):
        return [normal_dict(item) for item in d]
    return d


def to_str(node: ast.Node, as_value: bool = False) -> str:
    if isinstance(node, ast.SquareBracketsBlock):
        block = [to_str(v, as_value) for v in node.content]
        return block if as_value else str(block)
    if isinstance(node, list):
        return node
    return str(node.value)


tree = recursive_dd()
rules = strip_whitespace(parse_stylesheet(open(sys.argv[2]).read()))

for rule in rules:
    prev_target = target = tree
    path = strip_whitespace(rule.prelude)
    for i, ident in enumerate(path):
        name = to_str(ident)
        if name == "_root":
            break
        try:
            index = int(float(name.strip("[']")))
            if not isinstance(target, list):
                target = prev_target[to_str(path[i - 1])] = [recursive_dd()]
            if padding := index + 1 - len(target):
                target.extend([recursive_dd()] * padding)
            prev_target, target = target, target[index]
        except ValueError:
            prev_target, target = target, target[name]
    for line in split_semicolons(strip_whitespace(rule.content), literal_matcher(";")):
        if not line:
            continue
        key, colon, value = strip_whitespace(line)
        target[key.value] = to_str(value, True)

spec = yaml.dump(normal_dict(tree))
proc = subprocess.run(["kubectl", "apply", "-f", "-"], input=spec.encode())
