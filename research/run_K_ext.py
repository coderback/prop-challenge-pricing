"""Paper 2 extensions, exactly as pre-registered in amendment 2 of
research/PREREGISTRATION_paper2_contract_map.md (commit a9134c0).

    python research/run_K_ext.py k5    the horizon grid: contract clock x value window, policies re-selected
    python research/run_K_ext.py k6    the same contract on NAS100, EUR/USD and USD/JPY

Both reuse the gated simulator and the conventions of research/run_K.py. Contract valuations, not edge tests.
"""
import importlib.util
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
except KeyError:                                    # run_K dispatches on argv; "none" is not a stage
    pass

from propcontract.contract import (PASS, DayTuples, evaluate, fund, sharpe_at,       # noqa: E402
                                   side_moments, solve_p)

SPEC = "research/PREREGISTRATION_paper2_contract_map.md@a9134c0 (amendment 2)"
OUT = Path("data/checks")
if os.environ.get("K_SMOKE"):                       # a quick end-to-end check of the code path, never a result
    m.N = m.BATCH = int(os.environ["K_SMOKE"])
R_GRID, N, BATCH = m.R_GRID, m.N, m.BATCH
RF = [0.005, 0.01]                                   # FTG funded risks
CONV = (R_GRID.index(0.01), RF.index(0.01))          # the conventional policy: 1% and 1%
HORIZONS = {12: 252, 24: 504, 36: 756, 60: 1260}
ci, fmt_ci = m.ci, m.fmt_ci


def verdict(lo, hi, positive=True):
    if positive:
        return "SUPPORTED" if lo > 0 else "REFUTED" if hi < 0 else "INCONCLUSIVE"
    return "SUPPORTED" if hi < 0 else "REFUTED" if lo > 0 else "INCONCLUSIVE"


# ================================================================================================ K5
def price_h(days, n, c):
    """Every evaluation risk, then both funded risks on the accounts that passed. Returns the evaluation's
    outcome, pass and end offsets [r, path] and the payouts requested within each horizon [h, r, k, path]."""
    nr, nk = len(R_GRID), len(RF)
    ev = evaluate(days, np.tile(np.arange(n), nr), np.repeat(np.asarray(R_GRID, float), n), c)
    pay = np.zeros((len(HORIZONS), nr, nk, n), np.float32)
    won = np.flatnonzero(ev["outcome"] == PASS)
    if won.size:
        ri, pi = won // n, won % n
        fd = fund(days, np.tile(pi, nk), np.tile(ev["pass_t"][won] + c.fund_gap, nk), np.repeat(RF, won.size), c,
                  marks=(252, 504, 756))
        for k in range(nk):
            sl = slice(k * won.size, (k + 1) * won.size)
            for h in range(3):
                pay[h, ri, k, pi] = fd["pay_by"][sl, h]
            pay[3, ri, k, pi] = fd["payouts"][sl]
    return {k: ev[k].reshape(nr, n) for k in ("outcome", "pass_t", "end_t")}, pay


def k5():
    tup = m.tuples()
    sk = m.skill_table(tup)
    skills = ["coin", 0.0, 0.3, 1.0]
    ps = {s: float(sk.p[m.SKILL.index(s)]) for s in skills}
    window = HORIZONS[60]
    clocks = {"none": m.alpha("FTG", window=window, eval_days=None),
              "classic 30/60": m.alpha("FTG", window=window, eval_days=None, step_days=(30, 60))}
    nh, nr, nk = len(HORIZONS), len(R_GRID), len(RF)
    sel = {(c, s): np.zeros((nh, nr, nk)) for c in clocks for s in skills}
    pay = {(c, s): np.zeros((nh, nr, nk, N), np.float32) for c in clocks for s in skills}
    ev = {(c, s): {k: np.zeros((nr, N), np.int16) for k in ("outcome", "pass_t", "end_t")} for c in clocks for s in skills}
    print(f"spec {SPEC}\nwindow {window} days; purchase days {m.DAYS[m.FIRST]} to {m.DAYS[len(m.DAYS) - window]}")
    for name, seed in (("selection", m.SEED_SEL), ("evaluation", m.SEED_EVAL)):
        t0 = time.time()
        for b, paths in enumerate(m.draw(seed, n=N, window=window)):
            n = len(paths["U"])
            sl = slice(b * BATCH, b * BATCH + n)
            for cn, c in clocks.items():
                for s in skills:
                    e, x = price_h(m.days_of(tup, paths, ps[s]), n, c)
                    if name == "selection":
                        sel[(cn, s)] += x.sum(axis=3) / N
                    else:
                        pay[(cn, s)][..., sl] = x
                        for k in e:
                            ev[(cn, s)][k][:, sl] = e[k]
            print(f"  {name} batch {b + 1}/{N // BATCH} done ({time.time() - t0:.0f}s)", flush=True)

    rows, D, D0, pol = [], {}, {}, {}
    for cn in clocks:
        for hi, (months, days_h) in enumerate(HORIZONS.items()):
            v = {}
            for s in skills:
                ri, k = np.unravel_index(np.argmax(sel[(cn, s)][hi]), (nr, nk))
                pol[(cn, months, s)] = (int(ri), int(k))
                x = pay[(cn, s)][hi, ri, k].astype(float)
                conv = pay[(cn, s)][hi, CONV[0], CONV[1]].astype(float)
                e = ev[(cn, s)]
                passed = (e["outcome"][ri] == PASS) & (e["pass_t"][ri] < days_h)
                open_ = (e["end_t"][ri] < 0) | (e["end_t"][ri] >= days_h)
                open_conv = (e["end_t"][CONV[0]] < 0) | (e["end_t"][CONV[0]] >= days_h)
                mean, se, lo, hi_ = ci(x)
                rows.append({"clock": cn, "months": months, "skill": str(s), "r_pct": R_GRID[ri] * 100, "rf_pct": RF[k] * 100,
                             "p_pass": passed.mean(), "still_in_evaluation": open_.mean(), "V": mean, "V_lo": lo, "V_hi": hi_,
                             "V_conv": conv.mean(), "still_in_evaluation_conv": open_conv.mean()})
                v[s], v[(s, "conv")] = x, conv
            sizing = v["coin"] - v[("coin", "conv")]
            D[(cn, months)] = sizing - (v[0.3] - v["coin"])
            D0[(cn, months)] = (v[0.0] - v[(0.0, "conv")]) - (v[0.3] - v[0.0])
            for r in rows[-len(skills):]:
                r["V_coin_selected"] = v["coin"].mean()
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "K5_horizon.csv", index=False)
    for cn in clocks:
        print(f"\n=== K5 clock: {cn} (FTG, evaluation set; policy re-selected in every cell) ===")
        print(t[t.clock == cn].drop(columns="clock").round(3).to_string(index=False))

    drow = []
    for (cn, months), d in D.items():
        mean, se, lo, hi_ = ci(d)
        m0, _, lo0, hi0 = ci(D0[(cn, months)])
        coin = t[(t.clock == cn) & (t.months == months) & (t.skill == "coin")].iloc[0]
        s03 = t[(t.clock == cn) & (t.months == months) & (t.skill == "0.3")].iloc[0]
        drow.append({"clock": cn, "months": months, "sizing_gain": coin.V - coin.V_conv, "skill_gain": s03.V - coin.V,
                     "D": mean, "D_lo": lo, "D_hi": hi_, "D_from_S0": m0, "D_from_S0_lo": lo0, "D_from_S0_hi": hi0,
                     "V_S0.3_conv_minus_V_coin_selected": s03.V_conv - coin.V})
    dt = pd.DataFrame(drow)
    dt.to_csv(OUT / "K5_D.csv", index=False)
    print("\n=== K5: D = sizing gain minus the gain from a Sharpe of 0.3, by clock and window ===")
    print(dt.round(2).to_string(index=False))
    np.savez_compressed(OUT / "K5_paths.npz", **{f"D|{c}|{h}": d.astype(np.float32) for (c, h), d in D.items()})

    print("\n=== Hypotheses (FTG, evaluation set, 95% intervals paired by path) ===")
    lo, hi_ = ci(D[("classic 30/60", 12)])[2:]
    print(f"  H4 classic clock, 12 months, D > 0: {fmt_ci(D[('classic 30/60', 12)])}  {verdict(lo, hi_)}")
    lo, hi_ = ci(D[("none", 60)])[2:]
    print(f"  H5 no clock, 60 months, D < 0: {fmt_ci(D[('none', 60)])}  {verdict(lo, hi_, positive=False)}")
    months = list(HORIZONS)
    h6 = []
    for cn in clocks:
        for a, b in zip(months[:-1], months[1:]):
            d = D[(cn, a)] - D[(cn, b)]
            lo, hi_ = ci(d)[2:]
            h6.append(verdict(lo, hi_))
            print(f"  H6 {cn}: D({a}m) - D({b}m) > 0: {fmt_ci(d)}  {h6[-1]}")
    print("  H6 overall:", "SUPPORTED" if all(x == "SUPPORTED" for x in h6) else "REFUTED" if "REFUTED" in h6 else "INCONCLUSIVE")
    h7 = []
    for mo in months:
        d = D[("classic 30/60", mo)] - D[("none", mo)]
        lo, hi_ = ci(d)[2:]
        h7.append(verdict(lo, hi_))
        print(f"  H7 {mo} months: D(clock) - D(no clock) > 0: {fmt_ci(d)}  {h7[-1]}")
    print("  H7 overall:", "SUPPORTED" if all(x == "SUPPORTED" for x in h7) else "REFUTED" if "REFUTED" in h7 else "INCONCLUSIVE")

    print("\n=== Reported without a hypothesis: a skilled buyer at 1%/1% against the coin flip at its selected policy ===")
    out = []
    for cn in clocks:
        for mo in months:
            coin = t[(t.clock == cn) & (t.months == mo) & (t.skill == "coin")].iloc[0]
            out.append({"clock": cn, "months": mo, "V_coin_selected": coin.V} |
                       {f"V_S{s}_at_1%/1%": t[(t.clock == cn) & (t.months == mo) & (t.skill == str(s))].V_conv.iloc[0]
                        for s in (0.3, 1.0)})
    print(pd.DataFrame(out).round(1).to_string(index=False))


# ================================================================================================ K6
BOOKS = {"NAS100_USD": "index", "EUR_USD": "fx", "USD_JPY": "fx"}
LEV_EVAL = {"index": 10.0, "fx": 30.0}
LEV_FTG = {"index": 5.0, "fx": 15.0}
FTG_LOTS = 1.25


def tuples6(code: str, stress: float) -> DayTuples:
    """The day series of another instrument: shipped in data/r2cache, or rebuilt from raw bars in data/raw."""
    cache = Path(f"data/r2cache/K6_tuples_{code}_x{stress}.npz")
    if cache.exists():
        z = np.load(cache)
        return DayTuples(m.DAYS, z["has"], z["R"], z["L"], z["v"])
    from propcontract.book import build_tuples
    tup = build_tuples(pd.read_parquet(f"data/raw/{code}_M30.parquet"), m.META[code]["spread_by_server_hour"],
                       m.META[code]["ref_price"], stress=stress)
    np.savez(cache, has=tup.has, R=tup.R, L=tup.L, v=tup.v)
    return tup


def contract6(code: str):
    kind = BOOKS[code]
    ref = m.META[code]["ref_price"]
    size = float(m.META[code]["contract_size"])
    lot_usd = size if code.startswith("USD_") else size * ref          # one lot in dollars of notional
    lot_lev = FTG_LOTS * lot_usd / m.IB
    c = replace(m.alpha("FTG"), lev_eval=LEV_EVAL[kind], lev_funded=min(lot_lev, LEV_FTG[kind]))
    return c, ref, lot_lev


def k6():
    print(f"spec {SPEC}")
    rows = []
    D = {}
    for code in BOOKS:
        tup = tuples6(code, m.STRESS)
        c, ref, lot_lev = contract6(code)
        mo = side_moments(tup)
        gaps = np.diff(m.DAYS[tup.has]).astype(int)
        v = tup.v[tup.has]
        print(f"\n{code}: {tup.has.sum()} trade days from {m.DAYS[tup.has][0]}; reference price {ref:,.4f}; FTG lot cap as "
              f"leverage {lot_lev:.2f} (limit {LEV_FTG[BOOKS[code]]:.0f}); stop/price median {np.median(v):.4f}; "
              f"longest gap {gaps.max()} days")
        if gaps.max() >= 25 or m.DAYS[tup.has][0] > m.DAYS[m.FIRST]:
            print(f"  GATE: longest gap {gaps.max()} days, first trade day {m.DAYS[tup.has][0]}")
        if gaps.max() >= 25:
            print("  book dropped: the inactivity rule could bind")
            continue
        ps = {"coin": 0.5, 0.3: solve_p(0.3, mo)}
        print(f"  coin flip: mean {tup.R[tup.has].mean():+.4f}R a trade, net Sharpe {sharpe_at(0.5, mo):+.3f}; "
              f"hit rate on the better side for a Sharpe of 0.3: {ps[0.3]:.4f}; funded risk allowed at the median day "
              f"{min(0.01, c.lev_funded * np.median(v)):.2%}")
        fl = [("FTG", x) for x in RF]
        sel = {s: np.zeros((len(R_GRID), len(RF))) for s in ps}
        V = {s: np.zeros((len(R_GRID), len(RF), N), np.float32) for s in ps}
        passed = {s: np.zeros((len(R_GRID), N), bool) for s in ps}
        for name, seed in (("selection", m.SEED_SEL), ("evaluation", m.SEED_EVAL)):
            for b, paths in enumerate(m.draw(seed, n=N)):
                n = len(paths["U"])
                sl = slice(b * BATCH, b * BATCH + n)
                for s, p in ps.items():
                    res = m.price(m.days_of(tup, paths, p), n, R_GRID, fl, c, lambda g: c)
                    if name == "selection":
                        sel[s] += res["V"].sum(axis=2) / N
                    else:
                        V[s][..., sl] = res["V"]
                        passed[s][:, sl] = res["outcome"] == PASS
            print(f"  {name} set done", flush=True)
        pol = {s: np.unravel_index(np.argmax(sel[s]), sel[s].shape) for s in ps}
        rc, kc = pol["coin"]
        r3, k3 = pol[0.3]
        coin, conv, s03 = V["coin"][rc, kc].astype(float), V["coin"][CONV].astype(float), V[0.3][r3, k3].astype(float)
        D[code] = (coin - conv) - (s03 - coin)
        free = m.one_cell(tuples6(code, 0.0), 0.5, R_GRID[rc], RF[kc], c)["V"]
        mc, _, lo, hi = ci(coin)
        md, _, dlo, dhi = ci(D[code])
        rows.append({"book": code, "cost_R": tup.R[tup.has].mean(), "net_sharpe_coin": sharpe_at(0.5, mo),
                     "r_pct": R_GRID[rc] * 100, "rf_pct": RF[kc] * 100, "p_pass": passed["coin"][rc].mean(), "V_coin": mc,
                     "V_lo": lo, "V_hi": hi, "V_coin_1%/1%": conv.mean(), "r_pct_S0.3": R_GRID[r3] * 100, "V_S0.3": s03.mean(),
                     "D": md, "D_lo": dlo, "D_hi": dhi, "V_coin_no_costs": free.mean(),
                     "H8": "inside" if lo >= 75 and hi <= 130 else "outside" if hi < 75 or lo > 130 else "straddles",
                     "H9": verdict(dlo, dhi, positive=False)})
        print("  V of the coin flip along the sizing grid (funded 1%):",
              {f"{r:.1%}": round(float(V["coin"][i, 1].mean()), 1) for i, r in enumerate(R_GRID)})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "K6_books.csv", index=False)
    print("\n=== K6: the same contract on other books (FTG, 36 months, evaluation set) ===")
    print(t.round(3).to_string(index=False))
    print("  reference, US500 (K1): cost -0.0069R, coin flip $103 [100, 106] at 3.5%/1%, $33 at 1%/1%, $285 at S = 0.3")
    if len(t):
        h8 = "SUPPORTED" if (t.H8 == "inside").all() else "REFUTED" if (t.H8 == "outside").any() else "INCONCLUSIVE"
        h9 = "SUPPORTED" if (t.H9 == "SUPPORTED").all() else "REFUTED" if (t.H9 == "REFUTED").any() else "INCONCLUSIVE"
        print(f"\n  H8 every book's coin-flip V between $75 and $130: {h8}")
        print(f"  H9 D < 0 in every book: {h9}")


if __name__ == "__main__":
    {"k5": k5, "k6": k6}[STAGE]()
