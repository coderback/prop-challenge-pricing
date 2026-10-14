"""Paper 2 contract map, exactly as pre-registered (research/PREREGISTRATION_paper2_contract_map.md, a102df4).

    python research/run_K.py gates    G2 + G3: the new simulator against S2's table and against r2.evalsim
    python research/run_K.py k1       the skill x sizing map and H1-H3 (writes data/checks/K1_*.csv / .npz)
    python research/run_K.py k2       leave-one-rule-out
    python research/run_K.py k3       bridge to Lim's model
    python research/run_K.py robust   section 9 rows
    python research/run_K.py k4       fee and break-evens (from K1)
    python research/run_K.py x1       claim-exclusion table for the 24 tests (uses K4's break-even Sharpe)
    python research/run_K.py explore  checks outside the plan (reported as exploratory)
    python research/run_K.py export   copy the result tables and headline numbers into paper/prop_contract/results

Book Z2 (one intraday US500 trade a day, 1 x ATR stop), both sides simulated. Development data only. A contract
valuation, not an edge test.
"""
import json
import os
import re
import shutil
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from propcontract.legacy.evalsim import Book, SimConfig, run_funded, run_one
from propcontract.legacy.trades import TradeSet
from propcontract.contract import (BREACH_DAILY, BREACH_STATIC, IB, MAX_RISK, PASS, TIMEOUT, BookDays, Contract,
                                   DayTuples, MatrixDays, book_moments, evaluate, fund, sharpe_at, side_moments,
                                   solve_p, stationary_bootstrap)

pd.set_option("display.width", 250, "display.max_rows", 400, "display.max_columns", 40)
SPEC = "research/PREREGISTRATION_paper2_contract_map.md@a102df4"
CODE, STRESS = "SPX500_USD", 1.5
OUT = Path("data/checks")
SKILL = ["coin", 0.0, 0.15, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0]
R_GRID = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06, 0.08]
FUND = [("FTG", 0.005), ("FTG", 0.01)] + [("STD", x) for x in (0.005, 0.01, 0.015, 0.02, 0.025)]
REGIME_K = {"FTG": [0, 1], "STD": [2, 3, 4, 5, 6]}
N, BATCH, WINDOW = 50_000, 10_000, 756
if os.environ.get("K_SMOKE"):                      # a quick end-to-end check of the code path, never a result
    N = BATCH = int(os.environ["K_SMOKE"])
SEED_SEL, SEED_EVAL, SEED_BOOT = 20261013, 20261014, 20261015
FEES = (40.0, 147.0)
CONV = (R_GRID.index(0.01), {"FTG": 1, "STD": 3})       # the conventional policy: 1% and 1%
DAYS = pd.bdate_range("2005-01-03", "2024-09-30").to_numpy().astype("datetime64[D]")
FIRST = int(np.searchsorted(DAYS, np.datetime64("2005-02-01")))

META = json.loads(Path("data/derived/book_meta.json").read_text(encoding="utf-8"))
ref = META[CODE]["ref_price"]
LAM = 2.5 * ref / IB                                     # the 2.5-lot cap as leverage (one lot = one index unit)


def tuples(stress=STRESS) -> DayTuples:
    """The book's day series at a cost level: shipped in data/r2cache, or rebuilt from raw bars in data/raw."""
    cache = Path(f"data/r2cache/K_tuples_x{stress}.npz")
    if cache.exists():
        z = np.load(cache)
        return DayTuples(DAYS, z["has"], z["R"], z["L"], z["v"])
    from propcontract.book import build_tuples
    tup = build_tuples(pd.read_parquet(f"data/raw/{CODE}_M30.parquet"), META[CODE]["spread_by_server_hour"], ref, stress=stress)
    np.savez(cache, has=tup.has, R=tup.R, L=tup.L, v=tup.v)
    return tup


def skill_table(tup) -> pd.DataFrame:
    mo = side_moments(tup)
    rows = []
    for s in SKILL:
        p = 0.5 if s == "coin" else solve_p(s, mo)
        m, sd = book_moments(p, mo)
        rows.append({"skill": str(s), "p": p, "net_sharpe": sharpe_at(p, mo), "mean_R": m, "sd_R": sd})
    return pd.DataFrame(rows)


def alpha(regime, **kw) -> Contract:
    return Contract.alpha(LAM, regime, **kw)


def draw(seed, n=N, window=WINDOW, boot=False):
    """Batches of paths: purchase days (or resampled day indices) and one uniform per day."""
    rng = np.random.default_rng(seed)
    last = len(DAYS) - window
    for b0 in range(0, n, BATCH):
        k = min(BATCH, n - b0)
        if boot:
            yield {"gidx": stationary_bootstrap(FIRST, len(DAYS), k, window, 21, rng),
                   "U": rng.random((k, window), dtype=np.float32)}
        else:
            yield {"start": rng.integers(FIRST, last + 1, k), "U": rng.random((k, window), dtype=np.float32)}


def days_of(tup, paths, p):
    return BookDays(tup, start=paths.get("start"), gidx=paths.get("gidx"), take_better=paths["U"] < p)


def price(days, n, r_list, fund_list, c_eval: Contract, c_fund) -> dict:
    """Evaluation for every r, then the funded stage for every (regime, r_f) on the accounts that passed.
    ``c_fund(regime)`` returns the funded contract. Arrays are indexed [r, path] and [r, fund, path]."""
    nr, nk = len(r_list), len(fund_list)
    row = np.tile(np.arange(n), nr)
    ev = evaluate(days, row, np.repeat(np.asarray(r_list, float), n), c_eval)
    out = {"outcome": ev["outcome"].reshape(nr, n), "pass_t": ev["pass_t"].reshape(nr, n),
           "p1": (ev["p1_t"] >= 0).reshape(nr, n), "V": np.zeros((nr, nk, n), np.float32),
           "npay": np.zeros((nr, nk, n), np.int16), "close": np.zeros((nr, nk, n), np.int8),
           "V12": np.zeros((nr, nk, n), np.float32), "V24": np.zeros((nr, nk, n), np.float32)}
    won = np.flatnonzero(ev["outcome"] == PASS)
    if won.size == 0:
        return out
    ri, pi = won // n, won % n
    for regime in sorted({g for g, _ in fund_list}):
        ks = [k for k, (g, _) in enumerate(fund_list) if g == regime]
        c = c_fund(regime)
        fd = fund(days, np.tile(pi, len(ks)), np.tile(ev["pass_t"][won] + c.fund_gap, len(ks)),
                  np.repeat([fund_list[k][1] for k in ks], won.size), c, marks=(252, 504))
        for j, k in enumerate(ks):
            sl = slice(j * won.size, (j + 1) * won.size)
            out["V"][ri, k, pi] = fd["payouts"][sl]
            out["npay"][ri, k, pi] = fd["n_pay"][sl]
            out["close"][ri, k, pi] = fd["outcome"][sl]
            out["V12"][ri, k, pi] = fd["pay_by"][sl, 0]
            out["V24"][ri, k, pi] = fd["pay_by"][sl, 1]
    return out


def pct(x):
    return round(x * 100, 4)


def ci(x):
    x = np.asarray(x, float)
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    return m, se, m - 1.96 * se, m + 1.96 * se


def fmt_ci(x, unit="$"):
    m, se, lo, hi = ci(x)
    return f"{unit}{m:,.1f} [{lo:,.1f}, {hi:,.1f}]"


# ================================================================================================ gates
def gates():
    """The simulator against the older, independently written one, path by path, on seeded random-side books
    built from the shipped day series. (The research repository's gate G2, exact reproduction of an earlier
    study's table, needs that study's seeded books; its log is in results/reference/logs/run_K_gates.log.)"""
    tup = tuples()
    c = Contract.s2()
    r_s2 = (0.005, 0.01, 0.02, 0.03, 0.04)

    def starts(lo, window_end):
        s0 = int(np.searchsorted(DAYS, np.datetime64(lo)))
        last = int(np.searchsorted(DAYS, np.datetime64(window_end), side="right")) - WINDOW
        return np.arange(s0, last + 1, 10)

    all_st = np.r_[starts("2005-02-01", "2016-12-31"), starts("2017-01-02", "2024-09-30")]
    g = np.flatnonzero(tup.has)
    code = {"pass": PASS, "breach_static": BREACH_STATIC, "breach_daily": BREACH_DAILY, "timeout": TIMEOUT}
    n_cases = n_bad = 0
    for seed, rs in ((1, r_s2), (2, (0.03,))):
        side = np.zeros(len(DAYS), int)
        side[g] = np.random.default_rng(seed).integers(0, 2, len(g))
        Rg, Lg = tup.R[g, side[g]].copy(), tup.L[g, side[g]].copy()
        trades = pd.DataFrame({"R": Rg, "Rw": Rg, "stop_dist": tup.v[g], "entry": np.ones(len(g))})
        bk = Book(TradeSet(trades, DAYS[g], np.arange(len(g)), np.ones(len(g), int), Rg, Lg), DAYS)
        bd = BookDays(tup, start=all_st, side=side)
        for r in rs:
            cfg = SimConfig(r=r, policy="fixed", horizon_days=504, keepalive_days=25)
            ev = evaluate(bd, np.arange(len(all_st)), np.full(len(all_st), r), c)
            won = np.flatnonzero(ev["outcome"] == PASS)
            pay = {}
            for rf in (min(r, 0.0066), r):
                fd = fund(bd, won, ev["pass_t"][won] + 3, np.full(won.size, rf), c)
                pay[rf] = dict(zip(won.tolist(), fd["payouts"].tolist()))
            for i, s in enumerate(all_st.tolist()):
                old = run_one(bk, s, cfg)
                ok = code[old["outcome"]] == ev["outcome"][i] and (-1 if old["p1_day"] is None else old["p1_day"]) == ev["p1_t"][i]
                if old["outcome"] == "pass":
                    ok &= old["days"] == ev["pass_t"][i]
                    for rf in pay:
                        f = run_funded(bk, s + old["days"] + 3, s + WINDOW, rf, cfg)
                        ok &= abs(f["payouts"] - pay[rf][i]) < 1e-6
                n_cases += 1
                n_bad += not ok
    print(f"{n_cases} cases against the older simulator, {n_bad} mismatches ->", "PASS" if n_bad == 0 else "FAIL")
    gaps = np.diff(DAYS[tup.has]).astype(int)
    print(f"inactivity: longest gap between trade days {gaps.max()} calendar days (must stay under 25)")
    assert n_bad == 0 and n_cases >= 2000 and gaps.max() < 25, "gate failed: no K result may be read"
    print("GATES PASSED")


# ================================================================================================ K1
def k1():
    tup = tuples()
    sk = skill_table(tup)
    v = tup.v[tup.has]
    print(f"spec {SPEC}")
    print(f"book: {tup.has.sum()} trade days; P_ref {ref:,.1f}; lot-cap leverage lambda {LAM:.3f} (FTG {LAM / 2:.3f}); "
          f"stop/price median {np.median(v):.4f} (5-95%: {np.percentile(v, 5):.4f}-{np.percentile(v, 95):.4f})")
    print(f"  funded risk allowed by the lot cap at the median day: STD {LAM * np.median(v):.2%}, FTG "
          f"{min(0.01, LAM / 2 * np.median(v)):.2%}; evaluation leverage cap binds for r > {10 * np.percentile(v, 5):.1%} "
          f"on 5% of days")
    print(sk.round(4).to_string(index=False))
    ns, nr, nk = len(SKILL), len(R_GRID), len(FUND)
    c_eval = alpha("FTG")
    sel = np.zeros((ns, nr, nk))
    keep = {k: np.zeros(shape, dt) for k, shape, dt in (
        ("V", (ns, nr, nk, N), np.float32), ("outcome", (ns, nr, N), np.int8), ("pass_t", (ns, nr, N), np.int16),
        ("p1", (ns, nr, N), bool))}
    agg = {k: np.zeros((ns, nr, nk)) for k in ("V12", "V24", "paid", "npay", "fd_static", "fd_daily", "fd_maxrisk")}
    start_all = np.zeros(N, np.int32)
    for name, seed in (("selection", SEED_SEL), ("evaluation", SEED_EVAL)):
        t0 = time.time()
        for b, paths in enumerate(draw(seed)):
            sl = slice(b * BATCH, b * BATCH + len(paths["U"]))
            for si, p in enumerate(sk.p):
                res = price(days_of(tup, paths, p), len(paths["U"]), R_GRID, FUND, c_eval, alpha)
                if name == "selection":
                    sel[si] += res["V"].sum(axis=2) / N
                else:
                    for k in keep:
                        keep[k][si][..., sl] = res[k]
                    agg["V12"][si] += res["V12"].sum(axis=2) / N
                    agg["V24"][si] += res["V24"].sum(axis=2) / N
                    agg["paid"][si] += (res["npay"] > 0).sum(axis=2) / N
                    agg["npay"][si] += res["npay"].sum(axis=2) / N
                    for name_, code_ in (("fd_static", BREACH_STATIC), ("fd_daily", BREACH_DAILY), ("fd_maxrisk", MAX_RISK)):
                        agg[name_][si] += (res["close"] == code_).sum(axis=2) / N
            if name == "evaluation":
                start_all[sl] = paths["start"]
            print(f"  {name} batch {b + 1}/{N // BATCH} done ({time.time() - t0:.0f}s)", flush=True)
    np.savez_compressed(OUT / "K1_paths.npz", start=start_all, sel=sel, **keep, **{"agg_" + k: v for k, v in agg.items()})
    report_k1(sk, sel, keep, start_all, agg)


def load_k1():
    z = np.load(OUT / "K1_paths.npz")
    return z["sel"], {k: z[k] for k in ("V", "outcome", "pass_t", "p1")}, z["start"]


def select(sel) -> dict:
    """(skill index, regime) -> (r index, fund index) with the highest selection-set V."""
    pol = {}
    for si in range(len(SKILL)):
        for regime, ks in REGIME_K.items():
            sub = sel[si][:, ks]
            ri, j = np.unravel_index(np.argmax(sub), sub.shape)
            pol[(si, regime)] = (int(ri), ks[int(j)])
    return pol


def report_k1(sk, sel, keep, start, agg):
    pol = select(sel)
    V, outc, pt = keep["V"], keep["outcome"], keep["pass_t"]
    rows = []
    for si, s in enumerate(SKILL):
        for ri, r in enumerate(R_GRID):
            o = outc[si, ri]
            won = o == PASS
            base = {"skill": str(s), "net_sharpe": sk.net_sharpe[si], "r_pct": pct(r), "p_step1": keep["p1"][si, ri].mean(),
                    "p_pass": won.mean(), "months_p50": np.median(pt[si, ri][won] / 21) if won.any() else np.nan,
                    "ev_static": (o == BREACH_STATIC).mean(), "ev_daily": (o == BREACH_DAILY).mean(),
                    "ev_timeout": (o == TIMEOUT).mean()}
            for k, (regime, rf) in enumerate(FUND):
                m, se, lo, hi = ci(V[si, ri, k])
                g = {name: agg[name][si, ri, k] for name in agg}
                rows.append(base | {"regime": regime, "rf_pct": pct(rf), "V": m, "V_se": se, "V_lo": lo, "V_hi": hi,
                                    "V_sel": sel[si, ri, k], "V12": g["V12"], "V24": g["V24"], "p_payout": g["paid"],
                                    "n_pay_if_any": g["npay"] / g["paid"] if g["paid"] > 0 else np.nan,
                                    "fd_static": g["fd_static"], "fd_daily": g["fd_daily"], "fd_maxrisk": g["fd_maxrisk"],
                                    "selected": pol[(si, regime)] == (ri, k)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "K1_map.csv", index=False)
    for regime in ("FTG", "STD"):
        print(f"\n=== K1 selected policy by skill, {regime} (evaluation set) ===")
        print(df[df.selected & (df.regime == regime)][["skill", "net_sharpe", "r_pct", "rf_pct", "p_step1", "p_pass",
              "months_p50", "p_payout", "V", "V_lo", "V_hi", "V_sel", "V12", "V24"]].round(3).to_string(index=False))
        for s in ("coin", "0.3", "1.0"):
            rf = df[df.selected & (df.regime == regime) & (df.skill == s)].rf_pct.iloc[0]
            print(f"\n--- {regime}, skill {s}: every r at the selected r_f = {rf:g}% ---")
            print(df[(df.regime == regime) & (df.skill == s) & (df.rf_pct == rf)][["r_pct", "p_step1", "p_pass", "months_p50",
                  "ev_static", "ev_daily", "ev_timeout", "p_payout", "V", "V_lo", "V_hi", "fd_static", "fd_daily",
                  "fd_maxrisk"]].round(3).to_string(index=False))
    print("\n=== V by skill x r at the selected r_f (FTG), USD ===")
    piv = pd.concat([df[(df.regime == "FTG") & (df.skill == str(s)) &
                        (df.rf_pct == pct(FUND[pol[(si, "FTG")][1]][1]))].set_index("r_pct").V.rename(str(s))
                     for si, s in enumerate(SKILL)], axis=1).T
    print(piv.round(0).to_string())
    piv = pd.concat([df[(df.regime == "FTG") & (df.skill == str(s)) & (df.rf_pct == 1.0)].set_index("r_pct").p_pass.rename(str(s))
                     for s in SKILL], axis=1).T
    print("\n=== P(pass) by skill x r ===")
    print(piv.round(3).to_string())
    hypotheses(pol, V, start, "FTG", "primary")
    hypotheses(pol, V, start, "STD", "robustness row 1 (STD, its own selected policy)")
    g = {"2005-02 to 2014-02": start <= np.searchsorted(DAYS, np.datetime64("2014-02-04")),
         "2017-01 to 2021-11": start >= np.searchsorted(DAYS, np.datetime64("2017-01-02"))}
    for name, mask in g.items():
        hypotheses(pol, V[..., mask], start[mask], "FTG", f"robustness row 3, purchases {name} (n={mask.sum()})")
    yr = pd.Series(DAYS[start]).dt.year.to_numpy()
    ri, k = pol[(0, "FTG")]
    r3, k3 = pol[(3, "FTG")]
    by = pd.DataFrame({"year": yr, "coin": V[0, ri, k], "S0.3": V[3, r3, k3]}).groupby("year").agg(["mean", "count"])
    print("\n=== V by purchase year, FTG selected policies ===")
    print(by.round(1).to_string())


def hypotheses(pol, V, start, regime, label):
    s_coin, s_03 = 0, SKILL.index(0.3)
    rc, kc = pol[(s_coin, regime)]
    r3, k3 = pol[(s_03, regime)]
    v_coin, v_conv, v_03 = V[s_coin, rc, kc].astype(float), V[s_coin, CONV[0], CONV[1][regime]].astype(float), \
        V[s_03, r3, k3].astype(float)
    sizing, skill = v_coin - v_conv, v_03 - v_coin
    D = sizing - skill
    print(f"\n=== Hypotheses, {regime}: {label} ===")
    print(f"  coin policy r={R_GRID[rc]:.1%}, r_f={FUND[kc][1]:.1%}; S=0.3 policy r={R_GRID[r3]:.1%}, r_f={FUND[k3][1]:.1%}")
    print(f"  V(coin, selected) {fmt_ci(v_coin)}   V(coin, 1%/1%) {fmt_ci(v_conv)}   V(S=0.3, selected) {fmt_ci(v_03)}")
    m, se, lo, hi = ci(v_coin)
    h1 = "SUPPORTED" if lo > 40 and hi < 147 else "REFUTED" if hi < 40 or lo > 147 else "INCONCLUSIVE"
    print(f"  H1 V(coin) > $40 and < $147: {h1}")
    m, se, lo, hi = ci(D)
    h2 = "SUPPORTED" if lo > 0 else "REFUTED" if hi < 0 else "INCONCLUSIVE"
    print(f"  H2 sizing gain {fmt_ci(sizing)}  minus skill gain {fmt_ci(skill)}  = D {fmt_ci(D)}: {h2}")
    m, se, lo, hi = ci(v_03)
    h3 = "SUPPORTED" if hi < 147 else "REFUTED" if lo > 147 else "INCONCLUSIVE"
    print(f"  H3 V(S=0.3) < $147: {h3}")
    return {"H1": h1, "H2": h2, "H3": h3, "D": ci(D)[0], "v_coin": v_coin.mean(), "v_03": v_03.mean()}


# ================================================================================================ K2
def cells(pol, regimes=("FTG", "STD"), skills=("coin", 0.3, 1.0)):
    return [(SKILL.index(s), g, R_GRID[pol[(SKILL.index(s), g)][0]], FUND[pol[(SKILL.index(s), g)][1]][1])
            for s in skills for g in regimes]


def one_cell(tup, p, r, rf, c: Contract, seed=SEED_EVAL, boot=False, n=N):
    """One (r, r_f) policy under contract ``c`` on the evaluation paths: per-path payouts and flags."""
    out = {k: [] for k in ("V", "passed", "paid")}
    for paths in draw(seed, n=n, window=c.window, boot=boot):
        res = price(days_of(tup, paths, p), len(paths["U"]), [r], [("x", rf)], c, lambda g: c)
        out["V"].append(res["V"][0, 0].astype(float))
        out["passed"].append(res["outcome"][0] == PASS)
        out["paid"].append(res["npay"][0, 0] > 0)
    return {k: np.concatenate(v) for k, v in out.items()}


def k2():
    tup, tup0 = tuples(), tuples(0.0)
    sk = skill_table(tup)
    sel, keep, start = load_k1()
    pol = select(sel)
    drop = {"a no daily floor": dict(daily_dd=None), "b floors at the close only": dict(intraday=False),
            "c one step": dict(target_p2=None), "d no minimum days": dict(min_days=0),
            "e no evaluation leverage cap": dict(lev_eval=None),
            "f no funded lot or position caps": dict(lev_funded=None, risk_cap=None),
            "g no Max Risk Rule": dict(max_risk=None), "h no Best Day Rule": dict(best_day=None),
            "i no 2% minimum": dict(min_profit=0.0), "j payout checks every 21 days": dict(payout_every=21),
            "k no payout lock": dict(payout_lock=0), "n step maturities 30/60": dict(step_days=(30, 60)),
            "o no trading costs": {}}
    bare = {}
    for name in "abdefghijk":
        bare |= next(v for k, v in drop.items() if k.startswith(name + " "))
    rows = []
    for si, regime, r, rf in cells(pol):
        p = sk.p[si]
        base_c = alpha(regime)
        base = one_cell(tup, p, r, rf, base_c)
        def add(name, x):
            dV = x["V"] - base["V"]
            m, se, lo, hi = ci(dV)
            rows.append({"skill": str(SKILL[si]), "regime": regime, "r_pct": pct(r), "rf_pct": pct(rf), "variant": name,
                         "p_pass": x["passed"].mean(), "p_payout": x["paid"].mean(), "V": x["V"].mean(),
                         "dP_pass": x["passed"].mean() - base["passed"].mean(),
                         "dP_payout": x["paid"].mean() - base["paid"].mean(), "dV": m, "dV_lo": lo, "dV_hi": hi})
        add("baseline", base)
        for name, kw in drop.items():
            add(name, one_cell(tup0 if name.startswith("o ") else tup, p, r, rf, replace(base_c, **kw)))
        add("bare contract (a, b, d-k, o)", one_cell(tup0, p, r, rf, replace(base_c, **bare)))
        b = rows[-len(drop) - 2]
        rows.append({**b, "variant": "l 100% split (arithmetic)", "V": b["V"] * 1.25, "dV": b["V"] * 0.25,
                     "dP_pass": 0.0, "dP_payout": 0.0, "dV_lo": np.nan, "dV_hi": np.nan})
        for fee in FEES:
            rows.append({**b, "variant": f"m fee refund at ${fee:.0f} (arithmetic)", "V": b["V"] + fee * b["p_payout"],
                         "dV": fee * b["p_payout"], "dP_pass": 0.0, "dP_payout": 0.0, "dV_lo": np.nan, "dV_hi": np.nan})
        print(f"  K2 {SKILL[si]} {regime} done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "K2_rules.csv", index=False)
    for (s, g), d in df.groupby(["skill", "regime"], sort=False):
        print(f"\n=== K2 leave one out: skill {s}, {g}, r={d.r_pct.iloc[0]:g}%, r_f={d.rf_pct.iloc[0]:g}% ===")
        print(d[["variant", "p_pass", "p_payout", "V", "dP_pass", "dP_payout", "dV", "dV_lo", "dV_hi"]].round(3).to_string(index=False))


# ================================================================================================ K3
def normal_days(rng, n, T, mean, sd=1.0):
    return MatrixDays((mean + sd * rng.standard_normal((n, T), dtype=np.float32)).astype(np.float64))


def k3():
    tup = tuples()
    sk = skill_table(tup)
    mo = side_moments(tup)
    sel, keep, start = load_k1()
    pol = select(sel)
    # ---- (i) Lim's tables with his contract and normal increments
    lim2 = {(0, "daily only"): 0.453, (2, "daily only"): 0.744, (0, "maturity only"): 0.310, (2, "maturity only"): 0.550,
            (0, "both"): 0.298, (2, "both"): 0.532}
    lim3 = {(0, 1): 0.026, (0, 2): 0.184, (0, 3): 0.195, (1, 1): 0.066, (1, 2): 0.298, (1, 3): 0.278,
            (2, 1): 0.135, (2, 2): 0.434, (2, 3): 0.375}
    variants = {"daily only": Contract.lim(maturity=False, target_p2=None, window=300),
                "maturity only": Contract.lim(daily_dd=None, target_p2=None, window=30),
                "both": Contract.lim(target_p2=None, window=30)}
    n, rows = 200_000, []
    rng = np.random.default_rng(20261016)
    for (S, name), want in lim2.items():
        c = variants[name]
        got = np.mean([(evaluate(normal_days(rng, 25_000, c.window, S / np.sqrt(252)), np.arange(25_000),
                                 np.full(25_000, 0.02), c)["outcome"] == PASS).mean() for _ in range(n // 25_000)])
        rows.append({"table": "Lim T2 step 1, 2% vol", "S": S, "cell": name, "lim": want, "ours": got})
    c = Contract.lim(window=90)
    for (S, vol), want in lim3.items():
        got = np.mean([(evaluate(normal_days(rng, 50_000, 90, S / np.sqrt(252)), np.arange(50_000),
                                 np.full(50_000, vol / 100), c)["outcome"] == PASS).mean() for _ in range(n // 50_000)])
        rows.append({"table": "Lim T3 funded", "S": S, "cell": f"{vol}% vol", "lim": want, "ours": got})
    t = pd.DataFrame(rows)
    t["diff"] = t.ours - t.lim
    print("=== K3 (i) replication of Lim's tables (normal increments, his contract) ===")
    print(t.round(4).to_string(index=False))
    print(f"largest |difference| {t['diff'].abs().max():.4f} ->", "AGREES within 0.01" if t["diff"].abs().max() <= 0.01
          else "DOES NOT AGREE within 0.01")
    # ---- (ii) real paths through Lim's contract
    rows = []
    for S in (0, 1, 2):
        p = solve_p(float(S), mo)
        sd = book_moments(p, mo)[1]
        for vol in (1, 2, 3):
            r = vol / 100 / sd
            got = {}
            for name, cc in (("close", Contract.lim(window=90)), ("intraday", Contract.lim(window=90, intraday=True))):
                hit = [(evaluate(days_of(tup, paths, p), np.arange(len(paths["U"])), np.full(len(paths["U"]), r),
                                 cc)["outcome"] == PASS) for paths in draw(SEED_EVAL, window=90)]
                got[name] = np.concatenate(hit).mean()
            rows.append({"S": S, "vol_pct": vol, "r_pct": pct(r), "lim_normal": lim3[(S, vol)],
                         "real_close": got["close"], "real_intraday": got["intraday"]})
    t2 = pd.DataFrame(rows)
    print("\n=== K3 (ii) real paths through Lim's classic contract: P(funded) ===")
    print(t2.round(4).to_string(index=False))
    # ---- (iii) a Gaussian book with the real book's mean and sd through Alpha's rules
    vmed = float(np.median(tup.v[tup.has]))
    rows = []
    k1map = pd.read_csv(OUT / "K1_map.csv", dtype={"skill": str})
    for s in ("coin", 0.3, 1.0):
        si = SKILL.index(s)
        m, sd = book_moments(sk.p[si], mo)
        for regime in ("FTG", "STD"):
            rf = FUND[pol[(si, regime)][1]][1]
            c = alpha(regime)
            acc = {r: [] for r in R_GRID}
            passed = {r: [] for r in R_GRID}
            rng = np.random.default_rng(20261017)
            for _ in range(N // BATCH):
                days = MatrixDays((m + sd * rng.standard_normal((BATCH, WINDOW), dtype=np.float32)).astype(np.float64), v=vmed)
                res = price(days, BATCH, R_GRID, [(regime, rf)], c, lambda g: c)
                for ri, r in enumerate(R_GRID):
                    acc[r].append(res["V"][ri, 0].astype(float))
                    passed[r].append(res["outcome"][ri] == PASS)
            for r in R_GRID:
                real = k1map[(k1map.skill == str(s)) & (k1map.regime == regime) & (k1map.r_pct == pct(r)) &
                             (k1map.rf_pct == pct(rf))].iloc[0]
                x = np.concatenate(acc[r])
                rows.append({"skill": str(s), "regime": regime, "rf_pct": pct(rf), "r_pct": pct(r),
                             "p_pass_normal": np.concatenate(passed[r]).mean(), "p_pass_real": real.p_pass,
                             "V_normal": x.mean(), "V_normal_se": ci(x)[1], "V_real": real.V})
        print(f"  K3 (iii) {s} done", flush=True)
    t3 = pd.DataFrame(rows)
    print("\n=== K3 (iii) Gaussian book through Alpha's rules, against the real book (K1) ===")
    print(t3.round(3).to_string(index=False))
    t.to_csv(OUT / "K3_lim_replication.csv", index=False)
    t2.to_csv(OUT / "K3_real_through_lim.csv", index=False)
    t3.to_csv(OUT / "K3_normal_through_alpha.csv", index=False)


# ================================================================================================ robustness
def robust():
    sel, keep, start = load_k1()
    pol = select(sel)
    sk = skill_table(tuples())
    i3 = SKILL.index(0.3)
    rc, kc = pol[(0, "FTG")]
    r3, k3 = pol[(i3, "FTG")]
    policies = {"coin": (0, R_GRID[rc], FUND[kc][1]), "conv": (0, 0.01, 0.01), "s03": (i3, R_GRID[r3], FUND[k3][1])}
    specs = {"2 block bootstrap (21 days)": dict(boot=True, seed=SEED_BOOT),
             "4 payout checks every 21 days": dict(kw=dict(payout_every=21)),
             "5 60-month window": dict(kw=dict(window=1260)),
             "6 cost stress x1.0": dict(stress=1.0), "6 cost stress x2.0": dict(stress=2.0)}
    rows = []
    for name, spec in specs.items():
        tup = tuples(spec.get("stress", STRESS))
        c = alpha("FTG", **spec.get("kw", {}))
        ps = sk.p if "stress" not in spec else skill_table(tup).p     # the same skill definition at that cost level
        x = {k: one_cell(tup, ps[si], r, rf, c, seed=spec.get("seed", SEED_EVAL), boot=spec.get("boot", False))["V"]
             for k, (si, r, rf) in policies.items()}
        sizing, skill = x["coin"] - x["conv"], x["s03"] - x["coin"]
        D = sizing - skill
        rows.append({"row": name, "V_coin": fmt_ci(x["coin"]), "V_conv": fmt_ci(x["conv"]), "V_s03": fmt_ci(x["s03"]),
                     "D": fmt_ci(D), "H1 sign": bool(x["coin"].mean() > 40 and x["coin"].mean() < 147),
                     "H2 sign": bool(D.mean() > 0), "H3 sign": bool(x["s03"].mean() < 147)})
        print(f"  robustness {name} done", flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "K_robustness.csv", index=False)
    print("\n=== Section 9 rows 2, 4, 5, 6 (FTG, policies fixed at the primary selection) ===")
    print(t.to_string(index=False))


# ================================================================================================ K4
SWING_FEES = {5_000: 70, 10_000: 147, 25_000: 247, 50_000: 357, 100_000: 577, 200_000: 1_097}   # checkout, 2026-10-13
BEST_CODE = {5_000: 56.0, 10_000: 40.0, 25_000: 197.6, 50_000: 285.6, 100_000: 461.6, 200_000: 877.6}   # ALPHA20; 10KFOR40


def frontier(regime):
    """Net Sharpe and V at the selected policy for every skill level, with the policy's per-path payouts."""
    sel, keep, start = load_k1()
    pol = select(sel)
    S = skill_table(tuples()).net_sharpe.to_numpy()
    paths = [keep["V"][si][pol[(si, regime)]].astype(float) for si in range(len(SKILL))]
    best = np.array([x.mean() for x in paths])
    assert (np.diff(best) > 0).all(), "V is not increasing in skill: interpolation invalid"
    return S, best, paths, keep["V"][0, CONV[0], CONV[1][regime]].mean()


def sharpe_at_value(target, S, best):
    """Sharpe at which V equals ``target`` (linear interpolation); None outside the grid."""
    return float(np.interp(target, best, S)) if best[0] < target <= best[-1] else None


def k4():
    for regime in ("FTG", "STD"):
        S, best, paths, conv = frontier(regime)
        se = np.array([ci(x)[1] for x in paths])
        print(f"\n=== K4 {regime}: break-even fee by skill (V at the selected policy) ===")
        print(pd.DataFrame({"skill": [str(s) for s in SKILL], "net_sharpe": S.round(3), "V_usd": best.round(1),
                            "se": se.round(1), "V_pct_of_account": (best / IB * 100).round(3),
                            "denial_break_even_at_40": (1 - 40 / best).round(3),
                            "denial_break_even_at_147": (1 - 147 / best).round(3)}).to_string(index=False))

        def s_at(target):
            x = sharpe_at_value(target, S, best)
            if x is None:
                return f"below the coin flip ({S[0]:.2f})" if target <= best[0] else f"above {S[-1]:.1f}"
            return f"{x:.2f}"

        print(f"  break-even Sharpe at $40: {s_at(40)};  at $147: {s_at(147)}")
        sizing = best[0] - conv
        print(f"  sizing gain for the coin flip (selected vs 1%/1%): ${sizing:.1f}; skill equivalent of sizing: S = "
              f"{s_at(best[0] + sizing)}")
        print(f"  skill equivalent of the $107 promo discount: S = {s_at(best[0] + 107)}")
        if regime == "FTG":
            for label, fees in (("list fee", SWING_FEES), ("fee with the best code (ALPHA20; 10KFOR40 at $10k)", BEST_CODE)):
                print(f"  {label} by account size against V (% of account; rules scale with size under FTG):")
                print(pd.DataFrame({"account": list(fees), "fee": list(fees.values()),
                                    "fee_pct": [round(f / a * 100, 3) for a, f in fees.items()],
                                    "break_even_sharpe": [s_at(f / a * IB) for a, f in fees.items()],
                                    "EV_coin_pct": [round((best[0] - f / a * IB) / IB * 100, 3) for a, f in fees.items()],
                                    "EV_coin_usd": [round((best[0] - f / a * IB) * a / IB, 0) for a, f in fees.items()],
                                    "EV_S0.3_usd": [round((best[3] - f / a * IB) * a / IB, 0) for a, f in fees.items()],
                                    "denial_break_even_coin": [round(1 - f / a * IB / best[0], 3) for a, f in fees.items()]}
                                   ).to_string(index=False))


def explore():
    """Not pre-registered; labelled exploratory in the results."""
    sel, keep, start = load_k1()
    pol = select(sel)
    tup = tuples()
    sk = skill_table(tup)
    m = pd.read_csv(OUT / "K1_map.csv", dtype={"skill": str})
    i3 = SKILL.index(0.3)
    print("=== Exploratory 1: H2's two gains by horizon (FTG, policies fixed at the 36-month selection) ===")

    def cell(si, ri, k):
        return m[(m.skill == str(SKILL[si])) & (m.r_pct == pct(R_GRID[ri])) & (m.regime == FUND[k][0]) &
                 (m.rf_pct == pct(FUND[k][1]))].iloc[0]

    coin, conv, s03 = cell(0, *pol[(0, "FTG")]), cell(0, CONV[0], CONV[1]["FTG"]), cell(i3, *pol[(i3, "FTG")])
    print(pd.DataFrame([{"months": h, "V_coin": coin[c], "V_coin_1%/1%": conv[c], "V_S0.3": s03[c],
                         "sizing_gain": coin[c] - conv[c], "skill_gain": s03[c] - coin[c],
                         "D": (coin[c] - conv[c]) - (s03[c] - coin[c])}
                        for h, c in ((12, "V12"), (24, "V24"), (36, "V"))]).round(1).to_string(index=False))
    print("\n=== Exploratory 2: the 2 x 2 of sizing and skill (FTG, 36 months) ===")
    c03 = cell(i3, CONV[0], CONV[1]["FTG"])
    print(pd.DataFrame({"1%/1%": [conv.V, c03.V], "selected": [coin.V, s03.V]}, index=["coin", "S=0.3"]).round(1).to_string())
    print("\n=== Exploratory 3: FTG with the 2% Max Risk Rule of accounts from $50k (selected policies) ===")
    for si in (0, i3, SKILL.index(1.0)):
        ri, k = pol[(si, "FTG")]
        x = one_cell(tup, sk.p[si], R_GRID[ri], FUND[k][1], alpha("FTG", max_risk=0.02))
        base = keep["V"][si, ri, k].astype(float)
        print(f"  skill {SKILL[si]}: V at 3% {base.mean():.1f}, at 2% {x['V'].mean():.1f}, difference {fmt_ci(x['V'] - base)}")
    print("\n=== Exploratory 4: the coin flip's funded stage (FTG selected policy) ===")
    ri, k = pol[(0, "FTG")]
    v = keep["V"][0, ri, k].astype(float)
    won = keep["outcome"][0, ri] == PASS
    print(f"  P(pass) {won.mean():.3f}; V per funded account ${v[won].mean():.0f}; share of funded accounts paid "
          f"{(v[won] > 0).mean():.3f}; payouts if paid: median ${np.median(v[v > 0]):.0f}, mean ${v[v > 0].mean():.0f}, "
          f"95th percentile ${np.percentile(v[v > 0], 95):.0f}")
    print(f"  buyers who get back at least $40: {(v >= 40).mean():.3f}; at least $147: {(v >= 147).mean():.3f}")


def hyp_stats(pol, V, regime) -> dict:
    """The three quantities behind H1-H3 and their paired differences: mean and 95% interval of each."""
    i3 = SKILL.index(0.3)
    coin = V[0][pol[(0, regime)]].astype(float)
    conv = V[0, CONV[0], CONV[1][regime]].astype(float)
    s03 = V[i3][pol[(i3, regime)]].astype(float)
    out = {}
    for name, x in (("coin", coin), ("conv", conv), ("s03", s03), ("sizing", coin - conv), ("skill", s03 - coin),
                    ("D", (coin - conv) - (s03 - coin))):
        m, se, lo, hi = ci(x)
        out[name] = {"mean": m, "lo": lo, "hi": hi}
    return out | {"n": int(V.shape[-1])}


def export():
    dst = Path("paper/prop_contract/results")
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("K1_map.csv", "K2_rules.csv", "K3_lim_replication.csv", "K3_real_through_lim.csv",
                 "K3_normal_through_alpha.csv", "X1_claim_exclusion.csv", "K_robustness.csv"):
        shutil.copyfile(OUT / name, dst / name)
    sel, keep, start = load_k1()
    pol = select(sel)
    tup = tuples()
    sk = skill_table(tup)
    V = keep["V"]
    v = tup.v[tup.has]
    i3 = SKILL.index(0.3)
    early = start <= np.searchsorted(DAYS, np.datetime64("2014-02-04"))
    late = start >= np.searchsorted(DAYS, np.datetime64("2017-01-02"))
    hyp = {"FTG": hyp_stats(pol, V, "FTG"), "STD": hyp_stats(pol, V, "STD"),
           "FTG purchases 2005-02 to 2014-02": hyp_stats(pol, V[..., early], "FTG"),
           "FTG purchases 2017-01 to 2021-11": hyp_stats(pol, V[..., late], "FTG")}
    num = re.compile(r"\$(-?[\d.]+) \[(-?[\d.]+), (-?[\d.]+)\]")
    rb = pd.read_csv(OUT / "K_robustness.csv")
    robust = {r["row"]: {k: dict(zip(("mean", "lo", "hi"), map(float, num.match(r[c]).groups())))
                         for k, c in (("coin", "V_coin"), ("conv", "V_conv"), ("s03", "V_s03"), ("D", "D"))}
              for _, r in rb.iterrows()}
    front = {}
    for regime in ("FTG", "STD"):
        S, best, paths, conv = frontier(regime)
        front[regime] = {"S": S.tolist(), "V": best.tolist(), "se": [ci(x)[1] for x in paths],
                         "be_40": sharpe_at_value(40.0, S, best), "be_147": sharpe_at_value(147.0, S, best),
                         "sizing_gain": best[0] - conv, "skill_eq_sizing": sharpe_at_value(2 * best[0] - conv, S, best),
                         "skill_eq_promo": sharpe_at_value(best[0] + 107.0, S, best)}
    ri, k = pol[(0, "FTG")]
    vc = V[0, ri, k].astype(float)
    won = keep["outcome"][0, ri] == PASS
    coin = {"p_pass": float(won.mean()), "v_per_funded": float(vc[won].mean()), "share_funded_paid": float((vc[won] > 0).mean()),
            "p_paid": float((vc > 0).mean()), "paid_median": float(np.median(vc[vc > 0])), "paid_mean": float(vc[vc > 0].mean()),
            "paid_p95": float(np.percentile(vc[vc > 0], 95))}
    yr = pd.Series(DAYS[start]).dt.year.to_numpy()
    r3, k3 = pol[(i3, "FTG")]
    by_year = pd.DataFrame({"year": yr, "coin": vc, "s03": V[i3, r3, k3]}).groupby("year").mean().round(2)
    mr = {}
    for si in (0, i3, SKILL.index(1.0)):
        a, b = pol[(si, "FTG")]
        x = one_cell(tup, sk.p[si], R_GRID[a], FUND[b][1], alpha("FTG", max_risk=0.02))["V"]
        mr[str(SKILL[si])] = float(np.abs(x - V[si, a, b].astype(float)).max())
    head = {"spec": SPEC, "n_paths": N, "trade_days": int(tup.has.sum()), "p_ref": ref, "lam": LAM,
            "v_median": float(np.median(v)), "v_p5": float(np.percentile(v, 5)), "v_p95": float(np.percentile(v, 95)),
            "skill": sk.to_dict("records"),
            "policy": {f"{SKILL[si]}|{g}": [R_GRID[a], FUND[b][1]] for (si, g), (a, b) in pol.items()},
            "hyp": hyp, "robust": robust, "frontier": front, "coin_funded": coin,
            "by_year": {int(y): r.to_dict() for y, r in by_year.iterrows()},
            "max_risk_2pct_largest_path_difference": mr,
            "fees": {"list": SWING_FEES, "code": BEST_CODE}}
    (dst / "headline.json").write_text(json.dumps(head, indent=1), encoding="utf-8")
    print("exported to", dst)
    print(json.dumps({"hyp FTG": hyp["FTG"], "max risk check": mr, "coin": coin}, indent=1))


# ================================================================================================ X1
X1 = [  # test, idea, annualised net Sharpe, years, sample its decision used, source
    ("A1", "European FX-fix reversal", -0.13, 7.75, "validation 2017-2024-09 (discovery 0.92 passed)", "RESULTS_A1_fix_reversal.md"),
    ("A2a", "Month-end hedge flow before the fix", 0.02, 12.0, "2005-2016", "RESULTS_batch_A1b_A2_A3.md"),
    ("A2b", "Month-end reversal after the fix", 0.36, 12.0, "2005-2016", "RESULTS_batch_A1b_A2_A3.md"),
    ("A3", "FOMC-eve carry", 0.29, 12.0, "2005-2016", "RESULTS_batch_A1b_A2_A3.md"),
    ("A4", "Post-FOMC long USD", 0.31, 12.0, "2005-2016", "RESULTS_batch_A4_A5_A6.md"),
    ("A5", "VIX-inversion index shorts", -0.13, 7.25, "2009-10 to 2016", "RESULTS_batch_A4_A5_A6.md"),
    ("A6", "CFTC speculator following", 0.12, 12.0, "2005-2016", "RESULTS_batch_A4_A5_A6.md"),
    ("A8", "G8 FX momentum 12-1", -0.08, 11.67, "140 months to 2016", "RESULTS_batch_A8_A9.md"),
    ("A9", "G8 FX value", -0.16, 11.67, "140 months to 2016", "RESULTS_batch_A8_A9.md"),
    ("B1", "Diversified futures trend", 0.14, 11.0, "2006-2016", "RESULTS_B1_futures_trend.md"),
    ("B3", "Crypto weekly momentum", 0.62, 6.0, "2014-2019", "RESULTS_B3_crypto_trend.md"),
    ("M1", "Macro-surprise drift", -1.09, 10.0, "2007-2016", "RESULTS_M_macro_surprise.md"),
    ("M2", "Macro reaction momentum", -0.28, 10.0, "2007-2016", "RESULTS_M_macro_surprise.md"),
    ("M1r", "Fade the macro surprise (post hoc)", 0.65, 10.0, "2007-2016", "RESULTS_M_macro_surprise.md"),
    ("P1", "S&P 500 earnings drift", -0.74, 10.0, "2007-2016, quarterly series", "RESULTS_P1_earnings_drift.md"),
    ("R1", "FX PCA-residual reversal", -0.45, 11.0, "2006-2016", "RESULTS_batch_R_relative_value.md"),
    ("R2", "Cointegrated pairs", -0.77, 11.0, "2006-2016", "RESULTS_batch_R_relative_value.md"),
    ("L1", "Pooled LightGBM, next day", -0.01, 8.0, "2009-2016 walk-forward", "RESULTS_batch_L_ml_sentiment_regime.md"),
    ("L2", "GDELT news tone on US500", -0.35, 4.0, "2017-2020", "RESULTS_batch_L_ml_sentiment_regime.md"),
    ("L3", "HMM regime filter on trend", -0.04, 9.0, "2008-2016", "RESULTS_batch_L_ml_sentiment_regime.md"),
    ("I1", "Fade retail FX positioning", -0.22, 3.58, "2017-06 to 2020", "RESULTS_batch_I_informational.md"),
    ("I2", "Follow dark-pool DIX on US500", 0.09, 4.67, "2012-05 to 2016", "RESULTS_batch_I_informational.md"),
    ("T1", "Treasury auction cycle", -0.09, 12.0, "2005-2016", "RESULTS_batch_T_calendar.md"),
    ("T2", "Equity turn of month", 0.05, 12.0, "2005-2016", "RESULTS_batch_T_calendar.md"),
]


def x1():
    S, best, paths, conv = frontier("FTG")
    star = sharpe_at_value(147.0, S, best)
    marks = {"0.3": 0.3, "0.5": 0.5} | ({f"S*={star:.2f}": star} if star is not None else {})
    print("break-even Sharpe at the list fee (FTG):", "outside the grid" if star is None else f"{star:.2f}")
    t = pd.DataFrame(X1, columns=["test", "idea", "sharpe", "years", "sample", "source"])
    t["se"] = np.sqrt((1 + t.sharpe ** 2 / 2) / t.years)
    t["lower"], t["upper"] = t.sharpe - 1.645 * t.se, t.sharpe + 1.645 * t.se
    t["mde"] = 2.49 / np.sqrt(t.years)
    for name, thr in marks.items():
        t[f"at {name}"] = np.where(t.upper < thr, "REFUTED", np.where(t.lower > thr, "MATERIAL", "INCONCLUSIVE"))
    t.to_csv(OUT / "X1_claim_exclusion.csv", index=False)
    print(t.drop(columns=["idea", "source"]).round(2).to_string(index=False))
    for name in marks:
        print(f"  at {name}:", t[f"at {name}"].value_counts().to_dict())
    print(f"  median minimum detectable Sharpe {t.mde.median():.2f}; tests with a point estimate above 0.3: "
          f"{t[t.sharpe > 0.3].test.tolist()}")


if __name__ == "__main__":
    {"gates": gates, "k1": k1, "k2": k2, "k3": k3, "robust": robust, "k4": k4, "x1": x1, "explore": explore, "export": export}[sys.argv[1]]()
