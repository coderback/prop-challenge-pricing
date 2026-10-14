"""K9, real strategies through the contract, exactly as pre-registered in amendment 5 of
research/PREREGISTRATION_paper2_contract_map.md (commit c87a97f).

    python research/run_K9.py

Books: the forward-watchlist candidates A1b, A2b and M1r, their ensemble R3 (A2b + M1r) and all three (W3), each
from its own committed builder at ACG costs x 1.5. None is a confirmed edge. A contract valuation.
"""
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.argv = ["run_K.py", "none"]
_spec = importlib.util.spec_from_file_location("run_K", "research/run_K.py")
m = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(m)
except KeyError:
    pass

from propcontract.contract import PASS, TIMEOUT, BookDays, DayTuples, evaluate, fund, stationary_bootstrap   # noqa: E402

SPEC = "research/PREREGISTRATION_paper2_contract_map.md@c87a97f (amendment 5)"
OUT = Path("data/checks")
STRESS, WINDOW = 1.5, 756
DAYS, FIRST = m.DAYS, m.FIRST
R_EVAL = [0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.04, 0.06, 0.08, 0.12, 0.16]
R_FUND = [0.001, 0.0025, 0.005, 0.01]
LEV_EVAL, LEV_FTG, LOT_FTG = 30.0, 15.0, 12.5        # 1.25 currency lots = 125,000 units, taken at parity
EARLY_END, LATE_START = np.datetime64("2014-02-04"), np.datetime64("2017-01-02")
ci = m.ci


# ------------------------------------------------------------------------------------------------ books
def build_books() -> dict:
    """The five books as daily series at one unit of risk per trade. Their builders belong to a larger research
    codebase and are not part of this package; the series were written by its ``daily_series``."""
    z = np.load("data/derived/K9_daily_series.npz")
    return {b: {k: z[f"{b}|{k}"] for k in ("R", "W", "n", "notional", "entries", "n_trades")} for b in ("A1b", "A2b", "M1r", "R3", "W3")}


def day_sources(s: dict):
    has = s["n"] > 0
    R2, L2 = np.stack([s["R"], np.zeros(len(DAYS))], axis=1), np.stack([s["W"], np.zeros(len(DAYS))], axis=1)
    v_eval = np.where(has, 1.0 / np.maximum(s["notional"], 1e-12), 1.0)   # so that LEV_EVAL x v caps total notional
    lev_f = min(LOT_FTG, LEV_FTG)
    v_fund = np.where(has, np.minimum(lev_f * v_eval, 0.01 / np.maximum(s["n"], 1)) / lev_f, 1.0)
    return DayTuples(DAYS, has, R2, L2, v_eval), DayTuples(DAYS, has, R2, L2, v_fund), lev_f


def price(s: dict) -> dict:
    """V[r, r_f, start] for purchases on every business day on which the window fits."""
    t_eval, t_fund, lev_f = day_sources(s)
    starts = np.arange(FIRST, len(DAYS) - WINDOW + 1)
    n, nr, nk = len(starts), len(R_EVAL), len(R_FUND)
    side = np.zeros(len(DAYS), int)
    c_eval = replace(m.alpha("FTG"), lev_eval=LEV_EVAL)
    c_fund = replace(c_eval, lev_funded=lev_f, risk_cap=None, max_risk=None)
    ev = evaluate(BookDays(t_eval, start=starts, side=side), np.tile(np.arange(n), nr), np.repeat(R_EVAL, n), c_eval)
    V = np.zeros((nr, nk, n))
    npay = np.zeros((nr, nk, n), int)
    won = np.flatnonzero(ev["outcome"] == PASS)
    if won.size:
        ri, pi = won // n, won % n
        fd = fund(BookDays(t_fund, start=starts, side=side), np.tile(pi, nk), np.tile(ev["pass_t"][won] + c_fund.fund_gap, nk),
                  np.repeat(R_FUND, won.size), c_fund, marks=(252, 504))
        for k in range(nk):
            sl = slice(k * won.size, (k + 1) * won.size)
            V[ri, k, pi], npay[ri, k, pi] = fd["payouts"][sl], fd["n_pay"][sl]
    return {"V": V, "npay": npay, "outcome": ev["outcome"].reshape(nr, n), "pass_t": ev["pass_t"].reshape(nr, n),
            "starts": starts}


def boot_means(x: np.ndarray, seed: int, draws: int = 5000, block: float = 252.0) -> np.ndarray:
    """Means of x over stationary-bootstrap resamples of the purchase days (neighbouring purchases overlap)."""
    idx = stationary_bootstrap(0, len(x), draws, len(x), block, np.random.default_rng(seed))
    return x[idx].mean(axis=1)


def interval(b: np.ndarray):
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def sharpe(r: np.ndarray) -> float:
    return float(r.mean() / r.std(ddof=1) * np.sqrt(252)) if r.std() > 0 else float("nan")


def main():
    print(f"spec {SPEC}")
    books = build_books()
    sel, keep, k1_start = m.load_k1()
    pol = m.select(sel)
    S_grid = m.skill_table(m.tuples()).net_sharpe.to_numpy()
    e_end, l_start = int(np.searchsorted(DAYS, EARLY_END)), int(np.searchsorted(DAYS, LATE_START))
    k1_mask = {"early": k1_start <= e_end, "late": k1_start >= l_start}
    ideal = {g: np.array([keep["V"][si][pol[(si, "FTG")]][mk].mean() for si in range(len(m.SKILL))]) for g, mk in k1_mask.items()}
    print("K1's idealised buyer by group of purchase days (FTG, selected policies):")
    print(pd.DataFrame(ideal, index=[str(s) for s in m.SKILL]).assign(net_sharpe=S_grid).round(2).T.to_string())
    span = {"early": slice(FIRST, e_end + WINDOW), "late": slice(l_start, len(DAYS))}
    rows, late_V, diffs = [], {}, {}
    for name, s in books.items():
        res = price(s)
        st = res["starts"]
        grp = {"early": st <= e_end, "late": st >= l_start}
        mean_early = res["V"][:, :, grp["early"]].mean(axis=2)
        ri, k = np.unravel_index(np.argmax(mean_early), mean_early.shape)
        gaps = np.diff(DAYS[s["entries"] > 0]).astype(int)
        print(f"\n{name}: {int(s['n_trades'])} trades, {int((s['n'] > 0).sum())} days with a position, up to {int(s['n'].max())} open at "
              f"once; longest spell without an entry {gaps.max()} calendar days; selected {R_EVAL[ri]:.2%} a trade in the "
              f"evaluation, {R_FUND[k]:.2%} funded")
        print("  V by evaluation risk (early purchases, selected funded risk):",
              {f"{r:.2%}": round(float(v), 1) for r, v in zip(R_EVAL, mean_early[:, k])})
        per = {}
        for g in ("early", "late"):
            mk = grp[g]
            v = res["V"][ri, k, mk]
            o, pt = res["outcome"][ri, mk], res["pass_t"][ri, mk]
            S = sharpe(s["R"][span[g]])
            v_id = float(np.interp(S, S_grid, ideal[g]))
            b = boot_means(v, seed=20261020 + len(rows))
            lo, hi = interval(b)
            per[g] = (v, b)
            rows.append({"book": name, "purchases": g, "n": int(mk.sum()), "net_sharpe": S,
                         "trades_per_year": int(s['n_trades']) / ((DAYS[-1] - DAYS[0]).astype(int) / 365.25),
                         "p_pass": (o == PASS).mean(), "months_p50": float(np.median(pt[o == PASS]) / 21) if (o == PASS).any() else np.nan,
                         "still_in_evaluation": (o == TIMEOUT).mean(), "p_payout": (res["npay"][ri, k, mk] > 0).mean(),
                         "V": v.mean(), "V_lo": lo, "V_hi": hi, "V_ideal_same_sharpe": v_id,
                         "V_minus_ideal_lo": lo - v_id, "V_minus_ideal_hi": hi - v_id})
        late_V[name] = per["late"]
        d = per["late"][1] - per["early"][1]                              # independent resamples of the two groups
        diffs[name] = (per["late"][0].mean() - per["early"][0].mean(), *interval(d))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "K9_real_books.csv", index=False)
    print("\n=== K9: real strategies through the Alpha Swing contract (FTG; policy selected on early purchases) ===")
    print(t.round(3).to_string(index=False))

    coin_late = float(ideal["late"][0])
    print("\n=== Hypotheses (late purchases; 95% intervals from a stationary bootstrap of the purchase days) ===")
    late = t[t.purchases == "late"].set_index("book")
    h19 = ["SUPPORTED" if r.V_minus_ideal_hi < 0 else "REFUTED" if r.V_minus_ideal_lo > 0 else "INCONCLUSIVE" for r in late.itertuples()]
    for (bk, r), v in zip(late.iterrows(), h19):
        print(f"  H19 {bk}: V ${r.V:.1f} [{r.V_lo:.1f}, {r.V_hi:.1f}] against ${r.V_ideal_same_sharpe:.1f} for an idealised buyer at "
              f"Sharpe {r.net_sharpe:+.2f}  {v}")
    print("  H19 overall:", "SUPPORTED" if all(x == "SUPPORTED" for x in h19) else "REFUTED" if "REFUTED" in h19 else "INCONCLUSIVE")
    best = late.V.idxmax()
    lo, hi = late.loc[best, "V_lo"], late.loc[best, "V_hi"]
    h20 = "SUPPORTED" if hi < coin_late else "REFUTED" if lo > coin_late else "INCONCLUSIVE"
    print(f"  H20 best book {best}: V ${late.loc[best, 'V']:.1f} [{lo:.1f}, {hi:.1f}] against the coin flip's ${coin_late:.1f}  {h20}")
    h21 = []
    for bk, (d, lo, hi) in diffs.items():
        h21.append("SUPPORTED" if hi < 0 else "REFUTED" if lo > 0 else "INCONCLUSIVE")
        print(f"  H21 {bk}: late minus early ${d:+.1f} [{lo:+.1f}, {hi:+.1f}]  {h21[-1]}")
    print("  H21 overall:", "SUPPORTED" if all(x == "SUPPORTED" for x in h21) else "REFUTED" if "REFUTED" in h21 else "INCONCLUSIVE")


if __name__ == "__main__":
    main()
