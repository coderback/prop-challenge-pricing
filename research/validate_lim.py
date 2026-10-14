"""Amendment 1, V1: an independent re-implementation of Lim (2026), SSRN 7178078, from Sections 4-5 of the paper.

It does not import the project's contract simulator. Conventions and tolerances are fixed in
research/PREREGISTRATION_paper2_contract_map.md (amendment 1). Run from the repository root:
    python research/validate_lim.py
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("data/checks")
N, SEED = 200_000, 20261017
A1, A2, B, D = 0.10, 0.05, 0.10, 0.05          # step targets, overall loss, daily loss (shares of the initial balance)
T1, T2, CAP = 30, 60, 300                      # classic maturities; cap of the no-time-limit variant
SPLIT, EVERY, HORIZON, FEE, ACCOUNT = 0.80, 20, 250, 500.0, 100_000.0
SHARPES = [-5.0, -4.0, -3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0, 4.0]
VOLS = [0.005, 0.01, 0.02, 0.03, 0.05]
TAB_S = [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0]

# Lim's published numbers ("<0.001" entered as 0.0005)
LIM3 = np.array([[0.0005, 0.001, 0.022, 0.046, 0.070], [0.0005, 0.002, 0.049, 0.078, 0.096],
                 [0.0005, 0.008, 0.100, 0.128, 0.130], [0.0005, 0.015, 0.137, 0.160, 0.149],
                 [0.0005, 0.026, 0.184, 0.195, 0.172], [0.0005, 0.041, 0.237, 0.234, 0.195],
                 [0.0005, 0.066, 0.298, 0.278, 0.220], [0.001, 0.135, 0.434, 0.375, 0.275],
                 [0.004, 0.241, 0.576, 0.471, 0.334]])
LIM4 = np.array([[0, 0, 24, 33, 9], [0, 3, 102, 100, 24], [0, 27, 404, 280, 58], [0, 72, 783, 457, 85],
                 [0, 183, 1502, 728, 127], [1, 432, 2790, 1143, 184], [2, 979, 5058, 1730, 263],
                 [13, 3746, 15826, 3865, 534], [68, 11324, 44874, 7955, 1005]], dtype=float)
LIM2 = {("daily only", 0.0): 0.453, ("daily only", 2.0): 0.744, ("maturity only", 0.0): 0.310,
        ("maturity only", 2.0): 0.550, ("both", 0.0): 0.298, ("both", 2.0): 0.532}
LIM_T = {0.0: 0.273, 2.0: 0.503}
LIM5 = {"value, refundable classic": 221.0, "value, non-refundable classic": 203.0,
        "value, no time limit (non-refundable)": 369.0, "value, no cost drag (classic)": 1098.0,
        "P(funded), classic": 0.075, "P(funded), no time limit": 0.105, "P(funded), no cost drag": 0.153,
        "break-even net Sharpe at 2%": -0.87, "break-even net Sharpe at 5%": 1.94, "break-even net Sharpe at 1%": 0.56}
LIM6 = {("conservative", 0.05): 441, ("conservative", 0.10): 163, ("conservative", 0.15): 60,
        ("base", 0.05): 557, ("base", 0.10): 221, ("base", 0.15): 87,
        ("aggressive", 0.05): 517, ("aggressive", 0.10): 213, ("aggressive", 0.15): 87}
WEIGHTS = {"conservative": [0.20, 0.40, 0.25, 0.10, 0.05], "base": [0.05, 0.20, 0.30, 0.25, 0.20],
           "aggressive": [0.0, 0.10, 0.25, 0.30, 0.35]}


def step(rng, s, vol, target, T, daily=True, t_df=None) -> float:
    """Probability of reaching +target before -B, the daily rule or the maturity. Daily closes only."""
    mu = s * vol / np.sqrt(252)
    x, alive, passed = np.zeros(N), np.ones(N, bool), np.zeros(N, bool)
    for _ in range(T):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        z = rng.standard_normal(idx.size) if t_df is None else rng.standard_t(t_df, idx.size) / np.sqrt(t_df / (t_df - 2))
        r = mu + vol * z
        out_daily = (r <= -D) if daily else np.zeros(idx.size, bool)      # the daily rule is checked first
        xn = x[idx] + r
        win = ~out_daily & (xn >= target)
        lose = out_daily | (~win & (xn <= -B))
        x[idx] = xn
        passed[idx[win]] = True
        alive[idx[win | lose]] = False
    return float(passed.mean())


def funded(rng, s, vol) -> dict:
    """Funded stage: sweeps of 80% of positive profit every 20 days, 250 days. Also the day-250 sweep variant."""
    mu = s * vol / np.sqrt(252)
    x, alive, paid, any_pay = np.zeros(N), np.ones(N, bool), np.zeros(N), np.zeros(N, bool)
    for t in range(1, HORIZON + 1):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        r = mu + vol * rng.standard_normal(idx.size)
        xn = x[idx] + r
        dead = (r <= -D) | (xn <= -B)
        if t % EVERY == 0:
            sweep = ~dead & (xn > 0)
            paid[idx[sweep]] += SPLIT * xn[sweep]
            any_pay[idx[sweep]] = True
            xn = np.where(sweep, 0.0, xn)
        x[idx] = xn
        alive[idx[dead]] = False
    last = alive & (x > 0) if HORIZON % EVERY else np.zeros(N, bool)     # residual profit on day 250, not swept
    paid_alt, any_alt = paid + np.where(last, SPLIT * x, 0.0), any_pay | last
    return {"E": float(paid.mean() * ACCOUNT), "q": float(any_pay.mean()),
            "E_alt": float(paid_alt.mean() * ACCOUNT), "q_alt": float(any_alt.mean())}


def cells() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows, t0 = [], time.time()
    for s in SHARPES:
        for vol in VOLS:
            f = funded(rng, s, vol)
            rows.append({"S": s, "vol": vol, "p1": step(rng, s, vol, A1, T1), "p2": step(rng, s, vol, A2, T2),
                         "p1u": step(rng, s, vol, A1, CAP), "p2u": step(rng, s, vol, A2, CAP), **f})
        print(f"net Sharpe {s:+.1f} done ({time.time() - t0:.0f}s)", flush=True)
    c = pd.DataFrame(rows)
    c["P"], c["Pu"] = c.p1 * c.p2, c.p1u * c.p2u
    for tag in ("", "_alt"):
        c["fair" + tag] = c.P * c["E" + tag] / (1 - c.P * c["q" + tag])
        c["v_nonref" + tag] = c.P * c["E" + tag]
        c["v_ref" + tag] = c.P * (c["E" + tag] + c["q" + tag] * FEE)
        c["v_nonref_u" + tag] = c.Pu * c["E" + tag]
    return c


def grid(c: pd.DataFrame, col: str) -> np.ndarray:
    return c.pivot(index="S", columns="vol", values=col).loc[SHARPES, VOLS].to_numpy()


def population(c: pd.DataFrame, col: str, weights, k: float, g: np.ndarray) -> float:
    net = g - k * np.sqrt(252)
    m = grid(c, col)
    return float(sum(w * np.interp(net, SHARPES, m[:, j]).mean() for j, w in enumerate(weights)))


def break_even(c: pd.DataFrame, vol: float, tag: str = "") -> float:
    ev = grid(c, "v_ref" + tag)[:, VOLS.index(vol)] - FEE
    for i in range(len(SHARPES) - 1):
        if ev[i] < 0 <= ev[i + 1]:
            return SHARPES[i] + (SHARPES[i + 1] - SHARPES[i]) * (-ev[i]) / (ev[i + 1] - ev[i])
    return float("nan")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = cells()
    c.to_csv(OUT / "V1_lim_cells.csv", index=False)
    rng = np.random.default_rng(SEED + 1)
    g = rng.standard_normal(2_000_000)
    sel = [SHARPES.index(s) for s in TAB_S]
    res = {}

    # a. Tables 2 and 3
    t2 = {}
    for s in (0.0, 2.0):
        t2[("daily only", s)] = step(rng, s, 0.02, A1, CAP)
        t2[("maturity only", s)] = step(rng, s, 0.02, A1, T1, daily=False)
        t2[("both", s)] = step(rng, s, 0.02, A1, T1)
    d2 = {f"{k[0]}, S={k[1]:g}": (v, LIM2[k], abs(v - LIM2[k])) for k, v in t2.items()}
    P = grid(c, "P")[sel]
    d3 = np.abs(P - LIM3)
    res["a"] = {"table 2": {k: [round(x, 4) for x in v] for k, v in d2.items()}, "table 2 worst": max(v[2] for v in d2.values()),
                "table 3 worst": float(d3.max()), "table 3 cells within 0.01": int((d3 <= 0.01).sum()), "of": int(d3.size),
                "ok": bool(d3.max() <= 0.01 and max(v[2] for v in d2.values()) <= 0.01)}

    out = {}
    for tag, name in (("", "primary (no sweep on day 250)"), ("_alt", "alternative (final sweep on day 250)")):
        r = {}
        z = c[(c.S == 0.0) & (c.vol == 0.02)].iloc[0]
        r["b"] = {"E": float(z["E" + tag]), "q": float(z["q" + tag]), "fair": float(z["fair" + tag]),
                  "ok": bool(abs(z["E" + tag] / 7300 - 1) <= 0.05 and abs(z["q" + tag] - 0.56) <= 0.02
                             and abs(z["fair" + tag] / 1502 - 1) <= 0.05)}
        F = grid(c, "fair" + tag)[sel]
        tol = np.maximum(0.05 * LIM4, 5.0)
        hit = np.abs(F - LIM4) <= tol
        big = LIM4 >= 100
        r["c"] = {"cells within tolerance": int(hit.sum()), "of": int(hit.size),
                  "worst relative difference where Lim >= $100": float((np.abs(F - LIM4) / np.where(big, LIM4, np.inf)).max()),
                  "median relative difference where Lim >= $100": float(np.median((F / LIM4 - 1)[big])),
                  "misses": [f"S={TAB_S[i]:+g}, vol={VOLS[j]:.1%}: {F[i, j]:.0f} against {LIM4[i, j]:.0f}"
                             for i, j in zip(*np.where(~hit))], "ok": bool(hit.sum() >= 41)}
        w = WEIGHTS["base"]
        t5 = {"value, refundable classic": population(c, "v_ref" + tag, w, 0.10, g),
              "value, non-refundable classic": population(c, "v_nonref" + tag, w, 0.10, g),
              "value, no time limit (non-refundable)": population(c, "v_nonref_u" + tag, w, 0.10, g),
              "value, no cost drag (classic)": population(c, "v_ref" + tag, w, 0.0, g),
              "P(funded), classic": population(c, "P", w, 0.10, g), "P(funded), no time limit": population(c, "Pu", w, 0.10, g),
              "P(funded), no cost drag": population(c, "P", w, 0.0, g),
              "break-even net Sharpe at 2%": break_even(c, 0.02, tag), "break-even net Sharpe at 5%": break_even(c, 0.05, tag),
              "break-even net Sharpe at 1%": break_even(c, 0.01, tag)}
        ok5 = {}
        for k, v in t5.items():
            want = LIM5[k]
            ok5[k] = bool(abs(v / want - 1) <= 0.10 if k.startswith("value") else
                          abs(v - want) <= 0.007 if k.startswith("P(") else abs(v - want) <= 0.15)
        r["d"] = {"got": {k: round(v, 4) for k, v in t5.items()}, "lim": LIM5, "within": ok5, "ok": bool(all(ok5.values()))}
        t6 = {f"{nm}, k={k}": (population(c, "v_ref" + tag, WEIGHTS[nm], k, g), want) for (nm, k), want in LIM6.items()}
        hit6 = {k: bool(abs(v - want) <= max(0.10 * want, 10.0)) for k, (v, want) in t6.items()}
        r["e"] = {"got": {k: round(v[0], 1) for k, v in t6.items()}, "lim": {k: v[1] for k, v in t6.items()}, "within": hit6,
                  "ok": bool(sum(hit6.values()) >= 8)}
        out[name] = r
    res["by convention"] = out
    tt = {s: step(rng, s, 0.02, A1, T1, t_df=4) for s in (0.0, 2.0)}
    res["f"] = {"got": {f"S={s:g}": round(v, 4) for s, v in tt.items()}, "lim": {f"S={s:g}": v for s, v in LIM_T.items()},
                "ok": bool(all(abs(tt[s] - LIM_T[s]) <= 0.01 for s in tt))}
    for name, r in out.items():
        r["verdict"] = "REPRODUCED" if all([res["a"]["ok"], r["b"]["ok"], res["f"]["ok"], r["c"]["ok"], r["d"]["ok"],
                                           r["e"]["ok"]]) else "PARTLY REPRODUCED"
    (OUT / "V1_lim_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

    pd.set_option("display.width", 220)
    print("\nTable 3, P(funded): ours")
    print(pd.DataFrame(P, index=TAB_S, columns=[f"{v:.1%}" for v in VOLS]).round(3).to_string())
    for tag, name in (("", "primary"), ("_alt", "alternative")):
        print(f"\nTable 4, fair fee: ours, {name}")
        print(pd.DataFrame(grid(c, "fair" + tag)[sel], index=TAB_S, columns=[f"{v:.1%}" for v in VOLS]).round(0).to_string())
    print("\nTable 4: Lim")
    print(pd.DataFrame(LIM4, index=TAB_S, columns=[f"{v:.1%}" for v in VOLS]).to_string())
    print("\n" + json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
