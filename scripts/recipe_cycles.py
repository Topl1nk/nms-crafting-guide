"""Run:  python scripts/recipe_cycles.py [refine|cook|all]   (needs numpy and scipy, which the project itself does not use).

Minimal self-feeding loops of the recipe book (refining only; cooking has no stable machine-time and is another matter).

A loop = a smallest set of recipes with runs x >= 0 such that, per item, produced - consumed >= 0 (no item is net-consumed:
nothing has to come from outside), and every recipe of the set is really used. Found for each recipe: force it in, minimise the
total runs, then drop every other recipe that is not needed (try x_j = 0 and see whether it is still feasible).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

d = json.loads((Path(__file__).resolve().parent.parent / "web" / "data.json").read_text(encoding="utf8"))
name = lambda i: d["items"].get(i, {}).get("name", i)
R = d["recipes"]
domain = sys.argv[1] if len(sys.argv) > 1 else "refine"
rec = [(i, {a: n for a, n in r["in"]}, r["out"][0], r["out"][1]) for i, r in enumerate(R) if domain == "all" or r["domain"] == domain]

alive = set(range(len(rec)))
while True:
    made = {rec[k][2] for k in alive}
    keep = {k for k in alive if all(a in made for a in rec[k][1])}
    if keep == alive:
        break
    alive = keep
alive = sorted(alive)
items = sorted({a for k in alive for a in rec[k][1]} | {rec[k][2] for k in alive})
pos = {it: n for n, it in enumerate(items)}
A = np.zeros((len(items), len(alive)))
for j, k in enumerate(alive):
    i, ins, o, q = rec[k]
    A[pos[o], j] += q
    for a, n in ins.items():
        A[pos[a], j] -= n


def feasible(force, banned=()):
    """x >= 0, x_force >= 1, net >= 0; minimise total runs. Returns x or None."""
    bounds = [(0, 1e6)] * len(alive)
    for j in banned:
        bounds[j] = (0, 0)
    bounds[force] = (1, 1e6)
    res = linprog(np.ones(len(alive)), A_ub=-A, b_ub=np.zeros(len(items)), bounds=bounds, method="highs")
    return res.x if res.status == 0 else None


found = {}
for j0 in range(len(alive)):
    x = feasible(j0)
    if x is None:
        continue
    support = {j for j in range(len(alive)) if x[j] > 1e-7}
    banned = set()
    for j in sorted(support - {j0}):
        y = feasible(j0, banned | {j})
        if y is not None:
            banned.add(j)
            x = y
    support = frozenset(j for j in range(len(alive)) if x[j] > 1e-7)
    found.setdefault(support, x)

print(f"{domain}: {len(alive)} closable recipes, {len(found)} distinct minimal loops")
out = []
for support, x in found.items():
    net = A @ x
    gain = {items[m]: net[m] for m in range(len(items)) if abs(net[m]) > 1e-7}
    out.append((len(support), support, x, gain))
out.sort(key=lambda t: (t[0], -sum(t[3].values()) if t[3] else 0))
for size, support, x, gain in out[:60]:
    print(f"--- {size} recipes; per run of the first: net " + (", ".join(f"+{v/x[min(support)]:.3g} {k}" for k, v in gain.items()) or "exactly zero (a pure swap)"))
    for j in sorted(support):
        i, ins, o, q = rec[alive[j]]
        print(f"   x{x[j]:.3g}  #{i}: " + " + ".join(f"{n} {name(a)}" for a, n in ins.items()) + f" -> {q} {name(o)}   [{R[i]['machine'].split(' ')[0]}, {R[i]['time']:.0f}s]")
