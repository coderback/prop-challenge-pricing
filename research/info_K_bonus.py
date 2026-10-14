"""Amendment 1, V2 follow-up: the help centre lists a discretionary bonus of 0.25% of the initial balance on the fourth
performance-fee payment, which the rule record of 2026-10-13 omitted. This prices it at each selected policy on the
evaluation paths: bonus value = 0.0025 x account x P(at least four payouts). It is reported beside V, not folded in,
because the bonus is discretionary. Run from the repository root:
    python research/info_K_bonus.py
"""
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

ACCOUNT, BONUS = 10_000.0, 0.0025
tup = m.tuples()
sk = m.skill_table(tup)
k1 = pd.read_csv("data/checks/K1_map.csv")
sel = k1[k1.selected].assign(skill=lambda d: d.skill.astype(str))
rows = []
for si, s in enumerate(m.SKILL):
    for regime in ("FTG", "STD"):
        pol = sel[(sel.skill == str(s)) & (sel.regime == regime)].iloc[0]
        r, rf = pol.r_pct / 100, pol.rf_pct / 100
        npay, V = [], []
        for paths in m.draw(m.SEED_EVAL):
            res = m.price(m.days_of(tup, paths, sk.p[si]), len(paths["U"]), [r], [(regime, rf)], m.alpha("FTG"), m.alpha)
            npay.append(res["npay"][0, 0])
            V.append(res["V"][0, 0])
        npay, V = np.concatenate(npay), np.concatenate(V).astype(float)
        p4 = float((npay >= 4).mean())
        rows.append({"skill": s, "regime": regime, "r %": pol.r_pct, "r_f %": pol.rf_pct, "V": V.mean(), "V in K1": pol.V,
                     "P(any payout)": float((npay > 0).mean()), "P(4+ payouts)": p4, "bonus value $": ACCOUNT * BONUS * p4,
                     "bonus as % of V": 100 * ACCOUNT * BONUS * p4 / V.mean()})
        print(f"{s} {regime} done", flush=True)
out = pd.DataFrame(rows)
out.to_csv("data/checks/K_bonus.csv", index=False)
pd.set_option("display.width", 220)
print(out.round(3).to_string(index=False))
