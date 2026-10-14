"""K7, the buyer's best policy, exactly as pre-registered in amendment 3 of
research/PREREGISTRATION_paper2_contract_map.md (commit bb03b76).

    python research/run_K7.py gates     G5 and G6 (G4 is tests/test_rK_optimal.py)
    python research/run_K7.py solve     solve classes B, C, D and simulate them on K1's evaluation paths
    python research/run_K7.py report    hypotheses H10-H13 and the policy description, from the saved paths

Policy classes: A = K1's selected fixed policy; B = A's sizes with free payout timing; C = free sizing with the
earliest payout; D = both free. A contract valuation, not an edge test.
"""
import importlib.util
import os
import sys
import time
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

from propcontract.contract import IB, PASS, BookDays, evaluate, fund          # noqa: E402
from propcontract.optimal import Atoms, Grid, solve                           # noqa: E402

SPEC = "research/PREREGISTRATION_paper2_contract_map.md@bb03b76 (amendment 3)"
OUT = Path("data/checks")
POL = Path("data/r2cache/K7_policies")
N, BATCH = m.N, m.BATCH
EVAL_ACTIONS = [round(0.0025 * k, 4) for k in range(1, 21)] + [0.06, 0.08]
FUND_ACTIONS = {"FTG": [0.0025, 0.005, 0.0075, 0.01], "STD": [0.005, 0.01, 0.015, 0.02, 0.025]}
SKILLS = ["coin", 0.3, 1.0]
REGIMES = ["FTG", "STD"]
ci, fmt_ci = m.ci, m.fmt_ci


def k1_policy():
    sel, keep, start = m.load_k1()
    pol = m.select(sel)
    return {(s, g): (m.R_GRID[pol[(m.SKILL.index(s), g)][0]], m.FUND[pol[(m.SKILL.index(s), g)][1]][1],
                     keep["V"][m.SKILL.index(s)][pol[(m.SKILL.index(s), g)]].astype(float)) for s in SKILLS for g in REGIMES}


def actions(cls: str, regime: str, r: float, rf: float):
    """(evaluation sizes, funded sizes, free payout timing) of a policy class."""
    return {"A": ([r], [rf], False), "B": ([r], [rf], True), "C": (EVAL_ACTIONS, FUND_ACTIONS[regime], False),
            "D": (EVAL_ACTIONS, FUND_ACTIONS[regime], True)}[cls]


def simulate(tup, p, pol, c, paths_iter) -> dict:
    """A policy on a set of paths: payouts per purchase and what was done along the way."""
    out = {k: [] for k in ("V", "passed", "npay", "eval_risk", "lo", "hi", "peak")}
    for paths in paths_iter:
        n = len(paths["U"])
        days = m.days_of(tup, paths, p)
        ev = evaluate(days, np.arange(n), pol.eval_risk, c)
        won = np.flatnonzero(ev["outcome"] == PASS)
        V, npay, peak = np.zeros(n), np.zeros(n, np.int32), np.zeros(n)
        lo, hi = ev["risk_min"].copy(), ev["risk_max"].copy()
        if won.size:
            fd = fund(days, won, ev["pass_t"][won] + c.fund_gap, pol.fund_risk, c, marks=(252, 504), request=pol.request)
            V[won], npay[won], peak[won] = fd["payouts"], fd["n_pay"], fd["peak"]
            traded = fd["risk_max"] > 0
            lo[won] = np.where(traded, np.minimum(lo[won], fd["risk_min"]), lo[won])
            hi[won] = np.maximum(hi[won], fd["risk_max"])
        for k, x in (("V", V), ("passed", ev["outcome"] == PASS), ("npay", npay), ("eval_risk", ev["risk_mean"]),
                     ("lo", lo), ("hi", hi), ("peak", peak)):
            out[k].append(x)
    return {k: np.concatenate(v) for k, v in out.items()}


def iid_paths(n, window, seed):
    """Independent draws of business days, the solver's own model of a path."""
    rng = np.random.default_rng(seed)
    for b0 in range(0, n, BATCH):
        k = min(BATCH, n - b0)
        yield {"gidx": rng.integers(m.FIRST, len(m.DAYS), size=(k, window)).astype(np.int32),
               "U": rng.random((k, window), dtype=np.float32)}


def gates():
    tup = m.tuples()
    sk = m.skill_table(tup)
    k1 = k1_policy()
    c = m.alpha("FTG")
    atoms = Atoms.from_book(tup, m.FIRST, 0.5)
    r, rf, _ = k1[("coin", "FTG")]
    ok = True
    print(f"spec {SPEC}\n{len(atoms.w)} outcomes of a day; coin flip, FTG, K1 policy r={r:.1%}, r_f={rf:.1%}")
    t0 = time.time()
    polA = solve(atoms, c, *actions("A", "FTG", r, rf)[:2], free_timing=False)
    simA = simulate(tup, 0.5, polA, c, iid_paths(200_000, c.window, 20261018))["V"]
    mean, se = simA.mean(), simA.std(ddof=1) / np.sqrt(len(simA))
    g5 = abs(mean - polA.value) < 3 * se + 0.02 * polA.value
    ok &= g5
    print(f"G5: solver {polA.value:.2f}; simulated on independent days {mean:.2f} (se {se:.2f}) -> {'PASS' if g5 else 'FAIL'} "
          f"({time.time() - t0:.0f}s)")
    t0 = time.time()
    ea, fa, free = actions("D", "FTG", r, rf)
    polD = solve(atoms, c, ea, fa, free_timing=free)
    print(f"    D solved in {time.time() - t0:.0f}s: value {polD.value:.2f}")
    simD = simulate(tup, 0.5, polD, c, iid_paths(200_000, c.window, 20261019))["V"]
    mean, se = simD.mean(), simD.std(ddof=1) / np.sqrt(len(simD))
    g6a = abs(mean - polD.value) < 3 * se + 0.02 * polD.value
    t0 = time.time()
    fine = solve(atoms, c, ea, fa, Grid(h=2.5, hg=5.0), free_timing=free)
    g6b = abs(fine.value / polD.value - 1) < 0.02
    ok &= g6a and g6b
    print(f"G6: solver {polD.value:.2f}; simulated on independent days {mean:.2f} (se {se:.2f}) -> {'PASS' if g6a else 'FAIL'}; "
          f"half-step grid {fine.value:.2f} ({fine.value / polD.value - 1:+.2%}) -> {'PASS' if g6b else 'FAIL'} "
          f"({time.time() - t0:.0f}s)")
    assert ok, "gate failed: no K7 result may be read"
    print("K7 GATES PASSED")


def solve_all():
    tup = m.tuples()
    sk = m.skill_table(tup)
    k1 = k1_policy()
    POL.mkdir(parents=True, exist_ok=True)
    rows, paths = [], {}
    only = os.environ.get("K7_ONLY")                       # e.g. "coin|FTG", to run part of the grid
    for regime in REGIMES:
        c = m.alpha(regime)
        for s in SKILLS:
            if only and only != f"{s}|{regime}":
                continue
            p = float(sk.p[m.SKILL.index(s)])
            atoms = Atoms.from_book(tup, m.FIRST, p)
            r, rf, vA = k1[(s, regime)]
            mA, _, loA, hiA = ci(vA)
            rows.append({"skill": str(s), "regime": regime, "class": "A", "model_value": np.nan, "V": mA, "V_lo": loA, "V_hi": hiA})
            paths[f"V|{s}|{regime}|A"] = vA.astype(np.float32)
            for cls in ("B", "C", "D"):
                t0 = time.time()
                ea, fa, free = actions(cls, regime, r, rf)
                pol = solve(atoms, c, ea, fa, free_timing=free)
                t1 = time.time()
                x = simulate(tup, p, pol, c, m.draw(m.SEED_EVAL, n=N))
                mean, se, lo, hi = ci(x["V"])
                paid = x["npay"] > 0
                span = x["hi"] / np.maximum(x["lo"], 1e-12)
                rows.append({"skill": str(s), "regime": regime, "class": cls, "model_value": pol.value, "V": mean, "V_lo": lo,
                             "V_hi": hi, "p_pass": x["passed"].mean(), "p_payout": paid.mean(),
                             "payouts_if_any": x["npay"][paid].mean() if paid.any() else np.nan,
                             "paid_mean_usd": x["V"][paid].mean() if paid.any() else np.nan,
                             "eval_risk_mean": x["eval_risk"].mean(), "size_span_median": float(np.median(span)),
                             "size_span_p90": float(np.percentile(span, 90)),
                             "funded_reaching_cap": float((x["peak"][x["passed"]] >= IB + pol.grid.x_max - pol.grid.h).mean())
                             if x["passed"].any() else np.nan})
                for k in ("V", "eval_risk"):
                    paths[f"{k}|{s}|{regime}|{cls}"] = x[k].astype(np.float32)
                np.savez_compressed(POL / f"{s}_{regime}_{cls}.npz", pol1=pol.pol1, pol2=pol.pol2, act=pol.act, req=pol.req,
                                    eval_actions=pol.eval_actions, fund_actions=pol.fund_actions, value=pol.value)
                print(f"  {s} {regime} {cls}: model {pol.value:.1f}, real paths {fmt_ci(x['V'])}, A {mA:.1f} "
                      f"(solve {t1 - t0:.0f}s, simulate {time.time() - t1:.0f}s)", flush=True)
    t = pd.DataFrame(rows)
    tag = "" if not only else "_" + only.replace("|", "_")
    t.to_csv(OUT / f"K7_classes{tag}.csv", index=False)
    np.savez_compressed(OUT / f"K7_paths{tag}.npz", **paths)
    print(t.round(3).to_string(index=False))


def report():
    t = pd.read_csv(OUT / "K7_classes.csv", dtype={"skill": str})
    z = np.load(OUT / "K7_paths.npz")
    V = lambda s, g, cls: z[f"V|{s}|{g}|{cls}"].astype(float)                  # noqa: E731
    print(f"spec {SPEC}\n=== K7: value by policy class (K1's evaluation paths; USD per $10k purchase) ===")
    print(t.round(3).to_string(index=False))
    print("\n=== Gain over the fixed policy A, paired by path ===")
    for g in REGIMES:
        for s in SKILLS:
            a = V(s, g, "A")
            print(f"  {s:>4} {g}: " + "; ".join(f"{cls} {fmt_ci(V(s, g, cls) - a)} ({(V(s, g, cls).mean() / a.mean() - 1):+.1%})"
                                               for cls in ("B", "C", "D")))

    def verdict(lo, hi, positive=True):
        if positive:
            return "SUPPORTED" if lo > 0 else "REFUTED" if hi < 0 else "INCONCLUSIVE"
        return "SUPPORTED" if hi < 0 else "REFUTED" if lo > 0 else "INCONCLUSIVE"

    print("\n=== Hypotheses (95% intervals paired by path) ===")
    d = V("coin", "FTG", "D") - 1.10 * V("coin", "FTG", "A")
    print(f"  H10 coin flip, FTG: V_D - 1.10 V_A > 0: {fmt_ci(d)}  {verdict(*ci(d)[2:])}")
    er = {s: z[f"eval_risk|{s}|FTG|D"].astype(float) for s in SKILLS}
    h11 = []
    for a, b in (("coin", 0.3), (0.3, 1.0)):
        d = (er[a] - er[b]) * 100
        h11.append(verdict(*ci(d)[2:]))
        print(f"  H11 mean evaluation risk under D, {a} minus {b} > 0: {ci(d)[0]:.3f} points [{ci(d)[2]:.3f}, {ci(d)[3]:.3f}]  "
              f"{h11[-1]}   (levels {er[a].mean():.2%} and {er[b].mean():.2%})")
    print("  H11 overall:", "SUPPORTED" if all(x == "SUPPORTED" for x in h11) else "REFUTED" if "REFUTED" in h11 else "INCONCLUSIVE")
    row = t[(t.skill == "coin") & (t.regime == "FTG") & (t["class"] == "D")].iloc[0]
    lo, hi = row.model_value / row.V_hi, row.model_value / row.V_lo
    h12 = "SUPPORTED" if lo >= 0.90 and hi <= 1.10 else "REFUTED" if hi < 0.90 or lo > 1.10 else "INCONCLUSIVE"
    print(f"  H12 coin flip, FTG, D: model value / realised value = {row.model_value / row.V:.3f} [{lo:.3f}, {hi:.3f}]  {h12}")
    d1 = V("coin", "FTG", "B") - 1.02 * V("coin", "FTG", "A")
    d2 = V("1.0", "STD", "B") - 1.05 * V("1.0", "STD", "A")
    v1, v2 = verdict(*ci(d1)[2:], positive=False), verdict(*ci(d2)[2:])
    print(f"  H13a coin flip, FTG: V_B - 1.02 V_A < 0: {fmt_ci(d1)}  {v1}")
    print(f"  H13b S = 1.0, STD: V_B - 1.05 V_A > 0: {fmt_ci(d2)}  {v2}")
    print("  H13 overall:", "SUPPORTED" if v1 == v2 == "SUPPORTED" else "REFUTED" if "REFUTED" in (v1, v2) else "INCONCLUSIVE")

    print("\n=== D's policy, FTG: size (% of the account) by balance, on three days of the evaluation ===")
    bal1 = [9050, 9100, 9200, 9350, 9500, 9750, 10000, 10250, 10500, 10750, 10900, 10950, 10990]
    bal2 = [9050, 9100, 9200, 9350, 9500, 9750, 10000, 10150, 10300, 10400, 10450, 10490]
    for s in SKILLS:
        pz = np.load(POL / f"{s}_FTG_D.npz")
        ea = pz["eval_actions"] * 100
        for name, pol, bals in (("step 1", pz["pol1"], bal1), ("step 2", pz["pol2"], bal2)):
            tab = pd.DataFrame({f"day {d}": [ea[pol[d, int(round((b - 9000) / 5)) - 1]] for b in bals] for d in (0, 250, 450)},
                               index=[f"${b:,}" for b in bals]).T
            print(f"  skill {s}, {name}:\n{tab.to_string()}")
        act, req, fa = pz["act"], pz["req"], pz["fund_actions"] * 100
        xs = [-950, -900, -800, -600, -400, -200, 0, 100, 200, 400]
        print(f"  skill {s}, funded size by profit (best day 0): " + ", ".join(
            f"{x:+d}: {fa[act[100, int(round((x + 1000) / 5)) - 1, 0]]:.2f}%" for x in xs))
        thr = []
        for d in (50, 300, 600, 740):
            take = np.flatnonzero(req[d, :, 0])
            take = take[take >= int(round((200 + 1000) / 5)) - 1]
            thr.append(f"day {d}: ${-1000 + 5 * (take.min() + 1):,.0f}" if take.size else f"day {d}: never")
        print(f"  skill {s}, smallest profit at which a payout is taken (best day 0): " + "; ".join(thr))


if __name__ == "__main__":
    {"gates": gates, "solve": solve_all, "report": report}[STAGE]()
