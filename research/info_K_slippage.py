"""Exploratory (outside the plan): the simulated stop always fills at the stop price. What if every stop-out
slips by a fraction s of the stop distance? Coin flip only. Run from the repository root."""
import importlib.util
import sys

import numpy as np
import pandas as pd

sys.argv = ["run_K.py", "none"]
spec = importlib.util.spec_from_file_location("run_K", "research/run_K.py")
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except KeyError:
    pass
pd.set_option("display.width", 220)
base = m.tuples()
R_LIST = [0.03, 0.035, 0.04, 0.045]
FUNDS = [("FTG", 0.009), ("FTG", 0.01), ("STD", 0.02), ("STD", 0.025)]
rows = []
for s in (0.0, 0.05, 0.10, 0.25):
    stopped = base.L <= -1 + 1e-9
    tup = m.DayTuples(base.days, base.has, np.where(stopped, -(1 + s), base.R), np.where(stopped, -(1 + s), base.L), base.v)
    V = {k: [] for k in range(len(FUNDS))}
    passed, daily = [], []
    for paths in m.draw(m.SEED_EVAL):
        res = m.price(m.days_of(tup, paths, 0.5), len(paths["U"]), R_LIST, FUNDS, m.alpha("FTG"), m.alpha)
        for k in V:
            V[k].append(res["V"][:, k])
        passed.append(res["outcome"] == m.PASS)
        daily.append(res["outcome"] == m.BREACH_DAILY)
    passed, daily = np.concatenate(passed, axis=1), np.concatenate(daily, axis=1)
    for i, r in enumerate(R_LIST):
        row = {"slip (share of stop)": s, "eval risk %": r * 100, "P(pass)": passed[i].mean(), "daily-limit breaches": daily[i].mean()}
        for k, (g, rf) in enumerate(FUNDS):
            row[f"V {g} {rf:.1%}"] = np.concatenate(V[k], axis=1)[i].mean()
        rows.append(row)
    print(f"slippage {s:.0%} done; mean coin-flip result {tup.R[tup.has].mean():+.4f}R", flush=True)
print(pd.DataFrame(rows).round(3).to_string(index=False))
