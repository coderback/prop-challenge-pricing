"""Exploratory (not pre-registered): K9 with the restricted regime's 1% cap read per position.

Amendment 5 (commit c87a97f) caps the risk of all open positions together at 1% of the initial balance once
funded. The firm's Focused Trader Group article says "the maximum allowable risk for any single position is 1% of
your initial balance". This run keeps everything in run_K9.py as registered and changes only that reading: each
open trade may risk up to 1%, and total notional stays capped at the smaller of 1.25 lots and 15 times the account.
The per-asset Max Risk Rule (3% at $10,000) is not added; two same-asset positions at 1% each stay below it.

    python research/info_K9_position_cap.py

Writes data/checks/K9_per_position/K9_real_books.csv; the registered table in data/checks/ is not touched.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location("run_K9", "research/run_K9.py")
k9 = importlib.util.module_from_spec(_spec)
sys.modules["run_K9"] = k9
_spec.loader.exec_module(k9)


def day_sources_per_position(s: dict):
    """As run_K9.day_sources, with the funded 1% cap applied to each open trade rather than to their sum."""
    has = s["n"] > 0
    R2 = np.stack([s["R"], np.zeros(len(k9.DAYS))], axis=1)
    L2 = np.stack([s["W"], np.zeros(len(k9.DAYS))], axis=1)
    v_eval = np.where(has, 1.0 / np.maximum(s["notional"], 1e-12), 1.0)
    lev_f = min(k9.LOT_FTG, k9.LEV_FTG)
    v_fund = np.where(has, np.minimum(lev_f * v_eval, 0.01) / lev_f, 1.0)
    return k9.DayTuples(k9.DAYS, has, R2, L2, v_eval), k9.DayTuples(k9.DAYS, has, R2, L2, v_fund), lev_f


FROZEN = Path("data/derived/K9_daily_series.npz")


def frozen_books() -> dict:
    """The five books' daily series exactly as the registered K9 run used them (13 October 2026), as shipped in
    the reproduction package. Rebuilding them today gives a slightly different A2b, because its swap costs are
    calibrated at the latest price in the data store."""
    from types import SimpleNamespace
    z = np.load(FROZEN)
    keys = ("R", "W", "n", "notional", "entries")
    return {b: SimpleNamespace(series={k: z[f"{b}|{k}"] for k in keys}, trades=range(int(z[f"{b}|n_trades"])))
            for b in ("A1b", "A2b", "M1r", "R3", "W3")}


if __name__ == "__main__":
    k9.SPEC = "EXPLORATORY: run_K9.py with the funded 1% cap per position (not pre-registered)"
    k9.day_sources = day_sources_per_position
    if hasattr(k9, "daily_series") and FROZEN.exists():        # research repository: use the registered series
        k9.build_books = frozen_books
        k9.daily_series = lambda ts: ts.series
    k9.OUT = Path("data/checks/K9_per_position")
    k9.OUT.mkdir(parents=True, exist_ok=True)
    k9.main()
