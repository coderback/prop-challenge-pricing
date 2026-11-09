"""K10, reconciliation with Lim (2026b), exactly as pre-registered in amendment 6 of
research/PREREGISTRATION_paper2_contract_map.md (commit a06e364).

    python research/run_K10.py step1    H22: Lim's conventions on Alpha Pro 8% and One 6% at $100,000, every reading
    python research/run_K10.py step2    the 16 cells per plan (four factors at his level or ours), Shapley, H23, H24
    python research/run_K10.py report   the hypotheses from the saved tables

K_SMOKE=<n> runs a tiny version to check the code path; its numbers are never results.

Lim's conventions (his Sections 4 and 6): Gaussian daily increments with drift S*sigma/sqrt(252) at daily closes,
his benchmark population (net Sharpe g - 0.10*sqrt(252), g standard normal; sigma in 0.5-5% with weights
5/20/30/25/20%), a 300-day cap per phase, 250 funded days with sweeps of 80% of positive profit every tau days,
no consistency rule, no caps. Values are simulated on a $10,000 account and reported at $100,000 (the rules scale;
the 2% Max Risk Rule from $50,000 is used where it can bind).
"""
import importlib.util
import itertools
import math
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

STAGE = sys.argv[1] if len(sys.argv) > 1 else ""
_argv = sys.argv
_spec = importlib.util.spec_from_file_location("run_K8", "research/run_K8.py")
k8 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k8)                      # loads run_K as k8.m without running either
sys.argv = _argv
m = k8.m

from propcontract.contract import (PASS, BookDays, book_moments, evaluate, fund,  # noqa: E402
                                   sharpe_at, side_moments)

SPEC = "research/PREREGISTRATION_paper2_contract_map.md@a06e364 (amendment 6)"
OUT = Path("data/checks")
SMOKE = int(os.environ.get("K_SMOKE", "0"))
SCALE = 10.0                                      # $10,000 simulated, $100,000 reported
PLANS = ("Pro 8%", "One 6%")
FEE = {"Pro 8%": 527.0, "One 6%": 397.0}          # list fees at $100,000 (ours and Lim's)
HIS_EV = {"Pro 8%": -246.0, "One 6%": -188.0}     # Lim (2026b), Table 2
HIS_V = {p: FEE[p] + HIS_EV[p] for p in PLANS}    # $281 and $209 gross
TOL = {p: max(0.10 * HIS_V[p], 20.0) for p in PLANS}
TAUS = (20, 5, 10)                                # primary first
LOCKS = (False, True)                             # primary first: his Section 4.1 has no stop at the initial balance
SHARPES = [-5.0, -4.0, -3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0, 4.0]    # amendment 1's grid
VOLS = [0.005, 0.01, 0.02, 0.03, 0.05]
WEIGHTS = [0.05, 0.20, 0.30, 0.25, 0.20]
DRAG = 0.10 * math.sqrt(252)
T_LIM, T_OURS = 900, 756                          # path lengths: his conventions need 300 + 300 + 250 + gaps
NB = 20                                           # batches for standard errors
N1 = 100_000 if not SMOKE else SMOKE              # paths per grid point, step 1
NPOP = 20_000 if not SMOKE else SMOKE             # paths per grid point, step 2 population cells
NCOIN = m.N                                       # 50,000 a set in coin-flip cells (K8's)
SEED_G1, SEED_GPOP, SEED_RPOP = 20261109, 20261110, 20261111
SEED_GSEL, SEED_GEVAL = 20261112, 20261113
G = np.random.default_rng(20261114).standard_normal(2_000_000)   # draws of g for the population integral


def integrate(V: np.ndarray) -> float:
    """Population mean of V[S index, vol index] over net Sharpe g - DRAG and the volatility mixture."""
    net = G - DRAG
    return float(sum(w * np.interp(net, SHARPES, V[:, j]).mean() for j, w in enumerate(WEIGHTS)))


# ------------------------------------------------------------------------------------------------ contracts
def build(plan: str, f2: int, f4: int, tau: int = 20, lock: bool = False, regime: str = "FTG", keep: float = 0.0):
    """Evaluation and funded contracts for a cell. f2/f4 = 0 his level, 1 ours. f4 = 1 is the plan as the firm
    publishes it (K8's contracts: caps, Max Risk Rule, the regime, the trailing floor stopping at the initial
    balance, the daily limit on the day's opening balance); f4 = 0 strips what his model leaves out and reads the
    trailing floor and the daily rule as his Section 4.1 writes them."""
    mr = 0.02 if regime == "STD" else 0.03
    c_eval, c_fund = k8.contracts(plan, regime, mr, keep if f2 else 0.0)
    if not f4:
        strip = dict(lev_eval=None, lev_funded=None, risk_cap=None, max_risk=None, trail_lock=lock, daily_ref="initial")
        c_eval, c_fund = replace(c_eval, **strip), replace(c_fund, **strip)
    if not f2:
        his = dict(step_days=(300, 300), eval_days=None, phase_gap=0, fund_gap=1, window=T_LIM, funded_days=250)
        c_eval = replace(c_eval, **his)
        c_fund = replace(c_fund, **his, min_profit=0.0, best_day=None, payout_every=tau, payout_lock=0, buffer=0.0)
    return c_eval, c_fund


def funded_risks(plan: str, f2: int, f4: int, regime: str = "FTG"):
    """The coin flip's funded policies: (risk, profit left in). K8's grids; without the caps, K8's standard grid."""
    rfs = k8.RF["FTG"] if (f4 and regime == "FTG") else k8.RF["STD"]
    keeps = k8.KEEP if (plan.startswith("One") and f2) else [0.0]
    return [(rf, kp) for kp in keeps for rf in rfs]


# ------------------------------------------------------------------------------------------------ pricing
def price_fixed(days, n_paths: int, risks: np.ndarray, c_eval, c_fund) -> tuple[np.ndarray, np.ndarray]:
    """Accounts = every path at every risk in ``risks`` (same risk in both stages). Returns V [k, path] and
    passed [k, path]."""
    k = len(risks)
    row = np.tile(np.arange(n_paths), k)
    risk = np.repeat(risks, n_paths)
    ev = evaluate(days, row, risk, c_eval)
    V = np.zeros(k * n_paths)
    won = np.flatnonzero(ev["outcome"] == PASS)
    if won.size:
        fd = fund(days, row[won], ev["pass_t"][won] + c_fund.fund_gap, risk[won], c_fund, marks=())
        V[won] = fd["payouts"]
    return V.reshape(k, n_paths), (ev["outcome"] == PASS).reshape(k, n_paths)


class GaussStack:
    """Gaussian increments per unit of risk for stacked types, made on the fly from one shared draw:
    account row ``type * n + path`` has R[t] = mu[type] + sd * z[path, t], monitored at the close."""

    def __init__(self, rng, n: int, mu, T: int, v: float = np.inf, sd: float = 1.0):
        self.z = rng.standard_normal((n, T), dtype=np.float32)
        self.mu, self.n, self.v, self.sd = np.asarray(mu, float), n, v, sd

    def at(self, t: int, rows: np.ndarray):
        R = self.mu[rows // self.n] + self.sd * self.z[rows % self.n, t].astype(np.float64)
        return R, R, np.full(len(rows), self.v), np.ones(len(rows), bool)


def gauss_days(rng, n: int, mu, T: int, v: float = np.inf, sd: float = 1.0):
    return GaussStack(rng, n, mu, T, v, sd)


class StackedBook(BookDays):
    """Real paths for stacked types: account row ``type * n + path`` follows path ``path`` and takes the better
    side with that type's hit rate."""

    def __init__(self, tup, start, U, p_types):
        n = len(start)
        take = np.concatenate([U < p for p in p_types])
        super().__init__(tup, start=np.tile(start, len(p_types)), take_better=take)
        self.n = n


def type_grid(mo):
    """(S, vol) types: Gaussian drift per unit of risk, and on real paths the hit rate p(S) and risk vol / sd(R)."""
    lo, hi = sharpe_at(1e-4, mo), sharpe_at(1 - 1e-4, mo)
    rows = []
    for S in SHARPES:
        S_ = min(max(S, lo + 1e-9), hi - 1e-9)
        p = brentq(lambda q: sharpe_at(q, mo) - S_, 1e-4, 1 - 1e-4, xtol=1e-12)
        sd = book_moments(p, mo)[1]
        for vol in VOLS:
            rows.append({"S": S, "vol": vol, "mu": S / math.sqrt(252), "p": p, "r_real": vol / sd, "clipped": S_ != S})
    return pd.DataFrame(rows)


def population_cell(plan, f2, f3, f4, n_per, seed, tup, types, vmed, tau=20, lock=False, regime="FTG"):
    """Batch values (NB,) of the population cell, in dollars at $100,000, and the population pass rate."""
    c_eval, c_fund = build(plan, f2, f4, tau, lock, regime)
    T = T_LIM if not f2 else T_OURS
    nb = max(n_per // NB, 1)
    rng = np.random.default_rng(seed)
    out = np.zeros(NB)
    pas = np.zeros(NB)
    nS, nV = len(SHARPES), len(VOLS)
    for b in range(NB):
        if not f3:
            days = gauss_days(rng, nb, types.mu.to_numpy(), T, v=vmed)
            risks_by_row = np.repeat(types.vol.to_numpy(), nb)
        else:
            start = rng.integers(m.FIRST, len(m.DAYS) - T + 1, nb)
            U = rng.random((nb, T), dtype=np.float32)
            days = StackedBook(tup, start, U, types.p.to_numpy())
            risks_by_row = np.repeat(types.r_real.to_numpy(), nb)
        row = np.arange(len(types) * nb)
        ev = evaluate(days, row, risks_by_row, c_eval)
        V = np.zeros(len(row))
        won = np.flatnonzero(ev["outcome"] == PASS)
        if won.size:
            fd = fund(days, row[won], ev["pass_t"][won] + c_fund.fund_gap, risks_by_row[won], c_fund, marks=())
            V[won] = fd["payouts"]
        Vt = V.reshape(len(types), nb).mean(axis=1).reshape(nS, nV) * SCALE
        Pt = (ev["outcome"] == PASS).reshape(len(types), nb).mean(axis=1).reshape(nS, nV)
        out[b], pas[b] = integrate(Vt), integrate(Pt)
    return out, float(pas.mean())


def step1_cell(plan, lock, taus, vmed, types):
    """Step 1: his conventions (all factors at 0) with N1 paths per grid point; one evaluation, every tau."""
    nb = max(N1 // NB, 1)
    rng = np.random.default_rng(SEED_G1)
    res = {t: np.zeros(NB) for t in taus}
    pas = np.zeros(NB)
    nS, nV = len(SHARPES), len(VOLS)
    c_eval, _ = build(plan, 0, 0, taus[0], lock)
    for b in range(NB):
        days = gauss_days(rng, nb, types.mu.to_numpy(), T_LIM, v=vmed)
        row = np.arange(len(types) * nb)
        risk = np.repeat(types.vol.to_numpy(), nb)
        ev = evaluate(days, row, risk, c_eval)
        won = np.flatnonzero(ev["outcome"] == PASS)
        pas[b] = integrate((ev["outcome"] == PASS).reshape(len(types), nb).mean(axis=1).reshape(nS, nV))
        for tau in taus:
            _, c_fund = build(plan, 0, 0, tau, lock)
            V = np.zeros(len(row))
            if won.size:
                V[won] = fund(days, row[won], ev["pass_t"][won] + c_fund.fund_gap, risk[won], c_fund, marks=())["payouts"]
            res[tau][b] = integrate(V.reshape(len(types), nb).mean(axis=1).reshape(nS, nV) * SCALE)
        print(f"    {plan} lock={lock} batch {b + 1}/{NB}", flush=True)
    return res, float(pas.mean())


def coin_cell(plan, f2, f3, f4, tup, mo, vmed, regime="FTG"):
    """The coin flip, re-sized for the cell: policy (evaluation risk, funded risk, profit left in) selected on a
    selection set and valued on an independent evaluation set. Returns batch values (NB,) at $100,000, the policy
    and the pass rate."""
    T = T_LIM if not f2 else T_OURS
    pols = funded_risks(plan, f2, f4, regime)
    nr = len(m.R_GRID)
    mean_g, sd_g = book_moments(0.5, mo)

    def sets(seed_real, seed_gauss):
        if f3:
            for paths in m.draw(seed_real, n=NCOIN, window=T):
                yield len(paths["U"]), m.days_of(tup, paths, 0.5)
        else:
            rng = np.random.default_rng(seed_gauss)
            for b0 in range(0, NCOIN, m.BATCH):
                n = min(m.BATCH, NCOIN - b0)
                yield n, gauss_days(rng, n, [mean_g], T, v=vmed, sd=sd_g)

    def run(days, n):
        """V [r, policy, path] and passed [r, path]."""
        c_eval, _ = build(plan, f2, f4, regime=regime)
        ev = evaluate(days, np.tile(np.arange(n), nr), np.repeat(np.asarray(m.R_GRID, float), n), c_eval)
        V = np.zeros((nr, len(pols), n))
        won = np.flatnonzero(ev["outcome"] == PASS)
        if won.size:
            ri, pi = won // n, won % n
            for keep in sorted({kp for _, kp in pols}):
                ks = [i for i, (_, kp) in enumerate(pols) if kp == keep]
                _, c_fund = build(plan, f2, f4, regime=regime, keep=keep)
                fd = fund(days, np.tile(pi, len(ks)), np.tile(ev["pass_t"][won] + c_fund.fund_gap, len(ks)),
                          np.repeat([pols[i][0] for i in ks], won.size), c_fund, marks=())
                for j, i in enumerate(ks):
                    V[ri, i, pi] = fd["payouts"][j * won.size:(j + 1) * won.size]
        return V, (ev["outcome"] == PASS).reshape(nr, n)

    sel = np.zeros((nr, len(pols)))
    for n, days in sets(m.SEED_SEL, SEED_GSEL):
        sel += run(days, n)[0].sum(axis=2) / NCOIN
    ri, k = np.unravel_index(np.argmax(sel), sel.shape)
    Vs, Ps = [], []
    for n, days in sets(m.SEED_EVAL, SEED_GEVAL):
        V, P = run(days, n)
        Vs.append(V[ri, k])
        Ps.append(P[ri])
    v = np.concatenate(Vs) * SCALE
    batches = np.array([x.mean() for x in np.array_split(v, NB)])
    pol = {"r": m.R_GRID[ri], "rf": pols[k][0], "keep": pols[k][1]}
    return batches, pol, float(np.concatenate(Ps).mean()), float(v.mean())


# ------------------------------------------------------------------------------------------------ stages
def setup():
    tup = m.tuples()
    mo = side_moments(tup)
    vmed = float(np.median(tup.v[tup.has]))
    types = type_grid(mo)
    if types.clipped.any():
        print("note: S clipped to the attainable range on real paths for", types[types.clipped].S.unique().tolist())
    return tup, mo, vmed, types


def step1():
    print(f"spec {SPEC}\nK10 step 1 (H22): his conventions, N1 = {N1} paths per grid point" + (" [SMOKE]" if SMOKE else ""))
    tup, mo, vmed, types = setup()
    rows, t0 = [], time.time()
    for plan in PLANS:
        for lock in (LOCKS if plan.startswith("One") else (False,)):
            res, pas = step1_cell(plan, lock, TAUS, vmed, types)
            for tau in TAUS:
                b = res[tau]
                V, se = float(b.mean()), float(b.std(ddof=1) / math.sqrt(NB))
                rows.append({"plan": plan, "tau": tau, "trail_lock": lock if plan.startswith("One") else None,
                             "primary": tau == TAUS[0] and lock == LOCKS[0], "V": V, "V_se": se, "EV": V - FEE[plan],
                             "his_V": HIS_V[plan], "his_EV": HIS_EV[plan], "tol": TOL[plan],
                             "within": abs(V - HIS_V[plan]) <= TOL[plan], "p_pass": pas})
            print(f"  {plan} lock={lock} done ({time.time() - t0:.0f}s)", flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / f"K10_step1{'_smoke' if SMOKE else ''}.csv", index=False)
    print(t.round(2).to_string(index=False))
    h22(t)


def h22(t):
    prim = t[t.primary]
    if prim.within.all():
        v = "SUPPORTED"
    else:
        ok = [(tau, lk) for tau in TAUS for lk in LOCKS
              if all(t[(t.plan == p) & (t.tau == tau) & ((t.trail_lock.isna()) | (t.trail_lock == lk))].within.all() for p in PLANS)]
        v = f"PARTLY (within tolerance only under tau={ok[0][0]}, trail_lock={ok[0][1]})" if ok else "NOT REPRODUCED"
    print(f"\nH22 (reproduction within max(10%, $20) of $281 and $209): {v}")
    return v


def shapley(vals: dict) -> dict:
    """Shapley value of each factor from cell values keyed by (f1, f2, f3, f4); works on arrays (batches)."""
    phi = {}
    for i in range(4):
        tot = 0.0
        others = [j for j in range(4) if j != i]
        for k in range(4):
            w = math.factorial(k) * math.factorial(3 - k) / math.factorial(4)
            for S in itertools.combinations(others, k):
                lo = tuple(1 if j in S else 0 for j in range(4))
                hi = tuple(1 if (j in S or j == i) else 0 for j in range(4))
                tot = tot + w * (vals[hi] - vals[lo])
        phi[f"F{i + 1}"] = tot
    return phi


def step2():
    print(f"spec {SPEC}\nK10 step 2: 16 cells per plan" + (" [SMOKE]" if SMOKE else ""))
    s1 = pd.read_csv(OUT / f"K10_step1{'_smoke' if SMOKE else ''}.csv")
    verdict = h22(s1)
    if verdict.startswith("PARTLY"):
        tau, lock = int(verdict.split("tau=")[1].split(",")[0]), verdict.split("trail_lock=")[1].startswith("True")
    else:
        tau, lock = TAUS[0], LOCKS[0]
    print(f"base readings for step 2: tau = {tau}, trail_lock = {lock}" +
          ("" if verdict in ("SUPPORTED",) or verdict.startswith("PARTLY") else "  [EXPLORATORY: H22 not reproduced]"))
    tup, mo, vmed, types = setup()
    rows, cells, t0 = [], {}, time.time()
    for regime in ("FTG", "STD"):
        for plan in PLANS:
            for f in itertools.product((0, 1), repeat=4):
                f1, f2, f3, f4 = f
                if regime == "STD" and not f4:
                    cells[(regime, plan, f)] = cells[("FTG", plan, f)]          # F4 = 0 has no regime
                    continue
                if f1:
                    b, pol, pas, _ = coin_cell(plan, f2, f3, f4, tup, mo, vmed, regime)
                else:
                    seed = SEED_RPOP if f3 else SEED_GPOP
                    b, pas = population_cell(plan, f2, f3, f4, NPOP, seed, tup, types, vmed, tau, lock, regime)
                    pol = {"r": None, "rf": None, "keep": None}
                cells[(regime, plan, f)] = b
                rows.append({"regime": regime, "plan": plan, "F1": f1, "F2": f2, "F3": f3, "F4": f4, "V": b.mean(),
                             "V_se": b.std(ddof=1) / math.sqrt(NB), "EV": b.mean() - FEE[plan], "p_pass": pas, **pol})
                print(f"  {regime} {plan} {f}: V ${b.mean():,.0f} ({time.time() - t0:.0f}s)", flush=True)
    tag = "_smoke" if SMOKE else ""
    t = pd.DataFrame(rows)
    t.to_csv(OUT / f"K10_cells{tag}.csv", index=False)
    np.savez_compressed(OUT / f"K10_batches{tag}.npz",
                        **{f"{g}|{p}|{''.join(map(str, f))}": v for (g, p, f), v in cells.items()})
    report(cells)


def report(cells=None):
    tag = "_smoke" if SMOKE else ""
    if cells is None:
        z = np.load(OUT / f"K10_batches{tag}.npz")
        cells = {(k.split("|")[0], k.split("|")[1], tuple(int(c) for c in k.split("|")[2])): z[k] for k in z.files}
    k8gate = {"Pro 8%": 90.9172908972168 * SCALE, "One 6%": 32.97452114807129 * SCALE}
    rows = []
    for regime in ("FTG", "STD"):
        print(f"\n=== {regime} regime at F4 = 1 ===")
        for plan in PLANS:
            vals = {f: cells[(regime, plan, f)] for f in itertools.product((0, 1), repeat=4)}
            gap = vals[(1, 1, 1, 1)] - vals[(0, 0, 0, 0)]
            phi = shapley(vals)
            print(f"{plan}: his cell ${vals[(0, 0, 0, 0)].mean():,.0f}, ours ${vals[(1, 1, 1, 1)].mean():,.0f}, gap "
                  f"${gap.mean():,.0f} (se {gap.std(ddof=1) / math.sqrt(NB):.0f})")
            if regime == "FTG":
                print(f"  gate: all-ones ${vals[(1, 1, 1, 1)].mean():.4f} against K8 ${k8gate[plan]:.4f}")
            for name, x in phi.items():
                print(f"  Shapley {name}: ${x.mean():+,.0f} (se {x.std(ddof=1) / math.sqrt(NB):.0f}), "
                      f"{x.mean() / gap.mean():.0%} of the gap")
                rows.append({"regime": regime, "plan": plan, "factor": name, "shapley": x.mean(),
                             "se": x.std(ddof=1) / math.sqrt(NB), "share": x.mean() / gap.mean(), "gap": gap.mean()})
            path = [(0, 0, 0, 0), (1, 0, 0, 0), (1, 1, 0, 0), (1, 1, 1, 0), (1, 1, 1, 1)]
            print("  waterfall F1, F2, F3, F4: " + " -> ".join(f"${vals[f].mean():,.0f}" for f in path))
        if regime == "FTG":
            for plan in PLANS:
                vals = {f: cells[(regime, plan, f)] for f in itertools.product((0, 1), repeat=4)}
                phi = shapley(vals)
                worst = min(float((phi["F1"] - phi[o]).mean()) for o in ("F2", "F3", "F4"))
                print(f"  {plan}: F1 minus the next factor, smallest margin ${worst:,.0f}")
            h23 = []
            for plan in PLANS:
                vals = {f: cells[(regime, plan, f)] for f in itertools.product((0, 1), repeat=4)}
                phi = shapley(vals)
                d = [phi["F1"] - phi[o] for o in ("F2", "F3", "F4")]
                h23.append(("above" if all(x.mean() > 2 * x.std(ddof=1) / math.sqrt(NB) for x in d) else
                            "below" if any(x.mean() < -2 * x.std(ddof=1) / math.sqrt(NB) for x in d) else "unclear"))
            v23 = "SUPPORTED" if all(h == "above" for h in h23) else "REFUTED" if "below" in h23 else "INCONCLUSIVE"
            cell = (1, 0, 0, 0)
            d = (cells[(regime, "Pro 8%", cell)] - FEE["Pro 8%"]) - (cells[(regime, "One 6%", cell)] - FEE["One 6%"])
            se = d.std(ddof=1) / math.sqrt(NB)
            lo, hi = d.mean() - 2.093 * se, d.mean() + 2.093 * se        # t(19), 95%
            v24 = "SUPPORTED" if lo > 0 else "REFUTED" if hi < 0 else "INCONCLUSIVE"
            print(f"\nH23 (the buyer is the largest factor on both plans): {v23} ({h23})")
            print(f"H24 (the buyer alone reverses his ranking): EV(Pro 8%) - EV(One 6%) = ${d.mean():,.0f} "
                  f"({lo:,.0f} to {hi:,.0f}); {v24}")
    pd.DataFrame(rows).to_csv(OUT / f"K10_shapley{tag}.csv", index=False)


if __name__ == "__main__":
    {"step1": step1, "step2": step2, "report": report}[STAGE]()
