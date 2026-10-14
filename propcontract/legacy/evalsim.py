"""Mark-to-market evaluation simulator over real history (research/PREREGISTRATION_round2.md).

For each start date (every ``step``-th trading day) an account runs forward through the actual trade
paths with the firm's rules:
    daily floor  = 0.95 × balance at server midnight (floating P&L ignored at reset), checked on the
                   day's worst mark-to-market equity
    static floor = 90% of initial
    targets      = +10% (phase 1), then +5% on a fresh account (phase 2), reached at a day's close,
                   positions then flattened; at least 3 trading days per phase
    inactivity   = more than 30 calendar days without opening a trade fails the account; ``keepalive_days``
                   models a pre-registered token trade that resets the clock (it does not count towards
                   the 3 minimum trading days, and its cost is ignored)
Optional engine levels (the spec v1.4 §8.3 ladder, kept to reproduce rounds 2-6 and S1; spec v1.5 replaced it with
drawdown-scaled sizing, ``SimConfig.policy="drawdown"``): halve risk at 95% equity, no new trades at 93% (the account then
ends: flat and unable to recover), flatten at 92%; flatten when 60% of the daily allowance is lost.

Trade sizes: every trade risks r × initial × weight (R × weight is precomputed per trade and day).
Intraday lows of different positions are summed within a day: conservative for diversified books.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from propcontract.legacy.trades import TradeSet

TRADING_DAYS_PER_MONTH = 21


@dataclass
class SimConfig:
    r: float = 0.002
    engine_levels: bool = False
    horizon_days: int = 756          # 36 months of trading days
    phase_gap: int = 2
    initial: float = 10_000.0
    target_p1: float = 0.10
    target_p2: float = 0.05
    static_dd: float = 0.10
    daily_dd: float = 0.05
    min_days: int = 3
    inactivity_days: int = 30
    keepalive_days: int | None = None   # open a token trade (0.01 lot, P&L ignored) after this many idle days
    policy: str = "fixed"               # S1 risk policies: fixed | compound | drawdown | daily_budget


class Book:
    """Trade index for fast day-by-day lookups."""

    def __init__(self, ts: TradeSet, days: np.ndarray):
        self.ts = ts
        self.days = days.astype("datetime64[D]")
        self.day_pos = {d: i for i, d in enumerate(self.days.tolist())}
        d0 = ts.day0.astype("datetime64[D]")
        self.day0 = d0.view("int64")
        self.offsets = ts.offsets
        self.last_k = ts.lengths - 1
        self.close = ts.flat_close
        self.low = ts.flat_low
        entries: dict[int, list[int]] = {}
        for tid, d in enumerate(d0.tolist()):
            if d in self.day_pos:
                entries.setdefault(self.day_pos[d], []).append(tid)
        self.entries = {k: np.array(v, int) for k, v in entries.items()}


def policy_multiplier(cfg: SimConfig, eq_close: float, allowance: float, base: float, n_new: int) -> float:
    """Risk scaling for new trades (research/PREREGISTRATION_S1_sizing_policy.md). ``fixed`` and ``compound``
    return 1 (compound changes the base instead); ``drawdown`` shrinks risk linearly towards the static floor
    (never below 25%); ``daily_budget`` caps the day's new risk at 60% of the daily allowance."""
    ib = cfg.initial
    if cfg.policy == "drawdown":
        return min(1.0, max(0.25, (eq_close - (1 - cfg.static_dd) * ib) / (cfg.static_dd * ib)))
    if cfg.policy == "daily_budget" and n_new > 0 and base > 0:
        return min(1.0, 0.6 * allowance / (n_new * base))
    return 1.0


def run_one(book: Book, start: int, cfg: SimConfig) -> dict:
    ib = cfg.initial
    days = book.days
    dayint = days.view("int64")
    n_days = len(days)
    phase, targets = 0, (ib * (1 + cfg.target_p1), ib * (1 + cfg.target_p2))
    balance = ib
    open_t = np.zeros(0, int)
    open_m = np.zeros(0)
    traded_days = 0
    last_entry = dayint[start]
    phase_start = start
    eq_close = ib
    p1_day = None
    i = start
    end = min(n_days, start + cfg.horizon_days)
    while i < end:
        d = dayint[i]
        b_reset = balance
        d_floor = (1 - cfg.daily_dd) * b_reset
        allowance = cfg.daily_dd * b_reset
        # ---- new trades --------------------------------------------------------------------------
        mult = 1.0
        if cfg.engine_levels:
            if eq_close <= 0.93 * ib:
                if len(open_t) == 0:
                    return {"outcome": "halted_static_no_new", "days": i - start, "p1_day": p1_day}
                mult = 0.0
            elif eq_close <= 0.95 * ib:
                mult = 0.5
        new = book.entries.get(i)
        if new is not None and mult > 0 and i >= phase_start:
            base = cfg.r * (b_reset if cfg.policy == "compound" else ib)
            mult *= policy_multiplier(cfg, eq_close, allowance, base, len(new))
            open_t = np.concatenate([open_t, new])
            open_m = np.concatenate([open_m, np.full(len(new), base * mult)])
            traded_days += 1
            last_entry = d
        elif cfg.keepalive_days is not None and i >= phase_start and (d - last_entry) >= cfg.keepalive_days:
            last_entry = d                    # token trade keeps the account active; not a trading day
        # ---- today's marks ---------------------------------------------------------------------------
        if len(open_t):
            k = d - book.day0[open_t]
            k = np.minimum(k, book.last_k[open_t])
            idx = book.offsets[open_t] + k
            low = balance + float(np.dot(open_m, book.low[idx]))
            close_vals = book.close[idx]
            exiting = k >= book.last_k[open_t]
        else:
            low, close_vals, exiting = balance, np.zeros(0), np.zeros(0, bool)
        if low <= (1 - cfg.static_dd) * ib + 1e-9:
            return {"outcome": "breach_static", "days": i - start, "p1_day": p1_day}
        if low <= d_floor + 1e-9:
            return {"outcome": "breach_daily", "days": i - start, "p1_day": p1_day}
        if cfg.engine_levels:
            flat_at = None
            if low <= 0.92 * ib:
                flat_at = 0.92 * ib
            elif b_reset - low >= 0.6 * allowance:
                flat_at = b_reset - 0.6 * allowance
            if flat_at is not None and len(open_t):
                balance, eq_close = flat_at, flat_at
                open_t, open_m = np.zeros(0, int), np.zeros(0)
                i += 1
                continue
        # ---- exits and close-of-day equity -----------------------------------------------------------
        if len(open_t):
            balance += float(np.dot(open_m[exiting], close_vals[exiting]))
            keep = ~exiting
            open_t, open_m, close_vals = open_t[keep], open_m[keep], close_vals[keep]
            eq_close = balance + float(np.dot(open_m, close_vals))
        else:
            eq_close = balance
        # ---- target ----------------------------------------------------------------------------------------
        if eq_close >= targets[phase] - 1e-9 and traded_days >= cfg.min_days:
            if phase == 0:
                p1_day = i - start
                phase, balance, eq_close, traded_days = 1, ib, ib, 0
                open_t, open_m = np.zeros(0, int), np.zeros(0)
                phase_start = i + 1 + cfg.phase_gap
                last_entry = dayint[min(phase_start, n_days - 1)]
                i = phase_start
                continue
            return {"outcome": "pass", "days": i - start, "p1_day": p1_day}
        if (d - last_entry) > cfg.inactivity_days and i >= phase_start:
            return {"outcome": "inactivity", "days": i - start, "p1_day": p1_day}
        i += 1
    return {"outcome": "timeout" if end - start >= cfg.horizon_days else "censored", "days": end - start,
            "p1_day": p1_day}


def run_funded(book: Book, start: int, end: int, r_f: float, cfg: SimConfig, payout_every: int = 21,
               split: float = 0.80, min_profit: float = 0.02, best_day: float = 0.40) -> dict:
    """Funded (Qualified) account from index ``start`` to ``end``: fixed risk ``r_f`` × initial, static and daily
    floors, inactivity (with keep-alive). Every ``payout_every`` trading days, if flat with balance ≥ (1 +
    ``min_profit``) × initial and no single day since the last payout made more than ``best_day`` of the
    profit, withdraw ``split`` of the profit and reset the balance to initial."""
    ib = cfg.initial
    dayint = book.days.view("int64")
    balance, eq_prev, max_gain = ib, ib, 0.0
    open_t, open_m = np.zeros(0, int), np.zeros(0)
    payouts, n_pay, since = 0.0, 0, 0
    last_entry = dayint[start] if start < len(dayint) else 0
    out = lambda outcome, i: {"outcome": outcome, "payouts": payouts, "n_payouts": n_pay, "days": i - start}
    for i in range(start, min(end, len(dayint))):
        d = dayint[i]
        d_floor = (1 - cfg.daily_dd) * balance
        new = book.entries.get(i)
        if new is not None:
            open_t = np.concatenate([open_t, new])
            open_m = np.concatenate([open_m, np.full(len(new), r_f * ib)])
            last_entry = d
        elif cfg.keepalive_days is not None and (d - last_entry) >= cfg.keepalive_days:
            last_entry = d
        if len(open_t):
            k = np.minimum(d - book.day0[open_t], book.last_k[open_t])
            idx = book.offsets[open_t] + k
            low = balance + float(np.dot(open_m, book.low[idx]))
            close_vals = book.close[idx]
            exiting = k >= book.last_k[open_t]
            if low <= (1 - cfg.static_dd) * ib + 1e-9:
                return out("breach_static", i)
            if low <= d_floor + 1e-9:
                return out("breach_daily", i)
            balance += float(np.dot(open_m[exiting], close_vals[exiting]))
            keep = ~exiting
            open_t, open_m, close_vals = open_t[keep], open_m[keep], close_vals[keep]
            eq_close = balance + float(np.dot(open_m, close_vals))
        else:
            eq_close = balance
        max_gain = max(max_gain, eq_close - eq_prev)
        eq_prev = eq_close
        since += 1
        if since % payout_every == 0 and len(open_t) == 0:
            profit = balance - ib
            if profit >= min_profit * ib and max_gain <= best_day * profit:
                payouts += split * profit
                n_pay += 1
                balance, eq_prev, max_gain, since = ib, ib, 0.0, 0
        if (d - last_entry) > cfg.inactivity_days:
            return out("inactivity", i)
    return out("survived", min(end, len(dayint)))


def run_starts(book: Book, cfg: SimConfig, step: int = 5, first: int = 0, min_remaining: int = 504) -> pd.DataFrame:
    """Every ``step``-th trading day from ``first`` while ≥ ``min_remaining`` trading days remain."""
    rows = []
    last_start = len(book.days) - min_remaining
    for s in range(first, max(first, last_start), step):
        res = run_one(book, s, cfg)
        res["start"] = pd.Timestamp(book.days[s])
        rows.append(res)
    return pd.DataFrame(rows)


def summarize_starts(res: pd.DataFrame) -> dict:
    n = len(res)
    if n == 0:
        return {}
    months = res["days"] / TRADING_DAYS_PER_MONTH
    passed = res["outcome"] == "pass"
    out = {"starts": n,
           "p_pass_12m": float((passed & (months <= 12)).mean()),
           "p_pass_24m": float((passed & (months <= 24)).mean()),
           "p_pass_36m": float(passed.mean()),
           "p_breach": float(res["outcome"].str.startswith(("breach", "halted", "inactivity")).mean()),
           "p1_pass_rate": float(res["p1_day"].notna().mean()),
           "t_pass_p50_months": float(months[passed].median()) if passed.any() else np.nan}
    for k, v in res["outcome"].value_counts(normalize=True).items():
        out[f"out_{k}"] = float(v)
    return out


def daily_pnl(ts: TradeSet, days: np.ndarray) -> pd.Series:
    """Portfolio daily MTM P&L in units of R×weight (unit risk per trade), on the given trading days."""
    days = days.astype("datetime64[D]")
    out = np.zeros(len(days))
    dint = days.view("int64")
    pos = {d: i for i, d in enumerate(dint.tolist())}
    d0 = ts.day0.astype("datetime64[D]").view("int64")
    for t in range(len(d0)):
        o, L = ts.offsets[t], ts.lengths[t]
        path = ts.flat_close[o:o + L]
        inc = np.diff(np.r_[0.0, path])
        for k in np.flatnonzero(inc):
            j = pos.get(int(d0[t] + k))
            if j is not None:
                out[j] += inc[k]
            else:  # weekend/holiday mark: book on the next trading day
                nxt = np.searchsorted(dint, d0[t] + k)
                if nxt < len(out):
                    out[nxt] += inc[k]
    return pd.Series(out, index=pd.DatetimeIndex(days))
