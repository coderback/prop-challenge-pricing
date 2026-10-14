"""K8, the firm's plan menu, exactly as pre-registered in amendment 4 of
research/PREREGISTRATION_paper2_contract_map.md (commit ec0deb4).

    python research/run_K8.py run       price every plan (selection set, then evaluation set) and save the paths
    python research/run_K8.py report    hypotheses H14-H18 and the fee tables, from the saved paths

Book Z2 on US500, K1's conventions. Rules from the saved help-centre pages; list fees from the checkout
(research/FEES_alpha_2026-10-13.json). A contract valuation, not an edge test.
"""
import importlib.util
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

STAGE = sys.argv[1] if len(sys.argv) > 1 else ""
sys.argv = ["run_K.py", "none"]
_spec = importlib.util.spec_from_file_location("run_K", "research/run_K.py")
m = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(m)
except KeyError:
    pass

from propcontract.contract import IB, PASS, Contract, evaluate, fund          # noqa: E402

SPEC = "research/PREREGISTRATION_paper2_contract_map.md@ec0deb4 (amendment 4)"
OUT = Path("data/checks")
if os.environ.get("K_SMOKE"):
    m.N = m.BATCH = int(os.environ["K_SMOKE"])
N, BATCH, R_GRID = m.N, m.BATCH, m.R_GRID
ci, fmt_ci = m.ci, m.fmt_ci
LOT = m.ref / IB                                      # one US500 lot as leverage on a $10k account
SIZES = [5_000, 10_000, 25_000, 50_000, 100_000, 200_000]
FEES = json.loads(Path("research/FEES_alpha_2026-10-13.json").read_text(encoding="utf-8"))["plans"]


def fee_row(prefix: str, key: str = "on_demand"):
    return next(v[key] for k, v in FEES.items() if k.startswith(prefix))


# plan -> published terms per $10k: evaluation targets, limits, lots, index leverage, payout rules, list fees
PLANS = {
    "Swing": dict(t=(0.10, 0.05), static=0.10, daily=0.05, lots=2.5, lev=(10, 5), fees=fee_row("Swing")),
    "Pro 10%": dict(t=(0.10, 0.05), static=0.10, daily=0.05, lots=5, lev=(20, 10), fees=fee_row("Alpha Pro 10%")),
    "Pro 10% bi-weekly": dict(t=(0.10, 0.05), static=0.10, daily=0.05, lots=5, lev=(20, 10),
                              fees=fee_row("Alpha Pro 10%", "bi_weekly"),
                              pay=dict(payout_every=10, min_profit=0.01, best_day=None)),
    "Pro 8%": dict(t=(0.08, 0.05), static=0.08, daily=0.04, lots=5, lev=(20, 10), fees=fee_row("Alpha Pro 8%")),
    "Pro 6%": dict(t=(0.06, 0.06), static=0.06, daily=0.03, lots=5, lev=(20, 10), fees=fee_row("Alpha Pro 6%")),
    "One 6%": dict(t=(0.06, None), trail=0.04, daily=0.03, daily_funded=0.04, lots=5, lev=(10, 10), min_days=1,
                   fees=fee_row("Alpha One 6%")),
    "One 10%": dict(t=(0.10, None), trail=0.06, daily=0.04, lots=5, lev=(10, 10), min_days=1, fees=fee_row("Alpha One 10%")),
    "One 12%": dict(t=(0.12, None), trail=0.08, daily=0.05, lots=5, lev=(10, 10), min_days=1, fees=fee_row("Alpha One 12%")),
    "Direct": dict(t=None, trail=0.05, daily=0.03, lots=5, lev=(10, 10), fees=fee_row("Alpha Direct"),
                   pay=dict(buffer=0.03, min_profit=0.01, best_day=0.15, split=0.90, max_risk=0.01)),
}
RF = {"FTG": [0.005, 0.01], "STD": [0.005, 0.01, 0.015, 0.02, 0.025], "Direct": [0.0025, 0.005, 0.0075, 0.009]}
KEEP = [0.0, 0.02, 0.04]                              # profit left in at each payout on the One plans
EVAL = ("Swing", "Pro 10%", "Pro 8%", "Pro 6%", "One 6%", "One 10%", "One 12%")   # plans with an evaluation, for H16


def contracts(plan: str, regime: str, max_risk: float = 0.03, keep: float = 0.0):
    """The evaluation and funded contracts of a plan in a regime ("FTG" or "STD")."""
    p = PLANS[plan]
    lev_std, lev_ftg = p["lev"]
    limit = dict(static_dd=p["static"]) if "static" in p else dict(static_dd=p["trail"], trail_dd=p["trail"])
    lots, lev, cap = (p["lots"] / 2, lev_ftg, 0.01) if regime == "FTG" else (p["lots"], lev_std, None)
    funded = dict(lev_funded=min(lots * LOT, lev), risk_cap=cap, max_risk=max_risk, buffer=keep,
                  daily_dd=p.get("daily_funded", p["daily"]), **limit) | p.get("pay", {})
    if p["t"] is None:
        return None, Contract(**funded)
    c_eval = Contract(target_p1=p["t"][0], target_p2=p["t"][1], daily_dd=p["daily"], lev_eval=float(lev_std),
                      min_days=p.get("min_days", 3), **limit)
    return c_eval, replace(c_eval, **funded)


def variants(plan: str, regime: str):
    """Funded policies of a plan: (label, funded risk, profit left in)."""
    keeps = KEEP if plan.startswith("One") else [0.0]
    rfs = RF["Direct"] if plan == "Direct" else RF[regime]
    return [(f"{regime}|{rf}|{k}", rf, k) for k in keeps for rf in rfs]


def price_plan(days, n, plan: str, regime: str, max_risk: float = 0.03, cache: dict | None = None) -> dict:
    """V[r, variant, path] and the evaluation outcome [r, path] of a plan on one batch of paths. The evaluation
    does not depend on the regime, so ``cache`` carries it from one regime of a plan to the next."""
    var = variants(plan, regime)
    c_eval, _ = contracts(plan, regime, max_risk)
    if c_eval is None:                                 # Direct: funded from the day of purchase
        V = np.zeros((1, len(var), n), np.float32)
        npay = np.zeros((1, len(var), n), np.int16)
        for k, (_, rf, keep) in enumerate(var):
            fd = fund(days, np.arange(n), np.zeros(n, np.int32), np.full(n, rf), contracts(plan, regime, max_risk, keep)[1],
                      marks=(252, 504))
            V[0, k], npay[0, k] = fd["payouts"], fd["n_pay"]
        return {"V": V, "npay": npay, "passed": np.ones((1, n), bool)}
    nr = len(R_GRID)
    cache = {} if cache is None else cache
    if plan not in cache:
        cache[plan] = evaluate(days, np.tile(np.arange(n), nr), np.repeat(np.asarray(R_GRID, float), n), c_eval)
    ev = cache[plan]
    V = np.zeros((nr, len(var), n), np.float32)
    npay = np.zeros((nr, len(var), n), np.int16)
    won = np.flatnonzero(ev["outcome"] == PASS)
    if won.size:
        ri, pi = won // n, won % n
        for keep in sorted({k for _, _, k in var}):
            ks = [i for i, (_, _, kk) in enumerate(var) if kk == keep]
            c = contracts(plan, regime, max_risk, keep)[1]
            fd = fund(days, np.tile(pi, len(ks)), np.tile(ev["pass_t"][won] + c.fund_gap, len(ks)),
                      np.repeat([var[i][1] for i in ks], won.size), c, marks=(252, 504))
            for j, i in enumerate(ks):
                sl = slice(j * won.size, (j + 1) * won.size)
                V[ri, i, pi], npay[ri, i, pi] = fd["payouts"][sl], fd["n_pay"][sl]
    return {"V": V, "npay": npay, "passed": (ev["outcome"] == PASS).reshape(nr, n)}


CELLS = [(plan, regime, 0.03) for plan in PLANS for regime in (("STD",) if plan == "Direct" else ("FTG", "STD"))] + \
        [(plan, "STD", 0.02) for plan in PLANS if plan != "Direct"]      # the standard regime under the 2% rule from $50k


def run():
    tup = m.tuples()
    sk = m.skill_table(tup)
    ps = {"coin": 0.5, "0.3": float(sk.p[m.SKILL.index(0.3)])}
    print(f"spec {SPEC}\none US500 lot = {LOT:.3f}x leverage on $10k; {len(CELLS)} plan-regime cells; N = {N}")
    sel, keepV, meta = {}, {}, {}
    t0 = time.time()
    for name, seed in (("selection", m.SEED_SEL), ("evaluation", m.SEED_EVAL)):
        for b, paths in enumerate(m.draw(seed, n=N)):
            n = len(paths["U"])
            sl = slice(b * BATCH, b * BATCH + n)
            for s, p in ps.items():
                days = m.days_of(tup, paths, p)
                cache = {}
                for plan, regime, mr in CELLS:
                    if s == "0.3" and mr == 0.02:
                        continue
                    key = (plan, regime, mr, s)
                    res = price_plan(days, n, plan, regime, mr, cache)
                    if name == "selection":
                        sel[key] = sel.get(key, 0.0) + res["V"].sum(axis=2) / N
                    else:
                        ri, k = np.unravel_index(np.argmax(sel[key]), sel[key].shape)
                        d = keepV.setdefault(key, {"V": np.zeros(N, np.float32), "passed": np.zeros(N, bool),
                                                   "paid": np.zeros(N, bool)})
                        d["V"][sl], d["passed"][sl], d["paid"][sl] = res["V"][ri, k], res["passed"][ri], res["npay"][ri, k] > 0
                        meta[key] = (int(ri), int(k))
            print(f"  {name} batch {b + 1}/{N // BATCH} done ({time.time() - t0:.0f}s)", flush=True)
    rows, save = [], {}
    for (plan, regime, mr, s), d in keepV.items():
        ri, k = meta[(plan, regime, mr, s)]
        _, rf, keep = variants(plan, regime)[k]
        keep = PLANS[plan].get("pay", {}).get("buffer", keep)          # Direct's buffer is a rule, not a choice
        mean, se, lo, hi = ci(d["V"])
        rows.append({"plan": plan, "regime": regime, "max_risk": mr, "skill": s,
                     "r_pct": np.nan if plan == "Direct" else R_GRID[ri] * 100, "rf_pct": rf * 100, "keep_pct": keep * 100,
                     "p_pass": d["passed"].mean(), "p_payout": d["paid"].mean(), "V": mean, "V_se": se, "V_lo": lo, "V_hi": hi,
                     "V_sel": float(sel[(plan, regime, mr, s)][ri, k])})
        save[f"{plan}|{regime}|{mr}|{s}"] = d["V"]
    t = pd.DataFrame(rows)
    tag = ""
    t.to_csv(OUT / f"K8_plans{tag}.csv", index=False)
    np.savez_compressed(OUT / f"K8_paths{tag}.npz", **save)
    print(t.round(3).to_string(index=False))


def report():
    t = pd.read_csv(OUT / "K8_plans.csv", dtype={"skill": str})
    z = np.load(OUT / "K8_paths.npz")
    V = lambda plan, regime="FTG", s="coin", mr=0.03: z[f"{plan}|{regime}|{mr}|{s}"].astype(float)   # noqa: E731
    fee10 = {p: PLANS[p]["fees"][1] for p in PLANS}
    print(f"spec {SPEC}")
    k1 = pd.read_csv(OUT / "K1_map.csv", dtype={"skill": str})
    for regime in ("FTG", "STD"):
        for s in ("coin", "0.3"):
            mine = t[(t.plan == "Swing") & (t.regime == regime) & (t.skill == s) & (t.max_risk == 0.03)].V.iloc[0]
            ref = k1[k1.selected & (k1.regime == regime) & (k1.skill == s)].V.iloc[0]
            print(f"gate: Swing {regime} skill {s}: K8 {mine:.2f}, K1 {ref:.2f} -> {'PASS' if abs(mine - ref) < 0.01 else 'FAIL'}")
    for regime in ("FTG", "STD"):
        d = t[(t.max_risk == 0.03) & ((t.regime == regime) | (t.plan == "Direct"))]
        w = d.pivot_table(index="plan", columns="skill", values=["V", "p_pass", "p_payout", "r_pct", "rf_pct", "keep_pct"],
                          sort=False).reindex(list(PLANS))
        tab = pd.DataFrame({"fee_10k": pd.Series(fee10), "r %": w[("r_pct", "coin")], "r_f %": w[("rf_pct", "coin")],
                            "left in %": w[("keep_pct", "coin")], "P(pass)": w[("p_pass", "coin")],
                            "P(paid)": w[("p_payout", "coin")], "V coin": w[("V", "coin")], "V S=0.3": w[("V", "0.3")]})
        tab["EV coin"] = tab["V coin"] - tab["fee_10k"]
        tab["V coin per $ of fee"] = tab["V coin"] / tab["fee_10k"]
        tab["EV S=0.3"] = tab["V S=0.3"] - tab["fee_10k"]
        print(f"\n=== K8: the plan menu at $10k, {regime} regime (Direct has one regime) ===")
        print(tab.round(3).to_string())

    def verdict(lo, hi, positive=True):
        if positive:
            return "SUPPORTED" if lo > 0 else "REFUTED" if hi < 0 else "INCONCLUSIVE"
        return "SUPPORTED" if hi < 0 else "REFUTED" if lo > 0 else "INCONCLUSIVE"

    print("\n=== Hypotheses (coin flip, FTG, $10k; 95% intervals, differences paired by path) ===")
    d = V("Pro 10%") - V("Swing")
    print(f"  H14 V(Pro 10%) - V(Swing) > 0: {fmt_ci(d)}  {verdict(*ci(d)[2:])}")
    x = V("Pro 10%") - fee10["Pro 10%"]
    print(f"  H15 V(Pro 10%) > ${fee10['Pro 10%']}: EV {fmt_ci(x)}  {verdict(*ci(x)[2:])}")
    ratio = {p: tuple(v / fee10[p] for v in (ci(V(p))[0], ci(V(p))[2], ci(V(p))[3])) for p in EVAL}
    sw = ratio["Swing"]
    below = [p for p in EVAL if p != "Swing" and ratio[p][2] < sw[1]]        # wholly below Swing
    above = [p for p in EVAL if p != "Swing" and ratio[p][1] > sw[2]]        # wholly above Swing
    h16 = "REFUTED" if below else "SUPPORTED" if len(above) == len(EVAL) - 1 else "INCONCLUSIVE"
    print("  H16 Swing has the lowest V per dollar of fee: " +
          "; ".join(f"{p} {r[0]:.2f} [{r[1]:.2f}, {r[2]:.2f}]" for p, r in ratio.items()) + f"  {h16}")
    d = V("One 10%") - V("Pro 10%")
    print(f"  H17 V(One 10%) - V(Pro 10%) < 0: {fmt_ci(d)}  {verdict(*ci(d)[2:], positive=False)}")
    x = V("Direct", "STD") - fee10["Direct"]
    print(f"  H18 V(Direct) < ${fee10['Direct']}: EV {fmt_ci(x)}  {verdict(*ci(x)[2:], positive=False)}")

    print("\n=== Coin-flip EV at list by account size (USD; rules scale with the account) ===")
    for regime, label in (("FTG", "FTG"), ("STD", "STD; the 2% Max Risk Rule applies from $50k")):
        out = {}
        for p in PLANS:
            if p == "Pro 10% bi-weekly":
                continue                               # its $100 minimum does not scale
            g = "STD" if p == "Direct" else regime
            v3 = t[(t.plan == p) & (t.regime == g) & (t.skill == "coin") & (t.max_risk == 0.03)].V.iloc[0]
            v2 = v3 if (p == "Direct" or regime == "FTG") else \
                t[(t.plan == p) & (t.regime == "STD") & (t.skill == "coin") & (t.max_risk == 0.02)].V.iloc[0]
            out[p] = [None if f is None else round((v2 if a >= 50_000 else v3) * a / IB - f) for a, f in zip(SIZES, PLANS[p]["fees"])]
        print(f"  {label}:")
        print(pd.DataFrame(out, index=[f"${a:,}" for a in SIZES]).T.to_string())
    print("\n=== Fee as % of the account, against the coin flip's V as % of the account (FTG) ===")
    out = {p: [None if f is None else round(f / a * 100, 2) for a, f in zip(SIZES, PLANS[p]["fees"])] +
              [round(t[(t.plan == p) & (t.regime == ("STD" if p == "Direct" else "FTG")) & (t.skill == "coin") &
                       (t.max_risk == 0.03)].V.iloc[0] / IB * 100, 2)] for p in PLANS}
    print(pd.DataFrame(out, index=[f"fee ${a:,}" for a in SIZES] + ["V (any size)"]).T.to_string())


if __name__ == "__main__":
    {"run": run, "report": report}[STAGE]()
