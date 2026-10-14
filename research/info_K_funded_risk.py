"""Exploratory (outside the plan): how the coin flip's value depends on funded risk, and how far a stop can slip.
Run from the repository root."""
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
tup = m.tuples()
L, R = tup.L[tup.has], tup.R[tup.has]
flat = L.ravel()
print("worst intraday mark of a trade, in stop units (both sides, %d trades):" % len(flat))
print("  min %.3f; share at or below -1.00: %.3f; below -1.05: %.4f; below -1.10: %.4f; below -1.25: %.4f; below -1.5: %.4f; "
      "below -2: %.5f" % (flat.min(), (flat <= -1 + 1e-9).mean(), (flat < -1.05).mean(), (flat < -1.10).mean(),
                          (flat < -1.25).mean(), (flat < -1.5).mean(), (flat < -2).mean()))
print("  realised result: min %.3f; share below -1.05: %.4f" % (R.min(), (R.ravel() < -1.05).mean()))
print("  the ten worst marks:", np.sort(flat)[:10].round(2).tolist())

RF = [0.005, 0.0066, 0.008, 0.009, 0.01]
for regime, r_eval in (("FTG", 0.03), ("FTG", 0.035), ("STD", 0.03)):
    grid = RF + ([0.015, 0.02, 0.025] if regime == "STD" else [])
    acc = {k: [] for k in ("V", "V12", "V24", "npay", "close", "passed")}
    for paths in m.draw(m.SEED_EVAL):
        res = m.price(m.days_of(tup, paths, 0.5), len(paths["U"]), [r_eval], [(regime, x) for x in grid], m.alpha("FTG"), m.alpha)
        for k in ("V", "V12", "V24", "npay", "close"):
            acc[k].append(res[k][0])
        acc["passed"].append(res["outcome"][0] == m.PASS)
    V, V12, V24, npay, close = (np.concatenate(acc[k], axis=1) for k in ("V", "V12", "V24", "npay", "close"))
    passed = np.concatenate(acc["passed"])
    rows = []
    for j, x in enumerate(grid):
        v = V[j].astype(float)
        rows.append({"funded risk %": x * 100, "V": v.mean(), "se": v.std(ddof=1) / np.sqrt(len(v)), "V at 12m": V12[j].mean(),
                     "V at 24m": V24[j].mean(), "P(any payout)": (npay[j] > 0).mean(),
                     "payouts per paid buyer": npay[j][npay[j] > 0].mean(),
                     "funded accounts lost to the floor": (close[j][passed] == m.BREACH_STATIC).mean(),
                     "funded accounts still open": (close[j][passed] == 0).mean()})
    print(f"\ncoin flip, {regime}, evaluation risk {r_eval:.1%} (P(pass) {passed.mean():.3f}):")
    print(pd.DataFrame(rows).round(3).to_string(index=False))
